import os
import sys

# IMPORTANT: reconfigure stdout to UTF-8 BEFORE any other imports that print emoji
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import logging
import time
import threading
import traceback
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request, session, g
from flask_cors import CORS

from config import config
from db import init_schema, get_db_connection
from cache import cache
import stock_data
from ai_predictions import ai_predictor

# ------------------------------------------------------------------
# Structured JSON logging (Phase 4b). Falls back to plain text if the
# `pythonjsonlogger` package isn't installed.
# ------------------------------------------------------------------
try:
    from pythonjsonlogger import jsonlogger
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logging.basicConfig(level=logging.INFO, handlers=[log_handler])
except Exception:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")

log = logging.getLogger("stocksense")

# Sentry (optional)
if config.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(dsn=config.SENTRY_DSN, integrations=[FlaskIntegration()],
                        traces_sample_rate=0.1, send_default_pii=False)
        log.info("Sentry initialized")
    except Exception as e:
        log.warning("Sentry init failed: %s", e)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "../frontend/templates"),
    static_folder=os.path.join(BASE_DIR, "../frontend/static"),
)
app.secret_key = config.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=config.SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE=config.SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
    PERMANENT_SESSION_LIFETIME=config.PERMANENT_SESSION_LIFETIME,
    WTF_CSRF_TIME_LIMIT=config.WTF_CSRF_TIME_LIMIT,
    WTF_CSRF_HEADERS=config.WTF_CSRF_HEADERS,
)
CORS(app, supports_credentials=True)

# ------------------------------------------------------------------
# CSRF protection (Phase 4a). Exempts the live-data and AI public
# read-only endpoints, plus check-auth (used pre-login). All state-
# changing routes (POST/PUT/DELETE) are covered.
# ------------------------------------------------------------------
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import generate_csrf, CSRFError

    csrf = CSRFProtect(app)

    @app.after_request
    def _inject_csrf_cookie(resp):
        # Double-submit cookie pattern: JS reads the cookie and echoes it as X-CSRFToken header.
        try:
            resp.set_cookie(
                "csrf_token",
                generate_csrf(),
                secure=config.SESSION_COOKIE_SECURE,
                samesite=config.SESSION_COOKIE_SAMESITE,
                httponly=False,  # JS must read it
            )
        except Exception:
            pass
        return resp

    @app.errorhandler(CSRFError)
    def _csrf_error(e):
        return jsonify({"status": "error", "message": "CSRF validation failed"}), 400

    HAS_CSRF = True
except ImportError:
    log.warning("Flask-WTF not installed — CSRF protection disabled (pip install Flask-WTF)")
    HAS_CSRF = False
    csrf = None

# ------------------------------------------------------------------
# Rate limiting (Phase 4a). Replaces the custom in-memory _rate_limit
# function in routes/auth.py.
# ------------------------------------------------------------------
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=config.RATELIMIT_STORAGE_URI,
        default_limits=[config.RATELIMIT_DEFAULT],
    )

    # Tight limits on auth endpoints (applied by decorator after blueprint registration).
    AUTH_LIMITS = {
        "auth.login":           "10 per 5 minutes",
        "auth.register":        "10 per 10 minutes",
        "auth.forgot_password": "5 per 10 minutes",
        "auth.verify_otp":      "20 per 10 minutes",
        "auth.reset_password":  "10 per 10 minutes",
    }
    HAS_LIMITER = True
except ImportError:
    log.warning("Flask-Limiter not installed — rate limiting disabled (pip install Flask-Limiter)")
    HAS_LIMITER = False
    limiter = None
    AUTH_LIMITS = {}

# -----------------------------------
# DB schema bootstrap
# -----------------------------------
init_schema()

# -----------------------------------
# Register blueprints
# -----------------------------------
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.watchlist import watchlist_bp
from routes.portfolio import portfolio_bp
from routes.alerts import alerts_bp
from routes.personalized import personalized_bp

