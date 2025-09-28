-- Complete database setup for Railway PostgreSQL
-- Run this file to create all necessary tables

-- ============================================
-- PART 1: FINANCIAL DATA TABLES
-- ============================================

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    sector VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create financial_data table
CREATE TABLE IF NOT EXISTS financial_data (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    year INTEGER NOT NULL,
    quarter INTEGER,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(20, 2),
    unit VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, year, quarter, metric_name)
);

-- Insert sample companies
INSERT INTO companies (symbol, name, sector) VALUES
    ('PETR4', 'Petróleo Brasileiro S.A. - Petrobras', 'Energia'),
    ('VALE3', 'Vale S.A.', 'Mineração')
ON CONFLICT (symbol) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_financial_data_company ON financial_data(company_id);
CREATE INDEX IF NOT EXISTS idx_financial_data_year ON financial_data(year);
CREATE INDEX IF NOT EXISTS idx_financial_data_metric ON financial_data(metric_name);

-- ============================================
-- PART 2: EARNINGS CALLS TABLES (WITHOUT VECTOR)
-- ============================================

-- Create earnings calls metadata table
CREATE TABLE IF NOT EXISTS earnings_calls (
    id SERIAL PRIMARY KEY,
    company_symbol VARCHAR(10) NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    audio_url TEXT,
    transcript_url TEXT,
    file_size BIGINT,
    call_date DATE,
    language_code VARCHAR(10) DEFAULT 'pt_BR',
    duration_seconds INTEGER,
    processed_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_symbol, year, quarter)
);

-- Create transcription segments table WITHOUT vector embeddings
CREATE TABLE IF NOT EXISTS call_segments (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
    segment_number INTEGER NOT NULL,
    segment_text TEXT NOT NULL,
    timestamp_start FLOAT,
    timestamp_end FLOAT,
    speaker VARCHAR(100),
    sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    sentiment_label VARCHAR(20),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    keywords TEXT[],
    entities JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(call_id, segment_number)
);

-- Create insights summary table
CREATE TABLE IF NOT EXISTS call_insights (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
    overall_sentiment FLOAT,
    key_topics TEXT[],
    risk_mentions INTEGER DEFAULT 0,
    opportunity_mentions INTEGER DEFAULT 0,
    guidance_changes TEXT,
    summary_text TEXT,
    highlights JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(call_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_earnings_calls_company ON earnings_calls(company_symbol);
CREATE INDEX IF NOT EXISTS idx_earnings_calls_date ON earnings_calls(year DESC, quarter DESC);
CREATE INDEX IF NOT EXISTS idx_call_segments_call ON call_segments(call_id);
CREATE INDEX IF NOT EXISTS idx_call_segments_sentiment ON call_segments(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_call_segments_timestamp ON call_segments(timestamp_start);

-- Create full-text search index for Portuguese
CREATE INDEX IF NOT EXISTS idx_call_segments_text ON call_segments
USING gin(to_tsvector('portuguese', segment_text));

-- Create a view for easy querying
CREATE OR REPLACE VIEW earnings_call_overview AS
SELECT
    ec.id,
    ec.company_symbol,
    ec.year,
    ec.quarter,
    CONCAT(ec.quarter, 'T', SUBSTRING(ec.year::TEXT, 3, 2)) as period_label,
    ec.call_date,
    ec.processed_at IS NOT NULL as is_processed,
    COUNT(cs.id) as segment_count,
    AVG(cs.sentiment_score) as avg_sentiment,
    ci.overall_sentiment,
    ci.key_topics,
    ci.risk_mentions,
    ci.opportunity_mentions
FROM earnings_calls ec
LEFT JOIN call_segments cs ON ec.id = cs.call_id
LEFT JOIN call_insights ci ON ec.id = ci.call_id
GROUP BY
    ec.id, ec.company_symbol, ec.year, ec.quarter,
    ec.call_date, ec.processed_at,
    ci.overall_sentiment, ci.key_topics,
    ci.risk_mentions, ci.opportunity_mentions
ORDER BY ec.year DESC, ec.quarter DESC;

-- ============================================
-- PART 3: VERIFY INSTALLATION
-- ============================================

-- Show created tables
SELECT 'Tables created:' as status;
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Show record counts
SELECT 'companies' as table_name, COUNT(*) as record_count FROM companies
UNION ALL
SELECT 'financial_data', COUNT(*) FROM financial_data
UNION ALL
SELECT 'earnings_calls', COUNT(*) FROM earnings_calls
UNION ALL
SELECT 'call_segments', COUNT(*) FROM call_segments
UNION ALL
SELECT 'call_insights', COUNT(*) FROM call_insights;

-- Success message
SELECT '✅ Database setup complete!' as message;