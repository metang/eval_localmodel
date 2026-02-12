#!/usr/bin/env bash
# download_models.sh — Download / pull all models listed in config/models.yaml.
#
# Usage:  ./scripts/download_models.sh
#
# Reads config/models.yaml and:
#   • ollama     → runs `ollama pull <name>` for each model
#   • foundry    → runs SDK load_model (downloads on first use)
#   • llama-cpp  → downloads GGUF files from HuggingFace URLs

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

envName="eval_localmodel"
modelsConfig="$ROOT/config/models.yaml"

if [[ ! -f "$modelsConfig" ]]; then
    echo -e "${RED}[ERROR] config/models.yaml not found. Run setup.sh first.${NC}"
    exit 1
fi

# Parse YAML via Python and get JSON
configJson=$(conda run -n "$envName" python -c "
import yaml, json
with open('$modelsConfig') as f:
    cfg = yaml.safe_load(f)
print(json.dumps(cfg.get('models', {})))
" 2>/dev/null)

echo -e "\n${CYAN}=== Downloading models ===${NC}"

# ── Ollama ────────────────────────────────────────────────────────
ollamaModels=$(echo "$configJson" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('ollama', []):
    print(m['name'])
" 2>/dev/null || true)

if [[ -n "$ollamaModels" ]]; then
    echo -e "\n${MAGENTA}--- Ollama ---${NC}"
    if ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}[SKIP] ollama CLI not found. Install from https://ollama.com${NC}"
    else
        # Check if ollama server is running, start if needed
        if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
            echo -e "${YELLOW}[..] Starting ollama serve...${NC}"
            ollama serve &> /dev/null &
            OLLAMA_PID=$!
            sleep 2  # Give it time to start
            if curl -s http://localhost:11434/api/tags &> /dev/null; then
                echo -e "${GREEN}[OK] Ollama server started (PID: $OLLAMA_PID)${NC}"
            else
                echo -e "${RED}[FAIL] Could not start ollama server${NC}"
            fi
        else
            echo -e "${GREEN}[OK] Ollama server already running${NC}"
        fi

        while IFS= read -r name; do
            [[ -z "$name" ]] && continue
            echo -e "${YELLOW}[..] Pulling $name ...${NC}"
            if ollama pull "$name"; then
                echo -e "${GREEN}[OK] $name ready.${NC}"
            else
                echo -e "${RED}[FAIL] Could not pull $name${NC}"
            fi
        done <<< "$ollamaModels"
    fi
fi

# ── Foundry Local ─────────────────────────────────────────────────
foundryModels=$(echo "$configJson" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('foundry-local', []):
    devices = m.get('devices', ['cpu'])
    for d in devices:
        print(f\"{m['name']}|{d}\")
" 2>/dev/null || true)

if [[ -n "$foundryModels" ]]; then
    echo -e "\n${MAGENTA}--- Foundry Local ---${NC}"
    # Check if foundry CLI is available
    if command -v foundry &> /dev/null; then
        while IFS='|' read -r alias dev; do
            [[ -z "$alias" ]] && continue
            # Convert device to proper case (CPU, GPU, NPU)
            devFormatted=$(echo "$dev" | tr '[:lower:]' '[:upper:]')
            echo -e "${YELLOW}[..] Downloading $alias ($devFormatted) via foundry CLI...${NC}"
            # Use foundry CLI to download
            if foundry model download "$alias" --device "$devFormatted" 2>&1; then
                echo -e "${GREEN}[OK] $alias ($devFormatted) ready.${NC}"
            else
                echo -e "${YELLOW}[SKIP] $alias ($devFormatted): download failed${NC}"
            fi
        done <<< "$foundryModels"
    else
        echo -e "${YELLOW}[SKIP] foundry CLI not found. Install via: brew install foundry${NC}"
        echo -e "${YELLOW}       Models will be downloaded on first use during evaluation.${NC}"
    fi
fi

# ── llama-cpp GGUF downloads ─────────────────────────────────────
llamacppModels=$(echo "$configJson" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('llama-cpp', []):
    url = m.get('gguf_url', '')
    path = m.get('gguf_path', '')
    print(f\"{m['name']}|{url}|{path}\")
" 2>/dev/null || true)

if [[ -n "$llamacppModels" ]]; then
    echo -e "\n${MAGENTA}--- llama-cpp (GGUF) ---${NC}"
    mkdir -p "$ROOT/models"

    while IFS='|' read -r name url path; do
        [[ -z "$name" ]] && continue
        fullPath="$ROOT/$path"

        if [[ -f "$fullPath" ]]; then
            echo -e "${GREEN}[OK] $name already downloaded: $path${NC}"
            continue
        fi

        if [[ -z "$url" ]]; then
            echo -e "${YELLOW}[SKIP] $name — no gguf_url specified.${NC}"
            continue
        fi

        # Ensure parent dir exists
        mkdir -p "$(dirname "$fullPath")"

        echo -e "${YELLOW}[..] Downloading $name from $url ...${NC}"
        if curl -L --progress-bar -o "$fullPath" "$url"; then
            sizeMB=$(du -m "$fullPath" | cut -f1)
            echo -e "${GREEN}[OK] $name downloaded (${sizeMB} MB).${NC}"
        else
            echo -e "${RED}[FAIL] Could not download $name${NC}"
        fi
    done <<< "$llamacppModels"
fi

echo -e "\n${CYAN}=== Model downloads complete ===${NC}"
