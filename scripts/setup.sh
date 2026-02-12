#!/usr/bin/env bash
# setup.sh — One-time environment setup for eval-localmodel.
#
# Usage:  ./scripts/setup.sh
#
# What it does:
#   1. Creates (or reuses) the conda environment "eval_localmodel"
#   2. Installs Python dependencies
#   3. Generates config/models.yaml if it doesn't already exist

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo -e "\n${CYAN}=== eval-localmodel setup ===${NC}"

# ── 1. Conda environment ─────────────────────────────────────────
envName="eval_localmodel"

if conda env list | grep -qw "$envName"; then
    echo -e "${GREEN}[OK] Conda environment '$envName' already exists.${NC}"
else
    echo -e "${YELLOW}[..] Creating conda environment '$envName' (Python 3.11)...${NC}"
    conda create -n "$envName" python=3.11 -y
    echo -e "${GREEN}[OK] Environment created.${NC}"
fi

# ── 2. Install dependencies ──────────────────────────────────────
echo -e "${YELLOW}[..] Installing Python dependencies...${NC}"
conda run -n "$envName" --no-banner pip install -e ".[all]" > /dev/null 2>&1
echo -e "${GREEN}[OK] Dependencies installed.${NC}"

# Verify framework loads
echo -e "${YELLOW}[..] Verifying framework...${NC}"
runtimes=$(conda run -n "$envName" --no-banner python -c "from src.runtimes.registry import list_runtimes; print(list_runtimes())" 2>&1)
echo -e "${GREEN}[OK] Available runtimes: $runtimes${NC}"

# ── 3. Generate model config if missing ──────────────────────────
modelsConfig="$ROOT/config/models.yaml"

if [[ -f "$modelsConfig" ]]; then
    echo -e "${GREEN}[OK] Model config already exists: config/models.yaml${NC}"
else
    echo -e "${YELLOW}[..] Generating config/models.yaml with example models...${NC}"
    mkdir -p "$ROOT/config"

    cat > "$modelsConfig" << 'EOF'
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
EOF

    echo -e "${GREEN}[OK] Generated config/models.yaml — edit it to customise models.${NC}"
fi

echo -e "\n${CYAN}=== Setup complete ===${NC}"
echo "Next steps:"
echo "  1. Edit config/models.yaml to choose your models"
echo "  2. Run ./scripts/download_models.sh to download them"
echo "  3. Run ./scripts/run_eval.sh to evaluate and generate report"
echo ""
