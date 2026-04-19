# Setup

End-to-end setup for developers and demo environments: tooling, configuration, deploy order, and Athena data loading.

## Prerequisites

- **Node.js** (current LTS) and npm — for `frontend/`.
- **Python 3.11** — matches the query Lambda runtime in `calcofi-dashboard/template.yaml`.
- **AWS CLI** v2, configured with credentials (`aws sts get-caller-identity` works).
- **AWS SAM CLI** — for `sam build` and `sam deploy` ([Installing the AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)).

## Repository layout (quick reference)

- `frontend/` — Vite + React app.
- `backend/functions/` — Lambda source per function.
- `calcofi-dashboard/` — SAM `template.yaml`, `samconfig.toml`, `events/` (e.g. `query_event.json` for local invoke).
- `infrastructure/` — legacy `deploy.sh` wrapper only (forwards to `scripts/deploy_backend.sh`).
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

- **Stack name and region** — taken from **`calcofi-dashboard/samconfig.toml`** when you run `sam deploy` (default stack **`calcofi-dashboard`**, **`us-west-1`**). Override with `sam deploy --stack-name … --region …` if needed.
- `SAM_PARAMETER_OVERRIDES` — optional. The template defaults **`AthenaDatabase`** to **`default`**, **`AthenaTable`** to **`bottle_table`**, and **`AthenaOutputLocation`** to **`s3://your-calcofi-bucket/athena-results/`**. Override if your tables live in another database or bucket:

  ```bash
  export SAM_PARAMETER_OVERRIDES='AthenaDatabase=my_glue_db AthenaTable=bottle_table AthenaOutputLocation=s3://your-calcofi-bucket/athena-results/'
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

## GitHub Pages (frontend only)

Host the Vite app from the [`frontend/`](../frontend/) directory on [GitHub Pages](https://pages.github.com/) without relying on pushes to the **default branch** (`master` on [eri-gon/Chumbucket_hackathon26](https://github.com/eri-gon/Chumbucket_hackathon26)). The workflow [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml) runs on:

- **`workflow_dispatch`** — in GitHub: **Actions → Deploy to GitHub Pages → Run workflow**, and pick the branch that contains the workflow and current frontend (e.g. a long-lived `pages` branch).
- **`push` to branch `pages` only** — optional auto-deploy when you commit to `pages`; it does **not** run on `master`.

### Repository settings (GitHub UI)

1. **Settings → Pages → Build and deployment**: set **Source** to **GitHub Actions** (not “Deploy from a branch” for the old `gh-pages` flow).
2. **Settings → Secrets and variables → Actions**:
   - **Secret `VITE_API_URL`** — same value as local `frontend/.env`: API Gateway stage base, e.g. `https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/Prod` (no `/query` suffix; see [`frontend/src/services/api.ts`](../frontend/src/services/api.ts)). The workflow reads this at build time via `${{ secrets.VITE_API_URL }}`.
   - **Variable `VITE_BASE`** (optional) — leave unset to use **`/<repository-name>/`** for a project site. Set to **`/`** only if you publish a **user/org** site at the domain root.
3. **Settings → Environments → `github-pages`** — the **deploy** job in [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml) targets this environment. Under **Deployment branches and tags**, allow the branch you publish from (this repo uses **`pages`**). If only `main` / `master` is allowed, deploy fails with *Branch "pages" is not allowed to deploy to github-pages due to environment protection rules*. Fix: add **`pages`** under **Selected branches**, or use **All branches** only if your org policy allows it. If **Required reviewers** or a **Wait timer** is set on `github-pages`, approve the pending deployment or relax those rules so the deploy job can finish.

### Troubleshooting: Pages deploy blocked by environment

Symptoms: **build** succeeds; **deploy** fails with *Branch "pages" is not allowed to deploy to github-pages* or *The deployment was rejected or didn't satisfy other protection rules*.

1. **Deployment branches** — **Settings → Environments → `github-pages`**. Ensure **`pages`** is allowed (see step 3 above). Org-owned repos may need an org owner to change environment rules.
2. **Reviewers / wait timer** — Same environment page: remove or satisfy **Required reviewers**; check **Actions** for a deployment waiting on approval.
3. **Re-run** — After fixing rules: **Actions** → failed workflow → **Re-run failed jobs**, or push a new commit to **`pages`**.

### Project site URL shape

For this repo, the published app is:

`https://eri-gon.github.io/Chumbucket_hackathon26/`

