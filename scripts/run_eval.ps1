# run_eval.ps1 — Generate a compare config from models.yaml, run evaluation,
#                 and produce an HTML report.
#
# Usage:
#   .\scripts\run_eval.ps1                         # evaluate all models
#   .\scripts\run_eval.ps1 -Tag "my_experiment"    # custom output tag

param(
    [string]$Tag = (Get-Date -Format "yyyyMMdd_HHmmss")
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $ROOT) { $ROOT = (Get-Location).Path }
Push-Location $ROOT

$envName = "eval_localmodel"
$modelsConfig = Join-Path $ROOT "config" "models.yaml"

if (-not (Test-Path $modelsConfig)) {
    Write-Host "[ERROR] config/models.yaml not found. Run setup.ps1 first." -ForegroundColor Red
    Pop-Location; exit 1
}

# ── 1. Generate compare YAML from models.yaml ────────────────────
$compareConfig = Join-Path $ROOT "config" "compare_auto_$Tag.yaml"

Write-Host "`n=== Generating compare config ===" -ForegroundColor Cyan

# Use Python to convert models.yaml → compare YAML
conda run -n $envName --no-banner python -c @"
import yaml, sys

with open(r'$modelsConfig') as f:
    cfg = yaml.safe_load(f)

models = cfg.get('models', {})
runs = []

# Ollama
for m in models.get('ollama', []):
    runs.append({'runtime': 'ollama', 'model': m['name']})

# Foundry Local
for m in models.get('foundry-local', []):
    devices = m.get('devices', ['cpu'])
    for d in devices:
        runs.append({'runtime': 'foundry-local', 'model': m['name'], 'device': d})

# llama-cpp
for m in models.get('llama-cpp', []):
    entry = {'runtime': 'llama-cpp', 'model': m['name']}
    if m.get('base_url'):
        entry['base_url'] = m['base_url']
    if m.get('gguf_path'):
        entry['gguf_path'] = m['gguf_path']
    runs.append(entry)

if not runs:
    print('ERROR: No models configured in config/models.yaml')
    sys.exit(1)

with open(r'$compareConfig', 'w') as f:
    yaml.dump({'runs': runs}, f, default_flow_style=False, sort_keys=False)

print(f'Generated {len(runs)} run(s)')
"@

if (-not (Test-Path $compareConfig)) {
    Write-Host "[ERROR] Failed to generate compare config." -ForegroundColor Red
    Pop-Location; exit 1
}

Write-Host "[OK] Compare config: config/compare_auto_$Tag.yaml" -ForegroundColor Green

# ── 2. Ensure output directory exists ─────────────────────────────
$resultsDir = Join-Path $ROOT "results"
if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir | Out-Null }

$csvPath  = Join-Path $resultsDir "results_$Tag.csv"
$htmlPath = Join-Path $resultsDir "report_$Tag.html"

# ── 3. Run evaluation ────────────────────────────────────────────
Write-Host "`n=== Running evaluation ===" -ForegroundColor Cyan
conda run -n $envName --no-banner python -m src.cli compare `
    -c $compareConfig `
    --csv $csvPath `
    --html $htmlPath

# ── 4. Report ────────────────────────────────────────────────────
Write-Host "`n=== Done ===" -ForegroundColor Cyan
if (Test-Path $csvPath)  { Write-Host "  CSV  : $csvPath"  -ForegroundColor Green }
if (Test-Path $htmlPath) {
    Write-Host "  HTML : $htmlPath" -ForegroundColor Green
    Write-Host ""
    # Open HTML in default browser
    Start-Process $htmlPath
}

Pop-Location
