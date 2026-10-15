param(
  [string]$Distro = "Ubuntu-26.04",
  [string]$LinuxUser = "cvsz",
  [string]$Repo = "https://github.com/cvsz/zwslcore.git",
  [string]$Branch = "",
  [switch]$AllowFallback,
  [switch]$SkipStackInstall,
  [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step([string]$Message) {
  Write-Host ""
  Write-Host "[zwslcore-wsl] $Message" -ForegroundColor Cyan
}

function Test-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-Native([string]$FilePath, [string[]]$Arguments) {
  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$FilePath $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
  }
}

function Get-OptionalFeatureState([string]$FeatureName) {
  try {
    return (Get-WindowsOptionalFeature -Online -FeatureName $FeatureName).State
  } catch {
    Write-Warning "Get-WindowsOptionalFeature failed ($($_.Exception.Message)); falling back to dism.exe."
  }
  $info = & dism.exe /online /Get-FeatureInfo /FeatureName:$FeatureName 2>&1
  foreach ($line in $info) {
    if ([string]$line -match "^\s*State\s*:\s*(.+?)\s*$") { return $Matches[1].Trim() }
  }
  throw "Unable to determine state of optional feature $FeatureName."
}

function Enable-OptionalFeature([string]$FeatureName) {
  try {
    Enable-WindowsOptionalFeature -Online -FeatureName $FeatureName -All -NoRestart | Out-Null
    return
  } catch {
    Write-Warning "Enable-WindowsOptionalFeature failed ($($_.Exception.Message)); falling back to dism.exe."
  }
  Invoke-Native dism.exe @("/online", "/Enable-Feature", "/FeatureName:$FeatureName", "/All", "/NoRestart")
}

function ConvertFrom-WslDistroOutput([object[]]$Lines) {
  $names = [System.Collections.Generic.List[string]]::new()
  $ignored = @("NAME", "The", "Install", "Default", "Windows", "Copyright")

  foreach ($rawLine in $Lines) {
    if ($null -eq $rawLine) { continue }
    $line = ([string]$rawLine).Replace([string][char]0, "").Trim()
    if (-not $line) { continue }

    $line = $line.TrimStart("*").Trim()
    if (-not $line) { continue }

    $candidate = $null
    if ($line -match "^([A-Za-z0-9][A-Za-z0-9._-]*)$") {
      $candidate = $Matches[1]
    } elseif ($line -match "^([A-Za-z0-9][A-Za-z0-9._-]*)[ ]{2,}.+$") {
      $candidate = $Matches[1]
    }

    if ($candidate -and $ignored -notcontains $candidate -and -not $names.Contains($candidate)) {
      $names.Add($candidate)
    }
  }

  return @($names)
}

function Get-OnlineDistros {
  $items = & wsl.exe --list --online --quiet 2>$null
  if ($LASTEXITCODE -ne 0) {
    $items = & wsl.exe --list --online 2>$null
  }
  if ($LASTEXITCODE -ne 0) { return @() }

  $parsed = ConvertFrom-WslDistroOutput -Lines $items
  if ($parsed.Count -eq 0) {
    $fallback = & wsl.exe --list --online 2>$null
    if ($LASTEXITCODE -eq 0) {
      $parsed = ConvertFrom-WslDistroOutput -Lines $fallback
    }
  }
  return @($parsed)
}

function Get-InstalledDistros {
  $items = & wsl.exe --list --quiet 2>$null
  if ($LASTEXITCODE -ne 0) { return @() }
  return @(ConvertFrom-WslDistroOutput -Lines $items)
}

function Get-WslDistroVersion([string]$Name) {
  $lines = & wsl.exe --list --verbose 2>$null
  if ($LASTEXITCODE -ne 0) { return $null }

  foreach ($rawLine in $lines) {
    if ($null -eq $rawLine) { continue }
    $line = ([string]$rawLine).Replace([string][char]0, "").Trim()
    if (-not $line) { continue }

    $line = $line.TrimStart("*").Trim()
    $pattern = "^" + [regex]::Escape($Name) + "[ ]{2,}.*[ ]{2,}([12])$"
    if ($line -match $pattern) {
      return [int]$Matches[1]
    }
  }
  return $null
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BootstrapPath = Join-Path $ScriptRoot "bootstrap-wsl.sh"

if (-not $Branch) {
  try {
    $detectedBranch = (& git -C $RepoRoot branch --show-current 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -eq 0 -and $detectedBranch) {
      $Branch = $detectedBranch
    } else {
      $Branch = "main"
    }
  } catch {
    $Branch = "main"
  }
}

if ($ValidateOnly) {
  if (-not (Test-Path $BootstrapPath)) {
    throw "Missing $BootstrapPath"
  }

  $sample = @(
    "The following is a list of valid distributions that can be installed.",
    "",
    "NAME                            FRIENDLY NAME",
    "Ubuntu                          Ubuntu",
    "Ubuntu-26.04                    Ubuntu 26.04 LTS",
    "Ubuntu-24.04                    Ubuntu 24.04 LTS"
  )
  $parsed = ConvertFrom-WslDistroOutput -Lines $sample
  if ($parsed -notcontains "Ubuntu-26.04" -or $parsed -notcontains "Ubuntu-24.04") {
    throw "WSL distro parser self-test failed."
  }

  Write-Host "PowerShell installer loaded successfully."
  exit 0
}

if (-not (Test-Administrator)) {
  throw "Run PowerShell as Administrator."
}
if ($LinuxUser -notmatch "^[a-z_][a-z0-9_-]{0,31}$") {
  throw "LinuxUser must be a valid Linux account name."
}
if ($Branch -notmatch "^[A-Za-z0-9._/-]+$") {
  throw "Branch contains unsupported characters."
}
if ($Repo -notmatch "^https://github[.]com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+[.]git$") {
  throw "Repo must be an HTTPS github.com clone URL ending in .git."
}
if (-not (Test-Path $BootstrapPath)) {
  throw "Missing local bootstrap script: $BootstrapPath"
}

Write-Step "Checking Windows version"
$os = Get-CimInstance Win32_OperatingSystem
if ([version]$os.Version -lt [version]"10.0.19041") {
  throw "WSL requires Windows 10 build 19041+ or Windows 11 for this installer."
}

Write-Step "Enabling WSL and Virtual Machine Platform"
$restartRequired = $false
foreach ($feature in @("Microsoft-Windows-Subsystem-Linux", "VirtualMachinePlatform")) {
  $state = Get-OptionalFeatureState -FeatureName $feature
  if ($state -ne "Enabled") {
    Enable-OptionalFeature -FeatureName $feature
    $restartRequired = $true
  }
}
if ($restartRequired) {
  Write-Warning "Windows features were enabled. Restart Windows and run this same script again."
  exit 3010
}

Write-Step "Installing/updating WSL"
& wsl.exe --status *> $null
if ($LASTEXITCODE -ne 0) {
  & wsl.exe --install --no-distribution --web-download
  if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 3010) {
    throw "Unable to install WSL. Exit code: $LASTEXITCODE"
  }
  if ($LASTEXITCODE -eq 3010) {
    Write-Warning "WSL installation requires a Windows restart. Restart and rerun this script."
    exit 3010
  }
}
Invoke-Native wsl.exe @("--update")
Invoke-Native wsl.exe @("--set-default-version", "2")

Write-Step "Resolving Ubuntu distribution"
$online = Get-OnlineDistros
if ($online -notcontains $Distro) {
  if ($AllowFallback -and $online -contains "Ubuntu-24.04") {
    Write-Warning "$Distro is not currently listed by WSL; using Ubuntu-24.04 because -AllowFallback was supplied."
    $Distro = "Ubuntu-24.04"
  } else {
    throw "$Distro is not available from the WSL catalog. Parsed distros: $($online -join ', ')"
  }
}

$installed = Get-InstalledDistros
if ($installed -notcontains $Distro) {
  Write-Step "Installing $Distro"
  Invoke-Native wsl.exe @("--install", "--distribution", $Distro, "--no-launch", "--web-download")
}

Write-Step "Ensuring WSL2 and selecting default distribution"
$currentVersion = Get-WslDistroVersion -Name $Distro
if ($currentVersion -eq 2) {
  Write-Host "[zwslcore-wsl] $Distro is already WSL2; skipping conversion."
} else {
  & wsl.exe --terminate $Distro *> $null
  Start-Sleep -Seconds 1
  Invoke-Native wsl.exe @("--set-version", $Distro, "2")
}
Invoke-Native wsl.exe @("--set-default", $Distro)

Write-Step "Enabling systemd and interop"
$wslConf = @'
[boot]
systemd=true

[interop]
enabled=true
appendWindowsPath=true
'@
$encodedConf = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($wslConf))
Invoke-Native wsl.exe @(
  "-d", $Distro, "-u", "root", "--",
  "bash", "-lc",
  "echo '$encodedConf' | base64 -d > /etc/wsl.conf"
)

