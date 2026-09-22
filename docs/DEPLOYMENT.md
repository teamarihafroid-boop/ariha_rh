# Deploying ARIHA AI to production

You already have a Railway account. This walks through: creating the R2 bucket, configuring the
Railway project for this app, wiring up your custom domain, and setting up backups. Follow it in
order — each section depends on values from the one before it.

## 1. Cloudflare R2 (file storage)

1. Cloudflare dashboard → **R2 Object Storage** → **Create bucket**.
   - Name: `ariha-documents` (or anything — you'll put it in `STORAGE_S3_BUCKET`).
   - Location: **Automatic** — R2 doesn't offer manual EU pinning per-bucket the way some providers
     do; Cloudflare's network places it close to where it's used, which in practice keeps EU traffic
     in the EU. If strict EU-only guarantees matter, revisit this before storing real employee data.
2. **Manage R2 API Tokens** → **Create API Token**.
   - Permissions: **Object Read & Write**, scoped to the `ariha-documents` bucket only (not "all
     buckets").
   - Save the **Access Key ID** and **Secret Access Key** it shows you — the secret is shown once.
3. Your **endpoint URL** is `https://<account-id>.r2.cloudflarestorage.com` — the account ID is
   visible in the R2 dashboard's sidebar or in the token creation screen.

You now have the four `STORAGE_S3_*` values for step 3.

## 2. Railway project

1. In your existing Railway account, **New Project** → **Deploy from GitHub repo** → pick
   `teamarihafroid-boop/ariha_rh`. If Railway isn't already connected to that GitHub account/org,
   authorize it, and make sure `medghazouan` (or whoever else needs deploy access) is added as a
   repo collaborator first.
2. Railway will detect the `Dockerfile` at the repo root automatically — no buildpack config needed.
3. **Add a Postgres plugin** to the project (Railway's own managed Postgres) and a **Redis plugin** —
   both auto-inject `DATABASE_URL`/`REDIS_URL`-shaped variables. You'll need to reference those in
   the app service's own variables (Railway lets you do `${{Postgres.DATABASE_URL}}` etc. as a
   variable reference, so they stay in sync if Railway ever rotates them).
   - **Region:** pick an EU region for the project (e.g. `europe-west4`) for both the Postgres and
     Redis plugins — this is a Loi 09-08 data-residency point (see `TECHNICAL_DECISIONS.md` §8), not
     just a latency choice.
   - Railway's `DATABASE_URL` comes out as `postgresql://...` — this app's `DATABASE_URL` setting
     expects the `postgresql+psycopg://...` driver prefix. Either set
     `DATABASE_URL=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}`
     using Railway's individual `PG*` variables, or just take the provided `DATABASE_URL` and prepend
     `+psycopg` by hand in the app service's variable.
4. On the **app service**, set these variables (Railway → service → Variables):

   | Variable | Value |
   |---|---|
   | `ENV` | `production` |
   | `DATABASE_URL` | see note above |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` |
   | `SESSION_SECRET` | a long random string — generate one with `openssl rand -hex 32`, never reuse the dev value |
   | `COOKIE_SECURE` | `true` |
   | `CORS_ORIGINS` | `["https://your-domain.example"]` (see §3 — set this once you know the domain) |
   | `STORAGE_BACKEND` | `s3` |
   | `STORAGE_S3_BUCKET` | from step 1 |
   | `STORAGE_S3_ENDPOINT_URL` | from step 1 |
   | `STORAGE_S3_ACCESS_KEY_ID` | from step 1 |
   | `STORAGE_S3_SECRET_ACCESS_KEY` | from step 1 |
   | `GEMINI_API_KEY` | your key, if enabling CV auto-extraction (see the CNDP note below) |

   `PORT` is injected by Railway automatically — the Dockerfile's `CMD` already reads it.

5. Deploy. Railway builds the Dockerfile (frontend build + backend, per the multi-stage setup),
   runs `alembic upgrade head` on boot, then starts uvicorn. Watch the deploy logs for the migration
   step specifically — a bad migration fails loudly there, before the app ever starts serving.
6. Once it's up, seed the three baseline logins: open a Railway shell on the service (or a one-off
   run) and execute `python -m app.seed`. This creates `rh@arihafroid.ma` / `dg@arihafroid.ma`
   (password `ChangeMoi123!`) — **change these passwords immediately** via Comptes utilisateurs once
   you've logged in, this default is public in the repo's README.

## 3. Custom domain

1. Railway → app service → **Settings** → **Networking** → **Custom Domain** → enter your domain
   (e.g. `rh.arihafroid.ma`) and Railway gives you a CNAME target.
2. In your DNS provider (wherever `arihafroid.ma` is registered), add a **CNAME** record pointing
   your chosen subdomain at the target Railway gave you. Railway provisions a TLS certificate
   automatically once the CNAME resolves — this can take a few minutes to a few hours depending on
   DNS propagation.
3. Go back and set `CORS_ORIGINS=["https://rh.arihafroid.ma"]` (step 2.4) to the real domain once
   it's confirmed working, then redeploy.

## 4. Backups

`app/scripts/backup_db.py` dumps Postgres and uploads it (gzip'd) to the same R2 bucket, under
`backups/postgres/<timestamp>.sql.gz`. It refuses to run unless `STORAGE_BACKEND=s3`, so it's safe
by construction — it can't silently no-op into a non-durable destination.

To schedule it nightly on Railway:
1. **New Service** in the same project → **Empty Service** (or duplicate the app service).
2. Point it at the same Dockerfile/repo, but override the **start command** to
   `python -m app.scripts.backup_db` instead of the default uvicorn command.
3. Railway → service → **Settings** → **Cron Schedule** → e.g. `0 2 * * *` (02:00 daily).
4. Give it the same `DATABASE_URL`/`STORAGE_S3_*` variables as the app service (reference them the
   same way, e.g. `${{app.STORAGE_S3_BUCKET}}`, so they can't drift out of sync).

This is the independent second backup line — Railway's own managed Postgres backups are the first
(check they're enabled on the Postgres plugin itself, under its own Settings).

## 5. Before real employee data goes in

- [ ] Confirm login works end-to-end on the real domain, over HTTPS.
- [ ] Change the `rh@arihafroid.ma` / `dg@arihafroid.ma` passwords from the seed default.
- [ ] Confirm a document upload/download round-trip works (proves the R2 wiring end-to-end, not just
      that the app boots).
- [ ] Confirm the backup Cron Job has actually run once and produced a file in
      `backups/postgres/` in the R2 bucket.
- [ ] **CNDP authorization** for the Gemini CV-extraction feature, if `GEMINI_API_KEY` is set — per
      `TECHNICAL_DECISIONS.md` §5, sending candidate CVs to a non-EU cloud API requires prior
      authorization under Loi 09-08. This is a legal/compliance step outside this codebase; track it
      separately and don't treat the feature being *live* as the compliance step being *done*.
- [ ] Set up basic uptime monitoring (e.g. a free UptimeRobot check against `/health`) and error
      tracking (e.g. Sentry's free tier) — neither is wired into the app yet; both are optional but
      cheap insurance once real data is on the line.
