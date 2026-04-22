\
@echo off
cd /d C:\Users\Paul\Desktop\dev\surveyCatalyst

call .\.surveyCatalyst_venv\Scripts\activate.bat

echo Starting database...
.\postgres\bin\pg_ctl.exe -D postgres\data -o "-p 55433" start

echo Starting API...
start "surveyCatalyst-api" python scripts\run_api.py

timeout /t 2 >nul

start http://127.0.0.1:8000/
