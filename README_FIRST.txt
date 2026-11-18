SupeRR Selector Season 2 - Round 1 starter

STEP 1 - Extract this folder somewhere simple, e.g. Desktop\SupeRR_Selector.
STEP 2 - Copy the original competition ZIP into data\raw\ (do not extract or edit it).
        The ZIP filename can be anything, but keep only the supplied data-pack ZIP in this folder.
STEP 3 - Open PowerShell in the SupeRR_Selector folder and run:

  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python src\01_dataset_audit.py

If PowerShell blocks activation, run this once in the same terminal:
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1

The audit creates CSV reports in outputs\ and does not modify the original ZIP.

IMPORTANT:
- Do not upload the raw data pack to GitHub, public dashboards, or public AI tools.
- Keep raw data private. Share only approved aggregate results.
- This step audits the source. It does NOT calculate pressure scores or rankings.
- Do not start player rankings until we agree on the pressure definition and validate the delivery logic.
