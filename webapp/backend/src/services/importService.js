import crypto from 'node:crypto';
import fs from 'node:fs';
import { SOURCE_FILES } from '../config/paths.js';
import {
  cleanCell,
  readCsvRecords,
  streamCsvIndexed,
  toBool,
  toDate,
  toFloat,
  toInt,
  toNullableBool,
  toNullableFloat,
  toNullableInt,
  validateCsvHeaders,
} from '../utils/csvParser.js';
import { runDataReconciliation } from './reconcileService.js';

export const EXPECTED_COUNTS = {
  players: 1217,
  battingPerformance: 824,
  bowlingPerformance: 596,
  battingReliability: 824,
  bowlingReliability: 596,
  pressureExposure: 1420,
  battingBreakdowns: 2239,
  bowlingBreakdowns: 2037,
  seasonPerformance: 3008,
  battingRankings: 173,
  bowlingRankings: 165,
  matches: 853,
  innings: 1652,
  primaryDeliveries: 193988,
  methodologySections: 20,
};

let importLockActive = false;

export function isImportRunning() {
  return importLockActive;
}

function emptyBins() {
  return {
    modelC: new Array(20).fill(0),
    modelA: new Array(20).fill(0),
    modelB: new Array(20).fill(0),
  };
}

function addToBin(arr, score) {
  if (score === null || score === undefined || Number.isNaN(score)) return;
  const idx = Math.max(0, Math.min(19, Math.floor(score / 5)));
  arr[idx] += 1;
}

