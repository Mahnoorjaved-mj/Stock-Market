"""Audit log helper — writes to the audit_events collection.

Best-effort: never raises, so auditing can't crash a request. Ports
legacy `backend/services/audit.py`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request

from config.database import audit_events

log = logging.getLogger("stocksense.audit")


async def log_event(
    action: str,
    user_id: Optional[str] = None,
    request: Optional[Request] = None,
    metadata: Optional[dict] = None,
) -> None:
    ip = None
    user_agent = None
    if request is not None:
        try:
            ip = request.headers.get("x-forwarded-for") or (
                request.client.host if request.client else None
            )
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()
            user_agent = (request.headers.get("user-agent") or "")[:512]
        except Exception:
            pass

    try:
        await audit_events().insert_one(
            {
                "user_id": user_id,
                "action": action,
                "ip": ip,
                "user_agent": user_agent,
                "metadata": metadata,
                "occurred_at": datetime.now(timezone.utc),
            }
        )
    except Exception as e:  # pragma: no cover - best effort
        log.warning("audit log write failed for action=%s: %s", action, e)
