param(
  [string]$Distro = "Ubuntu-26.04",
  [string]$RepoPath = "~/zwslcore",
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$EngineerArgs
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($RepoPath -notmatch '^~?/[A-Za-z0-9._/-]+$') {
  throw "RepoPath contains unsupported characters."
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

$resolvedPath = (& wsl.exe -d $Distro -- bash -lc "cd $RepoPath && pwd" | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $resolvedPath) {
  throw "Unable to resolve WSL repository path '$RepoPath'."
}

Write-Host "[zwslcore-wsl] Running engineering CLI inside $Distro using $resolvedPath"
& wsl.exe -d $Distro --cd $resolvedPath -- python3 scripts/engineer.py @EngineerArgs
if ($LASTEXITCODE -ne 0) {
  throw "Engineering CLI failed with exit code $LASTEXITCODE"
}
