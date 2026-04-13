-- Migration 0002: Add debate conversation history table
--
-- Debate messages were stored in users.approvals with status='debate'
-- which was a hack. This gives them a proper table.

CREATE TABLE IF NOT EXISTS users.debate_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users.accounts(id),
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'user' or 'assistant'
    content TEXT NOT NULL DEFAULT '',
    citations_json TEXT NOT NULL DEFAULT '[]',
    suggested_followups_json TEXT NOT NULL DEFAULT '[]',
    ungrounded_claims_json TEXT NOT NULL DEFAULT '[]',
    model_portfolio_id VARCHAR(50) DEFAULT 'growth',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_debate_user ON users.debate_messages (user_id);
CREATE INDEX IF NOT EXISTS idx_debate_created ON users.debate_messages (created_at);

-- Grant to subscriber role (debate is a user-facing feature)
GRANT SELECT, INSERT ON users.debate_messages TO midas_subscriber;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA users TO midas_subscriber;
