-- Midas Platform — Initial Schema Migration
-- Creates all tables, Postgres roles, and grants.
--
-- CRITICAL: The midas_publisher role has ZERO grants on users.* tables.
-- This is the structural enforcement of the publisher exemption (ADR-001).
-- Boot-time assertion (M06-05) and CI check (M06-06) verify this.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- SCHEMAS
-- ============================================================
-- Market data and signals (accessible by publisher)
-- Default 'public' schema

-- User data (NOT accessible by publisher)
CREATE SCHEMA IF NOT EXISTS users;

-- Token storage (separate role)
CREATE SCHEMA IF NOT EXISTS tokens;

-- ============================================================
-- MARKET DATA TABLES (public schema)
-- ============================================================

CREATE TABLE IF NOT EXISTS bars (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION NOT NULL DEFAULT 0,
    high DOUBLE PRECISION NOT NULL DEFAULT 0,
    low DOUBLE PRECISION NOT NULL DEFAULT 0,
    close DOUBLE PRECISION NOT NULL DEFAULT 0,
    adj_close DOUBLE PRECISION NOT NULL DEFAULT 0,
    volume BIGINT NOT NULL DEFAULT 0,
    source VARCHAR(20) NOT NULL DEFAULT 'eodhd',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TimescaleDB hypertable for efficient time-series queries
-- SELECT create_hypertable('bars', 'date', if_not_exists => TRUE, migrate_data => TRUE);

-- Add unique constraint after hypertable creation
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_bars_unique ON bars (ticker, date, source);
CREATE INDEX IF NOT EXISTS idx_bars_ticker ON bars (ticker);

CREATE TABLE IF NOT EXISTS fundamentals (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    as_of_date DATE NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL DEFAULT 0,
    source VARCHAR(20) NOT NULL DEFAULT 'eodhd',
    UNIQUE(ticker, report_date, as_of_date, field_name)
);

CREATE TABLE IF NOT EXISTS corp_actions (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    ex_date DATE NOT NULL,
    action_type VARCHAR(20) NOT NULL,
    factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    announced_date DATE,
    source VARCHAR(20) NOT NULL DEFAULT 'eodhd'
);
CREATE INDEX IF NOT EXISTS idx_corp_actions_ticker ON corp_actions (ticker);
CREATE INDEX IF NOT EXISTS idx_corp_actions_ex_date ON corp_actions (ex_date);

CREATE TABLE IF NOT EXISTS etf_universe (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL DEFAULT '',
    inception_date DATE NOT NULL,
    delist_date DATE,
    sleeve VARCHAR(50) NOT NULL,
    expense_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_daily_volume BIGINT NOT NULL DEFAULT 0,
    liquidity_tier VARCHAR(10) NOT NULL DEFAULT 'high',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_etf_universe_ticker ON etf_universe (ticker);
CREATE INDEX IF NOT EXISTS idx_etf_universe_sleeve ON etf_universe (sleeve);

-- ============================================================
-- SIGNAL TABLES (public schema — NO user_id)
-- ============================================================

CREATE TABLE IF NOT EXISTS regime_signals (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    signal_name VARCHAR(50) NOT NULL,
    value DOUBLE PRECISION NOT NULL DEFAULT 0,
    ensemble_score DOUBLE PRECISION,
    regime VARCHAR(20),
    source VARCHAR(20) NOT NULL DEFAULT '',
    UNIQUE(date, signal_name)
);
CREATE INDEX IF NOT EXISTS idx_regime_signals_date ON regime_signals (date);

CREATE TABLE IF NOT EXISTS model_portfolios (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    vol_target DOUBLE PRECISION NOT NULL DEFAULT 0,
    style VARCHAR(50) NOT NULL DEFAULT '',
    monthly_price_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    model_portfolio_id VARCHAR(50) NOT NULL REFERENCES model_portfolios(id),
    timestamp TIMESTAMPTZ NOT NULL,
    regime VARCHAR(20) NOT NULL DEFAULT 'normal',
    allocations_json TEXT NOT NULL DEFAULT '{}',
    reasoning_json TEXT NOT NULL DEFAULT '{}',
    cost_estimate_json TEXT NOT NULL DEFAULT '{}',
    ensemble_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    UNIQUE(model_portfolio_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_signals_portfolio ON signals (model_portfolio_id);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (timestamp);

CREATE TABLE IF NOT EXISTS signal_inputs (
    id BIGSERIAL PRIMARY KEY,
    signal_id BIGINT NOT NULL REFERENCES signals(id),
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_signal_inputs_signal ON signal_inputs (signal_id);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id BIGSERIAL PRIMARY KEY,
    model_portfolio_id VARCHAR(50) NOT NULL REFERENCES model_portfolios(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    config_json TEXT NOT NULL DEFAULT '{}',
    results_json TEXT NOT NULL DEFAULT '{}',
    horizons_json TEXT NOT NULL DEFAULT '[]',
    regime_stats_json TEXT NOT NULL DEFAULT '[]',
    benchmarks_json TEXT NOT NULL DEFAULT '[]',
    deflated_sharpe DOUBLE PRECISION,
    pbo DOUBLE PRECISION,
    worst_12m_return DOUBLE PRECISION,
    status VARCHAR(20) NOT NULL DEFAULT 'running'
);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_portfolio ON backtest_runs (model_portfolio_id);

-- ============================================================
-- NEWS TABLE (public schema)
-- ============================================================

CREATE TABLE IF NOT EXISTS news_items (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'perplexity',
    published_at TIMESTAMPTZ NOT NULL,
    title VARCHAR(500) NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL DEFAULT '',
    perplexity_citations_json TEXT NOT NULL DEFAULT '[]',
    query VARCHAR(500) NOT NULL DEFAULT '',
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding vector(1536)
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items (published_at);

-- ============================================================
-- USER TABLES (users schema — NOT accessible by publisher)
-- ============================================================

CREATE TABLE IF NOT EXISTS users.accounts (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    mfa_secret VARCHAR(255),
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS users.preferences (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users.accounts(id),
    model_portfolio_id VARCHAR(50) NOT NULL DEFAULT 'growth' REFERENCES model_portfolios(id),
    notification_settings_json TEXT NOT NULL DEFAULT '{}',
    timeout_hours INTEGER NOT NULL DEFAULT 24,
    paper_trading BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_preferences_user ON users.preferences (user_id);

CREATE TABLE IF NOT EXISTS users.approvals (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users.accounts(id),
    signal_id BIGINT NOT NULL REFERENCES signals(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    decided_at TIMESTAMPTZ,
    method VARCHAR(20),
    trades_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_approvals_user ON users.approvals (user_id);
CREATE INDEX IF NOT EXISTS idx_approvals_signal ON users.approvals (signal_id);

-- ============================================================
-- TOKEN TABLE (tokens schema — separate role)
-- ============================================================

CREATE TABLE IF NOT EXISTS tokens.user_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users.accounts(id),
    access_token_enc BYTEA NOT NULL DEFAULT '',
    refresh_token_enc BYTEA NOT NULL DEFAULT '',
    expires_at TIMESTAMPTZ,
    scopes VARCHAR(255) NOT NULL DEFAULT 'read_positions,preview_order,place_order',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- AUDIT TRAIL (public schema, append-only)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_trail (
    id BIGSERIAL PRIMARY KEY,
    prev_hash VARCHAR(64) NOT NULL DEFAULT '',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    actor VARCHAR(100) NOT NULL DEFAULT 'system',
    hash VARCHAR(64) NOT NULL DEFAULT ''
);
-- SELECT create_hypertable('audit_trail', 'timestamp', if_not_exists => TRUE, migrate_data => TRUE);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_trail (event_type);

-- ============================================================
-- POSTGRES ROLES
-- ============================================================

-- Publisher role: reads market data + signals, writes signals
-- CANNOT access users.* or tokens.*
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'midas_publisher') THEN
        CREATE ROLE midas_publisher;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO midas_publisher;
GRANT SELECT ON bars, fundamentals, corp_actions, etf_universe, regime_signals, model_portfolios, backtest_runs, news_items TO midas_publisher;
GRANT SELECT, INSERT, UPDATE ON signals, signal_inputs, regime_signals TO midas_publisher;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO midas_publisher;

-- Subscriber role: reads signals + user preferences, writes approvals
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'midas_subscriber') THEN
        CREATE ROLE midas_subscriber;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public, users TO midas_subscriber;
GRANT SELECT ON signals, model_portfolios, backtest_runs, news_items, regime_signals, bars TO midas_subscriber;
GRANT SELECT, INSERT, UPDATE ON users.accounts, users.preferences, users.approvals TO midas_subscriber;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public, users TO midas_subscriber;

-- Broker role: reads/writes tokens only
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'midas_broker') THEN
        CREATE ROLE midas_broker;
    END IF;
END $$;

GRANT USAGE ON SCHEMA tokens TO midas_broker;
GRANT SELECT, INSERT, UPDATE, DELETE ON tokens.user_tokens TO midas_broker;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tokens TO midas_broker;

-- Audit role: INSERT + SELECT only, NO UPDATE/DELETE/TRUNCATE
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'midas_audit') THEN
        CREATE ROLE midas_audit;
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO midas_audit;
GRANT SELECT, INSERT ON audit_trail TO midas_audit;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO midas_audit;

-- ============================================================
-- SEED: Default model portfolios
-- ============================================================

INSERT INTO model_portfolios (id, name, description, vol_target, style, monthly_price_usd)
VALUES
    ('aggressive_growth', 'Aggressive Growth', 'Maximum growth with 18% vol target.', 18.0, 'aggressive_growth', 29.0),
    ('growth', 'Growth', 'Strong growth with 14% vol target.', 14.0, 'growth', 29.0),
    ('balanced', 'Balanced', 'Balanced risk-return with 10% vol target.', 10.0, 'balanced', 19.0),
    ('conservative', 'Conservative', 'Capital preservation with 6% vol target.', 6.0, 'conservative', 9.0),
    ('income', 'Income', 'Income-focused with 6% vol target. Dividend ETFs and bonds.', 6.0, 'income', 19.0)
ON CONFLICT (id) DO NOTHING;
