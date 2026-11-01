[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Root)

$ErrorActionPreference = 'Stop'
$Root = [IO.Path]::GetFullPath($Root)
$Port = 8765
$Url = "http://127.0.0.1:$Port/studio.html"
$Server = Join-Path $Root 'frontend\server.py'

function Write-Step([string]$Text) { Write-Host $Text }
function Get-FabuloomPage {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return ($response.StatusCode -eq 200 -and $response.Content -match 'Fabuloom Studio')
  } catch { return $false }
}

Write-Host ''
Write-Host 'FABULOOM STUDIO' -ForegroundColor Cyan
Write-Host 'Version 0.1.0-alpha'
Write-Host ''

if (-not (Test-Path -LiteralPath $Server -PathType Leaf)) {
  Write-Error "Pasta do Fabuloom invalida: server.py nao foi encontrado em $Root"
  exit 1
}

$python = $null
$venvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
  $python = $venvPython
  Write-Step '[OK] Ambiente virtual encontrado'
} else {
  $command = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($command) { $python = $command.Source; Write-Step '[OK] Python encontrado' }
}
if (-not $python) {
  Write-Host '[ERRO] Python 3.11 ou superior nao foi encontrado.' -ForegroundColor Red
  Write-Host 'Prepare um ambiente com: python -m venv .venv'
  exit 1
}

try {
  $version = (& $python --version 2>&1 | Out-String).Trim()
  if ($version -notmatch 'Python (3\.(1[1-9]|[2-9][0-9])|[4-9])') { throw "Versao incompatível: $version" }
} catch {
  Write-Host "[ERRO] Nao foi possivel validar o Python: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}

if (Get-FabuloomPage) {
  Write-Step '[OK] Studio ja esta funcionando nesta porta'
  Write-Host 'Abrindo a instancia existente...'
  Start-Process $Url
  Write-Host 'Pressione Enter para fechar este inicializador.'
  [void](Read-Host)
  exit 0
}

try {
  $portCheck = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($portCheck) {
    Write-Host "[ERRO] A porta $Port esta ocupada por outro aplicativo." -ForegroundColor Red
    Write-Host 'Feche o aplicativo identificado ou escolha outra porta no codigo.'
    exit 1
  }
} catch {
  # If the optional diagnostic cmdlet is unavailable, the HTTP check below remains authoritative.
}

$workspace = Join-Path $Root 'workspace'
New-Item -ItemType Directory -Force -Path $workspace | Out-Null
$envForServer = @{ FABULOOM_WORKSPACE_ROOT = $Root; FABULOOM_EXPORT_ROOT = (Join-Path $workspace 'exports') }
$oldWorkspace = $env:FABULOOM_WORKSPACE_ROOT; $oldExport = $env:FABULOOM_EXPORT_ROOT
try {
  $env:FABULOOM_WORKSPACE_ROOT = $envForServer.FABULOOM_WORKSPACE_ROOT
  $env:FABULOOM_EXPORT_ROOT = $envForServer.FABULOOM_EXPORT_ROOT
  Write-Step '[OK] Dependencias basicas preparadas'
  $process = Start-Process -FilePath $python -ArgumentList @($Server, '--port', "$Port") -WorkingDirectory $Root -PassThru -WindowStyle Hidden
  Write-Step '[OK] Servidor iniciado'
  $ready = $false
  1..50 | ForEach-Object {
    if (-not $process.HasExited -and (Get-FabuloomPage)) { $ready = $true; return }
    Start-Sleep -Milliseconds 200
  }
  if (-not $ready) {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    throw 'O servidor nao respondeu como Fabuloom Studio.'
  }
  Write-Host ''
  Write-Host 'Abrindo Fabuloom Studio...' -ForegroundColor Green
  Write-Host $Url
  Start-Process $Url
  Write-Host ''
  Write-Host 'Pressione Enter para encerrar o servidor iniciado por este launcher.'
  [void](Read-Host)
  if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
} catch {
  Write-Host "[ERRO] $($_.Exception.Message)" -ForegroundColor Red
  exit 1
} finally {
  $env:FABULOOM_WORKSPACE_ROOT = $oldWorkspace
  $env:FABULOOM_EXPORT_ROOT = $oldExport
}
