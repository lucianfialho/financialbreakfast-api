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
            SELECT symbol, name, country, sector, currency
            FROM companies
            ORDER BY symbol
        """)
        return cursor.fetchall()

def get_company_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Get company details by symbol"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT symbol, name, country, sector, currency
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

        # Build query with filters
        query = """
            SELECT
                fp.year,
                fp.quarter,
                fp.period_label,
                fm.metric_name,
                fm.metric_label,
                fm.value,
                fm.currency,
                fm.unit,
                fm.metric_category
            FROM companies c
            JOIN financial_periods fp ON c.id = fp.company_id
            JOIN financial_metrics fm ON fp.id = fm.period_id
            WHERE c.symbol = %s
        """

        params = [symbol.upper()]

        if years:
            placeholders = ','.join(['%s'] * len(years))
            query += f" AND fp.year IN ({placeholders})"
            params.extend(years)

        if metrics:
            placeholders = ','.join(['%s'] * len(metrics))
            query += f" AND fm.metric_name IN ({placeholders})"
            params.extend(metrics)

        query += " ORDER BY fp.year DESC, fp.quarter DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Group by period
        periods = {}
        for row in rows:
            period_key = f"{row['year']}_{row['quarter']}"

            if period_key not in periods:
                periods[period_key] = {
                    "year": row['year'],
                    "quarter": row['quarter'],
                    "period_label": row['period_label'],
                    "financial_data": []
                }

            periods[period_key]["financial_data"].append({
                "metric_name": row['metric_name'],
                "metric_label": row['metric_label'],
                "value": float(row['value']),
                "currency": row['currency'],
                "unit": row['unit'],
                "metric_category": row['metric_category']
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
            SELECT DISTINCT fm.metric_name
            FROM companies c
            JOIN financial_periods fp ON c.id = fp.company_id
            JOIN financial_metrics fm ON fp.id = fm.period_id
            WHERE c.symbol = %s
            ORDER BY fm.metric_name
        """, (symbol.upper(),))

        return [row['metric_name'] for row in cursor.fetchall()]

def get_available_periods(symbol: str) -> List[Dict[str, Any]]:
    """Get list of available periods for a company"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT fp.year, fp.quarter, fp.period_label
            FROM companies c
            JOIN financial_periods fp ON c.id = fp.company_id
            WHERE c.symbol = %s
            ORDER BY fp.year DESC, fp.quarter DESC
        """, (symbol.upper(),))

        return cursor.fetchall()

def get_metric_time_series(symbol: str, metric_name: str) -> List[Dict[str, Any]]:
    """Get time series data for a specific metric"""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT
                fp.year,
                fp.quarter,
                fp.period_label as period,
                fm.value,
                fm.currency,
                fm.unit,
                fm.metric_label
            FROM companies c
            JOIN financial_periods fp ON c.id = fp.company_id
            JOIN financial_metrics fm ON fp.id = fm.period_id
            WHERE c.symbol = %s AND fm.metric_name = %s
            ORDER BY fp.year DESC, fp.quarter DESC
        """, (symbol.upper(), metric_name))

        return [
            {
                "year": row['year'],
                "quarter": row['quarter'],
                "period": row['period'],
                "value": float(row['value']),
                "currency": row['currency'],
                "unit": row['unit'],
                "metric_label": row['metric_label']
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