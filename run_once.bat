@echo off
setlocal
set PROJ=D:\PaperRader\PaperRadar_plus
set PY=%PROJ%\.venv\Scripts\python.exe
if not exist "%PY%" (
  where py.exe >nul 2>nul && set PY=py.exe
)
echo Running: "%PY%" "%PROJ%\paper_radar_plus.py" --since_days 2
"%PY%" "%PROJ%\paper_radar_plus.py" --since_days 2
echo.
echo Done. Press any key to exit.
pause >nul
