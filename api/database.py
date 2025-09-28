"""
Database connection and query functions for PostgreSQL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://lucianfialho@localhost/financial_data')

# Parse DATABASE_URL for connection
def parse_database_url(url):
    """Parse DATABASE_URL into connection parameters"""
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    from urllib.parse import urlparse
    parsed = urlparse(url)

    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:] if parsed.path else 'financial_data',
        'user': parsed.username,
        'password': parsed.password or ''
    }

@contextmanager
def get_db_connection():
    """Get database connection context manager"""
    conn = None
    try:
        db_params = parse_database_url(DATABASE_URL)
        conn = psycopg2.connect(**db_params, cursor_factory=RealDictCursor)
        yield conn
    finally:
        if conn:
            conn.close()

@contextmanager
def get_db_cursor():
    """Get database cursor context manager"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

# Query functions
def get_all_companies() -> List[Dict[str, Any]]:
    """Get all companies from database"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT symbol, name, sector
            FROM companies
            ORDER BY symbol
        """)
        return cursor.fetchall()

def get_company_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get company details by symbol"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT symbol, name, sector
            FROM companies
            WHERE symbol = %s
        """, (symbol.upper(),))
        return cursor.fetchone()

def get_financial_data(
    symbol: str,
    years: Optional[List[int]] = None,
    metrics: Optional[List[str]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Get financial data for a company with optional filters"""

    with get_db_cursor() as cursor:
        # Get company info
        company = get_company_by_symbol(symbol)
        if not company:
            return None

        # Build query with filters using new schema
        query = """
            SELECT
                fd.year,
                fd.quarter,
                fd.metric_name,
                fd.metric_value,
                fd.unit
            FROM companies c
            JOIN financial_data fd ON c.id = fd.company_id
            WHERE c.symbol = %s
        """

        params = [symbol.upper()]

        if years:
            placeholders = ','.join(['%s'] * len(years))
            query += f" AND fd.year IN ({placeholders})"
            params.extend(years)

        if metrics:
            placeholders = ','.join(['%s'] * len(metrics))
            query += f" AND fd.metric_name IN ({placeholders})"
            params.extend(metrics)

        query += " ORDER BY fd.year DESC, fd.quarter DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Group by period
        periods = {}
        for row in rows:
            period_key = f"{row['year']}_{row['quarter'] or 0}"
            period_label = f"{row['quarter'] or 'Y'}{str(row['year'])[2:]}" if row['quarter'] else str(row['year'])

            if period_key not in periods:
                periods[period_key] = {
                    "year": row['year'],
                    "quarter": row['quarter'],
                    "period_label": period_label,
                    "financial_data": []
                }

            periods[period_key]["financial_data"].append({
                "metric_name": row['metric_name'],
                "value": float(row['metric_value']) if row['metric_value'] else 0.0,
                "unit": row['unit']
            })

        # Convert to list and apply limit
        period_list = list(periods.values())[:limit]

        return {
            "company_symbol": company['symbol'],
            "company_name": company['name'],
            "periods": period_list,
            "total_periods": len(period_list)
        }

def get_available_metrics(symbol: str) -> List[str]:
    """Get list of available metrics for a company"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT fd.metric_name
            FROM companies c
            JOIN financial_data fd ON c.id = fd.company_id
            WHERE c.symbol = %s
            ORDER BY fd.metric_name
        """, (symbol.upper(),))

        return [row['metric_name'] for row in cursor.fetchall()]

def get_available_periods(symbol: str) -> List[Dict[str, Any]]:
    """Get list of available periods for a company"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT fd.year, fd.quarter
            FROM companies c
            JOIN financial_data fd ON c.id = fd.company_id
            WHERE c.symbol = %s
            ORDER BY fd.year DESC, fd.quarter DESC
        """, (symbol.upper(),))

        return cursor.fetchall()

def get_metric_time_series(symbol: str, metric_name: str) -> List[Dict[str, Any]]:
    """Get time series data for a specific metric"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT
                fd.year,
                fd.quarter,
                fd.metric_value,
                fd.unit
            FROM companies c
            JOIN financial_data fd ON c.id = fd.company_id
            WHERE c.symbol = %s AND fd.metric_name = %s
            ORDER BY fd.year DESC, fd.quarter DESC
        """, (symbol.upper(), metric_name))

        return [
            {
                "year": row['year'],
                "quarter": row['quarter'],
                "period": f"{row['quarter'] or 'Y'}{str(row['year'])[2:]}" if row['quarter'] else str(row['year']),
                "value": float(row['metric_value']) if row['metric_value'] else 0.0,
                "unit": row['unit']
            }
            for row in cursor.fetchall()
        ]

def test_connection():
    """Test database connection"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False