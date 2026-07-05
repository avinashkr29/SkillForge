#!/usr/bin/env bash
# SkillForge helper — indexes brain/ with official garrytan/gbrain
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "SkillForge GBrain setup"
echo "Official repos:"
echo "  GBrain: https://github.com/garrytan/gbrain"
echo "  GStack: https://github.com/garrytan/gstack"
echo ""

if ! command -v gbrain >/dev/null 2>&1; then
  echo "gbrain CLI not found."
  echo ""
  echo "Option A — GStack (recommended for Claude Code):"
  echo "  Install GStack, then run: /setup-gbrain"
  echo "  Guide: https://github.com/garrytan/gstack/blob/main/USING_GBRAIN_WITH_GSTACK.md"
  echo ""
  echo "Option B — CLI only:"
  echo "  curl -fsSL https://bun.sh/install | bash"
  echo "  bun install -g github:garrytan/gbrain"
  echo "  gbrain init --pglite"
  exit 1
fi

echo "Checking gbrain health..."
gbrain doctor

echo "Importing SkillForge brain pages from brain/ ..."
gbrain import brain/

echo "Sample query:"
gbrain search "product 1 assembly" || true

echo ""
echo "Done. Start SkillForge API:"
echo "  cd services/api && uvicorn skillforge_api.main:app --reload --port 8000"