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
    while IFS='|' read -r alias dev; do
        [[ -z "$alias" ]] && continue
        echo -e "${YELLOW}[..] Loading $alias ($dev) — will download on first use...${NC}"
        devUpper=$(echo "$dev" | tr '[:lower:]' '[:upper:]')
        result=$(conda run -n "$envName" python -c "
try:
    from foundry_local import FoundryLocalManager
    from foundry_local.models import DeviceType
    mgr = FoundryLocalManager('$alias', device=DeviceType('$devUpper'))
    info = mgr.load_model('$alias', device=DeviceType('$devUpper'))
    print(f'OK: {info.id}')
    mgr.unload_model(info.id)
except Exception as e:
    print(f'SKIP: {e}')
" 2>&1 | tail -1)
        if [[ "$result" == OK:* ]]; then
            echo -e "${GREEN}[OK] $alias ($dev) ready.${NC}"
        else
            echo -e "${YELLOW}[SKIP] $alias ($dev): $result${NC}"
        fi
    done <<< "$foundryModels"
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
        if curl -L -o "$fullPath" "$url"; then
            sizeMB=$(du -m "$fullPath" | cut -f1)
            echo -e "${GREEN}[OK] $name downloaded (${sizeMB} MB).${NC}"
        else
            echo -e "${RED}[FAIL] Could not download $name${NC}"
        fi
    done <<< "$llamacppModels"
fi

echo -e "\n${CYAN}=== Model downloads complete ===${NC}"
