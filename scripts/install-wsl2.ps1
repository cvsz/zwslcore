param(
  [string]$Distro = "Ubuntu-26.04",
  [string]$LinuxUser = "cvsz",
  [string]$Repo = "https://github.com/cvsz/zwslcore.git",
  [string]$Branch = "main",
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

function ConvertFrom-WslDistroOutput([object[]]$Lines) {
  $names = [System.Collections.Generic.List[string]]::new()
  $ignored = @("NAME", "The", "Install", "Default", "Windows", "Copyright")

  foreach ($rawLine in $Lines) {
    if ($null -eq $rawLine) { continue }

    $line = ([string]$rawLine).Replace([char]0, "").Trim()
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

  $parsed = ConvertFrom-WslDistroOutput @($items)
  if ($parsed.Count -eq 0) {
    $fallback = & wsl.exe --list --online 2>$null
    if ($LASTEXITCODE -eq 0) {
      $parsed = ConvertFrom-WslDistroOutput @($fallback)
    }
  }

  return @($parsed)
}

function Get-InstalledDistros {
  $items = & wsl.exe --list --quiet 2>$null
  if ($LASTEXITCODE -ne 0) { return @() }
  return @(ConvertFrom-WslDistroOutput @($items))
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BootstrapPath = Join-Path $ScriptRoot "bootstrap-wsl.sh"

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
  $parsed = ConvertFrom-WslDistroOutput $sample
  if ($parsed -notcontains "Ubuntu-26.04" -or $parsed -notcontains "Ubuntu-24.04") {
    throw "WSL distro parser self-test failed."
  }

  Write-Host "PowerShell installer loaded successfully."
  exit 0
}

if (-not (Test-Administrator)) {
  throw "Run PowerShell as Administrator."
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
  $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature).State
  if ($state -ne "Enabled") {
    Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
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
    throw "$Distro is not available from 'wsl --list --online'. Available: $($online -join ', ')"
  }
}

$installed = Get-InstalledDistros
if ($installed -notcontains $Distro) {
  Write-Step "Installing $Distro"
  Invoke-Native wsl.exe @("--install", "--distribution", $Distro, "--no-launch", "--web-download")
}

Write-Step "Forcing WSL2 and selecting default distribution"
Invoke-Native wsl.exe @("--set-version", $Distro, "2")
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
$userConf = @"
if ! grep -q '^\[user\]' /etc/wsl.conf; then
  printf '\n[user]\ndefault=$LinuxUser\n' >> /etc/wsl.conf
else
  sed -i '/^\[user\]/,/^\[/ { s/^default=.*/default=$LinuxUser/; }' /etc/wsl.conf
fi
"@
$userEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userConf))
Invoke-Native wsl.exe @(
  "-d", $Distro, "-u", "root", "--",
  "bash", "-lc",
  "echo '$userEncoded' | base64 -d | bash"
)

Write-Step "Restarting WSL to apply systemd/default-user settings"
Invoke-Native wsl.exe @("--shutdown")
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
make install
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
Write-Host "Open WebUI  : http://localhost:3000"
Write-Host "Provider    : http://localhost:8080"
Write-Host "LiteLLM     : http://localhost:4000"
Write-Host "Ollama      : http://localhost:11434"
Write-Host ""
Write-Host "Verify:"
Write-Host "  wsl -d $Distro -- bash -lc 'cd ~/zwslcore && make doctor'"
) {
      $candidate = $Matches[1]
    } elseif ($line -match '^([A-Za-z0-9][A-Za-z0-9._-]*)\s{2,}.+
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BootstrapPath = Join-Path $ScriptRoot "bootstrap-wsl.sh"

if ($ValidateOnly) {
  if (-not (Test-Path $BootstrapPath)) {
    throw "Missing $BootstrapPath"
  }
  Write-Host "PowerShell installer loaded successfully."
  exit 0
}

if (-not (Test-Administrator)) {
  throw "Run PowerShell as Administrator."
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
  $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature).State
  if ($state -ne "Enabled") {
    Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
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
    throw "$Distro is not available from 'wsl --list --online'. Available: $($online -join ', ')"
  }
}

