param(
  [string]$Distro = "Ubuntu-26.04",
  [string]$RepoPath = "~/zwslcore"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Wsl([string]$Command) {
  & wsl.exe -d $Distro -- bash -lc $Command
  if ($LASTEXITCODE -ne 0) {
    throw "WSL doctor failed with exit code $LASTEXITCODE"
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

Write-Host "[zwslcore-wsl] Running doctor inside $Distro using $RepoPath"
Invoke-Wsl "cd $RepoPath && make doctor"
