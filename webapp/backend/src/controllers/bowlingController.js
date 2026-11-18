import { buildPaginationMeta, resolveSort, sendSuccess } from '../utils/response.js';

const BOWLING_RANK_SORTS = {
  rank: 'rank',
  finalRankingScore: 'finalRankingScore',
  performanceScore: 'performanceScore',
  reliabilityScore: 'reliabilityScore',
  evidenceScore: 'evidenceScore',
  ebPressureImpact: 'ebPressureImpact',
  pressureEconomy: 'pressureEconomy',
  pressureWickets: 'pressureWickets',
  pressureLegalBalls: 'pressureLegalBalls',
  uniqueMatches: 'uniqueMatches',
  mcProbTop10Pct: 'mcProbTop10Pct',
};

function median(values) {
  const clean = values.filter((v) => v !== null && v !== undefined && Number.isFinite(v)).sort((a, b) => a - b);
  if (clean.length === 0) return null;
  const mid = Math.floor(clean.length / 2);
  return clean.length % 2 === 0 ? Number(((clean[mid - 1] + clean[mid]) / 2).toFixed(2)) : Number(clean[mid].toFixed(2));
}

function safeDiv(num, den, mult = 1, digits = 2) {
  if (!den || den <= 0) return null;
  return Number(((num / den) * mult).toFixed(digits));
}

