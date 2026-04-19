# Setup

End-to-end setup for developers and demo environments: tooling, configuration, deploy order, and Athena data loading.

## Prerequisites

- **Node.js** (current LTS) and npm — for `frontend/`.
- **Python 3.11** — matches Lambda runtime in `infrastructure/template.yaml`.
- **AWS CLI** v2, configured with credentials (`aws sts get-caller-identity` works).
- **AWS SAM CLI** — for `sam build` and `sam deploy` ([Installing the AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)).

## Repository layout (quick reference)

- `frontend/` — Vite + React app.
- `backend/functions/` — Lambda source per function.
- `infrastructure/` — `template.yaml`, `deploy.sh`, `events/` for local invoke.
- `data/` — Athena DDL (`data/schemas/calcofi_schema.sql`), sample queries, sample CSV.
- `scripts/` — `deploy_frontend.sh`, `deploy_backend.sh`, `seed_data.sh`.

## One-time AWS configuration

1. Pick an AWS **region** (for example `us-east-1`) and use it consistently for `AWS_REGION` or `AWS_DEFAULT_REGION`.
2. Ensure the account can create S3 buckets, Lambda, API Gateway, IAM roles, and Athena workgroups (default `primary` is referenced in the template environment for the query function).

## Backend (API + Lambdas)

From the repository root (Git Bash or WSL on Windows):

```bash
chmod +x scripts/deploy_backend.sh infrastructure/deploy.sh
./scripts/deploy_backend.sh
```

Environment variables (optional):

- `STACK_NAME` — defaults to `chumbucket-api`.
- `AWS_REGION` or `AWS_DEFAULT_REGION` — defaults to `us-east-1` in `infrastructure/deploy.sh`.
- `SAM_PARAMETER_OVERRIDES` — pass CloudFormation parameters, for example Athena result location:

  ```bash
  export SAM_PARAMETER_OVERRIDES='AthenaOutputLocation=s3://your-calcofi-bucket/athena-results/'
  ./scripts/deploy_backend.sh
  ```

  Create the bucket/prefix first; Athena needs write access (the query Lambda IAM policy allows S3 writes broadly for hackathon use).

After deploy, copy stack output **`ApiEndpoint`** from the CloudFormation console or CLI. That value is the API base URL.

## Frontend

1. In `frontend/`, create `.env` (or `.env.local`) with:

   ```bash
   VITE_API_URL=https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/Prod
   ```

   Use the exact `ApiEndpoint` string from the backend deploy (no path suffix; the app appends `/query`).

2. Build and deploy static assets to **your** S3 bucket (bucket must exist; website hosting optional depending on how you serve the app):

   ```bash
   export FRONTEND_S3_BUCKET=your-bucket-name
   chmod +x scripts/deploy_frontend.sh
   ./scripts/deploy_frontend.sh
   ```

Optional: set `CLOUDFRONT_DISTRIBUTION_ID` to invalidate `/*` after sync.

Local dev without S3:

```bash
cd frontend
npm ci
npm run dev
```

## Data: seed S3 and register Athena

1. Create or choose an S3 bucket for CalCOFI-style CSV data.
2. Upload the sample file so the prefix matches what you will put in the DDL:

   ```bash
   export DATA_S3_BUCKET=your-data-bucket
   export DATA_S3_PREFIX=calcofi/bottle_data/
   chmod +x scripts/seed_data.sh
   ./scripts/seed_data.sh
   ```

3. Edit `data/schemas/calcofi_schema.sql`: set `LOCATION` to your data prefix (for example `s3://your-calcofi-bucket/calcofi/bottle_data/`) so it matches where you upload CSVs (trailing slash as in AWS docs).
4. In the **Athena** console, run the statements in `data/schemas/calcofi_schema.sql`, then try queries from `data/queries/sample_queries.sql`.

## Local Lambda invoke (optional)

With SAM CLI, from repo root after `sam build`:

```bash
sam local invoke QueryFunction \
  --template-file infrastructure/template.yaml \
  --event infrastructure/events/api_events.json
```

Ensure the template path matches your build; for deploy, the project uses `.aws-sam/build/template.yaml` after `sam build`.

## Troubleshooting

| Issue | What to check |
| --- | --- |
| Frontend calls wrong host | `VITE_API_URL` must be the API Gateway base (`.../Prod`), rebuild after changing `.env`. |
| CORS errors | API template enables CORS for `POST`/`OPTIONS`; confirm you are not mixing `http`/`https` or wrong stage. |
| Athena empty or access denied | Table `LOCATION` matches seeded prefix; IAM on Lambda allows Athena and S3; Glue table exists. |
| SAM deploy fails | `CAPABILITY_IAM`, `--resolve-s3`, and correct region; bootstrap S3 bucket for SAM if first deploy in account/region. |
