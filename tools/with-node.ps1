param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = 'Stop'

$nodeDirs = @(
    'C:\Program Files\nodejs',
    (Join-Path $env:ProgramFiles 'nodejs'),
    (Join-Path $env:LOCALAPPDATA 'Programs\nodejs')
) | Where-Object { $_ }

$nodeDir = $nodeDirs | Where-Object {
    Test-Path (Join-Path $_ 'node.exe')
} | Select-Object -First 1

if (-not $nodeDir) {
    throw 'Node.js was not found in the standard Windows install locations. Install Node.js 20+ or update tools/with-node.ps1.'
}

$pathEntries = $env:Path -split ';'
if ($pathEntries -notcontains $nodeDir) {
    $env:Path = "$nodeDir;$env:Path"
}

if (-not $Command -or $Command.Count -eq 0) {
    Write-Host "Node.js is available for this PowerShell scope from: $nodeDir"
    Write-Host 'Run this script with a command, or dot-source it to keep Node on PATH for the current terminal session.'
    Write-Host 'Examples:'
    Write-Host '  . .\tools\with-node.ps1'
    Write-Host '  .\tools\with-node.ps1 npm.cmd --prefix obsidian-plugin install'
    exit 0
}

$commandName = $Command[0]
$commandArgs = @()
if ($Command.Count -gt 1) {
    $commandArgs = $Command[1..($Command.Count - 1)]
}

& $commandName @commandArgs
exit $LASTEXITCODE