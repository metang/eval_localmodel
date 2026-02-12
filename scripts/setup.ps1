# setup.ps1 — One-time environment setup for eval-localmodel.
#
# Usage:  .\scripts\setup.ps1
#
# What it does:
#   1. Creates (or reuses) the conda environment "eval_localmodel"
#   2. Installs Python dependencies
#   3. Generates config/models.yaml if it doesn't already exist

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $ROOT) { $ROOT = (Get-Location).Path }
Push-Location $ROOT

Write-Host "`n=== eval-localmodel setup ===" -ForegroundColor Cyan

# ── 1. Conda environment ─────────────────────────────────────────
$envName = "eval_localmodel"
$envExists = conda env list | Select-String -Pattern "\\b$envName\\b"

if ($envExists) {
    Write-Host "[OK] Conda environment '$envName' already exists." -ForegroundColor Green
} else {
    Write-Host "[..] Creating conda environment '$envName' (Python 3.11)..." -ForegroundColor Yellow
    conda create -n $envName python=3.11 -y
    Write-Host "[OK] Environment created." -ForegroundColor Green
}

# ── 2. Install dependencies ──────────────────────────────────────
Write-Host "[..] Installing Python dependencies..." -ForegroundColor Yellow
conda run -n $envName --no-banner pip install -e ".[all]" 2>&1 | Out-Null
Write-Host "[OK] Dependencies installed." -ForegroundColor Green

# Verify framework loads
Write-Host "[..] Verifying framework..." -ForegroundColor Yellow
$runtimes = conda run -n $envName --no-banner python -c "from src.runtimes.registry import list_runtimes; print(list_runtimes())" 2>&1
Write-Host "[OK] Available runtimes: $runtimes" -ForegroundColor Green

# ── 3. Generate model config if missing ──────────────────────────
$modelsConfig = Join-Path $ROOT "config" "models.yaml"
if (Test-Path $modelsConfig) {
    Write-Host "[OK] Model config already exists: config/models.yaml" -ForegroundColor Green
} else {
    Write-Host "[..] Generating config/models.yaml with example models..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path (Join-Path $ROOT "config") -Force | Out-Null

    @"
# Model configuration for eval-localmodel.
# Edit this file to specify which models to download and evaluate.

models:
  # Ollama models -- pulled via ``ollama pull <name>``
  ollama:
    - name: "qwen2.5:0.5b"
    # - name: "qwen2.5:1.5b"
    # - name: "llama3.2:1b"

  # Foundry Local models -- auto-downloaded by SDK on first load
  # Specify device variants to evaluate (cpu, gpu, npu)
  foundry-local:
    - name: qwen2.5-0.5b
      devices: [cpu, gpu]
    # - name: phi-4-mini
    #   devices: [cpu, gpu, npu]

  # llama-cpp models -- download GGUF from HuggingFace
  # llama-cpp:
  #   - name: qwen2.5-0.5b-q4km
  #     gguf_url: "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
  #     gguf_path: "models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
  #     base_url: "http://localhost:8000/v1"
"@ | Set-Content -Path $modelsConfig -Encoding utf8

    Write-Host "[OK] Generated config/models.yaml — edit it to customise models." -ForegroundColor Green
}

Write-Host "`n=== Setup complete ===" -ForegroundColor Cyan
Write-Host "Next steps:"
Write-Host "  1. Edit config/models.yaml to choose your models"
Write-Host "  2. Run .\scripts\download_models.ps1 to download them"
Write-Host "  3. Run .\scripts\run_eval.ps1 to evaluate and generate report"
Write-Host ""

Pop-Location