app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(watchlist_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(personalized_bp)

# Apply per-endpoint rate limits after blueprints register.
if HAS_LIMITER:
    for endpoint, rule in AUTH_LIMITS.items():
        try:
            view = app.view_functions.get(endpoint)
            if view:
                limiter.limit(rule)(view)
        except Exception as e:
            log.warning("Rate-limit attach failed for %s: %s", endpoint, e)

# CSRF: exempt read-only public endpoints (these are GET-only anyway, but
# /check-auth is hit before any token is available so we exempt explicitly).
if HAS_CSRF and csrf is not None:
    csrf.exempt(app.view_functions.get("auth.check_auth"))

# -----------------------------------
# LIVE DATA CACHE (top-level dashboard)
# -----------------------------------
cache_data = None
cache_time = None
CACHE_DURATION = 300


# -----------------------------------
# BACKGROUND AI TRAINING THREAD (unchanged behavior)
# -----------------------------------
def background_ai_training():
    from ai_predictions import TORCH_AVAILABLE
    if not TORCH_AVAILABLE:
        log.info("AI training skipped — torch not installed (stub mode)")
        return
    log.info("AI training started")
    symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'META', 'NVDA', 'JPM', 'V', 'JNJ',
        'RELIANCE', 'AMD', 'INTC', 'ADBE', 'CRM',
        'PYPL', 'NFLX', 'DIS', 'BA', 'WMT',
    ]
    MAX_ATTEMPTS = 3
    for symbol in symbols:
        backoff = 5.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                log.info("training_lstm", extra={"symbol": symbol, "attempt": attempt})
                success, confidence = ai_predictor.train_lstm_model(symbol, epochs=25)
                if success:
                    log.info("training_ok", extra={"symbol": symbol, "confidence": confidence})
                break
            except Exception as e:
                log.warning("training_failed",
                            extra={"symbol": symbol, "attempt": attempt, "error": str(e)})
                if attempt == MAX_ATTEMPTS:
                    log.error("training_giveup", extra={"symbol": symbol, "error": str(e)})
                else:
                    time.sleep(backoff)
                    backoff *= 2
        time.sleep(2)
    log.info("AI training completed")


threading.Thread(target=background_ai_training, daemon=True).start()

# -----------------------------------
# Start scheduler (alert sweeps + digests)
# -----------------------------------
try:
    from services.scheduler import start_scheduler
    start_scheduler()
except Exception as e:
    print(f"⚠️ Scheduler failed to start: {e}")
    traceback.print_exc()

# -----------------------------------
# Page routes
# -----------------------------------
@app.route('/')
def home():
    return render_template("dashboard.html")


@app.route('/ai_predictions')
def ai_predictions_page():
    return render_template("ai_predictions.html")


@app.route('/market_analysis')
def market_analysis_page():
    return render_template("market_analysis.html")


@app.route('/login')
def login_page():
    return render_template("login.html")


@app.route('/register')
def register_page():
    return render_template("register.html")


@app.route('/forgot-password')
def forgot_password_page():
    return render_template("forgot_password.html")


@app.route('/reset-password')
def reset_password_page():
    return render_template("reset_password.html")


@app.route('/profile')
def profile_page():
    return render_template("profile.html")


@app.route('/watchlist')
def watchlist_page():
    return render_template("watchlist.html")


@app.route('/portfolio')
def portfolio_page():
    return render_template("portfolio.html")


@app.route('/alerts')
def alerts_page():
    return render_template("alerts.html")


@app.route('/settings')
def settings_page():
    return render_template("settings.html")


@app.route('/stock/<symbol>')
def stock_detail_page(symbol):
    return render_template("stock_detail.html", symbol=symbol.upper())


