import { SOURCE_FILES } from '../config/paths.js';
import { cleanCell, readCsvRecords, toFloat, toInt } from '../utils/csvParser.js';

const SCORE_TOLERANCE = 0.015; // Submission CSV rounds composite scores to 2 decimal places
const IMPACT_TOLERANCE = 0.025;
const RELIABILITY_TOLERANCE = 0.055;

const SHARED_NAME_PLAYER_IDS = [4722, 20172, 6922, 7446, 7338, 28756];

function approxEqual(a, b, tol) {
  if (a === null || a === undefined || b === null || b === undefined) return false;
  return Math.abs(Number(a) - Number(b)) <= tol;
}

/**
 * Pure comparison helper comparing DB Top 10 rows against official Phase 6 submission CSV.
 */
export function compareTop10AgainstSubmission(dbTop10, submissionCsvPath, discipline) {
  const discrepancies = [];
  const subRows = readCsvRecords(submissionCsvPath, ['rank', 'player_id', 'player_name', 'final_ranking_score']);

  if (subRows.length !== 10) {
    discrepancies.push(`${discipline}: Official submission CSV has ${subRows.length} rows (expected 10).`);
  }
  if (dbTop10.length !== 10) {
    discrepancies.push(`${discipline}: Database returned ${dbTop10.length} Top-10 rows (expected 10).`);
  }

  const impactCol = discipline === 'batting' ? 'eb_pressure_impact_per_100b' : 'eb_pressure_impact_per_24b';
  const count = Math.min(subRows.length, dbTop10.length);

  for (let i = 0; i < count; i += 1) {
    const csvRow = subRows[i];
    const dbRow = dbTop10[i];
    const expectedRank = toInt(csvRow.rank);
    const expectedId = toInt(csvRow.player_id);
    const expectedName = cleanCell(csvRow.player_name);
    const expectedScore = toFloat(csvRow.final_ranking_score);
    const expectedImpact = toFloat(csvRow[impactCol]);
    const expectedRel = toFloat(csvRow.reliability_score);

    if (dbRow.rank !== expectedRank) {
      discrepancies.push(`${discipline} pos ${i + 1}: rank mismatch (DB=${dbRow.rank}, CSV=${expectedRank})`);
    }
    if (dbRow.playerId !== expectedId) {
      discrepancies.push(`${discipline} rank #${expectedRank}: player_id mismatch (DB=${dbRow.playerId}, CSV=${expectedId})`);
    }
    if (dbRow.playerName !== expectedName) {
      discrepancies.push(`${discipline} rank #${expectedRank}: player_name mismatch (DB=${dbRow.playerName}, CSV=${expectedName})`);
    }
    if (!approxEqual(dbRow.finalRankingScore, expectedScore, SCORE_TOLERANCE)) {
      discrepancies.push(
        `${discipline} rank #${expectedRank} (${expectedName}): score mismatch (DB=${dbRow.finalRankingScore}, CSV=${expectedScore})`
      );
    }
    if (!approxEqual(dbRow.ebPressureImpact, expectedImpact, IMPACT_TOLERANCE)) {
      discrepancies.push(
        `${discipline} rank #${expectedRank} (${expectedName}): EB impact mismatch (DB=${dbRow.ebPressureImpact}, CSV=${expectedImpact})`
      );
    }
    if (!approxEqual(dbRow.reliabilityScore, expectedRel, RELIABILITY_TOLERANCE)) {
      discrepancies.push(
        `${discipline} rank #${expectedRank} (${expectedName}): reliability mismatch (DB=${dbRow.reliabilityScore}, CSV=${expectedRel})`
      );
    }
  }

  return {
    discipline,
    submissionCount: subRows.length,
    dbTop10Count: dbTop10.length,
    exactMatch: discrepancies.length === 0,
    discrepancies,
  };
}

/**
 * Full database reconciliation check against official Phase 3–6 counts & submission CSVs.
 */
