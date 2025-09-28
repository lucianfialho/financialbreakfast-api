"""
Admin endpoints for database management
"""

from fastapi import APIRouter, HTTPException, Depends
try:
    from api.database import get_db_cursor
except ImportError:
    from database import get_db_cursor
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/admin", tags=["admin"])

def admin_key_required(x_api_key: str = None):
    """Simple admin key validation - replace with proper auth"""
    if x_api_key != "admin-migrate-key-2024":
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True

@router.post("/migrate")
async def run_database_migration(auth: bool = Depends(admin_key_required)):
    """
    Run database migration to create all necessary tables
    POST /api/v1/admin/migrate
    Headers: X-API-Key: admin-migrate-key-2024
    """

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
        with get_db_cursor() as cursor:
            # Execute migration
            cursor.execute(migration_sql)

            # Verify tables were created
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()

            # Get record counts
            record_counts = {}
            expected_tables = ['companies', 'financial_data', 'earnings_calls', 'call_segments', 'call_insights']
            for table_name in expected_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    count = cursor.fetchone()
                    record_counts[table_name] = count['count']
                except:
                    record_counts[table_name] = "Error"

            return {
                "status": "success",
                "message": "Database migration completed successfully",
                "tables_created": [table['table_name'] for table in tables],
                "record_counts": record_counts
            }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.get("/status")
async def database_status(auth: bool = Depends(admin_key_required)):
    """
    Check database status and table existence
    GET /api/v1/admin/status
    Headers: X-API-Key: admin-migrate-key-2024
    """

    try:
        with get_db_cursor() as cursor:
            # Check if tables exist
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()

            # Check record counts
            record_counts = {}
            expected_tables = ['companies', 'financial_data', 'earnings_calls', 'call_segments', 'call_insights']

            for table_name in expected_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name};")
                    count = cursor.fetchone()
                    record_counts[table_name] = count['count']
                except:
                    record_counts[table_name] = "Table not found"

            return {
                "status": "success",
                "tables_found": [table['table_name'] for table in tables],
                "expected_tables": expected_tables,
                "record_counts": record_counts,
                "database_ready": len(tables) >= len(expected_tables)
            }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")