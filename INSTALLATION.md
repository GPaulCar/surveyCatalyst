# surveyCatalyst Installation

surveyCatalyst is a Windows-first application. The repo includes the backend, frontend, and a local Postgres runtime, so installation is mostly about setting up the Python environment and validating the bundled services.

## Prerequisites

- Windows
- A working Python installation
- The bundled `postgres/` directory present in the repo
- A virtual environment at `.surveyCatalyst_venv`

## Install Python dependencies

From the repo root:

```powershell
.\scripts\bootstrap_python_env.ps1
```

That script:

- writes a `.pth` file so `src/` is importable from the virtual environment
- upgrades `pip`
- installs `requirements.txt`

If your virtual environment lives elsewhere, pass it explicitly:

```powershell
.\scripts\bootstrap_python_env.ps1 -VenvPath .\.venv
```

## Verify the environment

Run the import check after bootstrapping:

```powershell
python .\scripts\verify_python_env.py
```

That should print `OK` lines for the core modules.

## Start the application

Start the local database and API:

```powershell
python scripts/system_control.py restart
```

Then open the local app URL served by the API.

## Stop the application

```powershell
python scripts/system_control.py stop
```

## Runtime notes

- `scripts/system_control.py` manages the local Postgres process and the FastAPI process.
- `scripts/run_api.py` launches the API.
- `app/static/ui_boot.js` contains the frontend runtime, including the bilingual UI.
- `src/api/app.py` serves the HTTP API.

## If installation fails

Check these first:

- `runtime/logs/postgres.err.log`
- `runtime/logs/api.err.log`
- `python scripts/system_control.py status`

If Python imports fail, rerun the bootstrap script and then re-run the verification script.

