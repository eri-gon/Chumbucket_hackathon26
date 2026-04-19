#!/usr/bin/env bash
# Deploy from repo root context so relative CodeUri paths in template.yaml resolve.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STACK_NAME="${STACK_NAME:-chumbucket-api}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

echo "Building SAM application (template: infrastructure/template.yaml)..."
sam build --template-file infrastructure/template.yaml

echo "Deploying stack '${STACK_NAME}' to region '${REGION}'..."
DEPLOY_ARGS=(
  --template-file .aws-sam/build/template.yaml
  --stack-name "${STACK_NAME}"
  --capabilities CAPABILITY_IAM
  --resolve-s3
  --region "${REGION}"
  --no-confirm-changeset
)
if [[ -n "${SAM_PARAMETER_OVERRIDES:-}" ]]; then
  DEPLOY_ARGS+=(--parameter-overrides "${SAM_PARAMETER_OVERRIDES}")
fi
sam deploy "${DEPLOY_ARGS[@]}"

echo "Done. Copy ApiEndpoint from stack outputs and set VITE_API_URL in your frontend .env"
