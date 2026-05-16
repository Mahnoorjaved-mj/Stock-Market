# Deploying StockSense for free

This guide covers three free-tier paths. Render is the easiest; Fly.io is the most generous if you don't mind a credit-card check; Railway is the smoothest dev experience but only free for $5/month of credit.

| Provider     | Web app                  | Postgres                 | Redis             | Card req? | Sleeps?       |
| ------------ | ------------------------ | ------------------------ | ----------------- | --------- | ------------- |
| **Render**   | Free web service         | Free 90 days (1GB)       | Free key-value    | No        | 15-min idle ↘ |
| **Fly.io**   | 3 shared-cpu-1x@256MB    | 3GB Fly Postgres         | Upstash add-on    | Yes       | No            |
| **Railway**  | $5/mo credit             | Included in $5/mo        | Included          | Yes       | No            |
| **Koyeb**    | 1 free service           | Use Supabase             | Use Upstash       | No        | No            |

Recommended for a beginner: **Render**. Skip down to that section.

---

## Before any deploy: prep your repo

1. **Generate a strong secret key** locally and save it for the next step:
   ```
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Get SMTP credentials.** OTP signup, password reset, and alert digests all need email. Gmail App Password works:
   - Enable 2-step verification on your Google account.
   - Visit https://myaccount.google.com/apppasswords
   - Create an app password named "StockSense", copy the 16-character password.
   - Or use a free SMTP service: Resend (3 000 emails/month) — sign up at https://resend.com.

3. **Push your code to GitHub.** If the repo isn't on GitHub yet:
   ```
   git init
   git add .
   git commit -m "initial commit"
   gh repo create stock-market --public --source=. --push
   ```
   (Or create the repo manually at github.com/new and `git push` to it.)

4. **Verify `.env` is NOT tracked.** Run:
   ```
   git ls-files | grep .env
   ```
   If it prints `.env`, remove it from the index first:
   ```
   git rm --cached .env && git commit -m "untrack .env"
   ```

---

## Option A — Render (recommended)

### One-click via blueprint

1. Push the repo to GitHub (with `render.yaml` at the root — already provided).
2. Visit https://dashboard.render.com/blueprints → **New Blueprint Instance**.
3. Paste your GitHub repo URL.
4. Render reads `render.yaml`, provisions:
   - `stocksense-web` (free web service)
   - `stocksense-db` (free Postgres)
   - `stocksense-cache` (free key-value / Redis)
5. After provisioning, open the **stocksense-web → Environment** tab and fill in the SMTP vars that were marked `sync: false`:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
   - `APP_BASE_URL` → set this to your Render URL once you see it, e.g. `https://stocksense-web.onrender.com`
6. Click **Deploy latest commit**. First build takes ~5–8 minutes (heavy ML deps).
7. Health check at `https://stocksense-web.onrender.com/api/health` should return `200`.

### Manual setup (if blueprint fails)

1. **Postgres**: dashboard → **New + → PostgreSQL** → free plan → name `stocksense-db` → create. Copy the **Internal Database URL**.
2. **Key-value (Redis)**: dashboard → **New + → Key-Value** → free plan → name `stocksense-cache` → create. Copy the connection string.
3. **Web service**: dashboard → **New + → Web Service** → connect GitHub repo → settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `cd backend && python wsgi.py`
   - Health check path: `/api/health`
   - Environment variables (from the values you copied):
     ```
     FLASK_SECRET_KEY     = <generated string>
     FLASK_DEBUG          = false
     APP_BASE_URL         = https://YOUR-APP.onrender.com
     HOST                 = 0.0.0.0
     PORT                 = 5000
     DB_HOST              = (from Postgres internal URL)
     DB_PORT              = 5432
     DB_NAME              = stock_alert_db
     DB_USER              = (from Postgres URL)
     DB_PASSWORD          = (from Postgres URL)
     REDIS_URL            = (from key-value connection string)
     RATELIMIT_STORAGE_URI= (same as REDIS_URL)
     SMTP_HOST            = smtp.gmail.com
     SMTP_PORT            = 587
     SMTP_USER            = your-email@gmail.com
     SMTP_PASSWORD        = <gmail app password>
     SMTP_FROM_NAME       = StockSense Alerts
     ```
4. Click **Create Web Service** and wait for the build.

### Render free-tier caveats

- The free web service **sleeps after 15 minutes** of no traffic. First request after sleep takes ~30 s to wake. Acceptable for a portfolio demo.
- The free Postgres expires after **90 days**. Before then, migrate to Supabase (forever-free 500MB) by exporting + re-importing the database.
- The free key-value store has **25 MB**. Plenty for our cache.

---

## Option B — Fly.io

### One-time setup

```
# Install flyctl
curl -L https://fly.io/install.sh | sh        # macOS / Linux
# OR
iwr https://fly.io/install.ps1 -useb | iex     # Windows PowerShell

fly auth signup
```

### Launch

From the project root:

```
fly launch --no-deploy --name stocksense --region iad
fly postgres create --name stocksense-db --region iad --vm-size shared-cpu-1x --initial-cluster-size 1
fly postgres attach stocksense-db --app stocksense
fly secrets set \
  FLASK_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  FLASK_DEBUG=false \
  APP_BASE_URL=https://stocksense.fly.dev \
  SMTP_HOST=smtp.gmail.com SMTP_PORT=587 \
  SMTP_USER=your-email@gmail.com SMTP_PASSWORD='your-app-password'
fly deploy
```

