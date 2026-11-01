param([switch]$Quiet)
$ErrorActionPreference = 'Continue'
$checks = @(
  @{ Name = 'Python'; Command = 'python'; Args = @('--version') },
  @{ Name = 'Node'; Command = 'node'; Args = @('--version') },
  @{ Name = 'FFmpeg'; Command = 'ffmpeg'; Args = @('-version') },
  @{ Name = 'FFprobe'; Command = 'ffprobe'; Args = @('-version') }
)
$failed = 0
foreach ($check in $checks) {
  $resolved = Get-Command $check.Command -ErrorAction SilentlyContinue
  if (-not $resolved) { Write-Output "MISSING $($check.Name): $($check.Command) is not on PATH"; $failed++; continue }
  $version = & $resolved.Source @($check.Args) 2>&1 | Select-Object -First 1
  Write-Output "OK $($check.Name): $version"
}
if (-not $Quiet) {
  Write-Output "Workspace root: $($env:FABULOOM_WORKSPACE_ROOT ?? '(default)')"
  Write-Output "Export root: $($env:FABULOOM_EXPORT_ROOT ?? '(default)')"
}
if ($failed -gt 0) { exit 1 }