Write-Step "Restarting WSL to activate systemd"
Invoke-Native wsl.exe @("--terminate", $Distro)
Start-Sleep -Seconds 2
Invoke-Native wsl.exe @(
  "-d", $Distro, "-u", "root", "--",
  "bash", "-lc",
  'test "$(ps -p 1 -o comm=)" = systemd'
)

Write-Step "Installing Ubuntu software and Docker from local zwslcore bootstrap"
$bootstrapText = Get-Content -Raw -LiteralPath $BootstrapPath
$encodedBootstrap = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bootstrapText))
$bootstrapCommand = "echo '$encodedBootstrap' | base64 -d > /tmp/zwslcore-bootstrap.sh && chmod 700 /tmp/zwslcore-bootstrap.sh && bash /tmp/zwslcore-bootstrap.sh '$LinuxUser'"
Invoke-Native wsl.exe @("-d", $Distro, "-u", "root", "--", "bash", "-lc", $bootstrapCommand)

$newUserMarker = & wsl.exe -d $Distro -u root -- bash -lc "test -f /var/lib/zwslcore-user-created && echo yes || true"
if (($newUserMarker | Out-String).Trim() -eq "yes") {
  Write-Step "Set a password for the newly created Linux user $LinuxUser"
  & wsl.exe -d $Distro -u root -- passwd $LinuxUser
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to set password for $LinuxUser."
  }
  Invoke-Native wsl.exe @("-d", $Distro, "-u", "root", "--", "rm", "-f", "/var/lib/zwslcore-user-created")
}

