"""Audit log helper. Writes to audit_events table.

Usage:
    from services.audit import log_event
    log_event("login_success", user_id=42, request=request)
"""

import json
import logging
from typing import Any, Optional

from db import get_db_connection

log = logging.getLogger(__name__)


def log_event(
    action: str,
    user_id: Optional[int] = None,
    request: Any = None,
    metadata: Optional[dict] = None,
) -> None:
    """Best-effort write. Never raises — auditing should not crash callers."""
    ip = None
    user_agent = None
    if request is not None:
        try:
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()
            user_agent = request.headers.get("User-Agent", "")[:512]
        except Exception:
            pass

    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO audit_events (user_id, action, ip, user_agent, metadata)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (user_id, action, ip, user_agent, json.dumps(metadata) if metadata else None),
                )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning("audit log write failed for action=%s: %s", action, e)
