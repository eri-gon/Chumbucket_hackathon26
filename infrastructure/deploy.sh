#!/usr/bin/env bash
# Legacy entrypoint: SAM now lives under calcofi-dashboard/. Use scripts/deploy_backend.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Note: SAM template moved to calcofi-dashboard/. Running deploy from there..."
exec "${ROOT}/scripts/deploy_backend.sh"
