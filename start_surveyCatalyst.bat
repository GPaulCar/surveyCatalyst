@echo off
cd /d %~dp0
call .\.surveyCatalyst_venv\Scripts\activate.bat
.\postgres\bin\pg_ctl.exe -D postgres\data -o "-p 55433" start
python scripts\start_api_managed.py
start "" http://127.0.0.1:8000/
