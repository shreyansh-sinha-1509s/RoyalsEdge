import { buildBattingExplanation, buildBowlingExplanation } from '../utils/explanation.js';
import { AppError, buildPaginationMeta, resolveSort, sendSuccess } from '../utils/response.js';

const PLAYER_SORTS = {
  displayName: 'displayName',
  playerId: 'playerId',
  primaryBallsFaced: 'primaryBallsFaced',
  primaryLegalBallsBowled: 'primaryLegalBallsBowled',
  matchesInPlayingEleven: 'matchesInPlayingEleven',
};

export function createPlayersController(prisma) {
  return {
    async list(req, res, next) {
      try {
        const q = req.validatedQuery;
        const where = {};

        if (q.discipline === 'batting') {
          where.battingPerformance = { isNot: null };
        } else if (q.discipline === 'bowling') {
          where.bowlingPerformance = { isNot: null };
        }

        if (q.search) {
          const maybeId = Number(q.search);
          where.OR = [
            { displayName: { contains: q.search, mode: 'insensitive' } },
            { teamNames: { contains: q.search, mode: 'insensitive' } },
            ...(Number.isInteger(maybeId) ? [{ playerId: maybeId }] : []),
          ];
        }

        if (q.competition === 'IPL') where.inIpl = true;
        if (q.competition === 'T20I') where.inT20i = true;

        if (q.role && q.role !== 'ALL') {
          if (q.discipline === 'batting') {
            where.battingPerformance = { battingRole: q.role };
          } else if (q.discipline === 'bowling') {
            where.bowlingPerformance = { bowlingRole: q.role };
          } else {
            where.inferredPlayingRole = q.role;
          }
        }

        if (q.evidenceTier && q.evidenceTier !== 'ALL') {
          if (q.discipline === 'batting') {
            where.battingReliability = { evidenceTier: q.evidenceTier };
          } else if (q.discipline === 'bowling') {
            where.bowlingReliability = { evidenceTier: q.evidenceTier };
          } else {
            where.AND = [
              ...(where.AND || []),
              {
                OR: [
                  { battingReliability: { evidenceTier: q.evidenceTier } },
                  { bowlingReliability: { evidenceTier: q.evidenceTier } },
                ],
              },
            ];
          }
        }

        if (q.eligibleOnly) {
          if (q.discipline === 'batting') {
            where.battingRanking = { isNot: null };
          } else if (q.discipline === 'bowling') {
            where.bowlingRanking = { isNot: null };
          } else {
            where.AND = [
              ...(where.AND || []),
              { OR: [{ battingRanking: { isNot: null } }, { bowlingRanking: { isNot: null } }] },
            ];
          }
        }

        const orderBy = resolveSort(q.sortBy, q.sortOrder, PLAYER_SORTS, 'matchesInPlayingEleven', 'desc');
        const skip = (q.page - 1) * q.limit;

        const [total, players] = await Promise.all([
          prisma.player.count({ where }),
          prisma.player.findMany({
            where,
            orderBy,
            skip,
            take: q.limit,
            include: {
              battingPerformance: {
                select: {
                  battingRole: true,
                  pressureRuns: true,
                  pressureBallsFaced: true,
                  pressureStrikeRate: true,
                  pressureMatches: true,
                },
              },
              bowlingPerformance: {
                select: {
                  bowlingRole: true,
                  paceOrSpin: true,
                  pressureLegalBalls: true,
                  pressureWickets: true,
                  pressureEconomy: true,
                  pressureMatches: true,
                },
              },
              battingReliability: {
                select: {
                  evidenceTier: true,
                  isPrimaryEligible: true,
                  ebPressureImpact: true,
                  reliabilityScore: true,
                  evidenceStrengthScore: true,
                },
              },
              bowlingReliability: {
                select: {
                  evidenceTier: true,
                  isPrimaryEligible: true,
                  ebPressureImpact: true,
                  reliabilityScore: true,
                  evidenceStrengthScore: true,
                },
              },
              battingRanking: {
                select: { rank: true, isTop10: true, finalRankingScore: true, stabilityTier: true },
              },
              bowlingRanking: {
                select: { rank: true, isTop10: true, finalRankingScore: true, stabilityTier: true },
              },
            },
          }),
        ]);

        return sendSuccess(res, players, buildPaginationMeta(q.page, q.limit, total));
      } catch (err) {
        return next(err);
      }
    },

    async profile(req, res, next) {
      try {
        const { playerId } = req.validatedParams;
        const player = await prisma.player.findUnique({
          where: { playerId },
          include: {
            battingPerformance: true,
            bowlingPerformance: true,
            battingReliability: true,
            bowlingReliability: true,
            battingRanking: true,
            bowlingRanking: true,
            pressureExposures: true,
          },
        });

        if (!player) {
          throw new AppError(404, 'PLAYER_NOT_FOUND', `No player found with player_id=${playerId}.`);
        }

        const seasons = await prisma.playerSeasonPerformance.findMany({
          where: { playerId },
          select: { seasonYear: true, discipline: true },
          orderBy: { seasonYear: 'asc' },
        });
        const seasonsRepresented = [...new Set(seasons.map((s) => s.seasonYear))];

        const disciplines = [];
        if (player.battingPerformance) disciplines.push('batting');
        if (player.bowlingPerformance) disciplines.push('bowling');

        return sendSuccess(res, {
          overview: {
            playerId: player.playerId,
            displayName: player.displayName,
            teamNames: player.teamNames,
            disciplines,
            inferredPlayingRole: player.inferredPlayingRole,
            battingRole: player.battingPerformance?.battingRole ?? null,
            bowlingRole: player.bowlingPerformance?.bowlingRole ?? null,
            battingType: player.battingType,
            bowlingType: player.bowlingType,
            paceOrSpin: player.paceOrSpin,
            everWk: player.everWk,
            everCaptain: player.everCaptain,
            competitionExposure:
              player.inIpl && player.inT20i ? 'IPL + T20I' : player.inIpl ? 'IPL Only' : player.inT20i ? 'T20I Only' : 'Excluded / None',
            inIpl: player.inIpl,
            inT20i: player.inT20i,
            seasonsRepresented,
            sharesNameWithOtherId: player.sharesNameWithOtherId,
            matchesInPlayingEleven: player.matchesInPlayingEleven,
          },
          rankings: {
            batting: player.battingRanking,
            bowling: player.bowlingRanking,
          },
          exposures: player.pressureExposures,
          explanations: {
            batting: buildBattingExplanation(player.battingPerformance, player.battingReliability, player.battingRanking),
            bowling: buildBowlingExplanation(player.bowlingPerformance, player.bowlingReliability, player.bowlingRanking),
          },
        });
      } catch (err) {
        return next(err);
      }
    },

    async performance(req, res, next) {
      try {
        const { playerId } = req.validatedParams;
        const { discipline } = req.validatedQuery;

        const player = await prisma.player.findUnique({
          where: { playerId },
          select: {
            playerId: true,
            displayName: true,
            battingPerformance: true,
            bowlingPerformance: true,
            battingReliability: { select: { rawPressureImpact: true, ebPressureImpact: true, ebShrinkageWeight: true, ebKMatchesPrior: true } },
            bowlingReliability: { select: { rawPressureImpact: true, ebPressureImpact: true, ebShrinkageWeight: true, ebKMatchesPrior: true } },
          },
        });

        if (!player) {
          throw new AppError(404, 'PLAYER_NOT_FOUND', `No player found with player_id=${playerId}.`);
        }

        const breakdowns = await prisma.playerPressureBreakdown.findMany({
          where: {
            playerId,
            ...(discipline && discipline !== 'all' ? { discipline } : {}),
          },
        });

        return sendSuccess(res, {
          playerId: player.playerId,
          displayName: player.displayName,
          batting:
            !discipline || discipline === 'all' || discipline === 'batting'
              ? {
                  summary: player.battingPerformance,
                  shrinkage: player.battingReliability,
                  pressureBreakdown: breakdowns.filter((b) => b.discipline === 'batting'),
                }
              : null,
          bowling:
            !discipline || discipline === 'all' || discipline === 'bowling'
              ? {
                  summary: player.bowlingPerformance,
                  shrinkage: player.bowlingReliability,
                  pressureBreakdown: breakdowns.filter((b) => b.discipline === 'bowling'),
                }
              : null,
        });
      } catch (err) {
        return next(err);
      }
    },

    async reliability(req, res, next) {
      try {
        const { playerId } = req.validatedParams;
        const { discipline } = req.validatedQuery;

        const player = await prisma.player.findUnique({
          where: { playerId },
          select: {
            playerId: true,
            displayName: true,
            battingReliability: true,
            bowlingReliability: true,
            battingRanking: {
              select: {
                rank: true,
                isTop10: true,
                finalRankingScore: true,
                mcRankP05: true,
                mcRankMedian: true,
                mcRankP95: true,
                mcProbTop10Pct: true,
                methodsInTop10OutOf8: true,
                stabilityTier: true,
              },
            },
            bowlingRanking: {
              select: {
                rank: true,
                isTop10: true,
                finalRankingScore: true,
                mcRankP05: true,
                mcRankMedian: true,
                mcRankP95: true,
                mcProbTop10Pct: true,
                methodsInTop10OutOf8: true,
                stabilityTier: true,
              },
            },
          },
        });

        if (!player) {
          throw new AppError(404, 'PLAYER_NOT_FOUND', `No player found with player_id=${playerId}.`);
        }

        return sendSuccess(res, {
          playerId: player.playerId,
          displayName: player.displayName,
          nullPolicyNote:
            'reliabilityScore is intentionally NULL (never imputed as 0) when evidenceTier is INSUFFICIENT_EVIDENCE.',
          batting:
            !discipline || discipline === 'all' || discipline === 'batting'
              ? { reliability: player.battingReliability, rankingUncertainty: player.battingRanking }
              : null,
          bowling:
            !discipline || discipline === 'all' || discipline === 'bowling'
              ? { reliability: player.bowlingReliability, rankingUncertainty: player.bowlingRanking }
              : null,
        });
      } catch (err) {
        return next(err);
      }
    },

    async trends(req, res, next) {
      try {
        const { playerId } = req.validatedParams;
        const { discipline } = req.validatedQuery;

        const player = await prisma.player.findUnique({
          where: { playerId },
          select: {
            playerId: true,
            displayName: true,
            battingPerformance: {
              select: {
                pressureInn1Bf: true,
                pressureInn1Runs: true,
                pressureInn1Sr: true,
                pressureChaseBf: true,
                pressureChaseRuns: true,
                pressureChaseSr: true,
                pressurePowerplayBf: true,
                pressurePowerplaySr: true,
                pressureMiddleBf: true,
                pressureMiddleSr: true,
                pressureDeathBf: true,
                pressureDeathSr: true,
              },
            },
            bowlingPerformance: {
              select: {
                pressureInn1Lb: true,
                pressureInn1Wkts: true,
                pressureInn1Econ: true,
                pressureInn2Lb: true,
                pressureInn2Wkts: true,
                pressureInn2Econ: true,
                pressurePowerplayLb: true,
                pressurePowerplayEcon: true,
                pressureMiddleLb: true,
                pressureMiddleEcon: true,
                pressureDeathLb: true,
                pressureDeathEcon: true,
              },
            },
          },
        });

        if (!player) {
          throw new AppError(404, 'PLAYER_NOT_FOUND', `No player found with player_id=${playerId}.`);
        }

        const [seasons, breakdowns] = await Promise.all([
          prisma.playerSeasonPerformance.findMany({
            where: {
              playerId,
              ...(discipline && discipline !== 'all' ? { discipline } : {}),
            },
            orderBy: { seasonYear: 'asc' },
          }),
          prisma.playerPressureBreakdown.findMany({
            where: {
              playerId,
              pressureLevel: { in: ['HIGH PRESSURE', 'EXTREME PRESSURE'] },
              ...(discipline && discipline !== 'all' ? { discipline } : {}),
            },
          }),
        ]);

        return sendSuccess(res, {
          playerId: player.playerId,
          displayName: player.displayName,
          seasonTrends: seasons,
          highAndExtremeSplits: breakdowns,
          inningsAndPhaseSplits: {
            batting: player.battingPerformance,
            bowling: player.bowlingPerformance,
          },
        });
      } catch (err) {
        return next(err);
      }
    },

    async compare(req, res, next) {
      try {
        const { discipline, playerIds } = req.validatedQuery;

        const uniqueIds = [...new Set(playerIds)];
        if (uniqueIds.length < 2 || uniqueIds.length > 4) {
          throw new AppError(400, 'INVALID_COMPARISON', 'Compare requires between 2 and 4 distinct player IDs.');
        }

        const players = await prisma.player.findMany({
          where: { playerId: { in: uniqueIds } },
          include: {
            battingPerformance: discipline === 'batting',
            bowlingPerformance: discipline === 'bowling',
            battingReliability: discipline === 'batting',
            bowlingReliability: discipline === 'bowling',
            battingRanking: discipline === 'batting',
            bowlingRanking: discipline === 'bowling',
            pressureExposures: { where: { discipline } },
            pressureBreakdowns: { where: { discipline } },
            seasonPerformances: { where: { discipline }, orderBy: { seasonYear: 'asc' } },
          },
        });

        if (players.length !== uniqueIds.length) {
          const found = new Set(players.map((p) => p.playerId));
          const missing = uniqueIds.filter((id) => !found.has(id));
          throw new AppError(404, 'PLAYER_NOT_FOUND', `Player ID(s) not found: ${missing.join(', ')}`);
        }

        // Enforce strict same-discipline availability (do not compare a pure bowler in batting mode if no batting data)
        const noDisciplineData = players.filter((p) =>
          discipline === 'batting' ? !p.battingPerformance : !p.bowlingPerformance
        );
        if (noDisciplineData.length > 0) {
          throw new AppError(
            400,
            'DISCIPLINE_MISMATCH',
            `Selected player(s) have no ${discipline} records and cannot be compared in ${discipline} mode: ${noDisciplineData.map((p) => `${p.displayName} (${p.playerId})`).join(', ')}.`
          );
        }

        const ballsList = players.map((p) =>
          discipline === 'batting' ? p.battingPerformance.pressureBallsFaced : p.bowlingPerformance.pressureLegalBalls
        );
        const maxBalls = Math.max(...ballsList);
        const minBalls = Math.min(...ballsList);
        const substantialSampleGap = maxBalls > 0 && minBalls < maxBalls * 0.5;

        const ordered = uniqueIds.map((id) => players.find((p) => p.playerId === id));
        const compared = ordered.map((p) => {
          const perf = discipline === 'batting' ? p.battingPerformance : p.bowlingPerformance;
          const rel = discipline === 'batting' ? p.battingReliability : p.bowlingReliability;
          const ranking = discipline === 'batting' ? p.battingRanking : p.bowlingRanking;
          const balls = discipline === 'batting' ? perf.pressureBallsFaced : perf.pressureLegalBalls;
          return {
            playerId: p.playerId,
            displayName: p.displayName,
            teamNames: p.teamNames,
            sharesNameWithOtherId: p.sharesNameWithOtherId,
            role: discipline === 'batting' ? perf.battingRole : perf.bowlingRole,
            pressureBalls: balls,
            smallerSampleFlag: maxBalls > 0 && balls < maxBalls * 0.5,
            performance: perf,
            reliability: rel,
            ranking,
            exposure: p.pressureExposures[0] || null,
            pressureBreakdown: p.pressureBreakdowns,
            seasonTrends: p.seasonPerformances,
          };
        });

        return sendSuccess(res, {
          discipline,
          sampleSizeWarning: substantialSampleGap
            ? `Substantial sample-size difference detected (${minBalls} vs ${maxBalls} pressure balls). Interpret rate and reliability comparisons alongside 95% confidence intervals.`
            : null,
          maxPressureBalls: maxBalls,
          minPressureBalls: minBalls,
          players: compared,
        });
      } catch (err) {
        return next(err);
      }
    },
  };
}

