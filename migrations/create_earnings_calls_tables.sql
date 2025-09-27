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

-- Create extension for vector operations (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create transcription segments table with embeddings
CREATE TABLE IF NOT EXISTS call_segments (
    id SERIAL PRIMARY KEY,
    call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
    segment_number INTEGER NOT NULL,
    segment_text TEXT NOT NULL,
    timestamp_start FLOAT,
    timestamp_end FLOAT,
    speaker VARCHAR(100),
    sentiment_score FLOAT CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    sentiment_label VARCHAR(20), -- 'positive', 'negative', 'neutral'
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    embedding vector(768), -- For sentence-transformers embeddings
    keywords TEXT[], -- Array of extracted keywords
    entities JSONB, -- Named entities (companies, people, amounts)
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
    highlights JSONB, -- JSON array of important moments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(call_id)
);

-- Create indexes for better performance
CREATE INDEX idx_earnings_calls_company ON earnings_calls(company_symbol);
CREATE INDEX idx_earnings_calls_date ON earnings_calls(year DESC, quarter DESC);
CREATE INDEX idx_call_segments_call ON call_segments(call_id);
CREATE INDEX idx_call_segments_sentiment ON call_segments(sentiment_score);
CREATE INDEX idx_call_segments_timestamp ON call_segments(timestamp_start);

-- Create index for semantic search using IVFFlat
CREATE INDEX idx_call_segments_embedding ON call_segments
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100); -- Adjust lists parameter based on data size

-- Create full-text search index
CREATE INDEX idx_call_segments_text ON call_segments
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

-- Add comments for documentation
COMMENT ON TABLE earnings_calls IS 'Stores metadata about earnings call audio files and transcripts';
COMMENT ON TABLE call_segments IS 'Stores transcribed segments with embeddings for semantic search';
COMMENT ON TABLE call_insights IS 'Stores analyzed insights and summaries from earnings calls';
COMMENT ON COLUMN call_segments.embedding IS 'Vector embedding for semantic search (768 dimensions)';
COMMENT ON COLUMN call_segments.sentiment_score IS 'Sentiment score from -1 (negative) to 1 (positive)';