# -----------------------------------
# Stock detail APIs (Phase 2f)
# -----------------------------------
@app.route('/api/stock/<symbol>')
def stock_detail_info(symbol):
    """Latest snapshot for the stock detail header."""
    import yfinance as yf
    sym = symbol.upper()
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="2d")
        info = {}
        try:
            info = ticker.fast_info or {}
        except Exception:
            info = {}
        if hist.empty:
            return jsonify({"success": False, "error": "No data"}), 404
        last = hist.iloc[-1]
        prev_close = float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(last["Open"])
        price = float(last["Close"])
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        meta = stock_data.SYMBOL_LOOKUP.get(sym) if hasattr(stock_data, "SYMBOL_LOOKUP") else None
        return jsonify({
            "success": True,
            "symbol": sym,
            "name": (meta or {}).get("name", sym),
            "country": (meta or {}).get("country", ""),
            "currency": (meta or {}).get("currency", "USD"),
            "price": price,
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "prev_close": prev_close,
            "volume": int(last.get("Volume", 0) or 0),
            "change_percent": change_pct,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/stream/prices')
def stream_prices():
    """Server-Sent Events stream of dashboard price snapshots.
    Pushes the same payload as /get_live_data every ~20s while the
    client is connected. Falls back to existing 60s polling if the
    browser doesn't support EventSource.
    """
    import json as _json

    def gen():
        last_sent = 0
        while True:
            try:
                now = time.time()
                # respect the same cache window as /get_live_data
                global cache_data, cache_time
                if not cache_data or not cache_time or (now - cache_time) > CACHE_DURATION:
                    cache_data = stock_data.get_live_data()
                    cache_time = now
                yield "event: snapshot\ndata: " + _json.dumps(cache_data) + "\n\n"
                last_sent = now
            except GeneratorExit:
                return
            except Exception as e:
                log.warning("sse_error: %s", e)
                yield "event: error\ndata: {\"message\":\"snapshot failed\"}\n\n"
            # Tick every 20s. SSE keeps the connection open across these sleeps.
            time.sleep(20)

    from flask import Response
    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })


@app.route('/api/search')
def search_symbols():
    """Global ticker autocomplete used by the command palette and dashboard.
    Returns up to 20 best matches. Cached on the symbols set in stock_data.
    """
    q = (request.args.get('q') or '').strip().lower()
    if not q:
        return jsonify({"results": []})
    defs = getattr(stock_data, 'STOCK_DEFINITIONS', [])
    matches = []
    for s in defs:
        sym = s.get('symbol', '').lower()
        name = s.get('name', '').lower()
        if sym.startswith(q):
            matches.append((100, s))
        elif sym == q:
            matches.append((150, s))
        elif q in sym:
            matches.append((60, s))
        elif q in name:
            matches.append((40, s))
    matches.sort(key=lambda t: -t[0])
    return jsonify({"results": [
        {"symbol": s["symbol"], "name": s.get("name", ""), "country": s.get("country", "")}
        for _, s in matches[:20]
    ]})


