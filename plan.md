# StockSense — Production Redesign & Feature Plan

> Goal: transform StockSense from a working prototype into a polished, production-grade fintech app. Phased so each phase ships value on its own.

---

## Snapshot of where things stand today

**Working:** Flask + PostgreSQL backend, LSTM AI predictions, alert engine + email digests (APScheduler), bcrypt auth + session, password reset, 13 templates, dark/light theme toggle, Alpha Vantage + yfinance data.

**Pain points to fix:**
- Visual language is inconsistent — three eras of CSS layered on top of each other in `style.css`; every page redefines its own card/button styles; emojis in headings (📈, 🔔, 🤖) read as amateur.
- Body gradient, gradient text, bouncy hover transforms — all dated 2020-era patterns.
- Generic Segoe UI font, no proper typography scale, no tabular numerics for prices.
- `alert("...")` for user feedback instead of toasts.
- No real-time push, only 60s polling. No stock detail pages, no interactive charts beyond static SVG sparklines.
- No CSRF, no rate limiting, no tests, no production WSGI, no Docker.

---

## Design system — the foundation everything else stacks on

Build this once in `base.html` + `style.css`, every page inherits.

### Typography
- **Body:** Inter (Google Fonts) — `400 / 500 / 600 / 700`. Tabular-nums on price/number elements.
- **Numbers/tickers:** JetBrains Mono — small wins, big legibility boost.
- **Scale:** `12 / 13 / 14 / 16 / 18 / 22 / 28 / 36` (no in-between sizes).
- Line-height `1.5` body, `1.2` headings.

### Color tokens (CSS variables — single source of truth)

**Dark (default):**
```
--bg-app:           #0a0a0c
--bg-surface:       #111114      /* cards */
--bg-surface-hover: #161619
--bg-elevated:      #1a1a1f      /* modals, popovers */
--bg-input:         #131316
--border-subtle:    rgba(255,255,255,0.06)
--border:           rgba(255,255,255,0.10)
--border-strong:    rgba(255,255,255,0.15)
--text-primary:     #f4f4f5
--text-secondary:   #a1a1aa
--text-tertiary:    #71717a
--accent:           #4f8cff
--accent-hover:     #3a7aef
--accent-soft:      rgba(79,140,255,0.10)
--color-up:         #10b981      /* fintech green, not the harsh #16a34a */
--color-up-soft:    rgba(16,185,129,0.10)
--color-down:       #ef4444
--color-down-soft:  rgba(239,68,68,0.10)
--color-warn:       #f59e0b
```

**Light:**
```
--bg-app:           #fafafa
--bg-surface:       #ffffff
--bg-surface-hover: #f4f4f5
--bg-elevated:      #ffffff
--bg-input:         #ffffff
--border-subtle:    rgba(0,0,0,0.05)
--border:           rgba(0,0,0,0.10)
--border-strong:    rgba(0,0,0,0.15)
--text-primary:     #09090b
--text-secondary:   #52525b
--text-tertiary:    #71717a
--accent:           #2563eb
--accent-hover:     #1d4ed8
--accent-soft:      rgba(37,99,235,0.08)
--color-up:         #059669
--color-down:       #dc2626
```

Keep all legacy var names (`--card-bg`, `--accent-blue`, etc.) as **aliases** pointing to the new tokens so no template breaks.

### Radius / shadow / spacing
- `--radius-sm: 6px / --radius: 8px / --radius-lg: 12px` — no more `15px`/`16px`/`18px` chaos.
- Shadows mostly retired in favor of borders. Modal/popover only.
- Spacing scale `4 / 8 / 12 / 16 / 20 / 24 / 32 / 48`.

### Things to delete project-wide
- Body gradient (`linear-gradient(135deg, ...)` on `body` and `.card`).
- Gradient text on logo and page-title (`-webkit-background-clip: text`).
- Gradient buttons (`linear-gradient(90deg, #3b82f6, #2563eb)` etc.) — replace with solid accent + subtle border.
- `transform: translateY(-5px)` and `transform: scale(1.03)` hover effects — replace with `background` change only.
- 📈 / 🔔 / 🤖 / ⚖️ / 🚀 emojis in headings — replace with Font Awesome icons (already loaded).
- Old `.container` + `.card` rules in `style.css` lines 1–401 — dead code, kill them.

---

## Phase 1 — Design system rewrite (foundation)

Touches every page automatically via CSS variables. ~1 day of work.

1. **`frontend/templates/base.html`** — rewrite the inline `<style>` block (~290 lines) using the new tokens. Replace 📈 logo with a clean SVG mark + "StockSense" wordmark. Remove translate-x sidebar hover. Add subtle active-nav indicator (left bar 2px, no gradient).
2. **`frontend/static/style.css`** — delete legacy lines 1–538, keep the `.ss-*` shared components (lines 540–683), rewrite them against the new tokens. Add new shared classes: `.ss-tag`, `.ss-tag-up`, `.ss-tag-down`, `.ss-price` (with mono + tabular), `.ss-stat`, `.ss-empty-state`, `.ss-skeleton`.
3. **`frontend/static/login.css`** — delete (43 lines, redundant with `.ss-card`).
4. **Add `frontend/static/toast.js`** — tiny toast system to replace every `alert(...)` call across the app.

