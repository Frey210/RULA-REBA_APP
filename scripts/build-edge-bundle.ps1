param([string]$EdgeRepo = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\RULA-REBA_Detection_HailoAI'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root 'dist\edge-update'
New-Item -ItemType Directory -Path $output -Force | Out-Null
& git -C $EdgeRepo diff --quiet HEAD
if ($LASTEXITCODE -ne 0) { throw 'Commit tracked Pi agent changes before bundling.' }
& git -C $EdgeRepo bundle create (Join-Path $output 'ergosight-edge.bundle') main
if ($LASTEXITCODE -ne 0) { throw 'Could not build the offline Pi update bundle.' }
& git -C $EdgeRepo rev-parse HEAD | Set-Content -Encoding ascii (Join-Path $output 'edge-commit.txt')
$script = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'update-edge.sh')).Replace("`r`n", "`n")
[IO.File]::WriteAllText((Join-Path $output 'update-edge.sh'), $script, (New-Object Text.UTF8Encoding $false))
Copy-Item -LiteralPath (Join-Path $root 'docs\network_setup_0.2.4.md') -Destination $output
