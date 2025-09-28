"""
Lightweight semantic search service using only text search
Works without ML dependencies for Railway deployment
"""

from typing import List, Dict, Optional
import json
from api.db_utils import get_db_cursor


class SemanticSearchService:
    """Lightweight semantic search using PostgreSQL text search"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize service (no model loading needed for text search)"""
        pass  # No initialization needed for text-based search

    def search_similar_segments(
        self,
        query: str,
        company_symbol: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Search for similar segments using PostgreSQL full-text search

        Args:
            query: Search query text
            company_symbol: Optional filter by company
            limit: Maximum number of results
            threshold: Not used in text search mode

        Returns:
            List of similar segments with metadata
        """
        # Use PostgreSQL full-text search
        sql = """
        SELECT
            cs.id,
            cs.segment_text,
            cs.timestamp_start,
            cs.timestamp_end,
            cs.sentiment_score,
            cs.sentiment_label,
            cs.keywords,
            cs.entities,
            ec.company_symbol,
            ec.year,
            ec.quarter,
            CONCAT(ec.quarter, 'T', SUBSTRING(ec.year::TEXT, 3, 2)) as period_label,
            ec.call_date,
            ts_rank(to_tsvector('portuguese', cs.segment_text), plainto_tsquery('portuguese', %s)) as similarity
        FROM call_segments cs
        JOIN earnings_calls ec ON cs.call_id = ec.id
        WHERE
            to_tsvector('portuguese', cs.segment_text) @@ plainto_tsquery('portuguese', %s)
        """

        params = [query, query]

        if company_symbol:
            sql += " AND ec.company_symbol = %s"
            params.append(company_symbol)

        sql += """
        ORDER BY similarity DESC
        LIMIT %s;
        """
        params.append(limit)

        # Execute query
        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

        # Format results
        segments = []
        for row in results:
            segments.append({
                "id": row["id"],
                "text": row["segment_text"],
                "timestamp": {
                    "start": row["timestamp_start"],
                    "end": row["timestamp_end"]
                },
                "sentiment": {
                    "score": row["sentiment_score"],
                    "label": row["sentiment_label"]
                },
                "metadata": {
                    "company": row["company_symbol"],
                    "period": row["period_label"],
                    "year": row["year"],
                    "quarter": row["quarter"],
                    "call_date": str(row["call_date"]) if row["call_date"] else None,
                    "keywords": row["keywords"] or [],
                    "entities": row["entities"] or {}
                },
                "similarity_score": float(row["similarity"])
            })

        return segments

    def search_by_topic(
        self,
        topic: str,
        company_symbol: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search segments by topic keyword"""
        return self.search_similar_segments(
            query=topic,
            company_symbol=company_symbol,
            limit=limit
        )

    def get_sentiment_timeline(
        self,
        company_symbol: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[Dict]:
        """Get sentiment evolution over time"""
        sql = """
        SELECT
            ec.year,
            ec.quarter,
            CONCAT(ec.quarter, 'T', SUBSTRING(ec.year::TEXT, 3, 2)) as period_label,
            AVG(cs.sentiment_score) as avg_sentiment,
            COUNT(cs.id) as segment_count,
            ci.overall_sentiment
        FROM earnings_calls ec
        LEFT JOIN call_segments cs ON ec.id = cs.call_id
        LEFT JOIN call_insights ci ON ec.id = ci.call_id
        WHERE ec.company_symbol = %s
        """

        params = [company_symbol]

        if start_year:
            sql += " AND ec.year >= %s"
            params.append(start_year)

        if end_year:
            sql += " AND ec.year <= %s"
            params.append(end_year)

        sql += """
        GROUP BY ec.year, ec.quarter, ci.overall_sentiment
        ORDER BY ec.year, ec.quarter;
        """

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

        timeline = []
        for row in results:
            timeline.append({
                "period": row["period_label"],
                "year": row["year"],
                "quarter": row["quarter"],
                "sentiment": {
                    "average": float(row["avg_sentiment"]) if row["avg_sentiment"] else 0,
                    "overall": float(row["overall_sentiment"]) if row["overall_sentiment"] else 0
                },
                "segment_count": row["segment_count"]
            })

        return timeline

    def get_call_highlights(
        self,
        company_symbol: str,
        year: int,
        quarter: int,
        limit: int = 5
    ) -> Dict:
        """Get highlights from a specific earnings call"""
        # Get call metadata
        sql = """
        SELECT
            ec.id,
            ec.call_date,
            ec.duration_seconds,
            ci.overall_sentiment,
            ci.key_topics,
            ci.risk_mentions,
            ci.opportunity_mentions,
            ci.summary_text,
            ci.highlights
        FROM earnings_calls ec
        LEFT JOIN call_insights ci ON ec.id = ci.call_id
        WHERE ec.company_symbol = %s AND ec.year = %s AND ec.quarter = %s;
        """

        with get_db_cursor() as cursor:
            cursor.execute(sql, [company_symbol, year, quarter])
            call_data = cursor.fetchone()

        if not call_data:
            return {"error": "Call not found"}

        # Get most positive segments
        sql = """
        SELECT segment_text, sentiment_score, timestamp_start
        FROM call_segments
        WHERE call_id = %s AND sentiment_score IS NOT NULL
        ORDER BY sentiment_score DESC
        LIMIT %s;
        """

        cursor.execute(sql, [call_data["id"], limit])
        positive_segments = cursor.fetchall()

        # Get most negative segments
        sql = """
        SELECT segment_text, sentiment_score, timestamp_start
        FROM call_segments
        WHERE call_id = %s AND sentiment_score IS NOT NULL
        ORDER BY sentiment_score ASC
        LIMIT %s;
        """

        cursor.execute(sql, [call_data["id"], limit])
        negative_segments = cursor.fetchall()

        return {
            "call_info": {
                "company": company_symbol,
                "period": f"{quarter}T{str(year)[2:]}",
                "date": str(call_data["call_date"]) if call_data["call_date"] else None,
                "duration_seconds": call_data["duration_seconds"]
            },
            "insights": {
                "overall_sentiment": float(call_data["overall_sentiment"]) if call_data["overall_sentiment"] else 0,
                "key_topics": call_data["key_topics"] or [],
                "risk_mentions": call_data["risk_mentions"] or 0,
                "opportunity_mentions": call_data["opportunity_mentions"] or 0,
                "summary": call_data["summary_text"],
                "ai_highlights": call_data["highlights"]
            },
            "top_positive_moments": [
                {
                    "text": seg["segment_text"],
                    "sentiment": float(seg["sentiment_score"]),
                    "timestamp": float(seg["timestamp_start"])
                }
                for seg in positive_segments
            ],
            "top_negative_moments": [
                {
                    "text": seg["segment_text"],
                    "sentiment": float(seg["sentiment_score"]),
                    "timestamp": float(seg["timestamp_start"])
                }
                for seg in negative_segments
            ]
        }