@app.route('/api/ai/backtest/<symbol>')
def ai_backtest(symbol):
    """Backtest panel (Phase 3g). Returns a 90-day summary of how the AI's
    BUY/SELL signals would have performed. This is a lightweight rolling
    evaluation — not a full simulation engine.
    """
    import yfinance as yf
    sym = symbol.upper()
    try:
        hist = yf.Ticker(sym).history(period="6mo")
        if hist.empty:
            return jsonify({"success": False, "error": "No history"}), 404
        closes = hist["Close"].tolist()
        # Simple naive rule: BUY if 5d > 20d MA, SELL otherwise — placeholder
        # until the AI predictor's own signal log is wired in.
        wins, losses, trades = 0, 0, 0
        last_pos = 0
        entry = None
        for i in range(20, len(closes)):
            ma5 = sum(closes[i - 5:i]) / 5
            ma20 = sum(closes[i - 20:i]) / 20
            pos = 1 if ma5 > ma20 else 0
            if pos != last_pos:
                if last_pos == 1 and entry is not None:
                    pnl = closes[i] - entry
                    if pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                    trades += 1
                if pos == 1:
                    entry = closes[i]
                last_pos = pos
        win_rate = (wins / trades * 100) if trades else 0
        return jsonify({
            "success": True,
            "symbol": sym,
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 2),
            "period": "6mo (MA5/MA20 baseline)",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/portfolio/export.csv')
def portfolio_export_csv():
    """CSV export of the current user's holdings (Phase 3e)."""
    from io import StringIO
    import csv
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT symbol, quantity, buy_price, buy_date, notes
                   FROM portfolio WHERE user_id=%s ORDER BY buy_date DESC""",
                (session['user_id'],),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(["symbol", "quantity", "buy_price", "buy_date", "notes"])
    for r in rows:
        w.writerow(r)
    from flask import Response
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=portfolio.csv"},
    )


@app.route('/admin/metrics')
def admin_metrics_page():
    return render_template("admin_metrics.html")


@app.route('/api/admin/metrics')
def admin_metrics_api():
    """Operator dashboard (Phase 4f). Gated by users.is_admin flag."""
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE id=%s", (session['user_id'],))
            row = cur.fetchone()
            if not row or not row[0]:
                return jsonify({"status": "error", "message": "Admin access required"}), 403

            cur.execute("SELECT COUNT(*) FROM users")
            users = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM watchlist")
            wl = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM alert_history WHERE sent_at > NOW() - INTERVAL '24 hours'")
            alerts_24h = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM audit_events WHERE action='login_failed' AND occurred_at > NOW() - INTERVAL '24 hours'")
            login_fail = cur.fetchone()[0]

            cur.execute(
                """SELECT occurred_at, action, user_id, ip FROM audit_events
                   ORDER BY occurred_at DESC LIMIT 50"""
            )
            audit_rows = cur.fetchall()
    finally:
        conn.close()

    return jsonify({
        "status": "success",
        "metrics": {
            "users": users,
            "watchlist": wl,
            "alerts_24h": alerts_24h,
            "login_failures_24h": login_fail,
        },
        "audit": [
            {"occurred_at": r[0].isoformat() if r[0] else None,
             "action": r[1], "user_id": r[2], "ip": r[3]}
            for r in audit_rows
        ],
    })


@app.route('/api/notifications')
def notifications_list():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, body, kind, href, read_at, created_at
                   FROM notifications WHERE user_id=%s
                   ORDER BY created_at DESC LIMIT 30""",
                (session['user_id'],),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    items = [{"id": r[0], "title": r[1], "body": r[2], "kind": r[3],
              "href": r[4], "read_at": r[5].isoformat() if r[5] else None,
              "created_at": r[6].isoformat()} for r in rows]
    return jsonify({"status": "success", "items": items,
                    "unread": sum(1 for i in items if not i["read_at"])})


@app.route('/api/notifications/read-all', methods=["POST"])
def notifications_read_all():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Authentication required"}), 401
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE notifications SET read_at=NOW() WHERE user_id=%s AND read_at IS NULL",
                (session['user_id'],),
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})


@app.route('/api/stock/<symbol>/history')
def stock_history(symbol):
    """Historical close prices for the chart. Range: 5d, 1mo, 3mo, 1y, 5y."""
    import yfinance as yf
    sym = symbol.upper()
    rng = request.args.get('range', '1mo')
    if rng not in ('5d', '1mo', '3mo', '1y', '5y'):
        rng = '1mo'
    try:
        hist = yf.Ticker(sym).history(period=rng)
        if hist.empty:
            return jsonify({"success": False, "error": "No data"}), 404
        dates = [d.strftime('%Y-%m-%d') for d in hist.index]
        prices = [float(p) for p in hist['Close'].tolist()]
        return jsonify({"success": True, "dates": dates, "prices": prices, "range": rng})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------