Fly reads `Dockerfile` automatically. Health check uses `/api/health` per Dockerfile.

### Redis on Fly (optional)

```
fly redis create --name stocksense-cache --region iad
fly redis status stocksense-cache       # copy the connection URL
fly secrets set REDIS_URL='redis://...' RATELIMIT_STORAGE_URI='redis://...'
```

---

## Option C — Railway

1. Visit https://railway.app and sign up (GitHub login).
2. **New Project → Deploy from GitHub** → pick your repo.
3. Railway detects the `Dockerfile`, builds, and deploys.
4. **Add plugin → PostgreSQL** → it auto-injects `DATABASE_URL`. Add the individual vars too:
   - In service → **Variables**: click **Add Variable from Postgres** → expose host/port/name/user/password as `DB_HOST` etc.
5. Add SMTP and `FLASK_SECRET_KEY` manually.
6. **Settings → Networking → Generate Domain** to get a public URL.

Railway gives $5 free credit/month — enough for this app for ~3 weeks/month at low traffic.

---

## Option D — Docker Compose on any VPS

If a friend has a Linux server, or you find a free VPS:

```
git clone https://github.com/YOU/stock-market.git
cd stock-market
cp .env.example .env
# edit .env with your secrets
docker compose up -d --build
```

The stack includes Postgres + Redis + MailHog (dev SMTP UI at port 8025). For production swap MailHog for real SMTP credentials in `.env`.

---

## Free Postgres alternatives (when Render's 90-day clock runs out)

- **Supabase** — 500 MB forever-free. https://supabase.com → New Project → copy the `Direct connection` string.
- **Neon** — 0.5 GB forever-free, autoscaling. https://neon.tech.
- **Aiven** — 1-month trial then paid.

To migrate, just dump + restore:
```
pg_dump $RENDER_DB_URL > backup.sql
psql $NEW_DB_URL < backup.sql
```

Then update the `DB_*` env vars on Render and redeploy.

---

## Free Redis alternative

- **Upstash** — 10 000 commands/day forever-free. https://upstash.com → set `REDIS_URL` and `RATELIMIT_STORAGE_URI` to the Upstash URL.

---

## Free email alternatives (instead of Gmail)

- **Resend** — 3 000 emails/month, 100/day. https://resend.com. Use the SMTP integration: `smtp.resend.com:465`, user `resend`, password = your API key.
- **Brevo (Sendinblue)** — 300 emails/day free.
- **SendGrid** — 100 emails/day free.

---

## Post-deploy checklist

After your first successful deploy:

1. **Visit `https://YOUR-APP.onrender.com/api/health`** — expect `{"status":"healthy", "db":{"ok":true}, "scheduler":{"ok":true}}`.
2. **Register a real account** at `/register`. Check inbox for the OTP. If no email arrives:
   - Check Render logs: dashboard → service → **Logs**
   - Verify SMTP env vars
   - Test SMTP from a Render shell: `python -c "from services import email_service; email_service.send_otp('you@example.com', '123456')"`
3. **Make yourself admin** so you can access `/admin/metrics`:
   - From Render Postgres dashboard → **PSQL Command** tab
   - Run: `UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';`
4. **Set up uptime monitoring** (optional but recommended on Render free tier):
   - https://uptimerobot.com — free, pings every 5 min, keeps the service awake.
5. **Add a custom domain** (Render → Settings → Custom Domains; free, auto-HTTPS).

---

## Updating after the first deploy

```
git add . && git commit -m "your changes" && git push origin main
```

Render auto-deploys on push if `autoDeploy: true` in `render.yaml` (default).
Fly: `fly deploy`.
Railway: auto-deploys on push.

---

## Troubleshooting

**Build fails on Render with "torch not found":** the wheels for `torch` are heavy. If the build runs out of memory on the free plan, comment out `torch` lines from `ai_predictions.py` imports, or move to Fly.io (more RAM).

**App boots but `/` returns 500:** check that all `DB_*` env vars are set and `init_schema()` ran. Tail logs.

**OTP emails not arriving:** SMTP creds wrong, or Gmail blocked the login. Use an App Password, not your real Gmail password.

**Free Postgres ran out of disk:** the `alert_history` and `audit_events` tables grow over time. Run:
```sql
DELETE FROM alert_history WHERE sent_at < NOW() - INTERVAL '90 days';
DELETE FROM audit_events  WHERE occurred_at < NOW() - INTERVAL '90 days';
```

**Mobile users report layout broken:** clear browser cache (CDN caching the old CSS).

---

## What's deployed

- Flask + Waitress web server on port 5000
- APScheduler running alert sweeps every 15 min (US market hours) + daily/weekly email digests at 17:00 ET
- LSTM AI training warming up in a background thread
- SSE live price feed at `/stream/prices`
- CSRF on all forms, rate-limited auth, 2FA available in `/settings`
- Health check at `/api/health`, admin metrics at `/admin/metrics` (gated by `is_admin=TRUE`)
