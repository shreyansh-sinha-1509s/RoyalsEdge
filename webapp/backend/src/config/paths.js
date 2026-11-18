import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// webapp/backend/src/config -> webapp/backend -> webapp -> SupeRR_Selector
export const BACKEND_ROOT = path.resolve(__dirname, '..', '..');
export const WEBAPP_ROOT = path.resolve(BACKEND_ROOT, '..');
export const PROJECT_ROOT = path.resolve(WEBAPP_ROOT, '..');

export const DATA_PROCESSED_DIR = path.join(PROJECT_ROOT, 'data', 'processed');
export const OUTPUTS_DIR = path.join(PROJECT_ROOT, 'outputs');
export const SUBMISSION_DIR = path.join(PROJECT_ROOT, 'submission');

export const SOURCE_FILES = {
  playerMaster: path.join(DATA_PROCESSED_DIR, 'player_master.csv'),
  battingPerformance: path.join(DATA_PROCESSED_DIR, 'player_batting_performance.csv'),
  bowlingPerformance: path.join(DATA_PROCESSED_DIR, 'player_bowling_performance.csv'),
  battingReliability: path.join(DATA_PROCESSED_DIR, 'player_batting_reliability.csv'),
  bowlingReliability: path.join(DATA_PROCESSED_DIR, 'player_bowling_reliability.csv'),
  pressureExposure: path.join(DATA_PROCESSED_DIR, 'player_pressure_exposure.csv'),
  pressureVsNonPressure: path.join(DATA_PROCESSED_DIR, 'player_pressure_vs_nonpressure.csv'),
  battingPressureBreakdown: path.join(DATA_PROCESSED_DIR, 'player_batting_pressure_breakdown.csv'),
  bowlingPressureBreakdown: path.join(DATA_PROCESSED_DIR, 'player_bowling_pressure_breakdown.csv'),
  seasonPerformance: path.join(DATA_PROCESSED_DIR, 'player_season_performance.csv'),
  finalBattingRankings: path.join(DATA_PROCESSED_DIR, 'final_batting_rankings.csv'),
  finalBowlingRankings: path.join(DATA_PROCESSED_DIR, 'final_bowling_rankings.csv'),
  cleanMatches: path.join(DATA_PROCESSED_DIR, 'clean_matches.csv'),
  pressureMatchSummary: path.join(DATA_PROCESSED_DIR, 'pressure_match_summary.csv'),
  inningsSummary: path.join(DATA_PROCESSED_DIR, 'innings_summary.csv'),
  pressureInningsSummary: path.join(DATA_PROCESSED_DIR, 'pressure_innings_summary.csv'),
  pressureDeliveries: path.join(DATA_PROCESSED_DIR, 'pressure_deliveries.csv'),

  // Outputs audit & comparison tables
  top10OverlapAnalysis: path.join(OUTPUTS_DIR, 'top10_overlap_analysis.csv'),
  pressureLevelSummary: path.join(OUTPUTS_DIR, 'pressure_level_summary.csv'),
  pressureDistribution: path.join(OUTPUTS_DIR, 'pressure_distribution.csv'),
  pressureModelComparison: path.join(OUTPUTS_DIR, 'pressure_model_comparison.csv'),
  pressureExposureSummary: path.join(OUTPUTS_DIR, 'pressure_exposure_summary.csv'),
  pressureComponentSummary: path.join(OUTPUTS_DIR, 'pressure_component_summary.csv'),
  rankingRobustness: path.join(OUTPUTS_DIR, 'ranking_robustness.csv'),
  rankingMethodComparison: path.join(OUTPUTS_DIR, 'ranking_method_comparison.csv'),
  rankingThresholdSensitivity: path.join(OUTPUTS_DIR, 'ranking_threshold_sensitivity.csv'),
  shortlistAlternatives: path.join(OUTPUTS_DIR, 'shortlist_alternatives.csv'),

  // Official Phase 6 competition submission deliverables (authority for reconciliation)
  submissionTop10Batters: path.join(SUBMISSION_DIR, 'RR_Performance_Lab_Top_10_Batters.csv'),
  submissionTop10Bowlers: path.join(SUBMISSION_DIR, 'RR_Performance_Lab_Top_10_Bowlers.csv'),
  methodologyReportMd: path.join(SUBMISSION_DIR, 'RR_Performance_Lab_Methodology_Report.md'),
};