function parseMethodologySections(mdPath) {
  if (!fs.existsSync(mdPath)) {
    throw new Error(`Required methodology markdown missing: ${mdPath}`);
  }
  const raw = fs.readFileSync(mdPath, 'utf8');
  const lines = raw.split(/\r?\n/);
  const sections = [];
  let current = null;

  for (const line of lines) {
    const match = line.match(/^##\s+(\d+)\.\s+(.+)$/);
    if (match) {
      if (current) sections.push(current);
      const sectionNumber = Number(match[1]);
      const title = match[2].trim();
      const slug = title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
      current = { sectionNumber, slug, title, bodyLines: [] };
    } else if (current) {
      current.bodyLines.push(line);
    }
  }
  if (current) sections.push(current);

  return sections.map((sec) => {
    const contentMd = sec.bodyLines.join('\n').trim();
    const firstNonEmpty = sec.bodyLines.find((l) => l.trim() && !l.trim().startsWith('|') && !l.trim().startsWith('#')) || sec.title;
    const summary = firstNonEmpty.replace(/\*\*/g, '').replace(/`/g, '').trim().slice(0, 280);
    const formulas = sec.bodyLines
      .filter((l) => l.includes('=') && (l.includes('`') || l.includes('0.')))
      .map((l) => l.replace(/`/g, '').trim())
      .slice(0, 5);
    return {
      sectionNumber: sec.sectionNumber,
      slug: sec.slug,
      title: sec.title,
      summary,
      contentMd,
      formulasJson: formulas.length > 0 ? formulas : null,
    };
  });
}

/**
 * Validates all required source files & headers upfront before writing anything to PostgreSQL.
 */
export function validateAllSourceFiles() {
  const checks = [
    [SOURCE_FILES.playerMaster, ['player_id', 'standardized_display_name', 'in_ipl', 'in_t20i', 'shares_name_with_other_player_id']],
    [SOURCE_FILES.battingPerformance, ['player_id', 'player_name', 'batting_role', 'pressure_runs', 'pressure_balls_faced', 'pressure_strike_rate']],
    [SOURCE_FILES.bowlingPerformance, ['player_id', 'player_name', 'bowling_role', 'pressure_legal_balls', 'pressure_wickets', 'pressure_economy']],
    [SOURCE_FILES.battingReliability, ['player_id', 'evidence_tier', 'is_primary_eligible', 'eb_pressure_impact', 'reliability_score', 'evidence_strength_score']],
    [SOURCE_FILES.bowlingReliability, ['player_id', 'evidence_tier', 'is_primary_eligible', 'eb_pressure_impact', 'reliability_score', 'evidence_strength_score']],
    [SOURCE_FILES.pressureExposure, ['discipline', 'player_id', 'pressure_balls', 'extreme_pressure_balls', 'high_pressure_balls']],
    [SOURCE_FILES.pressureVsNonPressure, ['discipline', 'player_id', 'context_impact_diff_p_minus_np', 'ci95_excludes_zero']],
    [SOURCE_FILES.battingPressureBreakdown, ['player_id', 'pressure_level', 'runs', 'balls_faced', 'strike_rate']],
    [SOURCE_FILES.bowlingPressureBreakdown, ['player_id', 'pressure_level', 'runs_conceded', 'legal_balls', 'economy_rate']],
    [SOURCE_FILES.seasonPerformance, ['discipline', 'player_id', 'season_year', 'pressure_balls', 'primary_rate', 'net_impact_rate']],
    [SOURCE_FILES.finalBattingRankings, ['player_id', 'rank', 'final_ranking_score', 'performance_score', 'reliability_score', 'evidence_strength_score']],
    [SOURCE_FILES.finalBowlingRankings, ['player_id', 'rank', 'final_ranking_score', 'performance_score', 'reliability_score', 'evidence_strength_score']],
    [SOURCE_FILES.cleanMatches, ['match_id', 'comp_id', 'comp_name', 'match_format', 'season', 'match_date', 'home_team', 'away_team']],
    [SOURCE_FILES.pressureMatchSummary, ['match_id', 'mean_i1_pressure', 'mean_chase_pressure', 'mean_bowling_pressure']],
    [SOURCE_FILES.inningsSummary, ['match_id', 'innings', 'batting_team_id', 'bowling_team_id', 'total_runs', 'wickets', 'legal_deliveries']],
    [SOURCE_FILES.pressureInningsSummary, ['match_id', 'innings', 'mean_batting_pressure', 'mean_bowling_pressure']],
    [SOURCE_FILES.pressureDeliveries, ['match_format', 'season', 'innings', 'match_phase', 'chase_pressure_level', 'first_innings_pressure_level', 'bowling_pressure_level', 'batting_pressure_level']],
    [SOURCE_FILES.top10OverlapAnalysis, ['discipline', 'player_id', 'methods_in_top10_out_of_8', 'stability_classification']],
    [SOURCE_FILES.pressureLevelSummary, ['framework', 'pressure_level', 'deliveries']],
    [SOURCE_FILES.pressureDistribution, ['framework', 'column', 'valid_deliveries', 'mean']],
    [SOURCE_FILES.pressureModelComparison, ['framework', 'model', 'valid_n', 'mean', 'spearman_corr_with_model_c']],
    [SOURCE_FILES.pressureExposureSummary, ['dimension', 'segment', 'total_deliveries']],
    [SOURCE_FILES.pressureComponentSummary, ['framework', 'component', 'nominal_weight']],
    [SOURCE_FILES.rankingRobustness, ['discipline', 'robustness_test', 'spearman_corr_vs_primary', 'top10_overlap_pct']],
    [SOURCE_FILES.rankingMethodComparison, ['discipline', 'approach', 'weights_perf_rel_ext_evid']],
    [SOURCE_FILES.rankingThresholdSensitivity, ['discipline', 'min_pressure_balls', 'eligible_candidates_at_cutoff']],
    [SOURCE_FILES.shortlistAlternatives, ['discipline', 'audit_group', 'player_id', 'player_name']],
    [SOURCE_FILES.submissionTop10Batters, ['rank', 'player_id', 'player_name', 'final_ranking_score']],
    [SOURCE_FILES.submissionTop10Bowlers, ['rank', 'player_id', 'player_name', 'final_ranking_score']],
  ];

  for (const [filePath, headers] of checks) {
    validateCsvHeaders(filePath, headers);
  }
  if (!fs.existsSync(SOURCE_FILES.methodologyReportMd)) {
    throw new Error(`Required methodology markdown missing: ${SOURCE_FILES.methodologyReportMd}`);
  }
  return { validatedFiles: checks.length + 1 };
}

/**
 * Streams pressure_deliveries.csv (193,988 rows) into a compact additive OLAP cube.
 */
export async function buildPressureAnalyticsCube() {
  const map = new Map();

  function getBucket(framework, matchFormat, season, innings, matchPhase, pressureLevel) {
    const key = `${framework}|${matchFormat}|${season}|${innings}|${matchPhase}|${pressureLevel}`;
    let bucket = map.get(key);
    if (!bucket) {
      bucket = {
        framework,
        matchFormat,
        season,
        innings,
        matchPhase,
        pressureLevel,
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
        scoreBinsJson: emptyBins(),
      };
      map.set(key, bucket);
    }
    return bucket;
  }

  function accumulate(bucket, row, c, modelCScore, modelAScore, modelBScore) {
    const isLegal = toBool(row[c.is_legal_delivery]);
    const isBf = toBool(row[c.is_batter_ball_faced]);
    const totalRuns = toInt(row[c.total_runs]);
    const batRuns = toInt(row[c.batter_runs]);
    const bowlRuns = toInt(row[c.bowler_conceded_runs]);
    const isWkt = toBool(row[c.is_wicket_event]);
    const isBowlWkt = toBool(row[c.is_bowler_wicket]);
    const isBoundary = toBool(row[c.is_four]) || toBool(row[c.is_six]);

    bucket.deliveriesCount += 1;
    if (isLegal) bucket.legalBallsCount += 1;
    if (isBf) bucket.batterBallsFaced += 1;
    bucket.runsTotal += totalRuns;
    bucket.batterRuns += batRuns;
    bucket.bowlerConcededRuns += bowlRuns;
    if (isWkt) bucket.wicketsTotal += 1;
    if (isBowlWkt) bucket.bowlerWickets += 1;
    if (isBf && batRuns === 0) bucket.dotBallsBat += 1;
    if (isLegal && bowlRuns === 0) bucket.dotBallsBowl += 1;
    if (isBf && isBoundary) bucket.boundaryBallsBat += 1;
    if (isLegal && isBoundary) bucket.boundaryBallsBowl += 1;

    if (modelCScore !== null) {
      bucket.sumPressureIndex += modelCScore;
      bucket.validPressureCount += 1;
      addToBin(bucket.scoreBinsJson.modelC, modelCScore);
    }
    if (modelAScore !== null) addToBin(bucket.scoreBinsJson.modelA, modelAScore);
    if (modelBScore !== null) addToBin(bucket.scoreBinsJson.modelB, modelBScore);

    const rrr = toNullableFloat(row[c.required_run_rate_before]);
    if (rrr !== null) {
      bucket.sumRrr += rrr;
      bucket.validRrrCount += 1;
    }
    const crr = toNullableFloat(row[c.current_run_rate_before]);
    if (crr !== null) {
      bucket.sumCrr += crr;
      bucket.validCrrCount += 1;
    }
    const runsRem = toNullableFloat(row[c.runs_remaining_before]);
    if (runsRem !== null) {
      bucket.sumRunsRemaining += runsRem;
      bucket.validRunsRemCount += 1;
    }
    const ballsRem = toNullableFloat(row[c.legal_balls_remaining_before]);
    if (ballsRem !== null) {
      bucket.sumBallsRemaining += ballsRem;
      bucket.validBallsRemCount += 1;
    }

    bucket.sumWicketsLost += toFloat(row[c.wickets_before]);
    bucket.sumWicketsInHand += toFloat(row[c.wickets_in_hand_before]);
    bucket.sumCumScore += toFloat(row[c.cum_score_before]);
    bucket.sumBallsElapsed += toFloat(row[c.legal_balls_before]);
  }

  const totalDeliveries = await streamCsvIndexed(
    SOURCE_FILES.pressureDeliveries,
    [
      'match_format', 'season', 'innings', 'match_phase',
      'chase_pressure_level', 'first_innings_pressure_level', 'bowling_pressure_level', 'batting_pressure_level',
    ],
    (row, c) => {
      const format = cleanCell(row[c.eligibility_category]) || cleanCell(row[c.match_format]) || 'UNKNOWN';
      const season = cleanCell(row[c.season]) || 'UNKNOWN';
      const innings = toInt(row[c.innings], 1);
      const phase = cleanCell(row[c.match_phase]) || 'Unavailable';

      if (innings === 2) {
        const chaseLvl = cleanCell(row[c.chase_pressure_level]) || 'UNAVAILABLE';
        accumulate(
          getBucket('CHASE', format, season, innings, phase, chaseLvl),
          row,
          c,
          toNullableFloat(row[c.chase_pressure_index]),
          toNullableFloat(row[c.model_a_chase_pressure]),
          toNullableFloat(row[c.model_b_chase_pressure])
        );
      } else if (innings === 1) {
        const i1Lvl = cleanCell(row[c.first_innings_pressure_level]) || 'UNAVAILABLE';
        accumulate(
          getBucket('FIRST_INNINGS', format, season, innings, phase, i1Lvl),
          row,
          c,
          toNullableFloat(row[c.first_innings_pressure_index]),
          toNullableFloat(row[c.model_a_first_innings_pressure]),
          toNullableFloat(row[c.model_b_first_innings_pressure])
        );
      }

      const batLvl = cleanCell(row[c.batting_pressure_level]) || 'UNAVAILABLE';
      const batModelA =
        innings === 2
          ? toNullableFloat(row[c.model_a_chase_pressure])
          : toNullableFloat(row[c.model_a_first_innings_pressure]);
      const batModelB =
        innings === 2
          ? toNullableFloat(row[c.model_b_chase_pressure])
          : toNullableFloat(row[c.model_b_first_innings_pressure]);
      accumulate(
        getBucket('BATTING_COMBINED', format, season, innings, phase, batLvl),
        row,
        c,
        toNullableFloat(row[c.batting_pressure_index]),
        batModelA,
        batModelB
      );

      const bowlLvl = cleanCell(row[c.bowling_pressure_level]) || 'UNAVAILABLE';
      accumulate(
        getBucket('BOWLING', format, season, innings, phase, bowlLvl),
        row,
        c,
        toNullableFloat(row[c.bowling_pressure_index]),
        toNullableFloat(row[c.model_a_bowling_pressure]),
        toNullableFloat(row[c.model_b_bowling_pressure])
      );
    }
  );

  return { totalDeliveries, cubeRows: Array.from(map.values()) };
}

/**
 * Loads, parses, and validates every verified Phase 2–6 CSV dataset in memory
 * before writing anything to PostgreSQL. Pure read-only preparation step.
 */
export async function prepareAllDatasets({ includeCube = true } = {}) {
  validateAllSourceFiles();

  // 1. Players (1,217)
  const rawPlayers = readCsvRecords(SOURCE_FILES.playerMaster);
  const playerIdSet = new Set();
  const players = rawPlayers.map((r) => {
    const playerId = toNullableInt(r.player_id);
    if (playerId === null) throw new Error('Invalid null player_id in player_master.csv');
    if (playerIdSet.has(playerId)) throw new Error(`Duplicate player_id ${playerId} in player_master.csv`);
    playerIdSet.add(playerId);
    return {
      playerId,
      displayName: cleanCell(r.standardized_display_name) || `Player ${playerId}`,
      mappingSourceNames: cleanCell(r.mapping_source_names),
      ballFeedSourceNames: cleanCell(r.ball_feed_source_names),
      teamNames: cleanCell(r.team_names),
      inIpl: toBool(r.in_ipl),
      inT20i: toBool(r.in_t20i),
      inExcludedComp: toBool(r.in_excluded_non_ipl_t20),
      inPrimaryEligibleComp: toBool(r.in_primary_eligible_comp),
      primaryBallsFaced: toInt(r.primary_balls_faced),
      primaryLegalBallsBowled: toInt(r.primary_legal_balls_bowled),
      matchesInPlayingEleven: toInt(r.matches_in_playing_eleven),
      battingType: cleanCell(r.batting_type),
      bowlingType: cleanCell(r.bowling_type),
      paceOrSpin: cleanCell(r.pace_or_spin),
      everWk: toBool(r.ever_wk),
      everCaptain: toBool(r.ever_captain),
      inferredPlayingRole: cleanCell(r.inferred_playing_role),
      nameMismatchSources: toBool(r.name_mismatch_between_sources),
      sharesNameWithOtherId: toBool(r.shares_name_with_other_player_id),
    };
  });

  // 2. Batting Performance (824)
  const battingPerformance = readCsvRecords(SOURCE_FILES.battingPerformance).map((r) => ({
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    battingType: cleanCell(r.batting_type),
    everWk: toBool(r.ever_wk),
    battingRole: cleanCell(r.batting_role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
    isDualDisciplineAllrounder: toBool(r.is_dual_discipline_allrounder),
    medianBattingPosition: toNullableFloat(r.median_batting_position),
    openerInningsShare: toNullableFloat(r.opener_innings_share),
    ppBfShare: toNullableFloat(r.pp_bf_share),
    middleBfShare: toNullableFloat(r.middle_bf_share),
    deathBfShare: toNullableFloat(r.death_bf_share),
    overallRuns: toInt(r.overall_runs),
    overallBallsFaced: toInt(r.overall_balls_faced),
    overallDismissals: toInt(r.overall_dismissals),
    overallInnings: toInt(r.overall_innings),
    overallMatches: toInt(r.overall_matches),
    overallSeasons: toInt(r.overall_seasons),
    overallStrikeRate: toNullableFloat(r.overall_strike_rate),
    overallAverage: toNullableFloat(r.overall_average),
    overallBoundaryPct: toNullableFloat(r.overall_boundary_pct),
    overallDotBallPct: toNullableFloat(r.overall_dot_ball_pct),
    overallRvaePer100b: toNullableFloat(r.overall_rvae_per_100b),
    pressureRuns: toInt(r.pressure_runs),
    pressureBallsFaced: toInt(r.pressure_balls_faced),
    pressureDismissals: toInt(r.pressure_dismissals),
    pressureBowlerDismissals: toInt(r.pressure_bowler_dismissals),
    pressureRunOutDismissals: toInt(r.pressure_run_out_dismissals),
    pressureInnings: toInt(r.pressure_innings),
    pressureMatches: toInt(r.pressure_matches),
    pressureSeasons: toInt(r.pressure_seasons),
    pressureStrikeRate: toNullableFloat(r.pressure_strike_rate),
    pressureAverage: toNullableFloat(r.pressure_average),
    pressureRunsPerDismissal: toNullableFloat(r.pressure_runs_per_dismissal),
    pressureBoundaryPct: toNullableFloat(r.pressure_boundary_pct),
    pressureDotBallPct: toNullableFloat(r.pressure_dot_ball_pct),
    pressureDismissalRatePct: toNullableFloat(r.pressure_dismissal_rate_pct),
    pressureRunsPerInnings: toNullableFloat(r.pressure_runs_per_innings),
    pressureStdRunsPerInnings: toNullableFloat(r.pressure_std_runs_per_innings),
    pressureIqrRunsPerInnings: toNullableFloat(r.pressure_iqr_runs_per_innings),
    pressureContributionPct: toNullableFloat(r.pressure_contribution_pct),
    pressureRvaeTotal: toNullableFloat(r.pressure_rvae_total),
    pressureRvaePer100b: toNullableFloat(r.pressure_rvae_per_100b),
    pressureSurvivalAboveExp: toNullableFloat(r.pressure_survival_above_exp),
    pressureNetImpactPer100b: toNullableFloat(r.pressure_net_impact_per_100b),
    meanPressureIndexFaced: toNullableFloat(r.mean_pressure_index_faced),
    nonpressureRuns: toInt(r.nonpressure_runs),
    nonpressureBallsFaced: toInt(r.nonpressure_balls_faced),
    nonpressureDismissals: toInt(r.nonpressure_dismissals),
    nonpressureInnings: toInt(r.nonpressure_innings),
    nonpressureMatches: toInt(r.nonpressure_matches),
    nonpressureStrikeRate: toNullableFloat(r.nonpressure_strike_rate),
    nonpressureAverage: toNullableFloat(r.nonpressure_average),
    nonpressureBoundaryPct: toNullableFloat(r.nonpressure_boundary_pct),
    nonpressureDotBallPct: toNullableFloat(r.nonpressure_dot_ball_pct),
    nonpressureRunsPerInnings: toNullableFloat(r.nonpressure_runs_per_innings),
    nonpressureRvaePer100b: toNullableFloat(r.nonpressure_rvae_per_100b),
    nonpressureNetImpactPer100b: toNullableFloat(r.nonpressure_net_impact_per_100b),
    pressureIplBf: toInt(r.pressure_ipl_bf),
    pressureIplRuns: toInt(r.pressure_ipl_runs),
    pressureIplSr: toNullableFloat(r.pressure_ipl_sr),
    pressureIplAvg: toNullableFloat(r.pressure_ipl_avg),
    pressureIplRvaePer100b: toNullableFloat(r.pressure_ipl_rvae_per_100b),
    pressureT20iBf: toInt(r.pressure_t20i_bf),
    pressureT20iRuns: toInt(r.pressure_t20i_runs),
    pressureT20iSr: toNullableFloat(r.pressure_t20i_sr),
    pressureT20iAvg: toNullableFloat(r.pressure_t20i_avg),
    pressureT20iRvaePer100b: toNullableFloat(r.pressure_t20i_rvae_per_100b),
    pressureInn1Bf: toInt(r.pressure_inn1_bf),
    pressureInn1Runs: toInt(r.pressure_inn1_runs),
    pressureInn1Sr: toNullableFloat(r.pressure_inn1_sr),
    pressureInn1Avg: toNullableFloat(r.pressure_inn1_avg),
    pressureInn1RvaePer100b: toNullableFloat(r.pressure_inn1_rvae_per_100b),
    pressureChaseBf: toInt(r.pressure_chase_bf),
    pressureChaseRuns: toInt(r.pressure_chase_runs),
    pressureChaseSr: toNullableFloat(r.pressure_chase_sr),
    pressureChaseAvg: toNullableFloat(r.pressure_chase_avg),
    pressureChaseRvaePer100b: toNullableFloat(r.pressure_chase_rvae_per_100b),
    pressurePowerplayBf: toInt(r.pressure_powerplay_bf),
    pressurePowerplaySr: toNullableFloat(r.pressure_powerplay_sr),
    pressurePowerplayRvaePer100b: toNullableFloat(r.pressure_powerplay_rvae_per_100b),
    pressureMiddleBf: toInt(r.pressure_middle_bf),
    pressureMiddleSr: toNullableFloat(r.pressure_middle_sr),
    pressureMiddleRvaePer100b: toNullableFloat(r.pressure_middle_rvae_per_100b),
    pressureDeathBf: toInt(r.pressure_death_bf),
    pressureDeathSr: toNullableFloat(r.pressure_death_sr),
    pressureDeathRvaePer100b: toNullableFloat(r.pressure_death_rvae_per_100b),
    deltaSrPressureVsNon: toNullableFloat(r.delta_sr_pressure_vs_non),
    deltaAvgPressureVsNon: toNullableFloat(r.delta_avg_pressure_vs_non),
    deltaDotPctPressureVsNon: toNullableFloat(r.delta_dot_pct_pressure_vs_non),
    deltaBoundaryPctPressureVsNon: toNullableFloat(r.delta_boundary_pct_pressure_vs_non),
    deltaRvaePressureVsNon: toNullableFloat(r.delta_rvae_pressure_vs_non),
  }));

  // 3. Bowling Performance (596)
  const bowlingPerformance = readCsvRecords(SOURCE_FILES.bowlingPerformance).map((r) => ({
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    paceOrSpin: cleanCell(r.pace_or_spin),
    bowlingStyle: cleanCell(r.bowling_style),
    bowlingRole: cleanCell(r.bowling_role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
    isDualDisciplineAllrounder: toBool(r.is_dual_discipline_allrounder),
    ppLbShare: toNullableFloat(r.pp_lb_share),
    middleLbShare: toNullableFloat(r.middle_lb_share),
    deathLbShare: toNullableFloat(r.death_lb_share),
    overallRunsConceded: toInt(r.overall_runs_conceded),
    overallLegalBalls: toInt(r.overall_legal_balls),
    overallOvers: toNullableFloat(r.overall_overs),
    overallWickets: toInt(r.overall_wickets),
    overallInnings: toInt(r.overall_innings),
    overallMatches: toInt(r.overall_matches),
    overallSeasons: toInt(r.overall_seasons),
    overallEconomy: toNullableFloat(r.overall_economy),
    overallBowlingAverage: toNullableFloat(r.overall_bowling_average),
    overallBowlingStrikeRate: toNullableFloat(r.overall_bowling_strike_rate),
    overallDotBallPct: toNullableFloat(r.overall_dot_ball_pct),
    overallBoundaryConcededPct: toNullableFloat(r.overall_boundary_conceded_pct),
    overallWicketFrequency: toNullableFloat(r.overall_wicket_frequency),
    overallRsaePerOver: toNullableFloat(r.overall_rsae_per_over),
    pressureRunsConceded: toInt(r.pressure_runs_conceded),
    pressureLegalBalls: toInt(r.pressure_legal_balls),
    pressureOvers: toNullableFloat(r.pressure_overs),
    pressureWickets: toInt(r.pressure_wickets),
    pressureWides: toInt(r.pressure_wides),
    pressureNoballs: toInt(r.pressure_noballs),
    pressureInnings: toInt(r.pressure_innings),
    pressureMatches: toInt(r.pressure_matches),
    pressureSeasons: toInt(r.pressure_seasons),
    pressureEconomy: toNullableFloat(r.pressure_economy),
    pressureBowlingAverage: toNullableFloat(r.pressure_bowling_average),
    pressureBowlingStrikeRate: toNullableFloat(r.pressure_bowling_strike_rate),
    pressureDotBallPct: toNullableFloat(r.pressure_dot_ball_pct),
    pressureBoundaryConcededPct: toNullableFloat(r.pressure_boundary_conceded_pct),
    pressureWicketFrequency: toNullableFloat(r.pressure_wicket_frequency),
    pressureStdInningsEconomy: toNullableFloat(r.pressure_std_innings_economy),
    pressureIqrInningsEconomy: toNullableFloat(r.pressure_iqr_innings_economy),
    pressureRsaeTotal: toNullableFloat(r.pressure_rsae_total),
    pressureRsaePerOver: toNullableFloat(r.pressure_rsae_per_over),
    pressureWicketsAboveExp: toNullableFloat(r.pressure_wickets_above_exp),
    pressureNetImpactPer24b: toNullableFloat(r.pressure_net_impact_per_24b),
    meanPressureIndexBowled: toNullableFloat(r.mean_pressure_index_bowled),
    nonpressureRunsConceded: toInt(r.nonpressure_runs_conceded),
    nonpressureLegalBalls: toInt(r.nonpressure_legal_balls),
    nonpressureWickets: toInt(r.nonpressure_wickets),
    nonpressureInnings: toInt(r.nonpressure_innings),
    nonpressureMatches: toInt(r.nonpressure_matches),
    nonpressureEconomy: toNullableFloat(r.nonpressure_economy),
    nonpressureBowlingAverage: toNullableFloat(r.nonpressure_bowling_average),
    nonpressureBowlingStrikeRate: toNullableFloat(r.nonpressure_bowling_strike_rate),
    nonpressureDotBallPct: toNullableFloat(r.nonpressure_dot_ball_pct),
    nonpressureBoundaryConcededPct: toNullableFloat(r.nonpressure_boundary_conceded_pct),
    nonpressureWicketFrequency: toNullableFloat(r.nonpressure_wicket_frequency),
    nonpressureRsaePerOver: toNullableFloat(r.nonpressure_rsae_per_over),
    nonpressureNetImpactPer24b: toNullableFloat(r.nonpressure_net_impact_per_24b),
    pressureIplLb: toInt(r.pressure_ipl_lb),
    pressureIplWkts: toInt(r.pressure_ipl_wkts),
    pressureIplEcon: toNullableFloat(r.pressure_ipl_econ),
    pressureIplRsaePerOver: toNullableFloat(r.pressure_ipl_rsae_per_over),
    pressureT20iLb: toInt(r.pressure_t20i_lb),
    pressureT20iWkts: toInt(r.pressure_t20i_wkts),
    pressureT20iEcon: toNullableFloat(r.pressure_t20i_econ),
    pressureT20iRsaePerOver: toNullableFloat(r.pressure_t20i_rsae_per_over),
    pressureInn1Lb: toInt(r.pressure_inn1_lb),
    pressureInn1Wkts: toInt(r.pressure_inn1_wkts),
    pressureInn1Econ: toNullableFloat(r.pressure_inn1_econ),
    pressureInn1RsaePerOver: toNullableFloat(r.pressure_inn1_rsae_per_over),
    pressureInn2Lb: toInt(r.pressure_inn2_lb),
    pressureInn2Wkts: toInt(r.pressure_inn2_wkts),
    pressureInn2Econ: toNullableFloat(r.pressure_inn2_econ),
    pressureInn2RsaePerOver: toNullableFloat(r.pressure_inn2_rsae_per_over),
    pressurePowerplayLb: toInt(r.pressure_powerplay_lb),
    pressurePowerplayEcon: toNullableFloat(r.pressure_powerplay_econ),
    pressurePowerplayRsaePerOver: toNullableFloat(r.pressure_powerplay_rsae_per_over),
    pressureMiddleLb: toInt(r.pressure_middle_lb),
    pressureMiddleEcon: toNullableFloat(r.pressure_middle_econ),
    pressureMiddleRsaePerOver: toNullableFloat(r.pressure_middle_rsae_per_over),
    pressureDeathLb: toInt(r.pressure_death_lb),
    pressureDeathEcon: toNullableFloat(r.pressure_death_econ),
    pressureDeathRsaePerOver: toNullableFloat(r.pressure_death_rsae_per_over),
    deltaEconPressureVsNon: toNullableFloat(r.delta_econ_pressure_vs_non),
    deltaWktFreqPressureVsNon: toNullableFloat(r.delta_wkt_freq_pressure_vs_non),
    deltaDotPctPressureVsNon: toNullableFloat(r.delta_dot_pct_pressure_vs_non),
    deltaBoundaryConcededPressureVsNon: toNullableFloat(r.delta_boundary_conceded_pressure_vs_non),
    deltaRsaePressureVsNon: toNullableFloat(r.delta_rsae_pressure_vs_non),
  }));

  // Merge pressure_vs_nonpressure into reliability maps
  const pvnMap = new Map();
  for (const r of readCsvRecords(SOURCE_FILES.pressureVsNonPressure)) {
    const key = `${cleanCell(r.discipline)}|${toInt(r.player_id)}`;
    pvnMap.set(key, {
      contextImpactDiff: toNullableFloat(r.context_impact_diff_p_minus_np),
      contextImpactDiffCi95Low: toNullableFloat(r.context_impact_diff_ci95_low),
      contextImpactDiffCi95High: toNullableFloat(r.context_impact_diff_ci95_high),
      ci95ExcludesZero: toNullableBool(r.ci95_excludes_zero),
      sufficientBothSidesPrimary: toNullableBool(r.sufficient_both_sides_primary),
      evidenceInterpretation: cleanCell(r.evidence_interpretation),
    });
  }

  const mapReliabilityRow = (discipline) => (r) => {
    const playerId = toInt(r.player_id);
    const pvn = pvnMap.get(`${discipline}|${playerId}`) || {};
    return {
      playerId,
      playerName: cleanCell(r.player_name) || '',
      role: cleanCell(r.role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
      evidenceTier: cleanCell(r.evidence_tier) || 'INSUFFICIENT_EVIDENCE',
      isPrimaryEligible: toBool(r.is_primary_eligible),
      pressureBalls: toInt(r.pressure_balls),
      pressureInnings: toInt(r.pressure_innings),
      pressureMatches: toInt(r.pressure_matches),
      pressureSeasons: toInt(r.pressure_seasons),
      rawPressureImpact: toNullableFloat(r.raw_pressure_impact),
      ebShrinkageWeight: toNullableFloat(r.eb_shrinkage_weight),
      ebKMatchesPrior: toNullableFloat(r.eb_k_matches_prior),
      ebPressureImpact: toNullableFloat(r.eb_pressure_impact),
      inningsImpactIqr: toNullableFloat(r.innings_impact_iqr),
      inningsImpactSd: toNullableFloat(r.innings_impact_sd),
      seasonalImpactSd: toNullableFloat(r.seasonal_impact_sd),
      compInningsStability: toNullableFloat(r.comp_innings_stability),
      compFloorConsistency: toNullableFloat(r.comp_floor_consistency),
      compCrossConditionStability: toNullableFloat(r.comp_cross_condition_stability),
      compSeasonalStability: toNullableFloat(r.comp_seasonal_stability),
      performanceScore: toNullableFloat(r.performance_score),
      reliabilityScore: toNullableFloat(r.reliability_score), // Strictly nullable (NULL for INSUFFICIENT_EVIDENCE)
      evidenceStrengthScore: toNullableFloat(r.evidence_strength_score),
      impactCi95Low: toNullableFloat(r.impact_ci95_low),
      impactCi95High: toNullableFloat(r.impact_ci95_high),
      impactCi95Width: toNullableFloat(r.impact_ci95_width),
      impactBootSe: toNullableFloat(r.impact_boot_se),
      rawRateCi95Low: toNullableFloat(r.raw_rate_ci95_low),
      rawRateCi95High: toNullableFloat(r.raw_rate_ci95_high),
      contextImpactDiff: pvn.contextImpactDiff ?? null,
      contextImpactDiffCi95Low: pvn.contextImpactDiffCi95Low ?? null,
      contextImpactDiffCi95High: pvn.contextImpactDiffCi95High ?? null,
      ci95ExcludesZero: pvn.ci95ExcludesZero ?? null,
      sufficientBothSidesPrimary: pvn.sufficientBothSidesPrimary ?? null,
      evidenceInterpretation: pvn.evidenceInterpretation ?? null,
    };
  };

  // 4 & 5. Batting & Bowling Reliability (824 / 596)
  const battingReliability = readCsvRecords(SOURCE_FILES.battingReliability).map(mapReliabilityRow('batting'));
  const bowlingReliability = readCsvRecords(SOURCE_FILES.bowlingReliability).map(mapReliabilityRow('bowling'));

  // 6. Pressure Exposure (1,420)
  const pressureExposure = readCsvRecords(SOURCE_FILES.pressureExposure).map((r) => ({
    discipline: cleanCell(r.discipline) || 'batting',
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    role: cleanCell(r.role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
    evidenceTier: cleanCell(r.evidence_tier) || 'INSUFFICIENT_EVIDENCE',
    isPrimaryEligible: toBool(r.is_primary_eligible),
    pressureBalls: toInt(r.pressure_balls),
    pressureInnings: toInt(r.pressure_innings),
    pressureMatches: toInt(r.pressure_matches),
    pressureSeasons: toInt(r.pressure_seasons),
    evidenceStrengthScore: toNullableFloat(r.evidence_strength_score),
    extremePressureBalls: toInt(r.extreme_pressure_balls),
    highPressureBalls: toInt(r.high_pressure_balls),
    lowPressureBalls: toInt(r.low_pressure_balls),
    moderatePressureBalls: toInt(r.moderate_pressure_balls),
    totalValidBalls: toInt(r.total_valid_balls),
    highExtremeSharePct: toNullableFloat(r.high_extreme_share_pct),
  }));

  // 7. Season Performance (3,008)
  const seasonPerformance = readCsvRecords(SOURCE_FILES.seasonPerformance).map((r) => ({
    discipline: cleanCell(r.discipline) || 'batting',
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    seasonYear: toInt(r.season_year),
    pressureBalls: toInt(r.pressure_balls),
    pressureInnings: toInt(r.pressure_innings),
    pressureMatches: toInt(r.pressure_matches),
    pressureRunsOrConceded: toInt(r.pressure_runs_or_conceded),
    pressureDismissalsOrWkts: toInt(r.pressure_dismissals_or_wickets),
    primaryRate: toNullableFloat(r.primary_rate),
    netImpactRate: toNullableFloat(r.net_impact_rate),
  }));

  // 16. Player Pressure Breakdowns (2,239 bat + 2,037 bowl = 4,276)
  const batBreakdowns = readCsvRecords(SOURCE_FILES.battingPressureBreakdown).map((r) => ({
    discipline: 'batting',
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    role: cleanCell(r.batting_role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
    pressureLevel: cleanCell(r.pressure_level) || 'UNAVAILABLE',
    balls: toInt(r.balls_faced),
    runs: toInt(r.runs),
    wicketsOrDismissals: toInt(r.dismissals),
    dotBalls: toInt(r.dot_balls),
    boundaryBalls: toInt(r.boundary_balls),
    inningsCount: toInt(r.innings_count),
    matchesCount: toInt(r.matches_count),
    seasonsCount: toInt(r.seasons_count),
    primaryRate: toNullableFloat(r.strike_rate),
    average: toNullableFloat(r.batting_average),
    dotBallPct: toNullableFloat(r.dot_ball_pct),
    boundaryPct: toNullableFloat(r.boundary_pct),
    rvaeOrRsaeRate: toNullableFloat(r.rvae_per_100b),
    netImpactRate: toNullableFloat(r.net_impact_per_100b),
    meanPressureIndex: toNullableFloat(r.mean_pressure_index),
  }));

  const bowlBreakdowns = readCsvRecords(SOURCE_FILES.bowlingPressureBreakdown).map((r) => ({
    discipline: 'bowling',
    playerId: toInt(r.player_id),
    playerName: cleanCell(r.player_name) || '',
    role: cleanCell(r.bowling_role) || 'UNKNOWN / INSUFFICIENT EVIDENCE',
    pressureLevel: cleanCell(r.pressure_level) || 'UNAVAILABLE',
    balls: toInt(r.legal_balls),
    runs: toInt(r.runs_conceded),
    wicketsOrDismissals: toInt(r.bowler_wickets),
    dotBalls: toInt(r.dot_balls),
    boundaryBalls: toInt(r.boundary_conceded_balls),
    inningsCount: toInt(r.innings_count),
    matchesCount: toInt(r.matches_count),
    seasonsCount: toInt(r.seasons_count),
    primaryRate: toNullableFloat(r.economy_rate),
    average: toNullableFloat(r.bowling_average),
    dotBallPct: toNullableFloat(r.dot_ball_pct),
    boundaryPct: toNullableFloat(r.boundary_conceded_pct),
    rvaeOrRsaeRate: toNullableFloat(r.rsae_per_over),
    netImpactRate: toNullableFloat(r.net_impact_per_24b),
    meanPressureIndex: toNullableFloat(r.mean_pressure_index),
  }));
  const pressureBreakdowns = [...batBreakdowns, ...bowlBreakdowns];

  // Top-10 overlap stability metadata (30 rows: Top 15 bat + Top 15 bowl)
  const overlapMap = new Map();
  for (const r of readCsvRecords(SOURCE_FILES.top10OverlapAnalysis)) {
    overlapMap.set(`${cleanCell(r.discipline)}|${toInt(r.player_id)}`, {
      methodsInTop10OutOf8: toNullableInt(r.methods_in_top10_out_of_8),
      stabilityTier: cleanCell(r.stability_classification),
    });
  }

  // 8. Final Batting Rankings (173)
  const battingRankings = readCsvRecords(SOURCE_FILES.finalBattingRankings).map((r) => {
    const playerId = toInt(r.player_id);
    const rank = toInt(r.rank);
    const ov = overlapMap.get(`batting|${playerId}`) || {};
    return {
      playerId,
      rank,
      isTop10: rank <= 10,
      playerName: cleanCell(r.player_name) || '',
      role: cleanCell(r.batting_role) || 'UNKNOWN',
      teamContext: cleanCell(r.team_names),
      competitionContext: cleanCell(r.competition_context) || 'Unknown',
      seasonsRepresented: cleanCell(r.season_years_represented),
      evidenceTier: cleanCell(r.evidence_tier) || 'MODERATE_CONFIDENCE',
      finalRankingScore: toFloat(r.final_ranking_score),
      performanceScore: toFloat(r.performance_score),
      reliabilityScore: toFloat(r.reliability_score),
      evidenceScore: toFloat(r.evidence_strength_score),
      normPerfScore: toFloat(r.norm_perf_score),
      normRelScore: toFloat(r.norm_rel_score),
      normExtremeAndLiftScore: toFloat(r.norm_extreme_and_lift_score),
      normEvidenceScore: toFloat(r.norm_evidence_score),
      scoreBalancedPrimary: toFloat(r.score_Balanced_Primary),
      scorePerformanceDominant: toFloat(r.score_Performance_Dominant),
      scoreReliabilityDominant: toFloat(r.score_Reliability_Dominant),
      rankPerformanceDominant: toInt(r.rank_Performance_Dominant),
      rankReliabilityDominant: toInt(r.rank_Reliability_Dominant),
      ebPressureImpact: toFloat(r.eb_pressure_impact),
      rawPressureImpact: toFloat(r.raw_pressure_impact),
      pressureRuns: toInt(r.pressure_runs),
      pressureBallsFaced: toInt(r.pressure_balls_faced),
      pressureStrikeRate: toNullableFloat(r.pressure_strike_rate),
      pressureAverage: toNullableFloat(r.pressure_average),
      pressureBoundaryPct: toNullableFloat(r.pressure_boundary_pct),
      pressureDotBallPct: toNullableFloat(r.pressure_dot_ball_pct),
      pressureInnings: toInt(r.pressure_innings),
      uniqueMatches: toInt(r.pressure_matches),
      seasonsCount: toInt(r.pressure_seasons),
      extremeBalls: toInt(r.extreme_balls),
      extremeRawImpact: toNullableFloat(r.extreme_raw_impact),
      extremePrimaryRate: toNullableFloat(r.extreme_primary_rate),
      extremeInnings: toInt(r.extreme_innings),
      impactCi95Low: toNullableFloat(r.impact_ci95_low),
      impactCi95High: toNullableFloat(r.impact_ci95_high),
      mcRankP05: toNullableFloat(r.mc_rank_p05),
      mcRankMedian: toNullableFloat(r.mc_rank_median),
      mcRankP95: toNullableFloat(r.mc_rank_p95),
      mcProbTop10Pct: toNullableFloat(r.mc_prob_top10_pct),
      methodsInTop10OutOf8: ov.methodsInTop10OutOf8 ?? null,
      stabilityTier: ov.stabilityTier ?? null,
      keyStrengths: cleanCell(r.key_strengths),
      mainLimitation: cleanCell(r.main_limitation),
      confidenceDescription: cleanCell(r.confidence_description),
    };
  });

  // 9. Final Bowling Rankings (165)
  const bowlingRankings = readCsvRecords(SOURCE_FILES.finalBowlingRankings).map((r) => {
    const playerId = toInt(r.player_id);
    const rank = toInt(r.rank);
    const ov = overlapMap.get(`bowling|${playerId}`) || {};
    return {
      playerId,
      rank,
      isTop10: rank <= 10,
      playerName: cleanCell(r.player_name) || '',
      role: cleanCell(r.bowling_role) || 'UNKNOWN',
      paceOrSpin: cleanCell(r.pace_or_spin),
      teamContext: cleanCell(r.team_names),
      competitionContext: cleanCell(r.competition_context) || 'Unknown',
      seasonsRepresented: cleanCell(r.season_years_represented),
      evidenceTier: cleanCell(r.evidence_tier) || 'MODERATE_CONFIDENCE',
      finalRankingScore: toFloat(r.final_ranking_score),
      performanceScore: toFloat(r.performance_score),
      reliabilityScore: toFloat(r.reliability_score),
      evidenceScore: toFloat(r.evidence_strength_score),
      normPerfScore: toFloat(r.norm_perf_score),
      normRelScore: toFloat(r.norm_rel_score),
      normExtremeAndLiftScore: toFloat(r.norm_extreme_and_lift_score),
      normEvidenceScore: toFloat(r.norm_evidence_score),
      scoreBalancedPrimary: toFloat(r.score_Balanced_Primary),
      scorePerformanceDominant: toFloat(r.score_Performance_Dominant),
      scoreReliabilityDominant: toFloat(r.score_Reliability_Dominant),
      rankPerformanceDominant: toInt(r.rank_Performance_Dominant),
      rankReliabilityDominant: toInt(r.rank_Reliability_Dominant),
      ebPressureImpact: toFloat(r.eb_pressure_impact),
      rawPressureImpact: toFloat(r.raw_pressure_impact),
      pressureLegalBalls: toInt(r.pressure_legal_balls),
      pressureRunsConceded: toInt(r.pressure_runs_conceded),
      pressureWickets: toInt(r.pressure_wickets),
      pressureEconomy: toNullableFloat(r.pressure_economy),
      pressureBowlingAverage: toNullableFloat(r.pressure_bowling_average),
      pressureBowlingStrikeRate: toNullableFloat(r.pressure_bowling_strike_rate),
      pressureDotBallPct: toNullableFloat(r.pressure_dot_ball_pct),
      pressureBoundaryConcededPct: toNullableFloat(r.pressure_boundary_conceded_pct),
      pressureRsaePerOver: toNullableFloat(r.pressure_rsae_per_over),
      pressureInnings: toInt(r.pressure_innings),
      uniqueMatches: toInt(r.pressure_matches),
      seasonsCount: toInt(r.pressure_seasons),
      extremeBalls: toInt(r.extreme_balls),
      extremeRawImpact: toNullableFloat(r.extreme_raw_impact),
      extremePrimaryRate: toNullableFloat(r.extreme_primary_rate),
      extremeInnings: toInt(r.extreme_innings),
      impactCi95Low: toNullableFloat(r.impact_ci95_low),
      impactCi95High: toNullableFloat(r.impact_ci95_high),
      mcRankP05: toNullableFloat(r.mc_rank_p05),
      mcRankMedian: toNullableFloat(r.mc_rank_median),
      mcRankP95: toNullableFloat(r.mc_rank_p95),
      mcProbTop10Pct: toNullableFloat(r.mc_prob_top10_pct),
      methodsInTop10OutOf8: ov.methodsInTop10OutOf8 ?? null,
      stabilityTier: ov.stabilityTier ?? null,
      keyStrengths: cleanCell(r.key_strengths),
      mainLimitation: cleanCell(r.main_limitation),
      confidenceDescription: cleanCell(r.confidence_description),
    };
  });

  // 10. Matches (853) joined with pressure_match_summary (837)
  const matchPressureMap = new Map();
  for (const r of readCsvRecords(SOURCE_FILES.pressureMatchSummary)) {
    matchPressureMap.set(toInt(r.match_id), {
      meanI1Pressure: toNullableFloat(r.mean_i1_pressure),
      maxI1Pressure: toNullableFloat(r.max_i1_pressure),
      meanChasePressure: toNullableFloat(r.mean_chase_pressure),
      maxChasePressure: toNullableFloat(r.max_chase_pressure),
      meanBowlingPressure: toNullableFloat(r.mean_bowling_pressure),
      maxBowlingPressure: toNullableFloat(r.max_bowling_pressure),
      highOrExtremeBattingBalls: toNullableInt(r.high_or_extreme_batting_balls),
      highOrExtremeBowlingBalls: toNullableInt(r.high_or_extreme_bowling_balls),
    });
  }

  const teamNameByMatchAndId = new Map();
  const matches = readCsvRecords(SOURCE_FILES.cleanMatches).map((r) => {
    const matchId = toInt(r.match_id);
    const mp = matchPressureMap.get(matchId) || {};
    const homeTeamId = toNullableInt(r.home_team_id);
    const awayTeamId = toNullableInt(r.away_team_id);
    const homeTeam = cleanCell(r.home_team) || 'Unknown';
    const awayTeam = cleanCell(r.away_team) || 'Unknown';
    if (homeTeamId !== null) teamNameByMatchAndId.set(`${matchId}|${homeTeamId}`, homeTeam);
    if (awayTeamId !== null) teamNameByMatchAndId.set(`${matchId}|${awayTeamId}`, awayTeam);
    return {
      matchId,
      compId: toInt(r.comp_id),
      compName: cleanCell(r.comp_name) || '',
      matchFormat: cleanCell(r.eligibility_category) || cleanCell(r.match_format) || 'T20I',
      season: cleanCell(r.season) || '',
      eligibilityCategory: cleanCell(r.eligibility_category) || '',
      matchNumber: cleanCell(r.match_number),
      matchDate: toDate(r.match_date) || new Date('2022-01-01T00:00:00.000Z'),
      stage: cleanCell(r.stage),
      venueId: toNullableInt(r.venue_id),
      venueCountry: cleanCell(r.venue_country),
      homeTeamId,
      homeTeam,
      awayTeamId,
      awayTeam,
      tossWinTeamId: toNullableInt(r.toss_win_team_id),
      tossOpted: cleanCell(r.toss_opted),
      knockOut: toBool(r.knock_out),
      winTeamId: toNullableInt(r.win_team_id),
      result: cleanCell(r.result),
      hasBallData: toBool(r.has_ball_data),
      isAbandonedMatch: toBool(r.is_abandoned_match),
      isNoResultMatch: toBool(r.is_no_result_match),
      isDlsMatch: toBool(r.is_dls_match),
      isReducedOversMatch: toBool(r.is_reduced_overs_match),
      matchCompletionClassification: cleanCell(r.match_completion_classification) || 'unknown',
      regularDeliveries: toInt(r.regular_deliveries),
      regularLegalDeliveries: toInt(r.regular_legal_deliveries),
      inningsRecordedCount: toInt(r.innings_recorded_count),
      inn1TotalRuns: toNullableInt(r.inn1_total_runs),
      inn1Wickets: toNullableInt(r.inn1_wickets),
      inn1LegalBalls: toNullableInt(r.inn1_legal_balls),
      inn2TotalRuns: toNullableInt(r.inn2_total_runs),
      inn2Wickets: toNullableInt(r.inn2_wickets),
      inn2LegalBalls: toNullableInt(r.inn2_legal_balls),
      revisedTargetNum: toNullableInt(r.revised_target_num),
      meanI1Pressure: mp.meanI1Pressure ?? null,
      maxI1Pressure: mp.maxI1Pressure ?? null,
      meanChasePressure: mp.meanChasePressure ?? null,
      maxChasePressure: mp.maxChasePressure ?? null,
      meanBowlingPressure: mp.meanBowlingPressure ?? null,
      maxBowlingPressure: mp.maxBowlingPressure ?? null,
      highOrExtremeBattingBalls: mp.highOrExtremeBattingBalls ?? null,
      highOrExtremeBowlingBalls: mp.highOrExtremeBowlingBalls ?? null,
    };
  });

  // 11. Innings (1,652) joined with pressure_innings_summary (1,652)
  const innPressureMap = new Map();
  for (const r of readCsvRecords(SOURCE_FILES.pressureInningsSummary)) {
    innPressureMap.set(`${toInt(r.match_id)}|${toInt(r.innings)}`, {
      inningsType: cleanCell(r.innings_type) || 'regular',
      battingPressureValidBalls: toInt(r.batting_pressure_valid_balls),
      bowlingPressureValidBalls: toInt(r.bowling_pressure_valid_balls),
      meanBattingPressure: toNullableFloat(r.mean_batting_pressure),
      maxBattingPressure: toNullableFloat(r.max_batting_pressure),
      highOrExtremeBattingBalls: toInt(r.high_or_extreme_batting_balls),
      extremeBattingBalls: toInt(r.extreme_batting_balls),
      meanBowlingPressure: toNullableFloat(r.mean_bowling_pressure),
      maxBowlingPressure: toNullableFloat(r.max_bowling_pressure),
      highOrExtremeBowlingBalls: toInt(r.high_or_extreme_bowling_balls),
      extremeBowlingBalls: toInt(r.extreme_bowling_balls),
    });
  }

  const innings = readCsvRecords(SOURCE_FILES.inningsSummary).map((r) => {
    const matchId = toInt(r.match_id);
    const innNum = toInt(r.innings);
    const battingTeamId = toInt(r.batting_team_id);
    const bowlingTeamId = toInt(r.bowling_team_id);
    const ip = innPressureMap.get(`${matchId}|${innNum}`) || {};
    return {
      matchId,
      innings: innNum,
      compId: toInt(r.comp_id),
      compName: cleanCell(r.comp_name) || '',
      matchFormat: cleanCell(r.eligibility_category) || cleanCell(r.match_format) || 'T20I',
      season: cleanCell(r.season) || '',
      inningsType: ip.inningsType || (innNum === 1 ? 'regular_first' : 'regular_chase'),
      battingTeamId,
      battingTeamName: teamNameByMatchAndId.get(`${matchId}|${battingTeamId}`) || null,
      bowlingTeamId,
      bowlingTeamName: teamNameByMatchAndId.get(`${matchId}|${bowlingTeamId}`) || null,
      totalDeliveries: toInt(r.total_deliveries),
      legalDeliveries: toInt(r.legal_deliveries),
      batterBallsFaced: toInt(r.batter_balls_faced),
      wides: toInt(r.wides),
      overstepNoballs: toInt(r.overstep_noballs),
      otherNoballs: toInt(r.other_noballs),
      batterRuns: toInt(r.batter_runs),
      extrasTotalRuns: toInt(r.extras_total_runs),
      totalRuns: toInt(r.total_runs),
      bowlerConcededRuns: toInt(r.bowler_conceded_runs),
      wickets: toInt(r.wickets),
      bowlerWickets: toInt(r.bowler_wickets),
      runOuts: toInt(r.run_outs),
      isDlsMatch: toBool(r.is_dls_match),
      isReducedOversMatch: toBool(r.is_reduced_overs_match),
      battingPressureValidBalls: ip.battingPressureValidBalls ?? 0,
      bowlingPressureValidBalls: ip.bowlingPressureValidBalls ?? 0,
      meanBattingPressure: ip.meanBattingPressure ?? null,
      maxBattingPressure: ip.maxBattingPressure ?? null,
      highOrExtremeBattingBalls: ip.highOrExtremeBattingBalls ?? 0,
      extremeBattingBalls: ip.extremeBattingBalls ?? 0,
      meanBowlingPressure: ip.meanBowlingPressure ?? null,
      maxBowlingPressure: ip.maxBowlingPressure ?? null,
      highOrExtremeBowlingBalls: ip.highOrExtremeBowlingBalls ?? 0,
      extremeBowlingBalls: ip.extremeBowlingBalls ?? 0,
    };
  });

  // 12. Pressure Summaries (outputs/pressure_*.csv)
  const pressureSummaries = [];
  for (const r of readCsvRecords(SOURCE_FILES.pressureLevelSummary)) {
    pressureSummaries.push({
      summaryType: 'LEVEL_SUMMARY',
      framework: cleanCell(r.framework) || 'UNKNOWN',
      segmentKey: cleanCell(r.pressure_level) || 'UNKNOWN',
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.pressureDistribution)) {
    pressureSummaries.push({
      summaryType: 'DISTRIBUTION',
      framework: cleanCell(r.framework) || 'UNKNOWN',
      segmentKey: `${cleanCell(r.column)}|${cleanCell(r.scope)}`,
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.pressureModelComparison)) {
    pressureSummaries.push({
      summaryType: 'MODEL_COMPARISON',
      framework: cleanCell(r.framework) || 'UNKNOWN',
      segmentKey: cleanCell(r.model) || 'UNKNOWN',
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.pressureExposureSummary)) {
    pressureSummaries.push({
      summaryType: 'EXPOSURE_SUMMARY',
      framework: cleanCell(r.dimension) || 'UNKNOWN',
      segmentKey: cleanCell(r.segment) || 'UNKNOWN',
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.pressureComponentSummary)) {
    pressureSummaries.push({
      summaryType: 'COMPONENT_SUMMARY',
      framework: cleanCell(r.framework) || 'UNKNOWN',
      segmentKey: cleanCell(r.component) || 'UNKNOWN',
      payloadJson: r,
    });
  }

  // 13. Methodology Sections (20)
  const methodologySections = parseMethodologySections(SOURCE_FILES.methodologyReportMd);

  // 18. Ranking Robustness Audits (65)
  const rankingRobustnessAudits = [];
  for (const r of readCsvRecords(SOURCE_FILES.rankingRobustness)) {
    rankingRobustnessAudits.push({
      auditType: 'ROBUSTNESS_TEST',
      discipline: cleanCell(r.discipline) || 'unknown',
      specKey: cleanCell(r.robustness_test) || 'unknown',
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.rankingMethodComparison)) {
    rankingRobustnessAudits.push({
      auditType: 'METHOD_COMPARISON',
      discipline: cleanCell(r.discipline) || 'unknown',
      specKey: cleanCell(r.approach) || 'unknown',
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.rankingThresholdSensitivity)) {
    rankingRobustnessAudits.push({
      auditType: 'THRESHOLD_SENSITIVITY',
      discipline: cleanCell(r.discipline) || 'unknown',
      specKey: `${cleanCell(r.min_pressure_balls)}b_${cleanCell(r.min_pressure_innings_matches)}m`,
      payloadJson: r,
    });
  }
  for (const r of readCsvRecords(SOURCE_FILES.shortlistAlternatives)) {
    rankingRobustnessAudits.push({
      auditType: 'SHORTLIST_ALTERNATIVE',
      discipline: cleanCell(r.discipline) || 'unknown',
      specKey: `${cleanCell(r.audit_group)}|${cleanCell(r.player_id)}`,
      payloadJson: r,
    });
  }

  // 17. Pre-aggregated OLAP Cube from 193,988 pressure_deliveries.csv rows
  let pressureAnalyticsCube = [];
  let totalDeliveriesStreamed = 0;
  if (includeCube) {
    const cubeRes = await buildPressureAnalyticsCube();
    pressureAnalyticsCube = cubeRes.cubeRows;
    totalDeliveriesStreamed = cubeRes.totalDeliveries;
  }

  // Strict pre-commit count sanity check
  if (players.length !== EXPECTED_COUNTS.players) {
    throw new Error(`Expected ${EXPECTED_COUNTS.players} players, got ${players.length}`);
  }
  if (battingRankings.length !== EXPECTED_COUNTS.battingRankings) {
    throw new Error(`Expected ${EXPECTED_COUNTS.battingRankings} batting rankings, got ${battingRankings.length}`);
  }
  if (bowlingRankings.length !== EXPECTED_COUNTS.bowlingRankings) {
    throw new Error(`Expected ${EXPECTED_COUNTS.bowlingRankings} bowling rankings, got ${bowlingRankings.length}`);
  }
  if (includeCube && totalDeliveriesStreamed !== EXPECTED_COUNTS.primaryDeliveries) {
    throw new Error(`Expected ${EXPECTED_COUNTS.primaryDeliveries} deliveries, got ${totalDeliveriesStreamed}`);
  }

  return {
    players,
    battingPerformance,
    bowlingPerformance,
    battingReliability,
    bowlingReliability,
    pressureExposure,
    seasonPerformance,
    pressureBreakdowns,
    battingRankings,
    bowlingRankings,
    matches,
    innings,
    pressureSummaries,
    methodologySections,
    rankingRobustnessAudits,
    pressureAnalyticsCube,
    totalDeliveriesStreamed,
  };
}

async function createManyChunked(delegate, rows, chunkSize = 500) {
  let inserted = 0;
  for (let i = 0; i < rows.length; i += chunkSize) {
    const batch = rows.slice(i, i + chunkSize);
    const res = await delegate.createMany({ data: batch, skipDuplicates: false });
    inserted += res.count ?? batch.length;
  }
  return inserted;
}

/**
 * Executes an idempotent, transactional full analytics import into PostgreSQL
 * and runs mandatory post-import reconciliation against official submission CSVs.
 */
export async function runAnalyticsImport(prisma, { triggeredBy = 'CLI', adminUserId = null } = {}) {
  if (importLockActive) {
    throw new Error('Another analytics import is already in progress.');
  }
  importLockActive = true;
  const startedAt = Date.now();
  const batchId = `imp_${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}_${crypto.randomBytes(3).toString('hex')}`;

  const logRecord = await prisma.dataImportLog.create({
    data: {
      batchId,
      triggeredBy,
      adminUserId,
      status: 'STARTED',
    },
  });

  try {
    const data = await prepareAllDatasets({ includeCube: true });

    const sourceRowCount =
      data.players.length +
      data.battingPerformance.length +
      data.bowlingPerformance.length +
      data.battingReliability.length +
      data.bowlingReliability.length +
      data.pressureExposure.length +
      data.seasonPerformance.length +
      data.pressureBreakdowns.length +
      data.battingRankings.length +
      data.bowlingRankings.length +
      data.matches.length +
      data.innings.length +
      data.pressureSummaries.length +
      data.methodologySections.length +
      data.rankingRobustnessAudits.length +
      data.pressureAnalyticsCube.length;

    const tableCounts = await prisma.$transaction(
      async (tx) => {
        // Delete child analytical tables first (preserving admin_users, admin_audit_logs, data_import_logs)
        await tx.innings.deleteMany();
        await tx.match.deleteMany();
        await tx.battingRanking.deleteMany();
        await tx.bowlingRanking.deleteMany();
        await tx.playerSeasonPerformance.deleteMany();
        await tx.playerPressureBreakdown.deleteMany();
        await tx.playerPressureExposure.deleteMany();
        await tx.playerBattingReliability.deleteMany();
        await tx.playerBowlingReliability.deleteMany();
        await tx.playerBattingPerformance.deleteMany();
        await tx.playerBowlingPerformance.deleteMany();
        await tx.player.deleteMany();
        await tx.pressureSummary.deleteMany();
        await tx.methodologySection.deleteMany();
        await tx.rankingRobustnessAudit.deleteMany();
        await tx.pressureAnalyticsCube.deleteMany();

        // Insert parents first, then children in chunks
        const counts = {};
        counts.players = await createManyChunked(tx.player, data.players);
        counts.player_batting_performance = await createManyChunked(tx.playerBattingPerformance, data.battingPerformance);
        counts.player_bowling_performance = await createManyChunked(tx.playerBowlingPerformance, data.bowlingPerformance);
        counts.player_batting_reliability = await createManyChunked(tx.playerBattingReliability, data.battingReliability);
        counts.player_bowling_reliability = await createManyChunked(tx.playerBowlingReliability, data.bowlingReliability);
        counts.player_pressure_exposure = await createManyChunked(tx.playerPressureExposure, data.pressureExposure);
        counts.player_season_performance = await createManyChunked(tx.playerSeasonPerformance, data.seasonPerformance);
        counts.player_pressure_breakdowns = await createManyChunked(tx.playerPressureBreakdown, data.pressureBreakdowns);
        counts.batting_rankings = await createManyChunked(tx.battingRanking, data.battingRankings);
        counts.bowling_rankings = await createManyChunked(tx.bowlingRanking, data.bowlingRankings);
        counts.matches = await createManyChunked(tx.match, data.matches);
        counts.innings = await createManyChunked(tx.innings, data.innings);
        counts.pressure_summaries = await createManyChunked(tx.pressureSummary, data.pressureSummaries);
        counts.methodology_sections = await createManyChunked(tx.methodologySection, data.methodologySections);
        counts.ranking_robustness_audits = await createManyChunked(tx.rankingRobustnessAudit, data.rankingRobustnessAudits);
        counts.pressure_analytics_cube = await createManyChunked(tx.pressureAnalyticsCube, data.pressureAnalyticsCube);
        counts.source_deliveries_aggregated = data.totalDeliveriesStreamed;
        return counts;
      },
      { maxWait: 20000, timeout: 120000 }
    );

    const insertedCount = Object.entries(tableCounts)
      .filter(([k]) => k !== 'source_deliveries_aggregated')
      .reduce((acc, [, v]) => acc + v, 0);

    // Mandatory post-import reconciliation against official submission CSVs
    const reconcileReport = await runDataReconciliation(prisma);
    const durationMs = Date.now() - startedAt;

    const finalStatus = reconcileReport.passed ? 'SUCCESS' : 'FAILED_RECONCILIATION';

    await prisma.dataImportLog.update({
      where: { id: logRecord.id },
      data: {
        status: finalStatus,
        sourceRowCount,
        insertedCount,
        skippedCount: 0,
        tableCountsJson: tableCounts,
        reconcilePassed: reconcileReport.passed,
        reconcileSummary: reconcileReport,
        errorsJson: reconcileReport.passed ? null : reconcileReport.discrepancies,
        durationMs,
        completedAt: new Date(),
      },
    });

    if (!reconcileReport.passed) {
      throw new Error(`Post-import reconciliation failed with ${reconcileReport.discrepancies.length} discrepancy(ies).`);
    }

    return {
      batchId,
      status: finalStatus,
      sourceRowCount,
      insertedCount,
      skippedCount: 0,
      durationMs,
      tableCounts,
      reconcileReport,
    };
  } catch (err) {
    const durationMs = Date.now() - startedAt;
    await prisma.dataImportLog
      .update({
        where: { id: logRecord.id },
        data: {
          status: 'FAILED',
          errorsJson: [{ message: err.message }],
          durationMs,
          completedAt: new Date(),
        },
      })
      .catch(() => {});
    throw err;
  } finally {
    importLockActive = false;
  }
}

