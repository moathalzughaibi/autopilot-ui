
# Autopilot Project — Starter Pack

This ZIP contains the initial data layer files for the 7-step master plan trading project.

## Files
- ML_Trading_DataLayer_v1.xlsx
- ML_Trading_DataLayer_with_Autopilot_API_v1.xlsx
- autopilot_api_dictionary_v1.json

## Suggested placement on RunPod
Upload the ZIP to your mounted Network Volume and unzip under:
`/workspace/data/`

Example (inside your Pod terminal):
```
cd /workspace/data
unzip Autopilot_Project_Starter_2025-10-26.zip
```

## Minimal environment setup (inside the Pod)
```
mkdir -p ~/workspace/{notebooks,models,logs}
python3 -m venv ~/workspace/.venv && source ~/workspace/.venv/bin/activate
pip install --upgrade pip wheel
pip install numpy pandas polars matplotlib scikit-learn statsmodels ta yfinance openpyxl
```

## Smoke test
```
python - <<'PY'
import pandas as pd, os
print(pd.read_excel('/workspace/data/ML_Trading_DataLayer_v1.xlsx', nrows=5).head())
print('Data folder:', os.listdir('/workspace/data'))
PY
```
