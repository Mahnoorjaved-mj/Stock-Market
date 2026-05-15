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
"""

DROP_SQL = """
DROP TABLE IF EXISTS alert_history CASCADE;
DROP TABLE IF EXISTS portfolio CASCADE;
DROP TABLE IF EXISTS watchlist CASCADE;
DROP TABLE IF EXISTS password_reset_tokens CASCADE;
DROP TABLE IF EXISTS otp_verification CASCADE;
DROP TABLE IF EXISTS users CASCADE;
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
