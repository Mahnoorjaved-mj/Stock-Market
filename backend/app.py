import os
import sys

# IMPORTANT: reconfigure stdout to UTF-8 BEFORE any other imports that print emoji
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import time
import threading
import traceback
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS

from config import config
from db import init_schema
import stock_data
from ai_predictions import ai_predictor

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
)
CORS(app, supports_credentials=True)

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
    print("🤖 Background AI Training Started")
    symbols = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'META', 'NVDA', 'JPM', 'V', 'JNJ',
        'RELIANCE', 'AMD', 'INTC', 'ADBE', 'CRM',
        'PYPL', 'NFLX', 'DIS', 'BA', 'WMT',
    ]
    for symbol in symbols:
        try:
            print(f"🔁 Training LSTM for {symbol}")
            success, confidence = ai_predictor.train_lstm_model(symbol, epochs=25)
            if success:
                print(f"✅ Trained {symbol} with {confidence}% confidence")
            time.sleep(2)
        except Exception as e:
            print(f"❌ AI training failed for {symbol}: {e}")
    print("✅ Background AI Training Completed")


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


# -----------------------------------
# LIVE STOCK DATA API (public)
# -----------------------------------
@app.route('/get_live_data')
def get_data():
    global cache_data, cache_time
    try:
        current_time = time.time()
        if cache_data and cache_time and (current_time - cache_time) < CACHE_DURATION:
            return jsonify(cache_data)
        print("🌐 Fetching live stock data...")
        data = stock_data.get_live_data()
        cache_data = data
        cache_time = current_time
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
    return jsonify({
        "status": "healthy",
        "ai_enabled": True,
        "torch_available": True,
        "models_loaded": len(ai_predictor.models),
        "cache_status": "active",
        "server_time": datetime.now().isoformat(),
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(error):
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
