# StockSense

AI-powered stock prediction and alerting platform. Flask + PostgreSQL backend, LSTM neural-network predictor, email/browser-push alerts, real-time price stream, multi-currency portfolio + watchlist tracking, dark/light theme, mobile-friendly responsive UI.

---

## Quickstart — run on a fresh system

```bash
# 1. Clone
git clone https://github.com/Mahnoorjaved-mj/Stock-Market.git
cd Stock-Market

# 2. (Optional but recommended) virtual env
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux

# 3. Install everything (~3–5 min, torch is the slow one)
pip install -r requirements.txt

# 4. Set up env vars
cp .env.example .env
# edit .env: fill in FLASK_SECRET_KEY, DB_*, SMTP_*

# 5. Start Postgres (locally or via docker)
docker compose up -d db          # if you have docker
# or install Postgres locally and create database `stock_alert_db`

# 6. Run the server
cd backend && python wsgi.py
```

Open http://127.0.0.1:5000 — register an account at `/register`, check your inbox for the 6-digit OTP, finish sign-up, and you're in.

---

## What's inside

| Area | What you get |
| --- | --- |
| **Frontend** | Jinja2 templates, custom CSS design system (Inter + JetBrains Mono fonts), no JS framework, Chart.js for graphs, Server-Sent Events for live prices, Cmd/Ctrl+K command palette |
| **Backend** | Flask + Waitress, blueprint-based routes, bcrypt auth, OTP email verification, password reset, optional TOTP 2FA |
| **AI** | LSTM stock-price predictor (PyTorch), sentiment analysis, top-picks ranking. Falls back to synthetic predictions if torch isn't installed |
| **Database** | PostgreSQL with 12 tables: users, watchlist, portfolio, alerts, alert_history, alert_rules, audit_events, notifications, user_2fa_secrets, push_subscriptions, otp_verification, password_reset_tokens |
| **Background** | APScheduler — 15-min alert sweeps during US market hours, daily + weekly email digests |
| **Security** | CSRF (Flask-WTF), rate-limiting (Flask-Limiter), 4-hour sliding session timeout, audit log of all auth events, secure cookies |
| **Observability** | Structured JSON request logging, Sentry SDK (optional), `/api/health` checks DB + scheduler, `/admin/metrics` page |

---

## Project layout

```
Stock-Market/
├── backend/
│   ├── app.py              # Flask entry, routes, middleware
│   ├── ai_predictions.py   # LSTM predictor (graceful fallback)
│   ├── cache.py            # Redis / in-memory wrapper
│   ├── config.py           # env-driven config
│   ├── db.py               # schema + connection
│   ├── stock_data.py       # yfinance data layer
│   ├── wsgi.py             # production entry (Waitress)
│   ├── routes/             # auth, profile, watchlist, portfolio, alerts, personalized
│   ├── services/           # alerts_engine, audit, digests, email, scheduler
│   ├── email_templates/    # HTML email templates
│   └── tests/              # pytest suite
├── frontend/
│   ├── static/             # style.css, toast.js, cmdk.js
│   └── templates/          # 16 Jinja2 templates
├── alembic/                # DB migrations
├── Dockerfile              # production image
├── docker-compose.yml      # local stack (Flask + Postgres + Redis + MailHog)
├── render.yaml             # one-click deploy blueprint
└── deploymentguide.md      # detailed deploy instructions
```

---

## Configuration

Required environment variables (copy from `.env.example`):

| Key | Purpose |
| --- | --- |
| `FLASK_SECRET_KEY` | Session cookie signing — generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `FLASK_DEBUG` | `false` in production, `true` locally |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL connection |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Email for OTP, password reset, digests, alerts |
| `APP_BASE_URL` | Public URL of the deployed app |

Optional:

| Key | Effect when set |
| --- | --- |
| `REDIS_URL` | Shared cache + rate-limit storage (otherwise in-memory) |
| `SENTRY_DSN` | Error tracking |
| `ALPHA_VANTAGE_KEY` | Bonus market data source (yfinance is the default) |

See **[deploymentguide.md](./deploymentguide.md)** for the complete env-var reference and where to obtain each secret.

---

## Common tasks

```bash
# Run tests
pytest -q

# Lint
ruff check backend

# Format
black backend

# Stand up the full local stack (Postgres + Redis + MailHog + web)
docker compose up -d --build

# Tear it down
docker compose down

# Reset the database schema (DESTRUCTIVE — wipes all data)
DROP_AND_REBUILD_SCHEMA=true python -c "import sys; sys.path.insert(0, 'backend'); from db import init_schema; init_schema()"
```

Or use the `Makefile`: `make dev`, `make test`, `make lint`, `make docker-up`.

---

## Deployment

See **[deploymentguide.md](./deploymentguide.md)** for step-by-step instructions on:

- **Render.com** (recommended — no credit card, one-click blueprint via `render.yaml`)
- **Fly.io** (more resources, requires card)
- **Railway** ($5 free monthly credit, requires card)
- **Docker Compose on any VPS** (full control)

Free-tier components you can mix and match:

| Need | Free option |
| --- | --- |
| Web app | Render free web service · Koyeb nano |
| Postgres | Render Postgres (90 days) · Supabase (forever, 500 MB) · Neon (forever, 0.5 GB) |
| Redis | Render key-value · Upstash (10 k cmds/day) |
| Email (SMTP) | Gmail App Password · Resend (3 k emails/month) |
| Error tracking | Sentry free tier (5 k events/month) |
| Uptime ping | UptimeRobot (free, no card) |

---

## API endpoints (quick reference)

Public:
- `GET /api/health` — DB + scheduler status
- `GET /get_live_data` — cached dashboard snapshot
- `GET /stream/prices` — Server-Sent Events live feed
- `GET /api/search?q=…` — ticker autocomplete
- `GET /api/stock/<symbol>` — current price + day OHLC
- `GET /api/stock/<symbol>/history?range=1mo` — historical close prices
- `GET /api/predict/<symbol>?days=7` — AI prediction (or fallback)
- `GET /api/sentiment/<symbol>` — sentiment classification
- `GET /api/top_picks` — top 5 AI buy signals
- `GET /api/market-analysis` — daily OHLC for ~80 US tickers
- `GET /api/ai/backtest/<symbol>` — 6-month signal backtest

Authenticated (session cookie + CSRF token):
- `GET / POST / PUT / DELETE /api/watchlist` — manage tracked symbols
- `GET / POST / DELETE /api/portfolio` — manage holdings
- `GET /api/portfolio/export.csv` — CSV export
- `GET /api/alerts/history` — alert event log
- `POST /api/alerts/run-now` — manual sweep
- `GET / PUT / DELETE /api/profile` — user settings
- `POST /api/2fa/setup|verify|disable` — TOTP 2FA
- `GET /api/notifications`, `POST /api/notifications/read-all` — in-app notification center

Admin (requires `users.is_admin = TRUE`):
- `GET /admin/metrics` — operator dashboard
- `GET /api/admin/metrics` — raw metrics JSON

---

## License

MIT (or as specified in `LICENSE` — add one if you plan to open-source).
