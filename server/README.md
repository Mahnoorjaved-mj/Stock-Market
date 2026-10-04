# StockSense Backend API ⚡

> **High-Performance Asynchronous FastAPI Backend, PyTorch LSTM Forecast Engine & MongoDB Service.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-059669?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Motor%203.4-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-LSTM-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)

---

## 🌟 Overview & Architecture

The backend provides high-concurrency, asynchronous REST APIs and Server-Sent Events (SSE) live data streaming for StockSense. Built on **FastAPI** with **Motor (Async MongoDB)**, it handles real-time stock ingestion, financial metrics, JWT/2FA authentication, alert triggers, and deep learning price predictions.

### Key Capabilities
- **Real-Time Data Layer (`services/stock_data.py`)**: Hybrid market ingestion combining Alpha Vantage API with automatic yfinance fallback and in-memory TTL caching.
- **Server-Sent Events (`routes/market.py`)**: Real-time market pulse streaming at `/stream/prices` via `sse-starlette`.
- **LSTM Deep Learning Predictor (`services/ai_predictions.py`)**: PyTorch 3-layer LSTM with attention mechanisms and Monte Carlo Dropout for uncertainty estimation across 17 major equities.
- **Alert Sweeper & Email Digest Engine (`services/alerts_engine.py` & `services/digests.py`)**: Automated background tasks driven by APScheduler for threshold checks and scheduled portfolio digests.
- **Security & RBAC (`utils/security.py`, `utils/deps.py`)**: Secure bcrypt hashing, JWT access tokens, TOTP two-factor authentication, and IP-aware rate limiting (`slowapi`).

---

## 📁 Backend Directory Layout

```text
server/
├── ai_models/              # 17 pre-trained LSTM weights (.pth), scalers (.pkl)
├── controllers/            # Business logic handlers (auth, market, portfolio, AI)
├── routes/                 # FastAPI REST and SSE endpoints
├── services/               # Market data engine, LSTM predictions, alert scheduler
├── models/                 # Pydantic schemas & data validation models
└── email_templates/        # Responsive Jinja2 email templates
```

---

## ⚙️ Environment Variables

Create a `server/.env` file based on `server/.env.example`:

```env
# MongoDB Atlas or Local URI
MONGO_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=stocksense

# Security
JWT_SECRET=super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=4

# Server Configuration
APP_NAME=StockSense
DEBUG=True
APP_BASE_URL=http://127.0.0.1:8000
FRONTEND_ORIGIN=http://localhost:5173,http://127.0.0.1:5173

# Optional: Email / SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_NAME=StockSense Alerts

# Optional: Market Data & Cache
ALPHA_VANTAGE_KEY=
REDIS_URL=
SENTRY_DSN=
```

---

## 🚀 Running Locally

```bash
# 1. Activate your virtual environment
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python main.py
```

* API Gateway: **`http://127.0.0.1:8000`**
* Swagger Documentation: **`http://127.0.0.1:8000/docs`**
* ReDoc Documentation: **`http://127.0.0.1:8000/redoc`**
* Healthcheck: **`http://127.0.0.1:8000/api/health`**

---

## 🧪 Testing

Run the automated test suite with pytest:

```bash
python -m pytest tests/e2e_smoke.py -v
```
