import { buildPaginationMeta, resolveSort, sendSuccess } from '../utils/response.js';

const BATTING_RANK_SORTS = {
  rank: 'rank',
  finalRankingScore: 'finalRankingScore',
  performanceScore: 'performanceScore',
  reliabilityScore: 'reliabilityScore',
  evidenceScore: 'evidenceScore',
  ebPressureImpact: 'ebPressureImpact',
  pressureStrikeRate: 'pressureStrikeRate',
  pressureAverage: 'pressureAverage',
  pressureBallsFaced: 'pressureBallsFaced',
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

export function createBattingController(prisma) {
  return {
    async summary(req, res, next) {
      try {
        const q = req.validatedQuery;

        const perfWhere = {};
        if (q.role && q.role !== 'ALL') perfWhere.battingRole = q.role;
        if (q.playerId) perfWhere.playerId = q.playerId;

        const cubeWhere = { framework: 'BATTING_COMBINED' };
        if (q.format && q.format !== 'ALL') cubeWhere.matchFormat = q.format;
        if (q.season && q.season !== 'ALL') cubeWhere.season = q.season;
        if (q.pressureLevel && q.pressureLevel !== 'ALL') cubeWhere.pressureLevel = q.pressureLevel;
        if (q.innings) cubeWhere.innings = q.innings;
        if (q.phase && q.phase !== 'ALL') cubeWhere.matchPhase = q.phase;

        const [allBatters, eligibleRel, cubeRows, seasonRows] = await Promise.all([
          prisma.playerBattingPerformance.findMany({
            where: perfWhere,
            include: {
              player: {
                select: {
                  displayName: true,
                  inIpl: true,
                  inT20i: true,
                  battingReliability: true,
                  battingRanking: {
                    select: { rank: true, isTop10: true, finalRankingScore: true, stabilityTier: true },
                  },
                },
              },
            },
          }),
          prisma.playerBattingReliability.count({ where: { isPrimaryEligible: true } }),
          prisma.pressureAnalyticsCube.findMany({ where: cubeWhere }),
          prisma.playerSeasonPerformance.findMany({
            where: {
              discipline: 'batting',
              ...(q.season && q.season !== 'ALL' ? { seasonYear: Number(q.season) } : {}),
              ...(q.playerId ? { playerId: q.playerId } : {}),
            },
          }),
        ]);

        // Optional competition filter at player level
        const filteredBatters = allBatters.filter((b) => {
          if (q.format === 'IPL') return b.pressureIplBf > 0;
          if (q.format === 'T20I') return b.pressureT20iBf > 0;
          return true;
        });

        const totalPressureRuns = filteredBatters.reduce((s, b) => s + b.pressureRuns, 0);
        const totalPressureBalls = filteredBatters.reduce((s, b) => s + b.pressureBallsFaced, 0);
        const eligibleFiltered = filteredBatters.filter((b) => b.player?.battingReliability?.isPrimaryEligible);
        const medianPressureSr = median(eligibleFiltered.map((b) => b.pressureStrikeRate));

        const highExtCube = cubeRows.filter(
          (r) => r.pressureLevel === 'HIGH PRESSURE' || r.pressureLevel === 'EXTREME PRESSURE'
        );
        const highExtremeExposures = highExtCube.reduce((s, r) => s + r.deliveriesCount, 0);

        // Metrics by pressure category from cube
        const tierOrder = ['LOW PRESSURE', 'MODERATE PRESSURE', 'HIGH PRESSURE', 'EXTREME PRESSURE'];
        const byPressureCategory = tierOrder.map((lvl) => {
          const subset = cubeRows.filter((r) => r.pressureLevel === lvl);
          const bf = subset.reduce((s, r) => s + r.batterBallsFaced, 0);
          const runs = subset.reduce((s, r) => s + r.batterRuns, 0);
          const wkts = subset.reduce((s, r) => s + r.wicketsTotal, 0);
          const dots = subset.reduce((s, r) => s + r.dotBallsBat, 0);
          const bnd = subset.reduce((s, r) => s + r.boundaryBallsBat, 0);
          return {
            pressureLevel: lvl,
            ballsFaced: bf,
            runs,
            dismissals: wkts,
            strikeRate: safeDiv(runs, bf, 100, 2),
            average: safeDiv(runs, wkts, 1, 2),
            dotBallPct: safeDiv(dots, bf, 100, 2),
            boundaryPct: safeDiv(bnd, bf, 100, 2),
          };
        });

        // Performance vs Reliability scatter (eligible cohort)
        const scatter = eligibleFiltered.map((b) => ({
          playerId: b.playerId,
          playerName: b.playerName,
          role: b.battingRole,
          performanceScore: b.player?.battingReliability?.performanceScore ?? null,
          reliabilityScore: b.player?.battingReliability?.reliabilityScore ?? null,
          evidenceScore: b.player?.battingReliability?.evidenceStrengthScore ?? null,
          ebPressureImpact: b.player?.battingReliability?.ebPressureImpact ?? null,
          pressureBallsFaced: b.pressureBallsFaced,
          pressureStrikeRate: b.pressureStrikeRate,
          rank: b.player?.battingRanking?.rank ?? null,
          isTop10: b.player?.battingRanking?.isTop10 ?? false,
        }));

        // Pressure vs Non-Pressure comparison (eligible cohort)
        const pVsNp = {
          eligiblePlayers: eligibleFiltered.length,
          medianPressureSr: median(eligibleFiltered.map((b) => b.pressureStrikeRate)),
          medianNonPressureSr: median(eligibleFiltered.map((b) => b.nonpressureStrikeRate)),
          medianPressureBoundaryPct: median(eligibleFiltered.map((b) => b.pressureBoundaryPct)),
          medianNonPressureBoundaryPct: median(eligibleFiltered.map((b) => b.nonpressureBoundaryPct)),
          medianPressureDotPct: median(eligibleFiltered.map((b) => b.pressureDotBallPct)),
          medianNonPressureDotPct: median(eligibleFiltered.map((b) => b.nonpressureDotBallPct)),
        };

        // Seasonal trends
        const seasonMap = new Map();
        for (const sr of seasonRows) {
          const entry = seasonMap.get(sr.seasonYear) || { seasonYear: sr.seasonYear, balls: 0, runs: 0, dismissals: 0, players: 0 };
          entry.balls += sr.pressureBalls;
          entry.runs += sr.pressureRunsOrConceded;
          entry.dismissals += sr.pressureDismissalsOrWkts;
          entry.players += 1;
          seasonMap.set(sr.seasonYear, entry);
        }
        const seasonalTrends = Array.from(seasonMap.values())
          .sort((a, b) => a.seasonYear - b.seasonYear)
          .map((e) => ({
            seasonYear: e.seasonYear,
            playersExposed: e.players,
            pressureBalls: e.balls,
            pressureRuns: e.runs,
            strikeRate: safeDiv(e.runs, e.balls, 100, 2),
            average: safeDiv(e.runs, e.dismissals, 1, 2),
          }));

        return sendSuccess(res, {
          filtersApplied: q,
          kpis: {
            battersAnalyzed: filteredBatters.length,
            eligibleBatters: q.role || q.format || q.playerId ? eligibleFiltered.length : eligibleRel,
            totalPressureRuns,
            totalPressureBallsFaced: totalPressureBalls,
            medianPressureStrikeRate: medianPressureSr,
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

        const orderBy = resolveSort(q.sortBy, q.sortOrder, BATTING_RANK_SORTS, 'rank', 'asc');
        const skip = (q.page - 1) * q.limit;

        const [total, items] = await Promise.all([
          prisma.battingRanking.count({ where }),
          prisma.battingRanking.findMany({
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

