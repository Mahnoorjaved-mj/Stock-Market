import psycopg2
import psycopg2.extras

from config import config


def get_db_connection():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def get_dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    alert_threshold_pct NUMERIC NOT NULL DEFAULT 5,
    digest_frequency TEXT NOT NULL DEFAULT 'weekly',
    digest_day SMALLINT NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS otp_verification (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    otp TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_otp_email ON otp_verification(email);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pwreset_token ON password_reset_tokens(token);

CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    threshold_pct NUMERIC,
    target_price_high NUMERIC,
    target_price_low NUMERIC,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, symbol)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);

CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    buy_price NUMERIC NOT NULL,
    buy_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio(user_id);

CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    price NUMERIC NOT NULL,
    change_pct NUMERIC,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerthist_user_sym_time
    ON alert_history(user_id, symbol, sent_at DESC);

-- ===== Phase 4a security additions =====

-- Audit log of important auth/alert events for traceability.
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    ip TEXT,
    user_agent TEXT,
    metadata JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_events(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action_time ON audit_events(action, occurred_at DESC);

-- Opt-in TOTP-based 2FA.
CREATE TABLE IF NOT EXISTS user_2fa_secrets (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    secret TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Push subscriptions for browser notifications (Phase 3d).
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT UNIQUE NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);

-- In-app notification center entries.
CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT,
    kind TEXT NOT NULL DEFAULT 'info',
    href TEXT,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, created_at DESC);

-- Alerts engine v2: rule-based with multiple condition types (Phase 3f).
CREATE TABLE IF NOT EXISTS alert_rules (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    condition_type TEXT NOT NULL,         -- price_above | price_below | pct_change | volume_spike | ma_cross
    threshold NUMERIC NOT NULL,
    comparator TEXT NOT NULL DEFAULT 'gte', -- gte | lte | eq
    state TEXT NOT NULL DEFAULT 'active', -- active | paused | archived
    snoozed_until TIMESTAMPTZ,
    last_fired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alertrules_user ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alertrules_state ON alert_rules(state) WHERE state='active';

-- Portfolio PnL fields (Phase 3e). Added via ALTERs for forward-compat.
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS country TEXT;

-- OTP attempt tracking for resend rate-limit (Phase 4a OTP hardening).
ALTER TABLE otp_verification ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0;
ALTER TABLE otp_verification ADD COLUMN IF NOT EXISTS last_attempt_at TIMESTAMPTZ;

-- Admin flag for /admin/metrics access (Phase 4f).
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarded_at TIMESTAMPTZ;

-- updated_at columns + auto-update trigger (Phase 4e).
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION ss_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated ON users;
CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION ss_set_updated_at();
DROP TRIGGER IF EXISTS trg_watchlist_updated ON watchlist;
CREATE TRIGGER trg_watchlist_updated BEFORE UPDATE ON watchlist
    FOR EACH ROW EXECUTE FUNCTION ss_set_updated_at();
DROP TRIGGER IF EXISTS trg_portfolio_updated ON portfolio;
CREATE TRIGGER trg_portfolio_updated BEFORE UPDATE ON portfolio
    FOR EACH ROW EXECUTE FUNCTION ss_set_updated_at();
"""

DROP_SQL = """
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS push_subscriptions CASCADE;
DROP TABLE IF EXISTS user_2fa_secrets CASCADE;
DROP TABLE IF EXISTS audit_events CASCADE;
DROP TABLE IF EXISTS alert_rules CASCADE;
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS portfolio CASCADE;
DROP TABLE IF EXISTS watchlist CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS otp_verification CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP FUNCTION IF EXISTS ss_set_updated_at() CASCADE;
"""


def init_schema():
    """Create all tables. If DROP_AND_REBUILD_SCHEMA is true, drop first."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if config.DROP_AND_REBUILD_SCHEMA:
                print("⚠️  DROP_AND_REBUILD_SCHEMA is enabled - dropping all tables")
                cur.execute(DROP_SQL)
            cur.execute(SCHEMA_SQL)
        conn.commit()
        print("✅ Database schema ready")
    finally:
        conn.close()
