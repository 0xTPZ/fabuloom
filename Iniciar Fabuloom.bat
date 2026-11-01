@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.11+ nao foi encontrado no PATH.
  echo Consulte INSTALL.md para instalar o Python sem alterar este script.
  pause
  exit /b 1
)
set "FABULOOM_WORKSPACE_ROOT=%CD%"
set "FABULOOM_EXPORT_ROOT=%CD%\workspace\exports"
echo Iniciando Fabuloom Studio em http://127.0.0.1:8765/
start "Fabuloom Studio" http://127.0.0.1:8765/
python frontend\server.py --port 8765
endlocal
