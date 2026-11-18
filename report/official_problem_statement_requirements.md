# Official Round 1 Problem Statement Requirements — SupeRR Selector Season 2

**Primary Source:** `data/raw/Data Pack/Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf` (2 pages, Rajasthan Royals — SupeRR Selector Season 2)

> All requirements below are extracted directly from the supplied Round 1 PDF. This document serves as the authoritative specification for downstream data validation, modeling, and reporting.

---

## 1. Competition Objective

- **Theme:** *Identify the Most Reliable Players Under Pressure*
- **Core Task:** Build a data-driven system that measures how **batters** and **bowlers** perform in **high-pressure match situations compared with their usual (baseline) performance levels**, and use that system to identify and rank the players who deliver **most consistently when it matters**.

---

## 2. Eligible Formats, Seasons, and Supplied Dataset

- **Stated Coverage in Official Brief:** Historical **IPL** and **T20 International (T20I)** data **from 2022 onwards**.
- **Stated Data Components:**
  - **Ball-by-ball data:** Delivery-level match records in CSV format.
  - **Supporting data:** Competitions, teams, players, matches, playing XIs, and competition-team-player mappings.
  - **Analytical Use:** Connect player performance with match situations across competitions and seasons.
- **Verification Note (to be cross-checked in CSV audit):**
  - The PDF mentions "players" alongside `competition-team-player mappings`, whereas the Data Pack contains 6 CSVs (`ball_by_ball.csv`, `matches.csv`, `competitions.csv`, `teams.csv`, `playing_eleven.csv`, `competition_team_player_mapping.csv`) with no standalone `players.csv`.
  - Any competitions in `competitions.csv` outside IPL/T20I or outside `>= 2022` must be audited and documented explicitly rather than silently included or dropped.

---

## 3. Definition & Expectations for Pressure Analysis

- **Participant-Defined Pressure:** The PDF explicitly states *"That is for you to define."*
- **Suggested Context Signals (Non-Exhaustive):**
  - Required run rate (RRR)
  - Wickets in hand
  - Balls remaining
  - Stage of an innings
  - How close the contest is
  - Combination of factors and/or other relevant match-context signals
- **Required Properties of the Pressure Definition:**
  1. **Meaningful justification:** Explain *why* the chosen match situations and indicators represent genuine pressure.
  2. **Discriminative validation:** Demonstrate empirically how the definition distinguishes **high-pressure situations** from **ordinary situations**.
  3. **Dual applicability:** The framework must work coherently for **both batting and bowling** performance.
  4. **Baseline comparison:** Measure high-pressure performance **compared against usual/baseline performance**, not in isolation.
  5. **Consistency focus:** Evaluate reliability/consistency across matches, not single-match spikes.

---

## 4. Ranking Requirements

### Batter Rankings
- Submit an ordered **Top 10 batters** list (Rank 1 through Rank 10) via Unstop dropdowns.
- Rank 1 = highest-rated batter under pressure.
- **No duplicate players** within the Top 10 batters list.

### Bowler Rankings
- Submit an ordered **Top 10 bowlers** list (Rank 1 through Rank 10) via Unstop dropdowns.
- Rank 1 = highest-rated bowler under pressure.
- **No duplicate players** within the Top 10 bowlers list.

### Cross-Component Consistency
- Dropdown selections on Unstop **must exactly match** the rankings presented and justified in the Methodology Report.
- Note: The brief does not explicitly forbid an all-rounder from appearing once in the batter list and once in the bowler list (the restriction states *"Do not repeat a player within the same top-10 list"*).

---

## 5. Submission Format

Two mandatory components + one optional component:

| Component | Format | Requirements |
| :--- | :--- | :--- |
| **01. Player Rankings** | Unstop submission page dropdown fields | Ordered Top 10 batters (Ranks 1–10) and ordered Top 10 bowlers (Ranks 1–10). Exact match with report. |
| **02. Methodology Report** | Uploaded document | Must cover all five required sections listed in Section 6 below. |
| **Optional: Share Your Journey** | Photos, screenshots, or 30–60s video | Optional; explicitly does **not** affect evaluation. Rajasthan Royals will seek permission before publishing. |

---

## 6. Explicit Methodology Requirements & Restrictions

### Required Sections in the Methodology Report
1. **Pressure Definition:** Match situations and indicators used, and why they capture pressure.
2. **Performance Measurement:** Batting and bowling metrics, player baselines, and rating/scoring logic.
3. **Fair Comparisons:** Handling of sample sizes, player eligibility criteria, differing match contexts, and combining/comparing IPL and T20I data.
4. **Evidence for Your Top 10:** Results, comparisons, tables, or charts backing both player selections and exact rank ordering.
5. **Reliability and Limitations:** How cross-match consistency was tested, and where the model may have lower certainty.

### Explicit Rules & Restrictions
- **Reproducibility & Transparency:** The methodology must be transparent enough for someone else to understand and reproduce the approach.
- **Evidence-Based Only:** Rankings must be supported by analysis of the **supplied data**, not reputation alone.
- **Unstated / Open Design Choices (to be explicitly documented in Phase 3):**
  - Exact minimum sample size / eligibility thresholds (balls faced, balls bowled, matches, seasons).
  - Treatment of IPL vs. T20I competition weighting and opponent quality.
  - Handling of 1st-innings vs. 2nd-innings pressure (since Required Run Rate only exists in chases).
  - Treatment of Super Overs, reduced/DLS matches, or non-IPL/non-T20I competitions if present in the data pack.
  - Mapping between player IDs in the data pack and exact player names available in the Unstop dropdowns.

