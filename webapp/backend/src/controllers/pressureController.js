import { sendSuccess } from '../utils/response.js';

function safeDiv(num, den, mult = 1, digits = 2) {
  if (!den || den <= 0) return null;
  return Number(((num / den) * mult).toFixed(digits));
}

function buildCubeWhere(q, defaultFramework = null) {
  const where = {};
  const fw = q.framework || defaultFramework;
  if (fw && fw !== 'ALL') where.framework = fw;
  if (q.format && q.format !== 'ALL') where.matchFormat = q.format;
  if (q.season && q.season !== 'ALL') where.season = q.season;
  if (q.pressureLevel && q.pressureLevel !== 'ALL') where.pressureLevel = q.pressureLevel;
  if (q.innings) where.innings = q.innings;
  if (q.phase && q.phase !== 'ALL') where.matchPhase = q.phase;
  return where;
}

function aggregateCubeRows(rows) {
  const acc = {
    deliveriesCount: 0,
    legalBallsCount: 0,
    batterBallsFaced: 0,
    runsTotal: 0,
    batterRuns: 0,
    bowlerConcededRuns: 0,
    wicketsTotal: 0,
    bowlerWickets: 0,
    dotBallsBat: 0,
    dotBallsBowl: 0,
    boundaryBallsBat: 0,
    boundaryBallsBowl: 0,
    sumPressureIndex: 0,
    validPressureCount: 0,
    unavailableDeliveries: 0,
    highExtremeDeliveries: 0,
    sumRrr: 0,
    validRrrCount: 0,
    sumCrr: 0,
    validCrrCount: 0,
    sumRunsRemaining: 0,
    validRunsRemCount: 0,
    sumBallsRemaining: 0,
    validBallsRemCount: 0,
    sumWicketsLost: 0,
    sumWicketsInHand: 0,
    sumCumScore: 0,
    sumBallsElapsed: 0,
    bins: {
      modelC: new Array(20).fill(0),
      modelA: new Array(20).fill(0),
      modelB: new Array(20).fill(0),
    },
  };

  for (const r of rows) {
    acc.deliveriesCount += r.deliveriesCount;
    acc.legalBallsCount += r.legalBallsCount;
    acc.batterBallsFaced += r.batterBallsFaced;
    acc.runsTotal += r.runsTotal;
    acc.batterRuns += r.batterRuns;
    acc.bowlerConcededRuns += r.bowlerConcededRuns;
    acc.wicketsTotal += r.wicketsTotal;
    acc.bowlerWickets += r.bowlerWickets;
    acc.dotBallsBat += r.dotBallsBat;
    acc.dotBallsBowl += r.dotBallsBowl;
    acc.boundaryBallsBat += r.boundaryBallsBat;
    acc.boundaryBallsBowl += r.boundaryBallsBowl;
    acc.sumPressureIndex += r.sumPressureIndex;
    acc.validPressureCount += r.validPressureCount;
    if (r.pressureLevel === 'UNAVAILABLE') acc.unavailableDeliveries += r.deliveriesCount;
    if (r.pressureLevel === 'HIGH PRESSURE' || r.pressureLevel === 'EXTREME PRESSURE') {
      acc.highExtremeDeliveries += r.deliveriesCount;
    }
    acc.sumRrr += r.sumRrr;
    acc.validRrrCount += r.validRrrCount;
    acc.sumCrr += r.sumCrr;
    acc.validCrrCount += r.validCrrCount;
    acc.sumRunsRemaining += r.sumRunsRemaining;
    acc.validRunsRemCount += r.validRunsRemCount;
    acc.sumBallsRemaining += r.sumBallsRemaining;
    acc.validBallsRemCount += r.validBallsRemCount;
    acc.sumWicketsLost += r.sumWicketsLost;
    acc.sumWicketsInHand += r.sumWicketsInHand;
    acc.sumCumScore += r.sumCumScore;
    acc.sumBallsElapsed += r.sumBallsElapsed;

    const sb = r.scoreBinsJson;
    if (sb?.modelC) {
      for (let i = 0; i < 20; i += 1) {
        acc.bins.modelC[i] += sb.modelC[i] || 0;
        acc.bins.modelA[i] += sb.modelA?.[i] || 0;
        acc.bins.modelB[i] += sb.modelB?.[i] || 0;
      }
    }
  }

  return {
    totalDeliveries: acc.deliveriesCount,
    validPressureDeliveries: acc.validPressureCount,
    unavailableDeliveries: acc.unavailableDeliveries,
    highExtremeDeliveries: acc.highExtremeDeliveries,
    highExtremeSharePct: safeDiv(acc.highExtremeDeliveries, acc.validPressureCount, 100, 2),
    meanPressureIndex: safeDiv(acc.sumPressureIndex, acc.validPressureCount, 1, 2),
    contextMetrics: {
      meanRequiredRunRate: safeDiv(acc.sumRrr, acc.validRrrCount, 1, 2),
      meanCurrentRunRate: safeDiv(acc.sumCrr, acc.validCrrCount, 1, 2),
      meanRunsRemaining: safeDiv(acc.sumRunsRemaining, acc.validRunsRemCount, 1, 1),
      meanLegalBallsRemaining: safeDiv(acc.sumBallsRemaining, acc.validBallsRemCount, 1, 1),
      meanWicketsLost: safeDiv(acc.sumWicketsLost, acc.deliveriesCount, 1, 2),
      meanWicketsRemaining: safeDiv(acc.sumWicketsInHand, acc.deliveriesCount, 1, 2),
      meanCurrentScore: safeDiv(acc.sumCumScore, acc.deliveriesCount, 1, 1),
      meanLegalBallsElapsed: safeDiv(acc.sumBallsElapsed, acc.deliveriesCount, 1, 1),
    },
    outcomes: {
      battingStrikeRate: safeDiv(acc.batterRuns, acc.batterBallsFaced, 100, 2),
      battingDotBallPct: safeDiv(acc.dotBallsBat, acc.batterBallsFaced, 100, 2),
      battingBoundaryPct: safeDiv(acc.boundaryBallsBat, acc.batterBallsFaced, 100, 2),
      bowlingEconomy: safeDiv(acc.bowlerConcededRuns, acc.legalBallsCount, 6, 2),
      bowlingDotBallPct: safeDiv(acc.dotBallsBowl, acc.legalBallsCount, 100, 2),
      bowlingBoundaryConcededPct: safeDiv(acc.boundaryBallsBowl, acc.legalBallsCount, 100, 2),
      bowlingWicketFrequency: safeDiv(acc.bowlerWickets, acc.legalBallsCount, 100, 2),
    },
    bins: acc.bins,
  };
}

