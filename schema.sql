-- NexAudit Database Schema
-- PostgreSQL 15+

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- Users & Authentication
-- ========================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150),
    plan            VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);

-- ========================================
-- Audit Reports
-- ========================================
CREATE TABLE audit_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    score           INTEGER CHECK (score >= 0 AND score <= 100),
    -- Scraped data stored as JSONB for flexibility
    scraped_data    JSONB NOT NULL DEFAULT '{}',
    -- Technical issues array
    issues          JSONB NOT NULL DEFAULT '[]',
    -- Page metadata snapshots
    title           TEXT,
    meta_description TEXT,
    h1              TEXT,
    canonical       TEXT,
    images_total    INTEGER DEFAULT 0,
    images_missing_alt INTEGER DEFAULT 0,
    has_schema      BOOLEAN DEFAULT FALSE,
    -- Timing
    audit_duration_ms INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_reports_user ON audit_reports(user_id);
CREATE INDEX idx_audit_reports_url ON audit_reports(url);
CREATE INDEX idx_audit_reports_created ON audit_reports(created_at DESC);
CREATE INDEX idx_audit_reports_score ON audit_reports(score);

-- ========================================
-- AI-Generated Content
-- ========================================
CREATE TABLE ai_content (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_report_id         UUID REFERENCES audit_reports(id) ON DELETE CASCADE,
    user_id                 UUID REFERENCES users(id) ON DELETE CASCADE,
    optimized_title         TEXT,
    optimized_description   TEXT,
    -- Conversion steps as JSONB array
    conversion_steps        JSONB DEFAULT '[]',
    commercial_description  TEXT,
    -- AI model info for reproducibility
    model_used              VARCHAR(50) DEFAULT 'gpt-4o',
    tokens_used             INTEGER,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_content_audit ON ai_content(audit_report_id);
CREATE INDEX idx_ai_content_user ON ai_content(user_id);

-- ========================================
-- Search History
-- ========================================
CREATE TABLE search_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    query_type      VARCHAR(30) NOT NULL CHECK (query_type IN (
        'audit', 'keyword', 'domain', 'backlink', 'content', 'ppc', 'social'
    )),
    query_value     TEXT NOT NULL,
    results_count   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_type ON search_history(query_type);
CREATE INDEX idx_search_history_created ON search_history(created_at DESC);

-- ========================================
-- Keyword Research Results
-- ========================================
CREATE TABLE keyword_research (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    seed_keyword    VARCHAR(255) NOT NULL,
    -- Array of keyword results
    keywords        JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_keyword_research_user ON keyword_research(user_id);
CREATE INDEX idx_keyword_research_seed ON keyword_research(seed_keyword);

-- ========================================
-- Competitor Tracking
-- ========================================
CREATE TABLE competitor_domains (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    domain          VARCHAR(255) NOT NULL,
    display_name    VARCHAR(150),
    is_primary      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, domain)
);

-- ========================================
-- Position Tracking (time-series data)
-- ========================================
CREATE TABLE position_snapshots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    keyword         VARCHAR(255) NOT NULL,
    search_engine   VARCHAR(20) DEFAULT 'google',
    position        INTEGER CHECK (position > 0),
    url             TEXT,
    captured_at     DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX idx_position_user_keyword ON position_snapshots(user_id, keyword);
CREATE INDEX idx_position_captured ON position_snapshots(captured_at DESC);

-- ========================================
-- Usage & Rate Limiting
-- ========================================
CREATE TABLE usage_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    action          VARCHAR(50) NOT NULL,
    credits_used    INTEGER DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_user ON usage_logs(user_id);
CREATE INDEX idx_usage_action ON usage_logs(action);
CREATE INDEX idx_usage_created ON usage_logs(created_at);

-- ========================================
-- Helper: Update timestamp trigger
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$ BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
 $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ========================================
-- Sample data (for development)
-- ========================================
INSERT INTO users (email, password_hash, full_name, plan) VALUES
    ('demo@nexaudit.io', '$2b$12$placeholder_hash', 'Demo User', 'pro');