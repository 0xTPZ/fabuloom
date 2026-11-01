@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  set "FABULOOM_PYTHON=%CD%\.venv\Scripts\python.exe"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
  echo [ERRO] Python 3.11+ nao foi encontrado.
  echo Instale Python 3.11 ou superior e execute novamente. Nenhuma instalacao global sera feita pelo Fabuloom.
  pause
  exit /b 1
  )
  echo [CONFIGURACAO NECESSARIA] Ambiente virtual .venv nao encontrado.
  echo Usando Python do sistema somente para abrir o Studio. Para Kokoro, prepare um ambiente virtual local.
  set "FABULOOM_PYTHON=python"
)
set "FABULOOM_WORKSPACE_ROOT=%CD%"
set "FABULOOM_EXPORT_ROOT=%CD%\workspace\exports"
curl.exe --silent --fail http://127.0.0.1:8765/api/health >nul 2>nul
if not errorlevel 1 (
  echo [PRONTO] O Fabuloom ja esta rodando em http://127.0.0.1:8765/
  start "Fabuloom Studio" http://127.0.0.1:8765/
  exit /b 0
)
netstat -ano | findstr /R /C:":8765 .*LISTENING" >nul
if not errorlevel 1 (
  echo [ERRO] A porta 8765 esta ocupada por outro processo.
  echo Feche apenas o aplicativo que voce reconhece ou inicie o Fabuloom manualmente em outra porta.
  pause
  exit /b 2
)
echo Iniciando Fabuloom Studio em http://127.0.0.1:8765/
start "Fabuloom Studio" http://127.0.0.1:8765/
"%FABULOOM_PYTHON%" frontend\server.py --port 8765
if errorlevel 1 (
  echo [ERRO] O servidor nao conseguiu iniciar. Os detalhes acima podem ser enviados ao suporte.
  pause
)
endlocal
