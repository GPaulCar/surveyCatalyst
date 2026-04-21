$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path ".").Path
python -m streamlit run (Join-Path $repoRoot "app\map_app.py")