export function createPressureController(prisma) {
  return {
    async summary(req, res, next) {
      try {
        const q = req.validatedQuery;
        const baseWhere = buildCubeWhere(q, null);
        const rows = await prisma.pressureAnalyticsCube.findMany({ where: baseWhere });

        const byFramework = {};
        for (const fw of ['CHASE', 'FIRST_INNINGS', 'BOWLING', 'BATTING_COMBINED']) {
          const fwRows = rows.filter((r) => r.framework === fw);
          const agg = aggregateCubeRows(fwRows);
          const { bins: _omitBins, ...summaryMetrics } = agg;
          byFramework[fw] = summaryMetrics;
        }

        return sendSuccess(res, {
          filtersApplied: q,
          primaryModel: 'Model C (Context-Normalized LOMO)',
          unavailablePolicy:
            'Deliveries with missing DLS revised-overs metadata or Match 48610 corrupted revised_target are labeled UNAVAILABLE (NULL index) and never treated as LOW PRESSURE.',
          thresholds: {
            CHASE: { low: '< 32', moderate: '32–<50', high: '50–<74', extreme: '>= 74' },
            FIRST_INNINGS: { low: '< 30', moderate: '30–<45', high: '45–<61', extreme: '>= 61' },
            BOWLING: { low: '< 47', moderate: '47–<60', high: '60–<68', extreme: '>= 68' },
          },
          frameworks: byFramework,
        });
      } catch (err) {
        return next(err);
      }
    },

    async distribution(req, res, next) {
      try {
        const q = req.validatedQuery;
        const framework = q.framework && q.framework !== 'ALL' ? q.framework : 'BATTING_COMBINED';
        const where = buildCubeWhere(q, framework);
        const rows = await prisma.pressureAnalyticsCube.findMany({ where });

        const agg = aggregateCubeRows(rows);
        const histogram = agg.bins.modelC.map((countC, idx) => ({
          binLabel: `${idx * 5}–${(idx + 1) * 5}`,
          binStart: idx * 5,
          binEnd: (idx + 1) * 5,
          modelC: countC,
          modelA: agg.bins.modelA[idx],
          modelB: agg.bins.modelB[idx],
        }));

        const levelOrder = ['LOW PRESSURE', 'MODERATE PRESSURE', 'HIGH PRESSURE', 'EXTREME PRESSURE', 'UNAVAILABLE'];
        const byLevel = levelOrder.map((lvl) => {
          const lvlRows = rows.filter((r) => r.pressureLevel === lvl);
          const lvlAgg = aggregateCubeRows(lvlRows);
          return {
            pressureLevel: lvl,
            deliveries: lvlAgg.totalDeliveries,
            shareOfTotalPct: safeDiv(lvlAgg.totalDeliveries, agg.totalDeliveries, 100, 2),
            shareOfValidPct: lvl === 'UNAVAILABLE' ? null : safeDiv(lvlAgg.totalDeliveries, agg.validPressureDeliveries, 100, 2),
            meanPressureIndex: lvl === 'UNAVAILABLE' ? null : lvlAgg.meanPressureIndex,
            battingStrikeRate: lvlAgg.outcomes.battingStrikeRate,
            bowlingEconomy: lvlAgg.outcomes.bowlingEconomy,
          };
        });

        const phases = ['Powerplay', 'Middle', 'Death', 'Unavailable'];
        const byPhase = phases
          .map((ph) => {
            const phRows = rows.filter((r) => r.matchPhase === ph);
            if (phRows.length === 0) return null;
            const phAgg = aggregateCubeRows(phRows);
            return {
              matchPhase: ph,
              deliveries: phAgg.totalDeliveries,
              meanPressureIndex: phAgg.meanPressureIndex,
              highExtremeSharePct: phAgg.highExtremeSharePct,
            };
          })
          .filter(Boolean);

        const seasons = [...new Set(rows.map((r) => r.season))].sort();
        const bySeason = seasons.map((sn) => {
          const snRows = rows.filter((r) => r.season === sn);
          const snAgg = aggregateCubeRows(snRows);
          return {
            season: sn,
            deliveries: snAgg.totalDeliveries,
            meanPressureIndex: snAgg.meanPressureIndex,
            highExtremeSharePct: snAgg.highExtremeSharePct,
          };
        });

        return sendSuccess(res, {
          framework,
          filtersApplied: q,
          totalDeliveries: agg.totalDeliveries,
          validDeliveries: agg.validPressureDeliveries,
          unavailableDeliveries: agg.unavailableDeliveries,
          histogram,
          byLevel,
          byPhase,
          bySeason,
        });
      } catch (err) {
        return next(err);
      }
    },

    async models(req, res, next) {
      try {
        const { framework } = req.validatedQuery;
        const where = {
          summaryType: { in: ['MODEL_COMPARISON', 'COMPONENT_SUMMARY', 'DISTRIBUTION'] },
          ...(framework && framework !== 'ALL' ? { framework: { contains: framework, mode: 'insensitive' } } : {}),
        };
        const rows = await prisma.pressureSummary.findMany({ where });

        const modelComparison = rows
          .filter((r) => r.summaryType === 'MODEL_COMPARISON')
          .map((r) => ({
            ...r.payloadJson,
            isPrimaryFramework: String(r.segmentKey).includes('Model C'),
          }));
        const components = rows.filter((r) => r.summaryType === 'COMPONENT_SUMMARY').map((r) => r.payloadJson);
        const distributions = rows.filter((r) => r.summaryType === 'DISTRIBUTION').map((r) => r.payloadJson);

        return sendSuccess(res, {
          primaryModel: 'Model C (Context-Normalized LOMO - Primary)',
          modelComparison,
          components,
          distributions,
        });
      } catch (err) {
        return next(err);
      }
    },
  };
}