$installed = Get-InstalledDistros
if ($installed -notcontains $Distro) {
  Write-Step "Installing $Distro"
  Invoke-Native wsl.exe @("--install", "--distribution", $Distro, "--no-launch", "--web-download")
}

Write-Step "Forcing WSL2 and selecting default distribution"
Invoke-Native wsl.exe @("--set-version", $Distro, "2")
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
$userConf = @"
if ! grep -q '^\[user\]' /etc/wsl.conf; then
  printf '\n[user]\ndefault=$LinuxUser\n' >> /etc/wsl.conf
else
  sed -i '/^\[user\]/,/^\[/ { s/^default=.*/default=$LinuxUser/; }' /etc/wsl.conf
fi
"@
$userEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userConf))
Invoke-Native wsl.exe @(
  "-d", $Distro, "-u", "root", "--",
  "bash", "-lc",
  "echo '$userEncoded' | base64 -d | bash"
)

Write-Step "Restarting WSL to apply systemd/default-user settings"
Invoke-Native wsl.exe @("--shutdown")
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
make install
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
Write-Host "Open WebUI  : http://localhost:3000"
Write-Host "Provider    : http://localhost:8080"
Write-Host "LiteLLM     : http://localhost:4000"
Write-Host "Ollama      : http://localhost:11434"
Write-Host ""
Write-Host "Verify:"
Write-Host "  wsl -d $Distro -- bash -lc 'cd ~/zwslcore && make doctor'"
) {
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

  $parsed = ConvertFrom-WslDistroOutput @($items)
  if ($parsed.Count -eq 0) {
    $fallback = & wsl.exe --list --online 2>$null
    if ($LASTEXITCODE -eq 0) {
      $parsed = ConvertFrom-WslDistroOutput @($fallback)
    }
  }
  return @($parsed)
}

function Get-InstalledDistros {
  $items = & wsl.exe --list --quiet 2>$null
  if ($LASTEXITCODE -ne 0) { return @() }
  return @(ConvertFrom-WslDistroOutput @($items))
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptRoot
$BootstrapPath = Join-Path $ScriptRoot "bootstrap-wsl.sh"

if ($ValidateOnly) {
  if (-not (Test-Path $BootstrapPath)) {
    throw "Missing $BootstrapPath"
  }
  Write-Host "PowerShell installer loaded successfully."
  exit 0
}

if (-not (Test-Administrator)) {
  throw "Run PowerShell as Administrator."
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
  $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature).State
  if ($state -ne "Enabled") {
    Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
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
    throw "$Distro is not available from 'wsl --list --online'. Available: $($online -join ', ')"
  }
}

$installed = Get-InstalledDistros
if ($installed -notcontains $Distro) {
  Write-Step "Installing $Distro"
  Invoke-Native wsl.exe @("--install", "--distribution", $Distro, "--no-launch", "--web-download")
}

Write-Step "Forcing WSL2 and selecting default distribution"
Invoke-Native wsl.exe @("--set-version", $Distro, "2")
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
$userConf = @"
if ! grep -q '^\[user\]' /etc/wsl.conf; then
  printf '\n[user]\ndefault=$LinuxUser\n' >> /etc/wsl.conf
else
  sed -i '/^\[user\]/,/^\[/ { s/^default=.*/default=$LinuxUser/; }' /etc/wsl.conf
fi
"@
$userEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userConf))
Invoke-Native wsl.exe @(
  "-d", $Distro, "-u", "root", "--",
  "bash", "-lc",
  "echo '$userEncoded' | base64 -d | bash"
)

Write-Step "Restarting WSL to apply systemd/default-user settings"
Invoke-Native wsl.exe @("--shutdown")
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
make install
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
Write-Host "Open WebUI  : http://localhost:3000"
Write-Host "Provider    : http://localhost:8080"
Write-Host "LiteLLM     : http://localhost:4000"
Write-Host "Ollama      : http://localhost:11434"
Write-Host ""
Write-Host "Verify:"
Write-Host "  wsl -d $Distro -- bash -lc 'cd ~/zwslcore && make doctor'"
