# Python environment setup

## What this pack does

- standardises runtime Python dependencies
- adds the repo `src` folder to the active venv using a `.pth` file
- avoids relying on manual `PYTHONPATH` commands

## Files

- `requirements.txt`
- `requirements-dev.txt`
- `scripts/bootstrap_python_env.ps1`
- `scripts/verify_python_env.py`

## Usage

From repo root:

```powershell
.\scriptsootstrap_python_env.ps1
python .\scriptserify_python_env.py
```

If your venv path differs:

```powershell
.\scriptsootstrap_python_env.ps1 -VenvPath .\.venv
```

## Result

After bootstrap, imports like these should work directly:

```python
from orchestration.pipeline_orchestrator import PipelineOrchestrator
from export.export_pack_service import ExportPackService
```

without setting:

```powershell
$env:PYTHONPATH="src"
```

## External non-pip dependencies

These are still outside `requirements.txt` and must remain documented separately:

- PostgreSQL
- PostGIS
- GDAL / ogr2ogr
