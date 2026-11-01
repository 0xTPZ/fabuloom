@echo off
setlocal
title Fabuloom Studio 0.1.0-alpha
set "FABULOOM_ROOT=%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%FABULOOM_ROOT%scripts\launch-fabuloom.ps1" -Root "%FABULOOM_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo O Fabuloom nao foi iniciado. Consulte a mensagem acima.
  pause
)
exit /b %EXIT_CODE%