export function createBowlingController(prisma) {
  return {
    async summary(req, res, next) {
      try {
        const q = req.validatedQuery;

        const perfWhere = {};
        if (q.role && q.role !== 'ALL') perfWhere.bowlingRole = q.role;
        if (q.paceOrSpin && q.paceOrSpin !== 'ALL') perfWhere.paceOrSpin = q.paceOrSpin;
        if (q.playerId) perfWhere.playerId = q.playerId;

        const cubeWhere = { framework: 'BOWLING' };
        if (q.format && q.format !== 'ALL') cubeWhere.matchFormat = q.format;
        if (q.season && q.season !== 'ALL') cubeWhere.season = q.season;
        if (q.pressureLevel && q.pressureLevel !== 'ALL') cubeWhere.pressureLevel = q.pressureLevel;
        if (q.innings) cubeWhere.innings = q.innings;
        if (q.phase && q.phase !== 'ALL') cubeWhere.matchPhase = q.phase;

        const [allBowlers, eligibleRel, cubeRows, seasonRows] = await Promise.all([
          prisma.playerBowlingPerformance.findMany({
            where: perfWhere,
            include: {
              player: {
                select: {
                  displayName: true,
                  inIpl: true,
                  inT20i: true,
                  bowlingReliability: true,
                  bowlingRanking: {
                    select: { rank: true, isTop10: true, finalRankingScore: true, stabilityTier: true },
                  },
                },
              },
            },
          }),
          prisma.playerBowlingReliability.count({ where: { isPrimaryEligible: true } }),
          prisma.pressureAnalyticsCube.findMany({ where: cubeWhere }),
          prisma.playerSeasonPerformance.findMany({
            where: {
              discipline: 'bowling',
              ...(q.season && q.season !== 'ALL' ? { seasonYear: Number(q.season) } : {}),
              ...(q.playerId ? { playerId: q.playerId } : {}),
            },
          }),
        ]);

        const filteredBowlers = allBowlers.filter((b) => {
          if (q.format === 'IPL') return b.pressureIplLb > 0;
          if (q.format === 'T20I') return b.pressureT20iLb > 0;
          return true;
        });

        const totalPressureLegalBalls = filteredBowlers.reduce((s, b) => s + b.pressureLegalBalls, 0);
        const totalPressureWickets = filteredBowlers.reduce((s, b) => s + b.pressureWickets, 0);
        const eligibleFiltered = filteredBowlers.filter((b) => b.player?.bowlingReliability?.isPrimaryEligible);
        const medianPressureEcon = median(eligibleFiltered.map((b) => b.pressureEconomy));

        const highExtCube = cubeRows.filter(
          (r) => r.pressureLevel === 'HIGH PRESSURE' || r.pressureLevel === 'EXTREME PRESSURE'
        );
        const highExtremeExposures = highExtCube.reduce((s, r) => s + r.deliveriesCount, 0);

        const tierOrder = ['LOW PRESSURE', 'MODERATE PRESSURE', 'HIGH PRESSURE', 'EXTREME PRESSURE'];
        const byPressureCategory = tierOrder.map((lvl) => {
          const subset = cubeRows.filter((r) => r.pressureLevel === lvl);
          const lb = subset.reduce((s, r) => s + r.legalBallsCount, 0);
          const runs = subset.reduce((s, r) => s + r.bowlerConcededRuns, 0);
          const wkts = subset.reduce((s, r) => s + r.bowlerWickets, 0);
          const dots = subset.reduce((s, r) => s + r.dotBallsBowl, 0);
          const bnd = subset.reduce((s, r) => s + r.boundaryBallsBowl, 0);
          return {
            pressureLevel: lvl,
            legalBalls: lb,
            runsConceded: runs,
            wickets: wkts,
            economy: safeDiv(runs, lb, 6, 2),
            wicketFrequencyPct: safeDiv(wkts, lb, 100, 2),
            dotBallPct: safeDiv(dots, lb, 100, 2),
            boundaryConcededPct: safeDiv(bnd, lb, 100, 2),
          };
        });

        const scatter = eligibleFiltered.map((b) => ({
          playerId: b.playerId,
          playerName: b.playerName,
          role: b.bowlingRole,
          paceOrSpin: b.paceOrSpin,
          performanceScore: b.player?.bowlingReliability?.performanceScore ?? null,
          reliabilityScore: b.player?.bowlingReliability?.reliabilityScore ?? null,
          evidenceScore: b.player?.bowlingReliability?.evidenceStrengthScore ?? null,
          ebPressureImpact: b.player?.bowlingReliability?.ebPressureImpact ?? null,
          pressureLegalBalls: b.pressureLegalBalls,
          pressureEconomy: b.pressureEconomy,
          pressureWickets: b.pressureWickets,
          rank: b.player?.bowlingRanking?.rank ?? null,
          isTop10: b.player?.bowlingRanking?.isTop10 ?? false,
        }));

        const pVsNp = {
          eligiblePlayers: eligibleFiltered.length,
          medianPressureEcon: median(eligibleFiltered.map((b) => b.pressureEconomy)),
          medianNonPressureEcon: median(eligibleFiltered.map((b) => b.nonpressureEconomy)),
          medianPressureDotPct: median(eligibleFiltered.map((b) => b.pressureDotBallPct)),
          medianNonPressureDotPct: median(eligibleFiltered.map((b) => b.nonpressureDotBallPct)),
          medianPressureBoundaryPct: median(eligibleFiltered.map((b) => b.pressureBoundaryConcededPct)),
          medianNonPressureBoundaryPct: median(eligibleFiltered.map((b) => b.nonpressureBoundaryConcededPct)),
        };

        const seasonMap = new Map();
        for (const sr of seasonRows) {
          const entry = seasonMap.get(sr.seasonYear) || { seasonYear: sr.seasonYear, balls: 0, runs: 0, wickets: 0, players: 0 };
          entry.balls += sr.pressureBalls;
          entry.runs += sr.pressureRunsOrConceded;
          entry.wickets += sr.pressureDismissalsOrWkts;
          entry.players += 1;
          seasonMap.set(sr.seasonYear, entry);
        }
        const seasonalTrends = Array.from(seasonMap.values())
          .sort((a, b) => a.seasonYear - b.seasonYear)
          .map((e) => ({
            seasonYear: e.seasonYear,
            playersExposed: e.players,
            pressureLegalBalls: e.balls,
            pressureWickets: e.wickets,
            economy: safeDiv(e.runs, e.balls, 6, 2),
            wicketFrequencyPct: safeDiv(e.wickets, e.balls, 100, 2),
          }));

        return sendSuccess(res, {
          filtersApplied: q,
          kpis: {
            bowlersAnalyzed: filteredBowlers.length,
            eligibleBowlers: q.role || q.paceOrSpin || q.format || q.playerId ? eligibleFiltered.length : eligibleRel,
            totalPressureLegalBalls,
            totalPressureWickets,
            medianPressureEconomy: medianPressureEcon,
            highExtremeExposures,
          },
          byPressureCategory,
          pressureVsNonPressure: pVsNp,
          performanceVsReliabilityScatter: scatter,
          seasonalTrends,
        });
      } catch (err) {
        return next(err);
      }
    },

    async rankings(req, res, next) {
      try {
        const q = req.validatedQuery;
        const where = {};
        if (q.top10Only) where.isTop10 = true;
        if (q.role && q.role !== 'ALL') where.role = q.role;
        if (q.paceOrSpin && q.paceOrSpin !== 'ALL') where.paceOrSpin = q.paceOrSpin;
        if (q.competition && q.competition !== 'ALL') where.competitionContext = q.competition;
        if (q.stabilityTier && q.stabilityTier !== 'ALL') where.stabilityTier = q.stabilityTier;
        if (q.evidenceTier && q.evidenceTier !== 'ALL') where.evidenceTier = q.evidenceTier;
        if (q.search) {
          where.OR = [
            { playerName: { contains: q.search, mode: 'insensitive' } },
            { role: { contains: q.search, mode: 'insensitive' } },
            { teamContext: { contains: q.search, mode: 'insensitive' } },
          ];
        }

        const orderBy = resolveSort(q.sortBy, q.sortOrder, BOWLING_RANK_SORTS, 'rank', 'asc');
        const skip = (q.page - 1) * q.limit;

        const [total, items] = await Promise.all([
          prisma.bowlingRanking.count({ where }),
          prisma.bowlingRanking.findMany({
            where,
            orderBy,
            skip,
            take: q.limit,
          }),
        ]);

        return sendSuccess(res, items, buildPaginationMeta(q.page, q.limit, total));
      } catch (err) {
        return next(err);
      }
    },
  };
}

