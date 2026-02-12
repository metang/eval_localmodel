#!/usr/bin/env bash
# run_eval.sh — Generate a compare config from models.yaml, run evaluation,
#               and produce an HTML report.
#
# Usage:
#   ./scripts/run_eval.sh                    # evaluate all models
#   ./scripts/run_eval.sh -t my_experiment   # custom output tag

set -e

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
Tag=$(date +"%Y%m%d_%H%M%S")
while getopts "t:" opt; do
    case $opt in
        t) Tag="$OPTARG" ;;
        *) echo "Usage: $0 [-t tag]"; exit 1 ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

envName="eval_localmodel"
modelsConfig="$ROOT/config/models.yaml"

if [[ ! -f "$modelsConfig" ]]; then
    echo -e "${RED}[ERROR] config/models.yaml not found. Run setup.sh first.${NC}"
    exit 1
fi

# ── 1. Generate compare YAML from models.yaml ────────────────────
compareConfig="$ROOT/config/compare_auto_${Tag}.yaml"

echo -e "\n${CYAN}=== Generating compare config ===${NC}"

# Use Python to convert models.yaml → compare YAML
conda run -n "$envName" --no-banner python -c "
import yaml, sys

with open('$modelsConfig') as f:
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

with open('$compareConfig', 'w') as f:
    yaml.dump({'runs': runs}, f, default_flow_style=False, sort_keys=False)

print(f'Generated {len(runs)} run(s)')
"

if [[ ! -f "$compareConfig" ]]; then
    echo -e "${RED}[ERROR] Failed to generate compare config.${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Compare config: config/compare_auto_${Tag}.yaml${NC}"

# ── 2. Ensure output directory exists ─────────────────────────────
resultsDir="$ROOT/results"
mkdir -p "$resultsDir"

csvPath="$resultsDir/results_${Tag}.csv"
htmlPath="$resultsDir/report_${Tag}.html"

# ── 3. Run evaluation ────────────────────────────────────────────
echo -e "\n${CYAN}=== Running evaluation ===${NC}"
conda run -n "$envName" --no-banner python -m src.cli compare \
    -c "$compareConfig" \
    --csv "$csvPath" \
    --html "$htmlPath"

# ── 4. Report ────────────────────────────────────────────────────
echo -e "\n${CYAN}=== Done ===${NC}"
if [[ -f "$csvPath" ]]; then
    echo -e "${GREEN}  CSV  : $csvPath${NC}"
fi
if [[ -f "$htmlPath" ]]; then
    echo -e "${GREEN}  HTML : $htmlPath${NC}"
    echo ""
    # Open HTML in default browser (macOS)
    if command -v open &> /dev/null; then
        open "$htmlPath"
    # Linux
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$htmlPath"
    fi
fi