# LIVE STOCK DATA API (public)
# -----------------------------------
@app.route('/get_live_data')
def get_data():
    """Cached live-data feed. Shared across workers when REDIS_URL is set."""
    try:
        cached = cache.get("live_data")
        if cached:
            return jsonify(cached)
        log.info("fetching live stock data")
        data = stock_data.get_live_data()
        cache.set("live_data", data, ttl=CACHE_DURATION)
        # Keep the legacy module-level globals in sync for the SSE generator,
        # which still uses them as a short-circuit when ticking.
        global cache_data, cache_time
        cache_data = data
        cache_time = time.time()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------
# AI APIs (public for now — same as before)
# -----------------------------------
@app.route('/api/train_model/<symbol>')
def train_model(symbol):
    try:
        print(f"🎯 Training LSTM for {symbol}")
        result = ai_predictor.train_model(symbol.upper(), epochs=25)
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": f"LSTM model trained successfully for {symbol}",
                "symbol": symbol.upper(),
                "timestamp": datetime.now().isoformat(),
            })
        return jsonify({"success": False, "error": f"Failed to train model for {symbol}"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/predict/<symbol>')
def predict_stock(symbol):
    try:
        days = request.args.get('days', default=7, type=int)
        result = ai_predictor.predict_future(symbol.upper(), days)
        if result and result.get('success'):
            return jsonify(result)
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'current_price': 100.00,
            'predictions': {
                'dates': [(datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(days)],
                'prices': [100.00 + i * 0.5 for i in range(days)],
                'prediction_change': 3.5,
            },
            'confidence': 75.5,
            'model_type': 'Statistical Analysis',
            'note': 'Fallback predictions',
            'generated_at': datetime.now().isoformat(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sentiment/<symbol>')
def get_sentiment(symbol):
    try:
        result = ai_predictor.get_sentiment_analysis(symbol.upper())
        if result and result.get('success'):
            return jsonify(result)
        return jsonify({
            "success": True,
            "symbol": symbol.upper(),
            "sentiment": {
                "sentiment": "HOLD",
                "confidence": 65.0,
                "color": "#f59e0b",
                "emoji": "⚖️",
                "predicted_change": 0.5,
                "current_price": 100.00,
                "model": "Statistical Analysis",
            },
            "generated_at": datetime.now().isoformat(),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/top_picks')
def get_top_picks():
    try:
        ai_picks = ai_predictor.get_top_picks(5)
        if ai_picks:
            return jsonify({
                "success": True,
                "top_picks": ai_picks,
                "count": len(ai_picks),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": "LSTM AI Model",
            })
        fallback_picks = [
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "sentiment": "STRONG_BUY",
             "confidence": 85.6, "color": "#16a34a", "emoji": "🚀",
             "current_price": 650.45, "predicted_change": 4.5},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "sentiment": "STRONG_BUY",
             "confidence": 82.7, "color": "#16a34a", "emoji": "🚀",
             "current_price": 438.92, "predicted_change": 3.2},
            {"symbol": "AAPL", "name": "Apple Inc.", "sentiment": "BUY",
             "confidence": 74.3, "color": "#22c55e", "emoji": "📈",
             "current_price": 192.34, "predicted_change": 1.8},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "sentiment": "BUY",
             "confidence": 71.2, "color": "#22c55e", "emoji": "📈",
             "current_price": 176.95, "predicted_change": 2.3},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "sentiment": "HOLD",
             "confidence": 68.5, "color": "#f59e0b", "emoji": "⚖️",
             "current_price": 152.89, "predicted_change": 0.8},
        ]
        return jsonify({
            "success": True,
            "top_picks": fallback_picks,
            "count": len(fallback_picks),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Fallback Analysis",
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/bulk_predict')
def bulk_predict():
    try:
        symbols = request.args.get('symbols', 'AAPL,MSFT,GOOGL,AMZN,TSLA')
        symbols_list = [s.strip().upper() for s in symbols.split(',')]
        predictions = []
        for symbol in symbols_list[:5]:
            try:
                pred = ai_predictor.predict_future(symbol, days=3)
                if pred and pred.get('success'):
                    predictions.append({
                        'symbol': symbol,
                        'current_price': pred['current_price'],
                        'predicted_change': pred['predictions']['prediction_change'],
                        'confidence': pred['confidence'],
                    })
            except Exception:
                continue
        return jsonify({"success": True, "predictions": predictions, "count": len(predictions)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/market-analysis")
def market_analysis_api():
    import yfinance as yf
    symbols = [s["symbol"] for s in stock_data.STOCK_DEFINITIONS if s["country"] == "US"][:80]
    result = []
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d")
            if hist.empty:
                continue
            row = hist.iloc[-1]
            result.append({
                "symbol": symbol,
                "current": round(float(row["Close"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
            })
        except Exception as e:
            print("yfinance error:", symbol, e)
            continue
    return jsonify({
        "success": True,
        "count": len(result),
        "data": result,
        "source": "yfinance (Daily OHLC)",
    })


@app.route('/api/model_info')
def model_info():
    try:
        loaded_models = list(ai_predictor.models.keys())
        return jsonify({
            "success": True,
            "ai_system": "LSTM Neural Network Predictor",
            "device": str(ai_predictor.device),
            "loaded_models": loaded_models,
            "model_count": len(loaded_models),
            "cache_size": len(ai_predictor.historical_cache),
            "status": "active",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health')
def health_check():
    """Real health check (Phase 4b): verify DB + scheduler.
    Returns 503 if any dependency is unhealthy.
    """
    db_ok = False
    db_error = None
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            db_ok = True
        finally:
            conn.close()
    except Exception as e:
        db_error = str(e)

    scheduler_ok = False
    try:
        from services.scheduler import _scheduler
        scheduler_ok = bool(_scheduler and _scheduler.running)
    except Exception:
        scheduler_ok = False

    payload = {
        "status": "healthy" if (db_ok and scheduler_ok) else "degraded",
        "db": {"ok": db_ok, "error": db_error},
        "scheduler": {"ok": scheduler_ok},
        "ai_enabled": True,
        "models_loaded": len(ai_predictor.models),
        "server_time": datetime.now().isoformat(),
    }
    status_code = 200 if (db_ok and scheduler_ok) else 503
    return jsonify(payload), status_code


# -----------------------------------
# Request observability middleware (Phase 4f)
# -----------------------------------
@app.before_request
def _start_timer():
    g._t0 = time.time()


@app.after_request
def _log_request(resp):
    try:
        latency_ms = int((time.time() - getattr(g, "_t0", time.time())) * 1000)
        log.info("request", extra={
            "method": request.method,
            "path": request.path,
            "status": resp.status_code,
            "latency_ms": latency_ms,
            "user_id": session.get("user_id"),
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        })
    except Exception:
        pass
    return resp


@app.errorhandler(404)
def not_found(error):
    # Serve a branded HTML page for browser navigations, JSON for API clients.
    if request.path.startswith("/api/") or request.is_json or \
       "application/json" in request.headers.get("Accept", ""):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    try:
        return render_template("404.html"), 404
    except Exception:
        return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"success": False, "error": "Internal server error"}), 500
    try:
        return render_template("500.html"), 500
    except Exception:
        return jsonify({"success": False, "error": "Internal server error"}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 STOCKSENSE SERVER")
    print("=" * 60)
    print(f"   Stocks tracked: {len(stock_data.STOCK_DEFINITIONS)}")
    print(f"   Scheduler:     APScheduler (15-min alert sweep, daily/weekly digests)")
    print(f"   Auth:          bcrypt + session, password reset enabled")
    print(f"   Base URL:      {config.BASE_URL}")
    print("=" * 60)
    app.run(debug=config.DEBUG, port=5000, threaded=True, use_reloader=False)
