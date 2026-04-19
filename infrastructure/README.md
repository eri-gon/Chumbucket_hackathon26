# Infrastructure (legacy folder)

The AWS SAM application template now lives in **`calcofi-dashboard/template.yaml`**.

- **Deploy:** from repo root, run **`./scripts/deploy_backend.sh`** (builds and deploys from `calcofi-dashboard/` using `samconfig.toml`).
- **Legacy:** `infrastructure/deploy.sh` forwards to that script.
