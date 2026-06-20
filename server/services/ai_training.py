"""Background LSTM training bootstrap (runs in a daemon thread on startup).

Ports the legacy background_ai_training thread from app.py. No-op when torch
is unavailable (the predictor runs in stub mode).
"""
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger("stocksense.ai_training")

SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NVDA", "JPM", "V", "JNJ",
    "RELIANCE", "AMD", "INTC", "ADBE", "CRM",
    "PYPL", "NFLX", "DIS", "BA", "WMT",
]
MAX_ATTEMPTS = 3


def _train_loop():
    from services.ai_predictions import TORCH_AVAILABLE, ai_predictor

    if not TORCH_AVAILABLE:
        log.info("AI training skipped — torch not installed (stub mode)")
        return
    log.info("AI training started")
    for symbol in SYMBOLS:
        backoff = 5.0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                success, confidence = ai_predictor.train_lstm_model(symbol, epochs=25)
                if success:
                    log.info("training_ok symbol=%s confidence=%s", symbol, confidence)
                break
            except Exception as e:
                log.warning("training_failed symbol=%s attempt=%s error=%s", symbol, attempt, e)
                if attempt == MAX_ATTEMPTS:
                    log.error("training_giveup symbol=%s", symbol)
                else:
                    time.sleep(backoff)
                    backoff *= 2
        time.sleep(2)
    log.info("AI training completed")


def start_background_training() -> None:
    threading.Thread(target=_train_loop, daemon=True).start()
