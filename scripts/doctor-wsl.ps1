param(
  [string]$Distro = "Ubuntu-26.04",
  [string]$RepoPath = "~/zwslcore",
  [switch]$Smoke
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Wsl([string]$Command) {
  & wsl.exe -d $Distro -- bash -lc $Command
  if ($LASTEXITCODE -ne 0) {
    throw "WSL command failed with exit code $LASTEXITCODE"
  }
}

$installed = & wsl.exe --list --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Unable to query WSL distributions."
}

$normalized = @(
  $installed |
    ForEach-Object { ([string]$_).Replace([string][char]0, "").Trim().TrimStart("*").Trim() } |
    Where-Object { $_ }
)

if ($normalized -notcontains $Distro) {
  throw "WSL distribution '$Distro' is not installed."
}

$command = "cd $RepoPath && make doctor"
if ($Smoke) {
  $command += " && make smoke"
}

Write-Host "[zwslcore-wsl] Running runtime checks inside $Distro using $RepoPath"
Invoke-Wsl $command
