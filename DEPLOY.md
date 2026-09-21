# Apply the Week 4 extension and redeploy

This is an **upgrade for your existing GitHub repository**. It adds the 3 missing views without removing the four animations or replacing your original data-preparation script. The ZIP intentionally omits the raw/processed PJME CSVs because they are **already in your repository**.

## 1. Back up the current app and extract files

Copy the downloaded `PJME_Week4_Complete_Upgrade.zip` to your Downloads folder. In macOS Terminal:

```bash
cd ~/Documents/Data_visual/HW_4/PJM-Energy-Trends-and-Seasonality
cp app.py app_before_week4_upgrade.py
unzip -o ~/Downloads/PJME_Week4_Complete_Upgrade.zip -d .
```

If macOS added a `(1)` to the ZIP name, substitute its actual filename. The archive includes `app.py`, `src/analysis.py`, `src/__init__.py`, `README.md`, `requirements.txt`, `requirements-notebook.txt`, `DEPLOY.md`, the notebook and `tests/test_analysis.py` / `tests/test_charts.py`. It does **not** overwrite `src/prepare_data.py` or the `data/` directory.

## 2. Activate the existing HW_4 virtual environment

```bash
source ../.venv/bin/activate
python -m pip install -r requirements.txt
```

The environment is in `HW_4/.venv`, **one level above** this repository. The path is not `.venv/bin/activate` unless you created a second venv inside the repository.

## 3. Verify before pushing

```bash
python -m py_compile app.py src/analysis.py
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

Inspect sidebar views 5, 6, and 7. In view 7, drag across the **bottom** overview chart to filter the upper chart. To inspect the full set, clear the selection.

## 4. Push only intended files

```bash
# Leave the local backup file untracked; do not add it to Git.
git add app.py src/analysis.py src/__init__.py README.md requirements.txt requirements-notebook.txt DEPLOY.md notebooks/01_time_series_analysis.ipynb tests/test_analysis.py tests/test_charts.py
git status
git commit -m "Add uncertainty, decomposition, and Altair date brush"
git push origin main
```

If the notebook is already in Git, the command updates it; if it is not there, it adds the companion analysis. GitHub/Streamlit will redeploy the existing app URL after the push:

https://pjm-energy-trends-and-seasonality.streamlit.app/

If the cloud build fails, open the app's **Manage app → Logs** in Streamlit Community Cloud. Ensure cloud Python 3.13 and that `src/analysis.py` was committed.

## Data note

The ZIP is an **overlay**, not an independent dataset download. It requires your existing files under `data/processed/`, as documented in the README. A fresh clone of your already populated GitHub repo supplies them.
