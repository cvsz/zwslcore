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

function Quote-Bash([string]$Value) {
  return "'" + $Value.Replace("'", "'"'"'") + "'"
}

$quotedArgs = @($EngineerArgs | ForEach-Object { Quote-Bash $_ })
$command = "cd $RepoPath && python3 scripts/engineer.py"
if ($quotedArgs.Count -gt 0) {
  $command += " " + ($quotedArgs -join " ")
}

Write-Host "[zwslcore-wsl] Running engineering CLI inside $Distro using $RepoPath"
& wsl.exe -d $Distro -- bash -lc $command
if ($LASTEXITCODE -ne 0) {
  throw "Engineering CLI failed with exit code $LASTEXITCODE"
}
