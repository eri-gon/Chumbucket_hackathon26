#!/usr/bin/env bash
# Deploy Lambda + API Gateway via AWS SAM (calcofi-dashboard/template.yaml + samconfig.toml).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/calcofi-dashboard"

echo "Building SAM application (template: calcofi-dashboard/template.yaml)..."
sam build

echo "Deploying (stack/region from calcofi-dashboard/samconfig.toml)..."
sam deploy

echo "Done. Copy ApiEndpoint from stack outputs and set VITE_API_URL in your frontend/.env"