[`frontend/vite.config.ts`](../frontend/vite.config.ts) sets `base` from **`VITE_BASE`** at build time (CI injects it). [`frontend/index.html`](../frontend/index.html) asset URLs are resolved relative to that base.

### Workflow without merging to `master`

1. Create branch **`pages`** from your current work (or any branch that already has `.github/workflows/deploy-pages.yml` and the `frontend/` tree you want live).
2. Push **`pages`** to GitHub (this does not change `master`).
3. Either push new commits to **`pages`** to trigger a deploy, or use **Run workflow** and select **`pages`** so Actions checks out that ref.

### Verification checklist

After a successful run:

1. Open the Pages URL above; confirm the shell loads (no blank page — wrong `VITE_BASE` usually breaks JS/CSS paths).
2. Open devtools **Network**, run **Query**; confirm `POST …/query` hits your API and CORS succeeds (Lambda returns `Access-Control-Allow-Origin: *` for the demo).

## Data: seed S3 and register Athena

1. Use bucket **`your-calcofi-bucket`** (or set `DATA_S3_BUCKET` to the bucket name that matches your Glue `LOCATION`).
2. Upload the sample file so the prefix matches `data/schemas/calcofi_schema.sql`:

   ```bash
   export DATA_S3_BUCKET=your-calcofi-bucket
   export DATA_S3_PREFIX=calcofi/bottle/
   chmod +x scripts/seed_data.sh
   ./scripts/seed_data.sh
   ```

3. Confirm `data/schemas/calcofi_schema.sql` **`LOCATION`** values: **`s3://your-calcofi-bucket/calcofi/cast/`** for `cast.csv` and **`s3://your-calcofi-bucket/calcofi/bottle/`** for `bottle.csv` (trailing slashes as in AWS docs).
4. In the **Athena** console, run the statements in `data/schemas/calcofi_schema.sql`, then try queries from `data/queries/sample_queries.sql`.

## Local Lambda invoke (optional)

With SAM CLI, from **`calcofi-dashboard/`** after **`sam build`**:

```bash
cd calcofi-dashboard
sam build
sam local invoke QueryFunction --event events/query_event.json
```

For deploy, SAM uses **`calcofi-dashboard/.aws-sam/build/template.yaml`** after **`sam build`**.

## Test deployed `POST /query` (Lambda → Athena)

From the **repo root**, with the same base URL as `frontend/.env` **`VITE_API_URL`** (no `/query` suffix), or set **`API_BASE_URL`**:

```bash
python scripts/test_query_api.py --metric temperature --depth 10
```

Or with **Node** (also used by the frontend npm script):

```bash
cd frontend
npm run test:api
```

Override URL once:

```bash
node scripts/test-query-api.mjs --url https://YOUR_API_ID.execute-api.YOUR_REGION.amazonaws.com/Prod
```

Successful responses include **`success`**, **`data`** (Athena rows), and **`query`** (SQL string). Exit code is non-zero on HTTP errors or **`success: false`**.

## Troubleshooting

| Issue | What to check |
| --- | --- |
| Frontend calls wrong host | `VITE_API_URL` must be the API Gateway base (`.../Prod`), rebuild after changing `.env`. |
| CORS errors | API template enables CORS for `POST`/`OPTIONS`; confirm you are not mixing `http`/`https` or wrong stage. |
| Athena empty or access denied | Table `LOCATION` matches seeded prefix; IAM on Lambda allows Athena and S3; Glue table exists. |
| SAM deploy fails | `CAPABILITY_IAM`, `--resolve-s3`, and correct region; bootstrap S3 bucket for SAM if first deploy in account/region. |
