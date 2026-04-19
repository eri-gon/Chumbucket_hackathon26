#!/usr/bin/env bash
# Build the Vite app and sync dist/ to S3 for static hosting.
# Required: FRONTEND_S3_BUCKET
# Optional: AWS_REGION, CLOUDFRONT_DISTRIBUTION_ID (invalidates /* after upload)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}/frontend"

FRONTEND_S3_BUCKET="${FRONTEND_S3_BUCKET:-}"
if [[ -z "${FRONTEND_S3_BUCKET}" ]]; then
  echo "Set FRONTEND_S3_BUCKET to your S3 bucket name (static site or assets bucket)." >&2
  exit 1
fi

echo "Installing dependencies..."
npm ci

echo "Building production bundle..."
npm run build

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
TARGET="s3://${FRONTEND_S3_BUCKET}/"

echo "Syncing dist/ to ${TARGET} (region ${REGION})..."
aws s3 sync ./dist "${TARGET}" --delete --region "${REGION}"

if [[ -n "${CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
  echo "Creating CloudFront invalidation for /* ..."
  aws cloudfront create-invalidation \
    --distribution-id "${CLOUDFRONT_DISTRIBUTION_ID}" \
    --paths "/*" \
    --output text
fi

echo "Frontend deploy finished."
