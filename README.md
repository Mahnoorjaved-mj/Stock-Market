# StockSense

Real-time global stock dashboard with watchlists, portfolio P&L, price alerts,
email digests, and LSTM-based AI predictions.

**Stack (after migration):**

| Layer    | Tech |
|----------|------|
| Frontend | React + Vite + Tailwind CSS, Context API (`client/`) |
| Backend  | FastAPI, JWT auth (`server/`) |
| Database | MongoDB (Motor async driver) |
| Jobs     | APScheduler (alert sweeps + daily/weekly digests) |
| AI       | PyTorch LSTM predictor (optional; degrades to a stub if torch is absent) |
| Data     | Alpha Vantage (primary) + yfinance (fallback) |

The previous Flask + PostgreSQL + Jinja implementation is archived under
[`legacy/`](./legacy) for reference.

---

## Repo layout

```
server/            FastAPI backend — config / models / controllers / routes / services / utils
server/ai_models/  trained LSTM weights (git-ignored)
client/            React SPA       — src/{components, pages, context}  (all API calls live in src/context/context.jsx)
old/               archived Flask app (git-ignored, reference only)
```

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- MongoDB 7 running locally (`mongodb://localhost:27017`) or a MongoDB Atlas URI

---

## Quick start (local dev)

### 1. Backend

```bash
cd server
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt   # omit torch to skip AI (stub fallback)
cp .env.example .env              # then fill in MONGO_URI, JWT_SECRET, SMTP, ALPHA_VANTAGE_KEY
uvicorn main:app --reload --port 8000
```

API docs: <http://127.0.0.1:8000/docs> · health: <http://127.0.0.1:8000/api/health>

### 2. Frontend

```bash
cd client
npm install
npm run dev                       # http://localhost:5173
```

The Vite dev server proxies `/api`, `/auth`, `/get_live_data`, and `/stream`
to the backend on port 8000, so no extra config is needed in development.
For production, set `VITE_API_BASE_URL` to the deployed API URL.

---

## Auth flow

1. `POST /auth/register` → emails a 6-digit OTP
2. `POST /auth/verify-otp` → creates the account, returns a **JWT**
3. `POST /auth/login` → returns a JWT
4. The client stores the token (localStorage) and sends `Authorization: Bearer <token>`

DB-backed routes return `401` without a valid token; admin routes require
`is_admin` on the user document (set it directly in Mongo to grant access).

---

## Notes

- **MongoDB must be running** for auth, watchlist, portfolio, alerts, and admin
  endpoints. Public market/AI endpoints (`/get_live_data`, `/api/predict/...`)
  work without it.
- **torch** is optional and large (~800 MB). Without it, AI endpoints return
  statistical fallback responses.
- Alert sweeps and digest emails run on a schedule during US market hours; the
  scheduler starts automatically with the API.
