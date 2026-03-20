param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath,

    [string]$PythonExe = "python",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Assert-CommandExists {
    param([string]$CommandName, [string]$InstallHint)
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "'$CommandName' was not found. $InstallHint"
    }
}

function Assert-LastExitCode {
    param([string]$StepName)
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $StepName (exit code $LASTEXITCODE)"
    }
}

Write-Step "Validating paths"
if (-not (Test-Path -LiteralPath $VaultPath)) {
    throw "Vault path does not exist: $VaultPath"
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginRoot = Join-Path $repoRoot "obsidian-plugin"
if (-not (Test-Path -LiteralPath $pluginRoot)) {
    throw "Could not find plugin folder at: $pluginRoot"
}

Write-Step "Checking prerequisites"
Assert-CommandExists -CommandName $PythonExe -InstallHint "Install Python 3.10+ and ensure it is in PATH."
Assert-CommandExists -CommandName "npm" -InstallHint "Install Node.js 18+ from https://nodejs.org/."
Assert-CommandExists -CommandName "node" -InstallHint "Install Node.js 18+ from https://nodejs.org/."

Write-Step "Creating/using virtual environment"
$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $PythonExe -m venv $venvPath
    Assert-LastExitCode -StepName "Create virtual environment"
}

Write-Step "Installing Auto-CV Python package"
Push-Location $repoRoot
& $venvPython -m pip install --upgrade pip
Assert-LastExitCode -StepName "Upgrade pip"
& $venvPython -m pip install -e ".[dev]"
Assert-LastExitCode -StepName "Install Auto-CV package"

if (-not $SkipTests) {
    Write-Step "Running Python tests"
    & $venvPython -m pytest tests -q
    Assert-LastExitCode -StepName "Run Python tests"
}

Write-Step "Installing plugin npm dependencies"
Push-Location $pluginRoot
npm install
Assert-LastExitCode -StepName "Install npm dependencies"

Write-Step "Building Obsidian plugin"
npm run build
Assert-LastExitCode -StepName "Build Obsidian plugin"
Pop-Location
Pop-Location

Write-Step "Copying plugin files into vault"
$pluginDest = Join-Path $VaultPath ".obsidian\plugins\auto-cv-obsidian"
New-Item -ItemType Directory -Path $pluginDest -Force | Out-Null

$pluginMain = Join-Path $pluginRoot "main.js"
if (-not (Test-Path -LiteralPath $pluginMain)) {
    throw "Plugin build output not found: $pluginMain"
}

Copy-Item -LiteralPath $pluginMain -Destination (Join-Path $pluginDest "main.js") -Force
Copy-Item -LiteralPath (Join-Path $pluginRoot "manifest.json") -Destination (Join-Path $pluginDest "manifest.json") -Force
Copy-Item -LiteralPath (Join-Path $pluginRoot "styles.css") -Destination (Join-Path $pluginDest "styles.css") -Force

$resolvedPython = (Resolve-Path -LiteralPath $venvPython).Path

Write-Step "Done"
Write-Host "Auto-CV is installed into your vault plugin folder:" -ForegroundColor Green
Write-Host "  $pluginDest" -ForegroundColor Green
Write-Host "`nNext in Obsidian:" -ForegroundColor Yellow
Write-Host "1. Settings -> Community plugins -> turn off Restricted Mode"
Write-Host "2. Enable plugin: Auto CV"
Write-Host "3. Open Auto CV settings and set Python executable to:"
Write-Host "   $resolvedPython"
Write-Host "4. Run command: Build Resume/CV"
