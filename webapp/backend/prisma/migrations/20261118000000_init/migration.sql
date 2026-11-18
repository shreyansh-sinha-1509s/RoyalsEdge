-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "players" (
    "player_id" INTEGER NOT NULL,
    "standardized_display_name" TEXT NOT NULL,
    "mapping_source_names" TEXT,
    "ball_feed_source_names" TEXT,
    "team_names" TEXT,
    "in_ipl" BOOLEAN NOT NULL DEFAULT false,
    "in_t20i" BOOLEAN NOT NULL DEFAULT false,
    "in_excluded_non_ipl_t20" BOOLEAN NOT NULL DEFAULT false,
    "in_primary_eligible_comp" BOOLEAN NOT NULL DEFAULT false,
    "primary_balls_faced" INTEGER NOT NULL DEFAULT 0,
    "primary_legal_balls_bowled" INTEGER NOT NULL DEFAULT 0,
    "matches_in_playing_eleven" INTEGER NOT NULL DEFAULT 0,
    "batting_type" TEXT,
    "bowling_type" TEXT,
    "pace_or_spin" TEXT,
    "ever_wk" BOOLEAN NOT NULL DEFAULT false,
    "ever_captain" BOOLEAN NOT NULL DEFAULT false,
    "inferred_playing_role" TEXT,
    "name_mismatch_between_sources" BOOLEAN NOT NULL DEFAULT false,
    "shares_name_with_other_player_id" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "players_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "player_batting_performance" (
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "batting_type" TEXT,
    "ever_wk" BOOLEAN NOT NULL DEFAULT false,
    "batting_role" TEXT NOT NULL,
    "is_dual_discipline_allrounder" BOOLEAN NOT NULL DEFAULT false,
    "median_batting_position" DOUBLE PRECISION,
    "opener_innings_share" DOUBLE PRECISION,
    "pp_bf_share" DOUBLE PRECISION,
    "middle_bf_share" DOUBLE PRECISION,
    "death_bf_share" DOUBLE PRECISION,
    "overall_runs" INTEGER NOT NULL DEFAULT 0,
    "overall_balls_faced" INTEGER NOT NULL DEFAULT 0,
    "overall_dismissals" INTEGER NOT NULL DEFAULT 0,
    "overall_innings" INTEGER NOT NULL DEFAULT 0,
    "overall_matches" INTEGER NOT NULL DEFAULT 0,
    "overall_seasons" INTEGER NOT NULL DEFAULT 0,
    "overall_strike_rate" DOUBLE PRECISION,
    "overall_average" DOUBLE PRECISION,
    "overall_boundary_pct" DOUBLE PRECISION,
    "overall_dot_ball_pct" DOUBLE PRECISION,
    "overall_rvae_per_100b" DOUBLE PRECISION,
    "pressure_runs" INTEGER NOT NULL DEFAULT 0,
    "pressure_balls_faced" INTEGER NOT NULL DEFAULT 0,
    "pressure_dismissals" INTEGER NOT NULL DEFAULT 0,
    "pressure_bowler_dismissals" INTEGER NOT NULL DEFAULT 0,
    "pressure_run_out_dismissals" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_seasons" INTEGER NOT NULL DEFAULT 0,
    "pressure_strike_rate" DOUBLE PRECISION,
    "pressure_average" DOUBLE PRECISION,
    "pressure_runs_per_dismissal" DOUBLE PRECISION,
    "pressure_boundary_pct" DOUBLE PRECISION,
    "pressure_dot_ball_pct" DOUBLE PRECISION,
    "pressure_dismissal_rate_pct" DOUBLE PRECISION,
    "pressure_runs_per_innings" DOUBLE PRECISION,
    "pressure_std_runs_per_innings" DOUBLE PRECISION,
    "pressure_iqr_runs_per_innings" DOUBLE PRECISION,
    "pressure_contribution_pct" DOUBLE PRECISION,
    "pressure_rvae_total" DOUBLE PRECISION,
    "pressure_rvae_per_100b" DOUBLE PRECISION,
    "pressure_survival_above_exp" DOUBLE PRECISION,
    "pressure_net_impact_per_100b" DOUBLE PRECISION,
    "mean_pressure_index_faced" DOUBLE PRECISION,
    "nonpressure_runs" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_balls_faced" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_dismissals" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_innings" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_matches" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_strike_rate" DOUBLE PRECISION,
    "nonpressure_average" DOUBLE PRECISION,
    "nonpressure_boundary_pct" DOUBLE PRECISION,
    "nonpressure_dot_ball_pct" DOUBLE PRECISION,
    "nonpressure_runs_per_innings" DOUBLE PRECISION,
    "nonpressure_rvae_per_100b" DOUBLE PRECISION,
    "nonpressure_net_impact_per_100b" DOUBLE PRECISION,
    "pressure_ipl_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_ipl_runs" INTEGER NOT NULL DEFAULT 0,
    "pressure_ipl_sr" DOUBLE PRECISION,
    "pressure_ipl_avg" DOUBLE PRECISION,
    "pressure_ipl_rvae_per_100b" DOUBLE PRECISION,
    "pressure_t20i_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_t20i_runs" INTEGER NOT NULL DEFAULT 0,
    "pressure_t20i_sr" DOUBLE PRECISION,
    "pressure_t20i_avg" DOUBLE PRECISION,
    "pressure_t20i_rvae_per_100b" DOUBLE PRECISION,
    "pressure_inn1_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn1_runs" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn1_sr" DOUBLE PRECISION,
    "pressure_inn1_avg" DOUBLE PRECISION,
    "pressure_inn1_rvae_per_100b" DOUBLE PRECISION,
    "pressure_chase_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_chase_runs" INTEGER NOT NULL DEFAULT 0,
    "pressure_chase_sr" DOUBLE PRECISION,
    "pressure_chase_avg" DOUBLE PRECISION,
    "pressure_chase_rvae_per_100b" DOUBLE PRECISION,
    "pressure_powerplay_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_powerplay_sr" DOUBLE PRECISION,
    "pressure_powerplay_rvae_per_100b" DOUBLE PRECISION,
    "pressure_middle_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_middle_sr" DOUBLE PRECISION,
    "pressure_middle_rvae_per_100b" DOUBLE PRECISION,
    "pressure_death_bf" INTEGER NOT NULL DEFAULT 0,
    "pressure_death_sr" DOUBLE PRECISION,
    "pressure_death_rvae_per_100b" DOUBLE PRECISION,
    "delta_sr_pressure_vs_non" DOUBLE PRECISION,
    "delta_avg_pressure_vs_non" DOUBLE PRECISION,
    "delta_dot_pct_pressure_vs_non" DOUBLE PRECISION,
    "delta_boundary_pct_pressure_vs_non" DOUBLE PRECISION,
    "delta_rvae_pressure_vs_non" DOUBLE PRECISION,

    CONSTRAINT "player_batting_performance_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "player_bowling_performance" (
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "pace_or_spin" TEXT,
    "bowling_style" TEXT,
    "bowling_role" TEXT NOT NULL,
    "is_dual_discipline_allrounder" BOOLEAN NOT NULL DEFAULT false,
    "pp_lb_share" DOUBLE PRECISION,
    "middle_lb_share" DOUBLE PRECISION,
    "death_lb_share" DOUBLE PRECISION,
    "overall_runs_conceded" INTEGER NOT NULL DEFAULT 0,
    "overall_legal_balls" INTEGER NOT NULL DEFAULT 0,
    "overall_overs" DOUBLE PRECISION,
    "overall_wickets" INTEGER NOT NULL DEFAULT 0,
    "overall_innings" INTEGER NOT NULL DEFAULT 0,
    "overall_matches" INTEGER NOT NULL DEFAULT 0,
    "overall_seasons" INTEGER NOT NULL DEFAULT 0,
    "overall_economy" DOUBLE PRECISION,
    "overall_bowling_average" DOUBLE PRECISION,
    "overall_bowling_strike_rate" DOUBLE PRECISION,
    "overall_dot_ball_pct" DOUBLE PRECISION,
    "overall_boundary_conceded_pct" DOUBLE PRECISION,
    "overall_wicket_frequency" DOUBLE PRECISION,
    "overall_rsae_per_over" DOUBLE PRECISION,
    "pressure_runs_conceded" INTEGER NOT NULL DEFAULT 0,
    "pressure_legal_balls" INTEGER NOT NULL DEFAULT 0,
    "pressure_overs" DOUBLE PRECISION,
    "pressure_wickets" INTEGER NOT NULL DEFAULT 0,
    "pressure_wides" INTEGER NOT NULL DEFAULT 0,
    "pressure_noballs" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_seasons" INTEGER NOT NULL DEFAULT 0,
    "pressure_economy" DOUBLE PRECISION,
    "pressure_bowling_average" DOUBLE PRECISION,
    "pressure_bowling_strike_rate" DOUBLE PRECISION,
    "pressure_dot_ball_pct" DOUBLE PRECISION,
    "pressure_boundary_conceded_pct" DOUBLE PRECISION,
    "pressure_wicket_frequency" DOUBLE PRECISION,
    "pressure_std_innings_economy" DOUBLE PRECISION,
    "pressure_iqr_innings_economy" DOUBLE PRECISION,
    "pressure_rsae_total" DOUBLE PRECISION,
    "pressure_rsae_per_over" DOUBLE PRECISION,
    "pressure_wickets_above_exp" DOUBLE PRECISION,
    "pressure_net_impact_per_24b" DOUBLE PRECISION,
    "mean_pressure_index_bowled" DOUBLE PRECISION,
    "nonpressure_runs_conceded" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_legal_balls" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_wickets" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_innings" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_matches" INTEGER NOT NULL DEFAULT 0,
    "nonpressure_economy" DOUBLE PRECISION,
    "nonpressure_bowling_average" DOUBLE PRECISION,
    "nonpressure_bowling_strike_rate" DOUBLE PRECISION,
    "nonpressure_dot_ball_pct" DOUBLE PRECISION,
    "nonpressure_boundary_conceded_pct" DOUBLE PRECISION,
    "nonpressure_wicket_frequency" DOUBLE PRECISION,
    "nonpressure_rsae_per_over" DOUBLE PRECISION,
    "nonpressure_net_impact_per_24b" DOUBLE PRECISION,
    "pressure_ipl_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_ipl_wkts" INTEGER NOT NULL DEFAULT 0,
    "pressure_ipl_econ" DOUBLE PRECISION,
    "pressure_ipl_rsae_per_over" DOUBLE PRECISION,
    "pressure_t20i_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_t20i_wkts" INTEGER NOT NULL DEFAULT 0,
    "pressure_t20i_econ" DOUBLE PRECISION,
    "pressure_t20i_rsae_per_over" DOUBLE PRECISION,
    "pressure_inn1_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn1_wkts" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn1_econ" DOUBLE PRECISION,
    "pressure_inn1_rsae_per_over" DOUBLE PRECISION,
    "pressure_inn2_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn2_wkts" INTEGER NOT NULL DEFAULT 0,
    "pressure_inn2_econ" DOUBLE PRECISION,
    "pressure_inn2_rsae_per_over" DOUBLE PRECISION,
    "pressure_powerplay_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_powerplay_econ" DOUBLE PRECISION,
    "pressure_powerplay_rsae_per_over" DOUBLE PRECISION,
    "pressure_middle_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_middle_econ" DOUBLE PRECISION,
    "pressure_middle_rsae_per_over" DOUBLE PRECISION,
    "pressure_death_lb" INTEGER NOT NULL DEFAULT 0,
    "pressure_death_econ" DOUBLE PRECISION,
    "pressure_death_rsae_per_over" DOUBLE PRECISION,
    "delta_econ_pressure_vs_non" DOUBLE PRECISION,
    "delta_wkt_freq_pressure_vs_non" DOUBLE PRECISION,
    "delta_dot_pct_pressure_vs_non" DOUBLE PRECISION,
    "delta_boundary_conceded_pressure_vs_non" DOUBLE PRECISION,
    "delta_rsae_pressure_vs_non" DOUBLE PRECISION,

    CONSTRAINT "player_bowling_performance_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "player_batting_reliability" (
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "evidence_tier" TEXT NOT NULL,
    "is_primary_eligible" BOOLEAN NOT NULL DEFAULT false,
    "pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_seasons" INTEGER NOT NULL DEFAULT 0,
    "raw_pressure_impact" DOUBLE PRECISION,
    "eb_shrinkage_weight" DOUBLE PRECISION,
    "eb_k_matches_prior" DOUBLE PRECISION,
    "eb_pressure_impact" DOUBLE PRECISION,
    "innings_impact_iqr" DOUBLE PRECISION,
    "innings_impact_sd" DOUBLE PRECISION,
    "seasonal_impact_sd" DOUBLE PRECISION,
    "comp_innings_stability" DOUBLE PRECISION,
    "comp_floor_consistency" DOUBLE PRECISION,
    "comp_cross_condition_stability" DOUBLE PRECISION,
    "comp_seasonal_stability" DOUBLE PRECISION,
    "performance_score" DOUBLE PRECISION,
    "reliability_score" DOUBLE PRECISION,
    "evidence_strength_score" DOUBLE PRECISION,
    "impact_ci95_low" DOUBLE PRECISION,
    "impact_ci95_high" DOUBLE PRECISION,
    "impact_ci95_width" DOUBLE PRECISION,
    "impact_boot_se" DOUBLE PRECISION,
    "raw_rate_ci95_low" DOUBLE PRECISION,
    "raw_rate_ci95_high" DOUBLE PRECISION,
    "context_impact_diff_p_minus_np" DOUBLE PRECISION,
    "context_impact_diff_ci95_low" DOUBLE PRECISION,
    "context_impact_diff_ci95_high" DOUBLE PRECISION,
    "ci95_excludes_zero" BOOLEAN,
    "sufficient_both_sides_primary" BOOLEAN,
    "evidence_interpretation" TEXT,

    CONSTRAINT "player_batting_reliability_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "player_bowling_reliability" (
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "evidence_tier" TEXT NOT NULL,
    "is_primary_eligible" BOOLEAN NOT NULL DEFAULT false,
    "pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_seasons" INTEGER NOT NULL DEFAULT 0,
    "raw_pressure_impact" DOUBLE PRECISION,
    "eb_shrinkage_weight" DOUBLE PRECISION,
    "eb_k_matches_prior" DOUBLE PRECISION,
    "eb_pressure_impact" DOUBLE PRECISION,
    "innings_impact_iqr" DOUBLE PRECISION,
    "innings_impact_sd" DOUBLE PRECISION,
    "seasonal_impact_sd" DOUBLE PRECISION,
    "comp_innings_stability" DOUBLE PRECISION,
    "comp_floor_consistency" DOUBLE PRECISION,
    "comp_cross_condition_stability" DOUBLE PRECISION,
    "comp_seasonal_stability" DOUBLE PRECISION,
    "performance_score" DOUBLE PRECISION,
    "reliability_score" DOUBLE PRECISION,
    "evidence_strength_score" DOUBLE PRECISION,
    "impact_ci95_low" DOUBLE PRECISION,
    "impact_ci95_high" DOUBLE PRECISION,
    "impact_ci95_width" DOUBLE PRECISION,
    "impact_boot_se" DOUBLE PRECISION,
    "raw_rate_ci95_low" DOUBLE PRECISION,
    "raw_rate_ci95_high" DOUBLE PRECISION,
    "context_impact_diff_p_minus_np" DOUBLE PRECISION,
    "context_impact_diff_ci95_low" DOUBLE PRECISION,
    "context_impact_diff_ci95_high" DOUBLE PRECISION,
    "ci95_excludes_zero" BOOLEAN,
    "sufficient_both_sides_primary" BOOLEAN,
    "evidence_interpretation" TEXT,

    CONSTRAINT "player_bowling_reliability_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "player_pressure_exposure" (
    "id" SERIAL NOT NULL,
    "discipline" TEXT NOT NULL,
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "evidence_tier" TEXT NOT NULL,
    "is_primary_eligible" BOOLEAN NOT NULL DEFAULT false,
    "pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_seasons" INTEGER NOT NULL DEFAULT 0,
    "evidence_strength_score" DOUBLE PRECISION,
    "extreme_pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "high_pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "low_pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "moderate_pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "total_valid_balls" INTEGER NOT NULL DEFAULT 0,
    "high_extreme_share_pct" DOUBLE PRECISION,

    CONSTRAINT "player_pressure_exposure_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "player_season_performance" (
    "id" SERIAL NOT NULL,
    "discipline" TEXT NOT NULL,
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "season_year" INTEGER NOT NULL,
    "pressure_balls" INTEGER NOT NULL DEFAULT 0,
    "pressure_innings" INTEGER NOT NULL DEFAULT 0,
    "pressure_matches" INTEGER NOT NULL DEFAULT 0,
    "pressure_runs_or_conceded" INTEGER NOT NULL DEFAULT 0,
    "pressure_dismissals_or_wickets" INTEGER NOT NULL DEFAULT 0,
    "primary_rate" DOUBLE PRECISION,
    "net_impact_rate" DOUBLE PRECISION,

    CONSTRAINT "player_season_performance_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "batting_rankings" (
    "player_id" INTEGER NOT NULL,
    "rank" INTEGER NOT NULL,
    "is_top10" BOOLEAN NOT NULL DEFAULT false,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "team_context" TEXT,
    "competition_context" TEXT NOT NULL,
    "seasons_represented" TEXT,
    "evidence_tier" TEXT NOT NULL,
    "final_ranking_score" DOUBLE PRECISION NOT NULL,
    "performance_score" DOUBLE PRECISION NOT NULL,
    "reliability_score" DOUBLE PRECISION NOT NULL,
    "evidence_score" DOUBLE PRECISION NOT NULL,
    "norm_perf_score" DOUBLE PRECISION NOT NULL,
    "norm_rel_score" DOUBLE PRECISION NOT NULL,
    "norm_extreme_and_lift_score" DOUBLE PRECISION NOT NULL,
    "norm_evidence_score" DOUBLE PRECISION NOT NULL,
    "score_balanced_primary" DOUBLE PRECISION NOT NULL,
    "score_performance_dominant" DOUBLE PRECISION NOT NULL,
    "score_reliability_dominant" DOUBLE PRECISION NOT NULL,
    "rank_performance_dominant" INTEGER NOT NULL,
    "rank_reliability_dominant" INTEGER NOT NULL,
    "eb_pressure_impact" DOUBLE PRECISION NOT NULL,
    "raw_pressure_impact" DOUBLE PRECISION NOT NULL,
    "pressure_runs" INTEGER NOT NULL,
    "pressure_balls_faced" INTEGER NOT NULL,
    "pressure_strike_rate" DOUBLE PRECISION,
    "pressure_average" DOUBLE PRECISION,
    "pressure_boundary_pct" DOUBLE PRECISION,
    "pressure_dot_ball_pct" DOUBLE PRECISION,
    "pressure_innings" INTEGER NOT NULL,
    "unique_matches" INTEGER NOT NULL,
    "seasons_count" INTEGER NOT NULL,
    "extreme_balls" INTEGER NOT NULL DEFAULT 0,
    "extreme_raw_impact" DOUBLE PRECISION,
    "extreme_primary_rate" DOUBLE PRECISION,
    "extreme_innings" INTEGER NOT NULL DEFAULT 0,
    "impact_ci95_low" DOUBLE PRECISION,
    "impact_ci95_high" DOUBLE PRECISION,
    "mc_rank_p05" DOUBLE PRECISION,
    "mc_rank_median" DOUBLE PRECISION,
    "mc_rank_p95" DOUBLE PRECISION,
    "mc_prob_top10_pct" DOUBLE PRECISION,
    "methods_in_top10_out_of_8" INTEGER,
    "stability_tier" TEXT,
    "key_strengths" TEXT,
    "main_limitation" TEXT,
    "confidence_description" TEXT,

    CONSTRAINT "batting_rankings_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "bowling_rankings" (
    "player_id" INTEGER NOT NULL,
    "rank" INTEGER NOT NULL,
    "is_top10" BOOLEAN NOT NULL DEFAULT false,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "pace_or_spin" TEXT,
    "team_context" TEXT,
    "competition_context" TEXT NOT NULL,
    "seasons_represented" TEXT,
    "evidence_tier" TEXT NOT NULL,
    "final_ranking_score" DOUBLE PRECISION NOT NULL,
    "performance_score" DOUBLE PRECISION NOT NULL,
    "reliability_score" DOUBLE PRECISION NOT NULL,
    "evidence_score" DOUBLE PRECISION NOT NULL,
    "norm_perf_score" DOUBLE PRECISION NOT NULL,
    "norm_rel_score" DOUBLE PRECISION NOT NULL,
    "norm_extreme_and_lift_score" DOUBLE PRECISION NOT NULL,
    "norm_evidence_score" DOUBLE PRECISION NOT NULL,
    "score_balanced_primary" DOUBLE PRECISION NOT NULL,
    "score_performance_dominant" DOUBLE PRECISION NOT NULL,
    "score_reliability_dominant" DOUBLE PRECISION NOT NULL,
    "rank_performance_dominant" INTEGER NOT NULL,
    "rank_reliability_dominant" INTEGER NOT NULL,
    "eb_pressure_impact" DOUBLE PRECISION NOT NULL,
    "raw_pressure_impact" DOUBLE PRECISION NOT NULL,
    "pressure_legal_balls" INTEGER NOT NULL,
    "pressure_runs_conceded" INTEGER NOT NULL,
    "pressure_wickets" INTEGER NOT NULL,
    "pressure_economy" DOUBLE PRECISION,
    "pressure_bowling_average" DOUBLE PRECISION,
    "pressure_bowling_strike_rate" DOUBLE PRECISION,
    "pressure_dot_ball_pct" DOUBLE PRECISION,
    "pressure_boundary_conceded_pct" DOUBLE PRECISION,
    "pressure_rsae_per_over" DOUBLE PRECISION,
    "pressure_innings" INTEGER NOT NULL,
    "unique_matches" INTEGER NOT NULL,
    "seasons_count" INTEGER NOT NULL,
    "extreme_balls" INTEGER NOT NULL DEFAULT 0,
    "extreme_raw_impact" DOUBLE PRECISION,
    "extreme_primary_rate" DOUBLE PRECISION,
    "extreme_innings" INTEGER NOT NULL DEFAULT 0,
    "impact_ci95_low" DOUBLE PRECISION,
    "impact_ci95_high" DOUBLE PRECISION,
    "mc_rank_p05" DOUBLE PRECISION,
    "mc_rank_median" DOUBLE PRECISION,
    "mc_rank_p95" DOUBLE PRECISION,
    "mc_prob_top10_pct" DOUBLE PRECISION,
    "methods_in_top10_out_of_8" INTEGER,
    "stability_tier" TEXT,
    "key_strengths" TEXT,
    "main_limitation" TEXT,
    "confidence_description" TEXT,

    CONSTRAINT "bowling_rankings_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "matches" (
    "match_id" INTEGER NOT NULL,
    "comp_id" INTEGER NOT NULL,
    "comp_name" TEXT NOT NULL,
    "match_format" TEXT NOT NULL,
    "season" TEXT NOT NULL,
    "eligibility_category" TEXT NOT NULL,
    "match_number" TEXT,
    "match_date" TIMESTAMP(3) NOT NULL,
    "stage" TEXT,
    "venue_id" INTEGER,
    "venue_country" TEXT,
    "home_team_id" INTEGER,
    "home_team" TEXT NOT NULL,
    "away_team_id" INTEGER,
    "away_team" TEXT NOT NULL,
    "toss_win_team_id" INTEGER,
    "toss_opted" TEXT,
    "knock_out" BOOLEAN NOT NULL DEFAULT false,
    "win_team_id" INTEGER,
    "result" TEXT,
    "has_ball_data" BOOLEAN NOT NULL DEFAULT false,
    "is_abandoned_match" BOOLEAN NOT NULL DEFAULT false,
    "is_no_result_match" BOOLEAN NOT NULL DEFAULT false,
    "is_dls_match" BOOLEAN NOT NULL DEFAULT false,
    "is_reduced_overs_match" BOOLEAN NOT NULL DEFAULT false,
    "match_completion_classification" TEXT NOT NULL,
    "regular_deliveries" INTEGER NOT NULL DEFAULT 0,
    "regular_legal_deliveries" INTEGER NOT NULL DEFAULT 0,
    "innings_recorded_count" INTEGER NOT NULL DEFAULT 0,
    "inn1_total_runs" INTEGER,
    "inn1_wickets" INTEGER,
    "inn1_legal_balls" INTEGER,
    "inn2_total_runs" INTEGER,
    "inn2_wickets" INTEGER,
    "inn2_legal_balls" INTEGER,
    "revised_target_num" INTEGER,
    "mean_i1_pressure" DOUBLE PRECISION,
    "max_i1_pressure" DOUBLE PRECISION,
    "mean_chase_pressure" DOUBLE PRECISION,
    "max_chase_pressure" DOUBLE PRECISION,
    "mean_bowling_pressure" DOUBLE PRECISION,
    "max_bowling_pressure" DOUBLE PRECISION,
    "high_or_extreme_batting_balls" INTEGER,
    "high_or_extreme_bowling_balls" INTEGER,

    CONSTRAINT "matches_pkey" PRIMARY KEY ("match_id")
);

