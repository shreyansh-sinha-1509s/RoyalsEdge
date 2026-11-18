# SupeRR Selector Season 2 — Rajasthan Royals IPL 2027 Auction Strategy

Professional cricket analytics workspace for **SupeRR Selector Season 2**, focused on data auditing, pressure-performance modeling, player evaluation, and auction strategy for the Rajasthan Royals (IPL 2027).

---

## Project Structure

```text
SupeRR_Selector/
├── dashboard/              # Interactive dashboard assets and app code
├── data/
│   ├── raw/
│   │   └── Data Pack/      # Original unmodified competition CSVs & Round 1 PDF (private)
│   ├── processed/          # Cleaned and engineered datasets (private, gitignored)
│   └── external/           # Optional publicly sourced reference datasets
├── notebooks/              # Exploratory notebooks and analysis prototypes
├── outputs/                # Audit CSVs, summary tables, and generated artifacts
├── report/                 # Final reports, slide decks, and written deliverables
├── src/
│   └── 01_dataset_audit.py # Read-only competition dataset audit script
├── .gitignore              # Excludes environments, caches, OS metadata, and private data
├── README.md               # Project overview and run instructions
├── README_FIRST.txt        # Original starter reference notes
└── requirements.txt        # Python dependencies
```

---

## Data Privacy & Integrity Rules

- **Keep raw and processed competition data private.** Never publish `data/raw/` or `data/processed/` to GitHub, public dashboards, or public tools.
- **Do not modify original files.** All CSV files inside `data/raw/Data Pack/` (`ball_by_ball.csv`, `competitions.csv`, `competition_team_player_mapping.csv`, `matches.csv`, `playing_eleven.csv`, `teams.csv`) must keep their original filenames and column names untouched.
- **Relative paths only.** All scripts in `src/` resolve paths relative to the `SupeRR_Selector/` project root (`Path(__file__).resolve().parents[1]`), avoiding hardcoded absolute paths.
- **Ignore OS metadata.** `__MACOSX/`, `.DS_Store`, and AppleDouble (`._*`) files are ignored via `.gitignore`.

---

## Setup & How to Run (Windows PowerShell)

1. Open PowerShell in the `SupeRR_Selector/` directory:
   ```powershell
   cd "SupeRR_Selector"
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(If PowerShell blocks script execution, run once in the same terminal:)*
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

3. Upgrade `pip` and install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Run the dataset audit script (Phase 2):
   ```powershell
   python src\01_dataset_audit.py
   ```
   > **Note on data input format:** The preserved starter script `src/01_dataset_audit.py` currently looks for a single `.zip` archive in `data/raw/`, whereas the dataset is currently extracted in `data/raw/Data Pack/`. Before running Phase 2, either update the loader in `src/01_dataset_audit.py` to read directly from `data/raw/Data Pack/` (with optional `.zip` fallback) or place the original data-pack `.zip` in `data/raw/`.

---

## Project Phases

- **Phase 1 (Complete):** Project root consolidation, folder structure setup, duplicate reconciliation, `.gitignore`, and documentation.
- **Phase 2 (Next):** Read-only dataset audit (`01_dataset_audit.py`), schema & delivery-logic validation, and competition coverage verification.
- **Phase 3+ (Upcoming):** Pressure metric definition, feature engineering, player evaluation, auction modeling, dashboard, and final report.

