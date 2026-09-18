"""Background LSTM training service for StockSense.

Startup training is disabled by default so the dashboard can load immediately.
Training can still be triggered manually in the background.

Set ENABLE_AI_STARTUP_TRAINING=true in .env only if automatic startup training
is explicitly desired.
"""
from __future__ import annotations

import logging
import os
import threading
import time

log = logging.getLogger("stocksense.ai_training")

SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NVDA", "JPM", "V", "JNJ",
    "RELIANCE", "AMD", "INTC", "ADBE", "CRM",
    "PYPL", "NFLX", "DIS", "BA", "WMT",
]

ENABLE_STARTUP_TRAINING = (
    os.getenv("ENABLE_AI_STARTUP_TRAINING", "false").strip().lower() == "true"
)

DEFAULT_EPOCHS = 10
MAX_ATTEMPTS = 1
DELAY_BETWEEN_MODELS = 0.5


def _train_loop() -> None:
    """Train configured LSTM models in a daemon background thread."""
    try:
        from services.ai_predictions import TORCH_AVAILABLE, ai_predictor
    except Exception as e:
        log.warning("Could not load AI predictor: %s", e)
        return

    if not TORCH_AVAILABLE:
        log.info("AI training skipped — torch not installed (stub mode)")
        return

    log.info("Background AI training started")

    for symbol in SYMBOLS:
        try:
            log.info("Training LSTM model for %s...", symbol)
            success, confidence = ai_predictor.train_lstm_model(
                symbol, epochs=DEFAULT_EPOCHS
            )
            if success:
                log.info("training_ok symbol=%s confidence=%s", symbol, confidence)
            else:
                log.warning("training_failed symbol=%s", symbol)
        except Exception as e:
            log.warning("training_failed symbol=%s error=%s", symbol, e)
        time.sleep(DELAY_BETWEEN_MODELS)

    log.info("Background AI training completed")


def start_background_training() -> None:
    """Start automatic training only when explicitly enabled."""
    if not ENABLE_STARTUP_TRAINING:
        log.info("AI startup training disabled — dashboard will load immediately")
        return

    thread = threading.Thread(
        target=_train_loop,
        name="stocksense-ai-training",
        daemon=True,
    )
    thread.start()
    log.info("AI training started in background")


def train_symbol_background(symbol: str, epochs: int = DEFAULT_EPOCHS) -> None:
    """Train one stock model in a daemon thread without blocking the API."""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        log.warning("Cannot train an empty symbol")
        return

    def _worker() -> None:
        try:
            from services.ai_predictions import TORCH_AVAILABLE, ai_predictor
            if not TORCH_AVAILABLE:
                log.info("AI training skipped — torch not installed")
                return

            log.info("Manual LSTM training started symbol=%s", symbol)
            success, confidence = ai_predictor.train_lstm_model(
                symbol, epochs=max(1, int(epochs))
            )
            if success:
                log.info("manual_training_ok symbol=%s confidence=%s", symbol, confidence)
            else:
                log.warning("manual_training_failed symbol=%s", symbol)
        except Exception as e:
            log.exception("Manual training error symbol=%s error=%s", symbol, e)

    threading.Thread(
        target=_worker,
        name=f"stocksense-ai-{symbol}",
        daemon=True,
    ).start()