### Definition of done for Phase 1
- Same pixels still render, but with new colors/typography/spacing.
- No gradient anywhere except the sidebar accent-bar (1px hairline).
- Login, register, forgot-password, reset-password, profile, watchlist, portfolio, alerts all look consistent because they already use `.ss-*` classes.

---

## Phase 2 — Page-by-page polish

Each page has its own `<style>` block at the top. After Phase 1 the colors are right, but layout per page still needs work.

### 2a. Dashboard (`dashboard.html`)
- Replace 4 generic metric cards with **proper KPI tiles**: large mono number, small label above, delta below with arrow.
- Stock cards → **data-dense ticker rows**: symbol + name on left, sparkline center, price + % delta right. Hover reveals quick actions (add to watchlist, set alert).
- Move "Connection status" out of fixed bottom-right popup into a discrete green/red dot next to the time in header.
- Kill the in-modal login (`#alertModal`). If user isn't logged in, the Alert button just routes to `/login` with a `?next=/alerts` param.
- Add a **search/filter bar** above the stock grid (filter by ticker, country, sentiment).

### 2b. AI Predictions (`ai_predictions.html`)
- 873 lines — split the inline JS into a separate `ai_predictions.js`.
- Rebuild the prediction card: chart on top (predicted vs historical, two lines), key stats below in a tight grid, sentiment as a colored pill not a giant emoji.
- Add **confidence band** around the prediction line.
- Loading → skeleton, not "🌀 Loading...".

### 2c. Market Analysis (`market_analysis.html`)
- Currently a flat list. Promote it to a **heatmap** view (sector × country grid, color = % change) with a fallback table.
- Sort by % change, volume, market cap.

### 2d. Watchlist / Portfolio / Alerts / Profile
- Already use `.ss-*` so 80% comes free. Audit for:
  - Replace `alert()` with toasts.
  - Consistent empty states (e.g. "No alerts yet — create your first one").
  - Form validation feedback inline, not at top of form.

### 2e. Auth pages
- Single column, max-width 420, centered. Brand mark at top. No sidebar (auth pages should be focused).
- **Password strength meter** on register.
- **Show/hide password** toggle.
- After login redirect respects `?next=` param.

### 2f. New pages to add
- **Stock detail page** `/stock/<symbol>` — price header, interactive Chart.js line/candle, key stats sidebar, news feed, recent AI predictions, "add to watchlist" / "set alert" / "buy" actions.
- **404 / 500 error pages** — branded, not Flask default.
- **Settings page** `/settings` — alert threshold, digest frequency, email preferences, theme, account deletion. (Currently mixed into `/profile`.)
- **Onboarding** — first-time login prompt to pick 3–5 tickers for the watchlist.

---

## Phase 3 — Feature additions for "production-level"

### 3a. Real-time
- Replace 60s polling with **Server-Sent Events** (`/stream/prices`). Simpler than WebSocket, fits Flask well.
- Live price flashes (green/red 200ms background pulse on update).

### 3b. Charts
- **Chart.js** (lightweight, MIT) for line + candlestick charts on dashboard ticker cards and the new stock detail page.
- Range selector: 1D / 1W / 1M / 3M / 1Y / 5Y.

### 3c. Command palette (`Cmd/Ctrl+K`)
- Quick navigation: jump to any page, search tickers, run actions ("Add AAPL to watchlist", "Set alert on TSLA").
- Big UX win, low implementation cost.

### 3d. Notifications
- **Toast system** (Phase 1 dependency) for in-app feedback.
- **Browser push notifications** for alerts (with user permission). Falls back to existing email.
- **Notification center** dropdown in header.

### 3e. Portfolio enhancements
- **PnL tracking** — cost basis, unrealized gains, % return.
- **Daily / total return** with chart.
- **CSV import** (broker exports) and **CSV/PDF export**.
- **Diversification view** — pie chart by sector, geography.

### 3f. Alerts enhancements
- Multiple condition types: price above/below, % change, volume spike, MA crossover.
- Alert history with timestamps.
- Snooze / pause / archive.

### 3g. AI features
- **Backtest panel** — "how would your AI's BUY signals have performed over the last 90 days?"
- **Confidence-weighted top picks** instead of raw top 5.
- **Model version** + last-trained timestamp visible to user (trust-building).

### 3h. Search & discovery
- **Global ticker search** with autocomplete, recently viewed, popular searches.
- **News feed** integration (NewsAPI / Finnhub) tied to user's watchlist.
- **Earnings calendar** with reminder option.

### 3i. Accessibility & i18n
- Focus rings on all interactive elements (currently missing).
- ARIA labels on icon-only buttons (theme toggle, alert button).
- Color contrast WCAG AA min (current gradient text fails).
- Currency formatting respects locale (`Intl.NumberFormat`).

