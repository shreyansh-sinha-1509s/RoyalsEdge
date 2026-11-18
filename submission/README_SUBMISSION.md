# SupeRR Selector Season 2 — Round 1 Submission Package (`RR PERFORMANCE LAB`)

> **HOLD FOR REVIEW:** Nothing has been submitted to Unstop or any external platform. Review every file below and verify exact player names in the Unstop dropdowns before uploading.

## Official Round 1 Submission Checklist (Per Supplied Problem Statement PDF)

1. **Component 01 — Ordered Player Rankings (Unstop Dropdowns):**
   - Two separate ordered Top-10 lists (Rank 1 = highest-rated, zero duplicates within a list).
   - Must **exactly match** the uploaded Methodology Report.
2. **Component 02 — Methodology Report Upload:**
   - Upload `RR_Performance_Lab_Methodology_Report.pdf` (with `RR_Performance_Lab_Executive_Summary.pdf` and `RR_Performance_Lab_Final_Rankings.xlsx` available as companion review materials).

---

## Ordered Top 10 Batters (For Unstop Dropdown Entry)

1. **Matthew Wade** (`player_id=796`, Score `80.51`)
2. **Naman Dhir** (`player_id=37052`, Score `77.83`)
3. **Ibrahim Zadran** (`player_id=6448`, Score `76.54`)
4. **Ravindra Jadeja** (`player_id=152`, Score `74.66`)
5. **Shai Hope** (`player_id=4369`, Score `73.68`)
6. **Ayush Badoni** (`player_id=6460`, Score `73.24`)
7. **Ruturaj Gaikwad** (`player_id=6059`, Score `72.96`)
8. **Tim David** (`player_id=6396`, Score `72.95`)
9. **Heinrich Klaasen** (`player_id=4260`, Score `72.47`)
10. **Romario Shepherd** (`player_id=6726`, Score `71.40`)

## Ordered Top 10 Bowlers (For Unstop Dropdown Entry)

1. **Nasum Ahmed** (`player_id=4658`, Score `76.11`)
2. **Axar Patel** (`player_id=2876`, Score `75.92`)
3. **Mark Wood** (`player_id=2985`, Score `74.10`)
4. **Rashid Khan** (`player_id=4722`, Score `73.14`)
5. **Mark Adair** (`player_id=5379`, Score `71.79`)
6. **Eshan Malinga** (`player_id=39657`, Score `71.12`)
7. **Ravichandran Ashwin** (`player_id=305`, Score `70.13`)
8. **Joshua Little** (`player_id=4807`, Score `69.29`)
9. **Wanindu Hasaranga** (`player_id=4900`, Score `68.61`)
10. **Matheesha Pathirana** (`player_id=8661`, Score `68.33`)

---

## Files Inside `submission/`

| File | Purpose |
| :--- | :--- |
| `RR_Performance_Lab_Top_10_Batters.csv` | Audited Top 10 Batters table with IDs, roles, scores, exposure, 95% CIs, strengths & limitations |
| `RR_Performance_Lab_Top_10_Bowlers.csv` | Audited Top 10 Bowlers table with IDs, roles, scores, exposure, 95% CIs, strengths & limitations |
| `RR_Performance_Lab_Final_Rankings.xlsx` | Multi-sheet RR PERFORMANCE LAB workbook (Top 10 Batters, Top 10 Bowlers, Method Comparison, Robustness, Overlap, Alternatives, Eligibility) |
| `RR_Performance_Lab_Methodology_Report.pdf` | Polished multi-page competition Methodology Report (for Unstop upload) |
| `RR_Performance_Lab_Methodology_Report.md` | Full 20-section Markdown source of the Methodology Report |
| `RR_Performance_Lab_Executive_Summary.pdf` | Concise 2-page franchise decision-maker Executive Summary |
| `README_SUBMISSION.md` | This submission guide & pre-upload checklist |

## Data Governance & Integrity Verification

- Original competition CSVs in `data/raw/Data Pack/` remain **100% unmodified** and private (excluded via `.gitignore`).
- Primary analysis strictly covers eligible **IPL (2022–2026)** and **T20I (2022–2026)** regular innings (`0` Super Overs, `0` excluded non-IPL T20 competitions).
- All CSV, Excel, Markdown, and PDF files are programmatically generated from the exact same `data/processed/final_batting_rankings.csv` and `data/processed/final_bowling_rankings.csv` tables and verified by `pytest tests -v`.
