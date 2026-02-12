# download_models.ps1 — Download / pull all models listed in config/models.yaml.
#
# Usage:  .\scripts\download_models.ps1
#
# Reads config/models.yaml and:
#   • ollama     → runs `ollama pull <name>` for each model
#   • foundry    → runs SDK load_model (downloads on first use)
#   • llama-cpp  → downloads GGUF files from HuggingFace URLs

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

# Parse YAML via Python
$configJson = conda run -n $envName --no-banner python -c @"
import yaml, json
with open(r'$modelsConfig') as f:
    cfg = yaml.safe_load(f)
print(json.dumps(cfg.get('models', {})))
"@ 2>&1 | Where-Object { $_ -match '^\{' }

$models = $configJson | ConvertFrom-Json

Write-Host "`n=== Downloading models ===" -ForegroundColor Cyan

# ── Ollama ────────────────────────────────────────────────────────
if ($models.ollama) {
    Write-Host "`n--- Ollama ---" -ForegroundColor Magenta
    # Check ollama is available
    $ollamaAvailable = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaAvailable) {
        Write-Host "[SKIP] ollama CLI not found. Install from https://ollama.com" -ForegroundColor Yellow
    } else {
        foreach ($m in $models.ollama) {
            $name = $m.name
            Write-Host "[..] Pulling $name ..." -ForegroundColor Yellow
            try {
                ollama pull $name
                Write-Host "[OK] $name ready." -ForegroundColor Green
            } catch {
                Write-Host "[FAIL] Could not pull $name : $_" -ForegroundColor Red
            }
        }
    }
}

# ── Foundry Local ─────────────────────────────────────────────────
if ($models.'foundry-local') {
    Write-Host "`n--- Foundry Local ---" -ForegroundColor Magenta
    foreach ($m in $models.'foundry-local') {
        $alias = $m.name
        $devices = $m.devices
        if (-not $devices) { $devices = @("cpu") }

        foreach ($dev in $devices) {
            Write-Host "[..] Loading $alias ($dev) — will download on first use..." -ForegroundColor Yellow
            $pyCmd = @"
try:
    from foundry_local import FoundryLocalManager
    from foundry_local.models import DeviceType
    mgr = FoundryLocalManager('$alias', device=DeviceType('$($dev.ToUpper())'))
    info = mgr.load_model('$alias', device=DeviceType('$($dev.ToUpper())'))
    print(f'OK: {info.id}')
    mgr.unload_model(info.id)
except Exception as e:
    print(f'SKIP: {e}')
"@
            $result = conda run -n $envName --no-banner python -c $pyCmd 2>&1 | Select-Object -Last 1
            if ($result -match '^OK:') {
                Write-Host "[OK] $alias ($dev) ready." -ForegroundColor Green
            } else {
                Write-Host "[SKIP] $alias ($dev): $result" -ForegroundColor Yellow
            }
        }
    }
}

# ── llama-cpp GGUF downloads ─────────────────────────────────────
if ($models.'llama-cpp') {
    Write-Host "`n--- llama-cpp (GGUF) ---" -ForegroundColor Magenta
    $modelsDir = Join-Path $ROOT "models"
    if (-not (Test-Path $modelsDir)) { New-Item -ItemType Directory -Path $modelsDir | Out-Null }

    foreach ($m in $models.'llama-cpp') {
        $name = $m.name
        $url  = $m.gguf_url
        $path = Join-Path $ROOT $m.gguf_path

        if (Test-Path $path) {
            Write-Host "[OK] $name already downloaded: $($m.gguf_path)" -ForegroundColor Green
            continue
        }
        if (-not $url) {
            Write-Host "[SKIP] $name — no gguf_url specified." -ForegroundColor Yellow
            continue
        }

        # Ensure parent dir exists
        $dir = Split-Path -Parent $path
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

        Write-Host "[..] Downloading $name from $url ..." -ForegroundColor Yellow
        try {
            Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing
            $sizeMB = [math]::Round((Get-Item $path).Length / 1MB, 1)
            Write-Host "[OK] $name downloaded (${sizeMB} MB)." -ForegroundColor Green
        } catch {
            Write-Host "[FAIL] Could not download $name : $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== Model downloads complete ===" -ForegroundColor Cyan
Pop-Location
