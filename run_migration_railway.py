#!/usr/bin/env python3
"""
Railway migration script - run this on Railway to set up database
Add this as a one-time deployment command in Railway
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def run_migration():
    """Execute the complete database setup migration on Railway"""

    # Get DATABASE_URL from Railway environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        return False

    print(f"🔌 Connecting to Railway database...")

    # Migration SQL directly in script to avoid file path issues
    migration_sql = """
-- Complete database setup for Railway PostgreSQL
-- PART 1: FINANCIAL DATA TABLES

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

-- PART 2: EARNINGS CALLS TABLES

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

-- Create transcription segments table
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
"""

    try:
        conn = psycopg2.connect(database_url)
        conn.set_session(autocommit=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            print("📄 Executing migration SQL...")

            # Execute the migration
            cursor.execute(migration_sql)
            print("✅ Migration completed successfully!")

            # Verify tables were created
            print("\n🔍 Verifying tables exist:")
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()

            for table in tables:
                print(f"  ✓ {table['table_name']}")

            # Check record counts
            print("\n📊 Record counts:")
            expected_tables = ['companies', 'financial_data', 'earnings_calls', 'call_segments', 'call_insights']
            for table_name in expected_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    count = cursor.fetchone()
                    print(f"  📋 {table_name}: {count['count']} records")
                except Exception as e:
                    print(f"  ❌ {table_name}: {e}")

        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Railway database migration...")
    success = run_migration()

    if success:
        print("\n🎉 Migration completed successfully!")
        print("💡 Database is now ready for the API")
    else:
        print("\n💥 Migration failed!")