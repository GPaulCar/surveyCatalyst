\
@echo off
cd /d C:\Users\Paul\Desktop\dev\surveyCatalyst

echo Stopping API...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /PID %%a /F

echo Stopping database...
.\postgres\bin\pg_ctl.exe -D postgres\data stop -m fast

echo Done.
pause