---

## Phase 4 — Production hardening (the non-UI stuff)

### 4a. Security
- **CSRF protection** — Flask-WTF or manual token on all state-changing POSTs.
- **Rate limiting** — Flask-Limiter on `/login`, `/register`, `/forgot-password`, `/api/*`.
- **Secure cookies** — already conditional on `FLASK_DEBUG`, audit before deploy.
- **Email verification gate** — block login until email verified (table already has `email_verified` column? — audit).
- **2FA / OTP** — TOTP via `pyotp` for opt-in users.
- **Password strength** — enforce min length, complexity on register + reset.
- **Session timeout** — auto-logout after inactivity.
- **Audit log table** — record auth events (login, password reset, alert created/deleted).
- Move secrets in `.env` to a real secret store before deploy (or at minimum, regenerate `FLASK_SECRET_KEY` and the SMTP password that's currently committed-in-the-clear).

### 4b. Reliability
- **Replace Flask dev server** with Waitress (Windows-friendly) or Gunicorn (Linux).
- **Error tracking** — Sentry SDK.
- **Structured logging** — Python `logging` with JSON formatter, INFO+ to file.
- **Health check** — `/api/health` should also check DB connectivity + scheduler status, not just return static `true`.
- **Background job resilience** — current AI training crashes silently per symbol; add retry with backoff, log to file.
- **Database migrations** — Alembic instead of `DROP_AND_REBUILD_SCHEMA=true`. Currently dangerous.
- **Connection pooling** — `psycopg2.pool` instead of opening a fresh connection per request.

### 4c. Tests
- **Unit tests** — `pytest` for `services/alerts_engine.py`, `services/digests.py`, password hashing, alert threshold logic.
- **Integration tests** — Flask test client against `/api/*` endpoints, real DB in a test schema.
- **Smoke test** — single end-to-end that registers → logs in → adds to watchlist → creates alert → asserts email-sent path is hit (with SMTP mocked).
- Existing `backend/tests/test_api.py` is a stub — expand or delete.

### 4d. DevOps
- **`Dockerfile`** for the backend, **`docker-compose.yml`** that brings up Flask + Postgres + a mailhog (dev SMTP).
- **`requirements.txt`** is missing (project relies on whatever's pip-installed) — generate one with pinned versions: `pip freeze > requirements.txt`.
- **`Makefile`** with `make dev`, `make test`, `make lint`, `make migrate`.
- **GitHub Actions CI** — run lint + tests on every PR.
- **Pre-commit hooks** — `black`, `ruff`, `isort`.

### 4e. Data layer
- **Cache layer** — Redis for the `/get_live_data` 5-min cache instead of in-process dict (currently doesn't survive restart and isn't shared across workers when we move off dev server).
- **Index audit** on `users.email`, `alerts.user_id`, `watchlist.user_id`, `portfolio.user_id`.
- **`updated_at` triggers** on all user-owned tables.

### 4f. Observability
- **Request log** — log every API request with latency, status, user_id.
- **Metrics dashboard** — at minimum: requests/sec, error rate, alert sweep duration, email send success rate. Prometheus + Grafana is overkill for v1; even a `/admin/metrics` page reading from the audit log is fine.

---

## Suggested execution order

If running this end-to-end:

1. **Phase 1** (design system) — biggest visual win for least effort. 1 day.
2. **Phase 2a, 2e** (dashboard + auth pages polish) — most-visited pages. 1 day.
3. **Phase 4a** (security basics: CSRF, rate-limit, secret rotation, email-verify gate) — non-negotiable before any deploy. 1 day.
4. **Phase 4b, 4d** (Waitress + Docker + requirements.txt + structured logging) — makes it deployable. 1 day.
5. **Phase 2b, 2c, 2d, 2f** (remaining page polish + new stock detail + 404/500) — finish the visual job. 1–2 days.
6. **Phase 3a, 3b** (real-time + Chart.js) — the "wow" features. 1 day.
7. **Phase 3c, 3d, 3e, 3f, 3g, 3h** (command palette, toasts, portfolio PnL, richer alerts, AI backtest, search) — pick and choose by user demand. 2–3 days.
8. **Phase 4c, 4e, 4f** (tests, Redis, observability) — invest before scaling traffic.

Total realistic estimate: **8–12 working days** to hit a credible v1.0 production release. Phase 1 alone is a step-change.

---

## Decisions still owed

Tell me before I start so I don't have to interrupt:

1. **Dark or light as default?** Plan currently keeps dark default (fintech convention). Flip if you want light.
2. **Charting library?** Chart.js (lightweight, MIT) is my default. Alternative: Lightweight Charts by TradingView (better looking, slightly heavier).
3. **Real-time transport?** SSE recommended (simpler, fits Flask). Alternative: Socket.IO (more flexible, more deps).
4. **Production WSGI?** Waitress on Windows, Gunicorn on Linux. Or both via env-detection.
5. **Anything in Phase 3 you want to drop?** "Production-level" doesn't require all of it; trim if you'd rather ship faster.