-- CreateTable
CREATE TABLE "innings" (
    "id" SERIAL NOT NULL,
    "match_id" INTEGER NOT NULL,
    "innings" INTEGER NOT NULL,
    "comp_id" INTEGER NOT NULL,
    "comp_name" TEXT NOT NULL,
    "match_format" TEXT NOT NULL,
    "season" TEXT NOT NULL,
    "innings_type" TEXT NOT NULL,
    "batting_team_id" INTEGER NOT NULL,
    "batting_team_name" TEXT,
    "bowling_team_id" INTEGER NOT NULL,
    "bowling_team_name" TEXT,
    "total_deliveries" INTEGER NOT NULL,
    "legal_deliveries" INTEGER NOT NULL,
    "batter_balls_faced" INTEGER NOT NULL,
    "wides" INTEGER NOT NULL DEFAULT 0,
    "overstep_noballs" INTEGER NOT NULL DEFAULT 0,
    "other_noballs" INTEGER NOT NULL DEFAULT 0,
    "batter_runs" INTEGER NOT NULL,
    "extras_total_runs" INTEGER NOT NULL,
    "total_runs" INTEGER NOT NULL,
    "bowler_conceded_runs" INTEGER NOT NULL,
    "wickets" INTEGER NOT NULL,
    "bowler_wickets" INTEGER NOT NULL,
    "run_outs" INTEGER NOT NULL DEFAULT 0,
    "is_dls_match" BOOLEAN NOT NULL DEFAULT false,
    "is_reduced_overs_match" BOOLEAN NOT NULL DEFAULT false,
    "batting_pressure_valid_balls" INTEGER NOT NULL DEFAULT 0,
    "bowling_pressure_valid_balls" INTEGER NOT NULL DEFAULT 0,
    "mean_batting_pressure" DOUBLE PRECISION,
    "max_batting_pressure" DOUBLE PRECISION,
    "high_or_extreme_batting_balls" INTEGER NOT NULL DEFAULT 0,
    "extreme_batting_balls" INTEGER NOT NULL DEFAULT 0,
    "mean_bowling_pressure" DOUBLE PRECISION,
    "max_bowling_pressure" DOUBLE PRECISION,
    "high_or_extreme_bowling_balls" INTEGER NOT NULL DEFAULT 0,
    "extreme_bowling_balls" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "innings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "pressure_summaries" (
    "id" SERIAL NOT NULL,
    "summary_type" TEXT NOT NULL,
    "framework" TEXT NOT NULL,
    "segment_key" TEXT NOT NULL,
    "payload_json" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "pressure_summaries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "methodology_sections" (
    "section_number" INTEGER NOT NULL,
    "slug" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "content_md" TEXT NOT NULL,
    "formulas_json" JSONB,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "methodology_sections_pkey" PRIMARY KEY ("section_number")
);

