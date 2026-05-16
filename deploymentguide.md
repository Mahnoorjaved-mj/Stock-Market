# StockSense — Deployment Guide

This guide answers two questions:

1. **Which env vars do I need to paste?** → [section below](#environment-variables)
2. **How do I deploy for free?** → [section below](#deploy-to-render-recommended)

---

## Environment variables

Paste these into your hosting provider's "Environment Variables" panel. **Required** ones must be set or the app will refuse to start / fail at first use. **Optional** ones unlock features but the app runs fine without them.

### Required

| Key                  | What it is                                        | Where to get it / example value                                                                                       |
| -------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `FLASK_SECRET_KEY`   | Random string used to sign session cookies        | Generate locally: `python -c "import secrets; print(secrets.token_urlsafe(48))"` — copy the output                    |
| `FLASK_DEBUG`        | `true` in dev, **`false`** in production          | Literal string `false`                                                                                                |
| `APP_BASE_URL`       | Public URL of your deployed app                   | After first deploy, e.g. `https://stocksense-web.onrender.com`                                                        |
| `DB_HOST`            | Postgres host                                     | Provider auto-fills from managed Postgres (Render `From Database`, Fly attach, etc.)                                  |
| `DB_PORT`            | Postgres port                                     | `5432`                                                                                                                |
| `DB_NAME`            | Postgres database name                            | `stock_alert_db` (or whatever your provider gave you)                                                                 |
| `DB_USER`            | Postgres user                                     | From provider                                                                                                         |
| `DB_PASSWORD`        | Postgres password                                 | From provider                                                                                                         |
| `SMTP_HOST`          | Email server hostname (for OTP, password reset, alerts) | Gmail: `smtp.gmail.com` · Resend: `smtp.resend.com`                                                              |
| `SMTP_PORT`          | Email server port                                 | Gmail: `587` · Resend: `465`                                                                                          |
| `SMTP_USER`          | Email login                                       | Your full address, e.g. `you@gmail.com` · Resend: literal string `resend`                                             |
| `SMTP_PASSWORD`      | Email password                                    | **Gmail:** an App Password from https://myaccount.google.com/apppasswords (NOT your real Gmail password) · Resend: your API key |
| `SMTP_FROM_NAME`     | Display name on outgoing email                    | `StockSense Alerts`                                                                                                   |

### Optional

| Key                       | What it is                                                              | Where to get it / example                                                                              |
| ------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `REDIS_URL`               | Shared cache (replaces in-process dict; needed if you run > 1 worker)   | Upstash: https://upstash.com → create database → copy connection URL · Render: from key-value service  |
| `RATELIMIT_STORAGE_URI`   | Where Flask-Limiter stores counters (defaults to in-memory)             | Same value as `REDIS_URL`                                                                              |
| `ALPHA_VANTAGE_KEY`       | Bonus market data source (yfinance is the default)                      | Free key at https://www.alphavantage.co/support/#api-key                                               |
| `SENTRY_DSN`              | Error tracking                                                          | Free 5k events/month at https://sentry.io → New Project → Python/Flask → copy DSN                      |
| `HOST`                    | Bind address                                                            | `0.0.0.0` (default)                                                                                    |
| `PORT`                    | Port to listen on                                                       | `5000` (Render/Fly will inject a different one — leave unset or set to `5000`)                         |
| `THREADS`                 | Waitress thread count                                                   | `8` (default)                                                                                          |
| `DROP_AND_REBUILD_SCHEMA` | **Dangerous.** Drops and recreates all tables on next start             | Leave **unset** in production. Only set to `true` once locally for a clean reset, then unset again.    |

### Where each env var is read

If you ever wonder which env var controls what, search the codebase:

| Var                       | Read in                          |
| ------------------------- | -------------------------------- |
| `FLASK_SECRET_KEY`        | `backend/config.py`              |
| `FLASK_DEBUG`             | `backend/config.py`              |
| `APP_BASE_URL`            | `backend/config.py` → emails    |
| `DB_*`                    | `backend/config.py` → `db.py`    |
| `SMTP_*`                  | `backend/config.py` → `services/email_service.py` |
| `REDIS_URL`               | `backend/cache.py`               |
| `RATELIMIT_STORAGE_URI`   | `backend/app.py` Flask-Limiter   |
| `SENTRY_DSN`              | `backend/app.py` Sentry init     |
| `ALPHA_VANTAGE_KEY`       | `backend/stock_data.py`          |

---

## Local development setup

Before you deploy, prove it works locally.

1. **Copy the env template:**
   ```bash
   cp .env.example .env
   ```
2. Edit `.env`:
   - Generate `FLASK_SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
   - Point `DB_*` at your local Postgres
   - Fill SMTP creds (or leave blank — emails just won't send)
3. **Install Postgres** locally OR use the Docker stack:
   ```bash
   docker compose up -d db redis mail   # starts Postgres + Redis + MailHog (port 8025 for email UI)
   ```
4. **Install Python deps:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the server:**
   ```bash
   cd backend && python wsgi.py
   ```
6. Open http://127.0.0.1:5000 — register an account. Check MailHog at http://127.0.0.1:8025 for the OTP email.

---

## Deploy to Render (recommended)

**Why Render?** No credit card required, free Postgres + Redis-compatible cache, free 750 hours/month web service (enough for one app 24/7), GitHub auto-deploy, free HTTPS, custom domain support.

**Free-tier caveat:** the web service sleeps after **15 minutes of no traffic** and takes ~30 s to wake. Fix this by adding a free https://uptimerobot.com ping every 5 minutes.

### Step 1 — Push your code to GitHub

```bash
# If you haven't initialized git yet:
git init
git add .
git commit -m "initial commit"

# Create a GitHub repo and push (using GitHub CLI):
gh repo create stock-market --public --source=. --push

# Or manually: create the repo at github.com/new, then:
git remote add origin https://github.com/YOUR-USERNAME/stock-market.git
git branch -M main
git push -u origin main
```

**Important:** before pushing, confirm `.env` is NOT tracked:
```bash
git ls-files | grep "^\.env$"
```
If that prints anything, run:
```bash
git rm --cached .env
git commit -m "untrack .env"
git push
```

### Step 2 — Sign up at Render

1. Go to https://render.com → **Sign up** (use your GitHub account for easiest setup).
2. Approve Render's access to your GitHub repo.

### Step 3 — One-click blueprint deploy

I've already written `render.yaml` at the repo root.

1. In Render's dashboard, click **New +** → **Blueprint**.
2. Pick your `stock-market` repo.
3. Render reads `render.yaml` and proposes three resources:
   - `stocksense-web` (web service, free plan)
   - `stocksense-db` (Postgres, free plan, 90-day expiry)
   - `stocksense-cache` (key-value / Redis-compatible, free plan)
4. Click **Apply**.

Render will provision the database first (1–2 min), then start building the web service. **First build takes 5–10 minutes** because `torch` and `tensorflow` are large.

### Step 4 — Set the SMTP env vars

The blueprint deliberately leaves SMTP unset so secrets aren't committed.

1. Once `stocksense-web` shows up in your dashboard, click into it → **Environment** tab.
2. Add the four SMTP variables (values per the [env table above](#required)):
   - `SMTP_HOST` = `smtp.gmail.com` (or whatever provider)
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = your email
   - `SMTP_PASSWORD` = your App Password
3. Also set `APP_BASE_URL` to your Render URL (visible at the top of the service page), e.g. `https://stocksense-web.onrender.com`.
4. Click **Save Changes** — Render redeploys automatically.

### Step 5 — Verify it works

1. Visit `https://YOUR-APP.onrender.com/api/health` — should return JSON with `"status":"healthy"`.
2. Visit the homepage — dashboard loads.
3. Go to `/register`, sign up, check your inbox for the 6-digit OTP, finish registration.

### Step 6 — Make yourself admin (optional)

So you can see `/admin/metrics`:

1. Render dashboard → `stocksense-db` → **Connect** → copy the **PSQL command**.
2. Paste it in any local terminal:
   ```bash
   psql 'postgresql://stocksense:...@dpg-...-a.oregon-postgres.render.com/stock_alert_db'
   ```
3. Run:
   ```sql
   UPDATE users SET is_admin = TRUE WHERE email = 'your@email.com';
   \q
   ```

### Step 7 — Keep the service awake (optional)

1. Sign up free at https://uptimerobot.com.
2. **+ Add New Monitor** → HTTPS → URL: `https://YOUR-APP.onrender.com/api/health` → interval 5 minutes.
3. Done — your service won't sleep.

### Step 8 — Custom domain (optional)

Render → service → **Settings** → **Custom Domains** → add e.g. `stocksense.yourdomain.com`. Free, HTTPS auto-provisioned.

---

## Alternative free hosts

### Fly.io — better resources, requires credit card

Generous free tier (3 small VMs + 3 GB Postgres), never sleeps, but you must add a credit card to verify (no charges within the free allowance).

```bash
# Install flyctl
iwr https://fly.io/install.ps1 -useb | iex      # Windows PowerShell
# OR
curl -L https://fly.io/install.sh | sh           # macOS / Linux

fly auth signup
fly launch --no-deploy --name stocksense --region iad
fly postgres create --name stocksense-db --region iad
fly postgres attach stocksense-db --app stocksense

fly secrets set \
  FLASK_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  FLASK_DEBUG=false \
  APP_BASE_URL=https://stocksense.fly.dev \
  SMTP_HOST=smtp.gmail.com \
  SMTP_PORT=587 \
  SMTP_USER=your-email@gmail.com \
  SMTP_PASSWORD='your-app-password' \
  SMTP_FROM_NAME='StockSense Alerts'

fly deploy
```

### Railway — $5 free monthly credit

Smoothest dev experience but technically not free forever — $5/month credit is enough for ~3 weeks of always-on running at low traffic.

1. https://railway.app → sign in with GitHub
2. **New Project → Deploy from GitHub** → pick your repo
3. **+ New → Database → PostgreSQL** in the same project
4. Set env vars in the service's **Variables** tab (use the table at top of this doc)
5. **Settings → Generate Domain**

### Koyeb — 1 free service forever

Use https://koyeb.com (1 free `nano` service), pair with Supabase Postgres + Upstash Redis. No card required.

### Docker Compose on any VPS

If you have an Ubuntu/Debian box:
```bash
git clone https://github.com/YOU/stock-market.git
cd stock-market
cp .env.example .env
# edit .env
docker compose up -d --build
```

---

## When Render's 90-day free Postgres expires

Migrate to a forever-free option:

1. Sign up at https://supabase.com (or https://neon.tech).
2. New project → copy the **Direct connection** string.
3. Dump + restore:
   ```bash
   pg_dump 'postgresql://...render-url...' > backup.sql
   psql 'postgresql://...supabase-url...' < backup.sql
   ```
4. Update `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` env vars on Render to the new database.
5. Trigger a redeploy.

---

## Quick reference: getting each secret

| Secret               | How to get it                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `FLASK_SECRET_KEY`   | Run `python -c "import secrets; print(secrets.token_urlsafe(48))"` in any terminal         |
| Gmail App Password   | https://myaccount.google.com/apppasswords (enable 2FA on Google first)                     |
| Resend SMTP password | Sign up at https://resend.com → API Keys → Create — use the key as `SMTP_PASSWORD`, user = `resend` |
| Postgres credentials | Render: auto-filled by blueprint · Fly: auto-filled by `fly postgres attach` · Manual: from your provider's dashboard |
| Upstash Redis URL    | https://upstash.com → Create Database → copy `Redis URL`                                   |
| Sentry DSN           | https://sentry.io → New Project (Python/Flask) → copy DSN                                  |
| Alpha Vantage key    | https://www.alphavantage.co/support/#api-key — free, instant                               |

---

## Troubleshooting

**Build fails: "torch / tensorflow not found"**
The free-tier build may run out of memory on heavy ML wheels. Either pay for a higher-tier build instance temporarily, or comment out the heavy imports in `ai_predictions.py` so the app boots without AI (predictions endpoint will return the fallback response).

**App boots but `/` returns 500**
Check Render logs (service → **Logs** tab). Most common cause: missing or wrong `DB_*` env vars. The first line of the log will say "could not connect to server: …".

**OTP email never arrives**
1. Check Render logs for `smtplib` errors.
2. Confirm `SMTP_*` env vars are set (no typos).
3. Gmail: confirm you're using an **App Password**, not your real Gmail password.
4. Test locally first: `python -c "import sys; sys.path.insert(0,'backend'); from services import email_service; email_service.send_otp('you@email.com', '123456')"`

**Health check shows `"db": {"ok": false}`**
Wrong `DB_*` env vars. Render: try the blueprint redeploy. Fly: re-run `fly postgres attach`.

**Redis warnings in logs**
Harmless — the app falls back to in-process cache automatically. Set `REDIS_URL` to silence them.

**Free Postgres ran out of space**
Old alert history and audit events pile up. Run:
```sql
DELETE FROM alert_history WHERE sent_at < NOW() - INTERVAL '90 days';
DELETE FROM audit_events  WHERE occurred_at < NOW() - INTERVAL '90 days';
VACUUM FULL;
```

**Mobile users see broken layout after redeploy**
CDN / browser cache. Hard refresh: Ctrl+Shift+R on desktop, or reinstall the home-screen icon on iOS.

---

## Post-deploy checklist

- [ ] `/api/health` returns 200 with all checks green
- [ ] Can register a new account and receive the OTP email
- [ ] Can log in
- [ ] Dashboard live data loads
- [ ] Stock detail page renders Chart.js
- [ ] Mobile drawer + responsive layout work on your phone
- [ ] Uptime Robot ping configured (Render free tier only)
- [ ] At least one user has `is_admin = TRUE` for `/admin/metrics`
- [ ] Sentry receiving events (if `SENTRY_DSN` set) — trigger a fake error to verify

You're live.
