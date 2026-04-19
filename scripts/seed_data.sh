#!/usr/bin/env bash
# Upload sample CSV to S3 so Athena external table LOCATION matches real data.
# Required: DATA_S3_BUCKET (e.g. your-calcofi-bucket — same as calcofi_schema.sql LOCATION)
# Optional: DATA_S3_PREFIX (default: calcofi/bottle/ — matches calcofi_schema.sql bottle LOCATION)
# Optional: AWS_REGION
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE="${ROOT}/data/sample_data/bottle_data_sample.csv"

if [[ ! -f "${SAMPLE}" ]]; then
  echo "Missing sample file: ${SAMPLE}" >&2
  exit 1
fi

DATA_S3_BUCKET="${DATA_S3_BUCKET:-}"
if [[ -z "${DATA_S3_BUCKET}" ]]; then
  echo "Set DATA_S3_BUCKET to the bucket used in data/schemas/calcofi_schema.sql LOCATION." >&2
  exit 1
fi

DATA_S3_PREFIX="${DATA_S3_PREFIX:-calcofi/bottle/}"
# Normalize: ensure trailing slash, no leading slash on key body
DATA_S3_PREFIX="${DATA_S3_PREFIX#/}"
[[ "${DATA_S3_PREFIX}" == */ ]] || DATA_S3_PREFIX="${DATA_S3_PREFIX}/"

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
DEST="s3://${DATA_S3_BUCKET}/${DATA_S3_PREFIX}bottle_data_sample.csv"

echo "Uploading ${SAMPLE} -> ${DEST}"
aws s3 cp "${SAMPLE}" "${DEST}" --region "${REGION}"

echo "Done. Ensure Glue/Athena table LOCATION is s3://${DATA_S3_BUCKET}/${DATA_S3_PREFIX}"
echo "Then run the DDL in data/schemas/calcofi_schema.sql (Athena) if the table is not registered yet."
