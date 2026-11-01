@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Fabuloom Studio - preparacao local do ambiente
echo.

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERRO] Python 3.11 ou superior nao foi encontrado.
    echo Instale Python pelo site oficial e execute este arquivo novamente.
    pause
    exit /b 1
  )
  set "FABULOOM_BOOTSTRAP_PY=python"
) else (
  set "FABULOOM_BOOTSTRAP_PY=py -3"
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Criando ambiente virtual local em .venv...
  %FABULOOM_BOOTSTRAP_PY% -m venv .venv
  if errorlevel 1 (
    echo [ERRO] Nao foi possivel criar .venv. Nenhuma alteracao global foi feita.
    pause
    exit /b 2
  )
) else (
  echo [1/3] Ambiente virtual local ja existe.
)

set "FABULOOM_PYTHON=%CD%\.venv\Scripts\python.exe"
echo [2/3] Instalando o Fabuloom e dependencias do Studio no ambiente local...
"%FABULOOM_PYTHON%" -m pip install --upgrade pip
"%FABULOOM_PYTHON%" -m pip install -e "."
if errorlevel 1 (
  echo [ERRO] A instalacao basica falhou. Verifique a conexao e tente novamente.
  pause
  exit /b 3
)

echo.
echo O Kokoro e opcional e pode baixar dependencias e o modelo publico Kokoro-82M.
echo Origem: PyPI e Hugging Face. Modelo: Apache-2.0. Destino: .venv e cache do usuario.
choice /C SN /N /M "Deseja instalar o extra Kokoro agora? [S/N] "
if errorlevel 2 goto :done
echo [3/3] Instalando Kokoro somente com sua autorizacao...
"%FABULOOM_PYTHON%" -m pip install -e ".[kokoro]"
if errorlevel 1 (
  echo [CONFIGURACAO NECESSARIA] Kokoro nao foi concluido. O Studio continua utilizavel para edicao.
  pause
  exit /b 4
)

:done
echo.
echo [PRONTO] Ambiente local preparado.
echo Execute "Iniciar Fabuloom.bat" para abrir o Studio e verificar o ambiente.
pause
endlocal