-- CreateTable
CREATE TABLE "admin_users" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "role" TEXT NOT NULL DEFAULT 'ADMIN',
    "is_active" BOOLEAN NOT NULL DEFAULT true,
    "last_login_at" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "admin_users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "data_import_logs" (
    "id" SERIAL NOT NULL,
    "batch_id" TEXT NOT NULL,
    "triggered_by" TEXT NOT NULL DEFAULT 'CLI',
    "admin_user_id" INTEGER,
    "status" TEXT NOT NULL,
    "source_row_count" INTEGER NOT NULL DEFAULT 0,
    "inserted_count" INTEGER NOT NULL DEFAULT 0,
    "skipped_count" INTEGER NOT NULL DEFAULT 0,
    "table_counts_json" JSONB,
    "reconcile_passed" BOOLEAN,
    "reconcile_summary" JSONB,
    "errors_json" JSONB,
    "duration_ms" INTEGER,
    "started_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3),

    CONSTRAINT "data_import_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "player_pressure_breakdowns" (
    "id" SERIAL NOT NULL,
    "discipline" TEXT NOT NULL,
    "player_id" INTEGER NOT NULL,
    "player_name" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "pressure_level" TEXT NOT NULL,
    "balls" INTEGER NOT NULL DEFAULT 0,
    "runs" INTEGER NOT NULL DEFAULT 0,
    "wickets_or_dismissals" INTEGER NOT NULL DEFAULT 0,
    "dot_balls" INTEGER NOT NULL DEFAULT 0,
    "boundary_balls" INTEGER NOT NULL DEFAULT 0,
    "innings_count" INTEGER NOT NULL DEFAULT 0,
    "matches_count" INTEGER NOT NULL DEFAULT 0,
    "seasons_count" INTEGER NOT NULL DEFAULT 0,
    "primary_rate" DOUBLE PRECISION,
    "average" DOUBLE PRECISION,
    "dot_ball_pct" DOUBLE PRECISION,
    "boundary_pct" DOUBLE PRECISION,
    "rvae_or_rsae_rate" DOUBLE PRECISION,
    "net_impact_rate" DOUBLE PRECISION,
    "mean_pressure_index" DOUBLE PRECISION,

    CONSTRAINT "player_pressure_breakdowns_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "pressure_analytics_cube" (
    "id" SERIAL NOT NULL,
    "framework" TEXT NOT NULL,
    "match_format" TEXT NOT NULL,
    "season" TEXT NOT NULL,
    "innings" INTEGER NOT NULL,
    "match_phase" TEXT NOT NULL,
    "pressure_level" TEXT NOT NULL,
    "deliveries_count" INTEGER NOT NULL DEFAULT 0,
    "legal_balls_count" INTEGER NOT NULL DEFAULT 0,
    "batter_balls_faced" INTEGER NOT NULL DEFAULT 0,
    "runs_total" INTEGER NOT NULL DEFAULT 0,
    "batter_runs" INTEGER NOT NULL DEFAULT 0,
    "bowler_conceded_runs" INTEGER NOT NULL DEFAULT 0,
    "wickets_total" INTEGER NOT NULL DEFAULT 0,
    "bowler_wickets" INTEGER NOT NULL DEFAULT 0,
    "dot_balls_bat" INTEGER NOT NULL DEFAULT 0,
    "dot_balls_bowl" INTEGER NOT NULL DEFAULT 0,
    "boundary_balls_bat" INTEGER NOT NULL DEFAULT 0,
    "boundary_balls_bowl" INTEGER NOT NULL DEFAULT 0,
    "sum_pressure_index" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "valid_pressure_count" INTEGER NOT NULL DEFAULT 0,
    "sum_rrr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "valid_rrr_count" INTEGER NOT NULL DEFAULT 0,
    "sum_crr" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "valid_crr_count" INTEGER NOT NULL DEFAULT 0,
    "sum_runs_remaining" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "valid_runs_rem_count" INTEGER NOT NULL DEFAULT 0,
    "sum_balls_remaining" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "valid_balls_rem_count" INTEGER NOT NULL DEFAULT 0,
    "sum_wickets_lost" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "sum_wickets_in_hand" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "sum_cum_score" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "sum_balls_elapsed" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "score_bins_json" JSONB NOT NULL,

    CONSTRAINT "pressure_analytics_cube_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ranking_robustness_audits" (
    "id" SERIAL NOT NULL,
    "audit_type" TEXT NOT NULL,
    "discipline" TEXT NOT NULL,
    "spec_key" TEXT NOT NULL,
    "payload_json" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ranking_robustness_audits_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "admin_audit_logs" (
    "id" SERIAL NOT NULL,
    "admin_user_id" INTEGER,
    "actor_email" TEXT,
    "action" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "ip_address" TEXT,
    "details_json" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "admin_audit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "players_standardized_display_name_idx" ON "players"("standardized_display_name");

-- CreateIndex
CREATE INDEX "players_in_primary_eligible_comp_idx" ON "players"("in_primary_eligible_comp");

-- CreateIndex
CREATE INDEX "players_inferred_playing_role_idx" ON "players"("inferred_playing_role");

-- CreateIndex
CREATE INDEX "players_shares_name_with_other_player_id_idx" ON "players"("shares_name_with_other_player_id");

-- CreateIndex
CREATE INDEX "player_batting_performance_batting_role_idx" ON "player_batting_performance"("batting_role");

-- CreateIndex
CREATE INDEX "player_batting_performance_pressure_balls_faced_idx" ON "player_batting_performance"("pressure_balls_faced");

-- CreateIndex
CREATE INDEX "player_batting_performance_pressure_strike_rate_idx" ON "player_batting_performance"("pressure_strike_rate");

-- CreateIndex
CREATE INDEX "player_bowling_performance_bowling_role_idx" ON "player_bowling_performance"("bowling_role");

-- CreateIndex
CREATE INDEX "player_bowling_performance_pace_or_spin_idx" ON "player_bowling_performance"("pace_or_spin");

-- CreateIndex
CREATE INDEX "player_bowling_performance_pressure_legal_balls_idx" ON "player_bowling_performance"("pressure_legal_balls");

-- CreateIndex
CREATE INDEX "player_bowling_performance_pressure_economy_idx" ON "player_bowling_performance"("pressure_economy");

-- CreateIndex
CREATE INDEX "player_batting_reliability_evidence_tier_idx" ON "player_batting_reliability"("evidence_tier");

-- CreateIndex
CREATE INDEX "player_batting_reliability_is_primary_eligible_idx" ON "player_batting_reliability"("is_primary_eligible");

-- CreateIndex
CREATE INDEX "player_bowling_reliability_evidence_tier_idx" ON "player_bowling_reliability"("evidence_tier");

-- CreateIndex
CREATE INDEX "player_bowling_reliability_is_primary_eligible_idx" ON "player_bowling_reliability"("is_primary_eligible");

-- CreateIndex
CREATE INDEX "player_pressure_exposure_discipline_evidence_tier_idx" ON "player_pressure_exposure"("discipline", "evidence_tier");

-- CreateIndex
CREATE UNIQUE INDEX "player_pressure_exposure_discipline_player_id_key" ON "player_pressure_exposure"("discipline", "player_id");

-- CreateIndex
CREATE INDEX "player_season_performance_discipline_season_year_idx" ON "player_season_performance"("discipline", "season_year");

-- CreateIndex
CREATE INDEX "player_season_performance_player_id_idx" ON "player_season_performance"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "player_season_performance_discipline_player_id_season_year_key" ON "player_season_performance"("discipline", "player_id", "season_year");

-- CreateIndex
CREATE UNIQUE INDEX "batting_rankings_rank_key" ON "batting_rankings"("rank");

-- CreateIndex
CREATE INDEX "batting_rankings_is_top10_idx" ON "batting_rankings"("is_top10");

-- CreateIndex
CREATE INDEX "batting_rankings_final_ranking_score_idx" ON "batting_rankings"("final_ranking_score");

-- CreateIndex
CREATE INDEX "batting_rankings_role_idx" ON "batting_rankings"("role");

-- CreateIndex
CREATE INDEX "batting_rankings_competition_context_idx" ON "batting_rankings"("competition_context");

-- CreateIndex
CREATE INDEX "batting_rankings_stability_tier_idx" ON "batting_rankings"("stability_tier");

-- CreateIndex
CREATE UNIQUE INDEX "bowling_rankings_rank_key" ON "bowling_rankings"("rank");

-- CreateIndex
CREATE INDEX "bowling_rankings_is_top10_idx" ON "bowling_rankings"("is_top10");

-- CreateIndex
CREATE INDEX "bowling_rankings_final_ranking_score_idx" ON "bowling_rankings"("final_ranking_score");

-- CreateIndex
CREATE INDEX "bowling_rankings_role_idx" ON "bowling_rankings"("role");

-- CreateIndex
CREATE INDEX "bowling_rankings_pace_or_spin_idx" ON "bowling_rankings"("pace_or_spin");

-- CreateIndex
CREATE INDEX "bowling_rankings_competition_context_idx" ON "bowling_rankings"("competition_context");

-- CreateIndex
CREATE INDEX "bowling_rankings_stability_tier_idx" ON "bowling_rankings"("stability_tier");

-- CreateIndex
CREATE INDEX "matches_match_format_season_idx" ON "matches"("match_format", "season");

-- CreateIndex
CREATE INDEX "matches_match_date_idx" ON "matches"("match_date");

-- CreateIndex
CREATE INDEX "matches_comp_id_idx" ON "matches"("comp_id");

-- CreateIndex
CREATE INDEX "matches_match_completion_classification_idx" ON "matches"("match_completion_classification");

-- CreateIndex
CREATE INDEX "innings_match_format_season_idx" ON "innings"("match_format", "season");

-- CreateIndex
CREATE UNIQUE INDEX "innings_match_id_innings_key" ON "innings"("match_id", "innings");

-- CreateIndex
CREATE INDEX "pressure_summaries_summary_type_framework_idx" ON "pressure_summaries"("summary_type", "framework");

-- CreateIndex
CREATE UNIQUE INDEX "pressure_summaries_summary_type_framework_segment_key_key" ON "pressure_summaries"("summary_type", "framework", "segment_key");

-- CreateIndex
CREATE UNIQUE INDEX "methodology_sections_slug_key" ON "methodology_sections"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "admin_users_email_key" ON "admin_users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "data_import_logs_batch_id_key" ON "data_import_logs"("batch_id");

-- CreateIndex
CREATE INDEX "data_import_logs_started_at_idx" ON "data_import_logs"("started_at");

-- CreateIndex
CREATE INDEX "data_import_logs_status_idx" ON "data_import_logs"("status");

-- CreateIndex
CREATE INDEX "player_pressure_breakdowns_discipline_pressure_level_idx" ON "player_pressure_breakdowns"("discipline", "pressure_level");

-- CreateIndex
CREATE INDEX "player_pressure_breakdowns_player_id_idx" ON "player_pressure_breakdowns"("player_id");

-- CreateIndex
CREATE UNIQUE INDEX "player_pressure_breakdowns_discipline_player_id_pressure_le_key" ON "player_pressure_breakdowns"("discipline", "player_id", "pressure_level");

-- CreateIndex
CREATE INDEX "pressure_analytics_cube_framework_match_format_season_idx" ON "pressure_analytics_cube"("framework", "match_format", "season");

-- CreateIndex
CREATE INDEX "pressure_analytics_cube_framework_pressure_level_idx" ON "pressure_analytics_cube"("framework", "pressure_level");

-- CreateIndex
CREATE UNIQUE INDEX "pressure_analytics_cube_framework_match_format_season_innin_key" ON "pressure_analytics_cube"("framework", "match_format", "season", "innings", "match_phase", "pressure_level");

-- CreateIndex
CREATE INDEX "ranking_robustness_audits_audit_type_discipline_idx" ON "ranking_robustness_audits"("audit_type", "discipline");

-- CreateIndex
CREATE UNIQUE INDEX "ranking_robustness_audits_audit_type_discipline_spec_key_key" ON "ranking_robustness_audits"("audit_type", "discipline", "spec_key");

-- CreateIndex
CREATE INDEX "admin_audit_logs_created_at_idx" ON "admin_audit_logs"("created_at");

-- CreateIndex
CREATE INDEX "admin_audit_logs_action_idx" ON "admin_audit_logs"("action");

-- AddForeignKey
ALTER TABLE "player_batting_performance" ADD CONSTRAINT "player_batting_performance_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_bowling_performance" ADD CONSTRAINT "player_bowling_performance_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_batting_reliability" ADD CONSTRAINT "player_batting_reliability_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_bowling_reliability" ADD CONSTRAINT "player_bowling_reliability_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_pressure_exposure" ADD CONSTRAINT "player_pressure_exposure_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_season_performance" ADD CONSTRAINT "player_season_performance_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "batting_rankings" ADD CONSTRAINT "batting_rankings_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bowling_rankings" ADD CONSTRAINT "bowling_rankings_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "innings" ADD CONSTRAINT "innings_match_id_fkey" FOREIGN KEY ("match_id") REFERENCES "matches"("match_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "data_import_logs" ADD CONSTRAINT "data_import_logs_admin_user_id_fkey" FOREIGN KEY ("admin_user_id") REFERENCES "admin_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "player_pressure_breakdowns" ADD CONSTRAINT "player_pressure_breakdowns_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("player_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "admin_audit_logs" ADD CONSTRAINT "admin_audit_logs_admin_user_id_fkey" FOREIGN KEY ("admin_user_id") REFERENCES "admin_users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

