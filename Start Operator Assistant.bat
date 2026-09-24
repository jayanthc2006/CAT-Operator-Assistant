@echo off
title CAT Operator Assistant
cd /d "%~dp0"

rem Start the local app server (runs fully offline on this machine)
start "CAT Operator Assistant - server" /min ".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501

rem Wait until the server is ready
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){try{Invoke-WebRequest http://localhost:8501/_stcore/health -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0}catch{Start-Sleep 1}}"

rem Open as a standalone app window (no browser tabs or address bar).
rem Edge is usually NOT on PATH, so use its standard install locations; fall back to the default browser.
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
    start "" "%EDGE%" --app=http://localhost:8501 --window-size=1440,900
) else (
    start "" http://localhost:8501
)