Write-Step "Setting the default Linux user"
$userCommand = "if grep -q '^\[user\]' /etc/wsl.conf; then " +
  "if sed -n '/^\[user\]/,/^\[/p' /etc/wsl.conf | grep -q '^default='; then " +
  "sed -i '/^\[user\]/,/^\[/ s/^default=.*/default=$LinuxUser/' /etc/wsl.conf; " +
  "else sed -i '/^\[user\]/a default=$LinuxUser' /etc/wsl.conf; fi; " +
  "else printf '\n[user]\ndefault=$LinuxUser\n' >> /etc/wsl.conf; fi"
Invoke-Native wsl.exe @("-d", $Distro, "-u", "root", "--", "bash", "-lc", $userCommand)

Write-Step "Restarting WSL to apply default-user settings"
Invoke-Native wsl.exe @("--terminate", $Distro)
Start-Sleep -Seconds 2

Write-Step "Validating WSL, systemd, Docker and development tools"
$validate = 'set -Eeuo pipefail; test "$(ps -p 1 -o comm=)" = systemd; docker version >/dev/null; docker compose version >/dev/null; git --version; python3 --version; curl --version | head -1'
Invoke-Native wsl.exe @("-d", $Distro, "--", "bash", "-lc", $validate)

if (-not $SkipStackInstall) {
  Write-Step "Cloning/updating zwslcore and installing the AI stack"
  $linuxInstall = @"
set -Eeuo pipefail
cd ~
if [ -d zwslcore/.git ]; then
  git -C zwslcore fetch origin
else
  git clone '$Repo' zwslcore
fi
git -C zwslcore checkout '$Branch'
git -C zwslcore pull --ff-only origin '$Branch'
cd zwslcore
echo "[zwslcore-wsl] Installing repo branch: $Branch"
set -o pipefail
make install 2>&1 | tee ~/zwslcore-install.log
"@
  $encodedInstall = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($linuxInstall))
  Invoke-Native wsl.exe @(
    "-d", $Distro, "--",
    "bash", "-lc",
    "echo '$encodedInstall' | base64 -d | bash"
  )
}

Write-Step "Installation complete"
Write-Host "Distro      : $Distro"
Write-Host "Linux user  : $LinuxUser"
Write-Host "Repo branch : $Branch"
Write-Host "Install log : ~/zwslcore-install.log"
Write-Host "Open WebUI  : http://localhost:3000"
Write-Host "Provider    : http://localhost:8080"
Write-Host "LiteLLM     : http://localhost:4000"
Write-Host "Ollama      : http://localhost:11434"
Write-Host ""
Write-Host "Verify:"
Write-Host "  .\scripts\doctor-wsl.ps1 -Smoke"
