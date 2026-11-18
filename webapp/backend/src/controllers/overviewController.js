import { appCache } from '../config/cache.js';
import { sendSuccess } from '../utils/response.js';

export function createOverviewController(prisma) {
  return {
    async health(_req, res, next) {
      try {
        await prisma.$queryRaw`SELECT 1`;
        const lastImport = await prisma.dataImportLog.findFirst({
          where: { status: 'SUCCESS' },
          orderBy: { completedAt: 'desc' },
          select: { batchId: true, completedAt: true, insertedCount: true, reconcilePassed: true },
        });
        return sendSuccess(res, {
          status: 'ok',
          service: 'royalsedge-api',
          database: 'connected',
          uptimeSeconds: Math.round(process.uptime()),
          timestamp: new Date().toISOString(),
          lastSuccessfulImport: lastImport,
        });
      } catch (err) {
        return next(err);
      }
    },

    async overview(_req, res, next) {
      try {
        const data = await appCache.getOrSet('overview', async () => {
          const [
            totalPlayers,
            battersAnalyzed,
            bowlersAnalyzed,
            eligibleBatters,
            eligibleBowlers,
            totalMatches,
            matchesWithBallData,
            totalInnings,
            cubeDeliveries,
            top10Batters,
            top10Bowlers,
            pressureLevelRows,
          ] = await Promise.all([
            prisma.player.count(),
            prisma.playerBattingPerformance.count(),
            prisma.playerBowlingPerformance.count(),
            prisma.battingRanking.count(),
            prisma.bowlingRanking.count(),
            prisma.match.count(),
            prisma.match.count({ where: { hasBallData: true } }),
            prisma.innings.count(),
            prisma.pressureAnalyticsCube.aggregate({
              where: { framework: 'BATTING_COMBINED' },
              _sum: { deliveriesCount: true },
            }),
            prisma.battingRanking.findMany({
              where: { isTop10: true },
              orderBy: { rank: 'asc' },
              select: {
                rank: true,
                playerId: true,
                playerName: true,
                role: true,
                competitionContext: true,
                finalRankingScore: true,
                performanceScore: true,
                reliabilityScore: true,
                evidenceScore: true,
                ebPressureImpact: true,
                pressureStrikeRate: true,
                pressureBallsFaced: true,
                uniqueMatches: true,
                mcProbTop10Pct: true,
                stabilityTier: true,
              },
            }),
            prisma.bowlingRanking.findMany({
              where: { isTop10: true },
              orderBy: { rank: 'asc' },
              select: {
                rank: true,
                playerId: true,
                playerName: true,
                role: true,
                paceOrSpin: true,
                competitionContext: true,
                finalRankingScore: true,
                performanceScore: true,
                reliabilityScore: true,
                evidenceScore: true,
                ebPressureImpact: true,
                pressureEconomy: true,
                pressureWickets: true,
                pressureLegalBalls: true,
                uniqueMatches: true,
                mcProbTop10Pct: true,
                stabilityTier: true,
              },
            }),
            prisma.pressureSummary.findMany({
              where: { summaryType: 'LEVEL_SUMMARY' },
            }),
          ]);

          return {
            brand: {
              name: 'RoyalsEdge',
              subtitle: 'IPL 2027 Performance & Auction Intelligence Platform',
              tagline: 'Beyond the Numbers. Inside the Pressure.',
              description:
                'IPL 2027 Performance & Auction Intelligence Platform uncovering the players who deliver when the pressure is highest.',
              disclaimer:
                'Independent historical analytics project (SupeRR Selector Season 2). Not an official Rajasthan Royals product.',
            },
            snapshot: {
              deliveries: cubeDeliveries?._sum?.deliveriesCount ?? 193988,
              matchesWithBallData,
              totalEligibleMatches: totalMatches,
              innings: totalInnings,
              totalPlayers,
              battersAnalyzed,
              bowlersAnalyzed,
              eligibleBatters,
              eligibleBowlers,
              seasonsCoverage: '2022–2026',
              formats: ['IPL', 'T20I'],
              primaryPressureModel: 'Model C (Context-Normalized LOMO)',
            },
            top10Batters,
            top10Bowlers,
            pressureLevels: pressureLevelRows.map((r) => r.payloadJson),
            pipelineStages: [
              { step: 1, title: 'Raw Data', slug: 'dataset-description-source-files', detail: '200,999 raw deliveries audited across 6 competition CSVs' },
              { step: 2, title: 'Data Cleaning', slug: 'data-cleaning-quality-controls', detail: '193,988 eligible IPL & T20I regular deliveries; zero reconciliation diffs' },
              { step: 3, title: 'Pressure Modeling', slug: 'pressure-framework-model-c-selection', detail: 'Pre-delivery Model C LOMO indices (Chase, First Innings, Bowling)' },
              { step: 4, title: 'Player Performance', slug: 'batting-performance-methodology', detail: 'Context-adjusted RVAE/RSAE + Empirical Bayes shrinkage' },
              { step: 5, title: 'Reliability', slug: 'reliability-evidence-scoring', detail: 'Volume-free variance-stabilized consistency + match-clustered bootstrap CIs' },
              { step: 6, title: 'Final Rankings', slug: 'ranking-model-composite-score-formula', detail: 'Balanced Primary (50/25/15/10) ordered Top 10 Batters & Bowlers' },
            ],
          };
        });

        return sendSuccess(res, data);
      } catch (err) {
        return next(err);
      }
    },
  };
}

