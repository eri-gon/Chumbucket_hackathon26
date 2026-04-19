#!/usr/bin/env bash
# Deploy Lambda + API Gateway via AWS SAM (see infrastructure/template.yaml).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${ROOT}/infrastructure/deploy.sh"