export async function runDataReconciliation(prisma) {
  const discrepancies = [];

  const [
    playersCount,
    batPerfCount,
    bowlPerfCount,
    batRelCount,
    bowlRelCount,
    batRankCount,
    bowlRankCount,
    matchesCount,
    inningsCount,
    methodologyCount,
    dbBatTop10,
    dbBowlTop10,
    badBatNullRel,
    badBowlNullRel,
    sharedNamePlayers,
    cubeBattingSum,
    cubeBowlingSum,
  ] = await Promise.all([
    prisma.player.count(),
    prisma.playerBattingPerformance.count(),
    prisma.playerBowlingPerformance.count(),
    prisma.playerBattingReliability.count(),
    prisma.playerBowlingReliability.count(),
    prisma.battingRanking.count(),
    prisma.bowlingRanking.count(),
    prisma.match.count(),
    prisma.innings.count(),
    prisma.methodologySection.count(),
    prisma.battingRanking.findMany({ where: { isTop10: true }, orderBy: { rank: 'asc' } }),
    prisma.bowlingRanking.findMany({ where: { isTop10: true }, orderBy: { rank: 'asc' } }),
    prisma.playerBattingReliability.count({
      where: { evidenceTier: 'INSUFFICIENT_EVIDENCE', reliabilityScore: { not: null } },
    }),
    prisma.playerBowlingReliability.count({
      where: { evidenceTier: 'INSUFFICIENT_EVIDENCE', reliabilityScore: { not: null } },
    }),
    prisma.player.findMany({
      where: { playerId: { in: SHARED_NAME_PLAYER_IDS } },
      select: { playerId: true, displayName: true, sharesNameWithOtherId: true },
    }),
    prisma.pressureAnalyticsCube.aggregate({
      where: { framework: 'BATTING_COMBINED' },
      _sum: { deliveriesCount: true },
    }),
    prisma.pressureAnalyticsCube.aggregate({
      where: { framework: 'BOWLING' },
      _sum: { deliveriesCount: true },
    }),
  ]);

  const expected = {
    players: 1217,
    battingPerformance: 824,
    bowlingPerformance: 596,
    battingReliability: 824,
    bowlingReliability: 596,
    battingRankings: 173,
    bowlingRankings: 165,
    matches: 853,
    innings: 1652,
    methodologySections: 20,
    deliveries: 193988,
  };

  const actual = {
    players: playersCount,
    battingPerformance: batPerfCount,
    bowlingPerformance: bowlPerfCount,
    battingReliability: batRelCount,
    bowlingReliability: bowlRelCount,
    battingRankings: batRankCount,
    bowlingRankings: bowlRankCount,
    matches: matchesCount,
    innings: inningsCount,
    methodologySections: methodologyCount,
    cubeBattingDeliveries: cubeBattingSum?._sum?.deliveriesCount ?? 0,
    cubeBowlingDeliveries: cubeBowlingSum?._sum?.deliveriesCount ?? 0,
  };

  for (const [key, expVal] of Object.entries(expected)) {
    if (key === 'deliveries') {
      if (actual.cubeBattingDeliveries !== expVal) {
        discrepancies.push(`Cube batting deliveries mismatch: DB=${actual.cubeBattingDeliveries}, expected=${expVal}`);
      }
      if (actual.cubeBowlingDeliveries !== expVal) {
        discrepancies.push(`Cube bowling deliveries mismatch: DB=${actual.cubeBowlingDeliveries}, expected=${expVal}`);
      }
    } else if (actual[key] !== expVal) {
      discrepancies.push(`Table count mismatch for ${key}: DB=${actual[key]}, expected=${expVal}`);
    }
  }

  if (badBatNullRel > 0) {
    discrepancies.push(`NULL reliability violation: ${badBatNullRel} INSUFFICIENT_EVIDENCE batting rows have non-null reliability_score.`);
  }
  if (badBowlNullRel > 0) {
    discrepancies.push(`NULL reliability violation: ${badBowlNullRel} INSUFFICIENT_EVIDENCE bowling rows have non-null reliability_score.`);
  }
  if (sharedNamePlayers.length !== SHARED_NAME_PLAYER_IDS.length) {
    discrepancies.push(`Shared-name identity check: found ${sharedNamePlayers.length}/${SHARED_NAME_PLAYER_IDS.length} distinct shared-name player_ids.`);
  }

  const battingTop10Check = compareTop10AgainstSubmission(dbBatTop10, SOURCE_FILES.submissionTop10Batters, 'batting');
  const bowlingTop10Check = compareTop10AgainstSubmission(dbBowlTop10, SOURCE_FILES.submissionTop10Bowlers, 'bowling');

  discrepancies.push(...battingTop10Check.discrepancies, ...bowlingTop10Check.discrepancies);

  return {
    passed: discrepancies.length === 0,
    checkedAt: new Date().toISOString(),
    counts: actual,
    nullReliabilityPreserved: badBatNullRel === 0 && badBowlNullRel === 0,
    sharedPlayerIdsPreserved: sharedNamePlayers.length === SHARED_NAME_PLAYER_IDS.length,
    battingTop10Check,
    bowlingTop10Check,
    discrepancies,
  };
}

