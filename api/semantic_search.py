"""
Semantic Search Service
Handles vector similarity search and database operations for earnings calls
"""

import os
import json
import psycopg2
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
from sentence_transformers import SentenceTransformer
from api.database import get_db_connection, get_db_cursor


class SemanticSearchService:
    """Service for semantic search on earnings call transcriptions"""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
        """
        Initialize semantic search service

        Args:
            model_name: Name of sentence transformer model
        """
        self.embedding_model = SentenceTransformer(model_name)

    def search_similar_segments(
        self,
        query: str,
        company_symbol: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Search for similar segments using text search (fallback without vector embeddings)

        Args:
            query: Search query text
            company_symbol: Optional filter by company
            limit: Maximum number of results
            threshold: Not used in text search mode

        Returns:
            List of similar segments with metadata
        """
        # Use PostgreSQL full-text search instead of vector similarity
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
                "keywords": row["keywords"] or [],
                "entities": row["entities"] or {},
                "company": row["company_symbol"],
                "period": row["period_label"],
                "year": row["year"],
                "quarter": row["quarter"],
                "call_date": row["call_date"].isoformat() if row["call_date"] else None,
                "similarity_score": round(row["similarity"], 3)
            })

        return segments

    def search_by_topic(
        self,
        topic: str,
        company_symbol: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search segments by topic/keyword

        Args:
            topic: Topic or keyword to search
            company_symbol: Optional company filter
            year: Optional year filter
            limit: Maximum number of results

        Returns:
            List of matching segments
        """
        sql = """
        SELECT
            cs.id,
            cs.segment_text,
            cs.timestamp_start,
            cs.timestamp_end,
            cs.sentiment_score,
            cs.sentiment_label,
            cs.keywords,
            ec.company_symbol,
            ec.year,
            ec.quarter,
            CONCAT(ec.quarter, 'T', SUBSTRING(ec.year::TEXT, 3, 2)) as period_label,
            ts_rank(to_tsvector('portuguese', cs.segment_text),
                    to_tsquery('portuguese', %s)) as relevance
        FROM call_segments cs
        JOIN earnings_calls ec ON cs.call_id = ec.id
        WHERE
            to_tsvector('portuguese', cs.segment_text) @@ to_tsquery('portuguese', %s)
        """

        # Process query for full-text search
        search_query = " & ".join(topic.split())
        params = [search_query, search_query]

        if company_symbol:
            sql += " AND ec.company_symbol = %s"
            params.append(company_symbol)

        if year:
            sql += " AND ec.year = %s"
            params.append(year)

        sql += """
        ORDER BY relevance DESC
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
                "keywords": row["keywords"] or [],
                "company": row["company_symbol"],
                "period": row["period_label"],
                "year": row["year"],
                "quarter": row["quarter"],
                "relevance_score": round(row["relevance"], 3)
            })

        return segments

    def get_sentiment_timeline(
        self,
        company_symbol: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[Dict]:
        """
        Get sentiment timeline for a company

        Args:
            company_symbol: Company to analyze
            start_year: Start year (optional)
            end_year: End year (optional)

        Returns:
            List of periods with average sentiment
        """
        sql = """
        SELECT
            ec.year,
            ec.quarter,
            CONCAT(ec.quarter, 'T', SUBSTRING(ec.year::TEXT, 3, 2)) as period_label,
            ec.call_date,
            AVG(cs.sentiment_score) as avg_sentiment,
            COUNT(cs.id) as segment_count,
            ci.overall_sentiment,
            ci.key_topics,
            ci.risk_mentions,
            ci.opportunity_mentions
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
        GROUP BY
            ec.year, ec.quarter, ec.call_date,
            ci.overall_sentiment, ci.key_topics,
            ci.risk_mentions, ci.opportunity_mentions
        ORDER BY ec.year DESC, ec.quarter DESC;
        """

        # Execute query
        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

        # Format results
        timeline = []
        for row in results:
            timeline.append({
                "year": row["year"],
                "quarter": row["quarter"],
                "period": row["period_label"],
                "call_date": row["call_date"].isoformat() if row["call_date"] else None,
                "sentiment": {
                    "average": round(row["avg_sentiment"], 3) if row["avg_sentiment"] else 0,
                    "overall": row["overall_sentiment"]
                },
                "segment_count": row["segment_count"],
                "key_topics": row["key_topics"] or [],
                "risk_mentions": row["risk_mentions"] or 0,
                "opportunity_mentions": row["opportunity_mentions"] or 0
            })

        return timeline

    def get_call_highlights(
        self,
        company_symbol: str,
        year: int,
        quarter: int
    ) -> Dict:
        """
        Get highlights from a specific earnings call

        Args:
            company_symbol: Company symbol
            year: Year
            quarter: Quarter

        Returns:
            Dictionary with call highlights
        """
        # Get call ID
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT id FROM earnings_calls
                WHERE company_symbol = %s AND year = %s AND quarter = %s
            """, (company_symbol, year, quarter))
            result = cursor.fetchone()

            if not result:
                return {"error": "Call not found"}

            call_id = result["id"]

            # Get insights
            cursor.execute("""
                SELECT * FROM call_insights WHERE call_id = %s
            """, (call_id,))
            insights = cursor.fetchone()

            # Get most positive and negative segments
            cursor.execute("""
                SELECT
                    segment_text,
                    sentiment_score,
                    sentiment_label,
                    timestamp_start,
                    timestamp_end,
                    keywords
                FROM call_segments
                WHERE call_id = %s
                ORDER BY sentiment_score DESC
                LIMIT 3
            """, (call_id,))
            positive_segments = cursor.fetchall()

            cursor.execute("""
                SELECT
                    segment_text,
                    sentiment_score,
                    sentiment_label,
                    timestamp_start,
                    timestamp_end,
                    keywords
                FROM call_segments
                WHERE call_id = %s
                ORDER BY sentiment_score ASC
                LIMIT 3
            """, (call_id,))
            negative_segments = cursor.fetchall()

        # Format response
        highlights = {
            "company": company_symbol,
            "period": f"{quarter}T{str(year)[2:]}",
            "overall_sentiment": insights["overall_sentiment"] if insights else None,
            "key_topics": insights["key_topics"] if insights else [],
            "risk_mentions": insights["risk_mentions"] if insights else 0,
            "opportunity_mentions": insights["opportunity_mentions"] if insights else 0,
            "summary": insights["summary_text"] if insights else None,
            "positive_highlights": [
                {
                    "text": seg["segment_text"][:300] + "...",
                    "sentiment_score": seg["sentiment_score"],
                    "timestamp": seg["timestamp_start"],
                    "keywords": seg["keywords"] or []
                }
                for seg in positive_segments
            ],
            "negative_highlights": [
                {
                    "text": seg["segment_text"][:300] + "...",
                    "sentiment_score": seg["sentiment_score"],
                    "timestamp": seg["timestamp_start"],
                    "keywords": seg["keywords"] or []
                }
                for seg in negative_segments
            ]
        }

        return highlights

    def save_segment_to_db(self, segment: Dict, call_id: int) -> int:
        """
        Save processed segment to database

        Args:
            segment: Processed segment dictionary
            call_id: ID of the earnings call

        Returns:
            Segment ID
        """
        sql = """
        INSERT INTO call_segments (
            call_id, segment_number, segment_text,
            timestamp_start, timestamp_end, speaker,
            sentiment_score, sentiment_label, confidence_score,
            keywords, entities
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (call_id, segment_number) DO UPDATE SET
            segment_text = EXCLUDED.segment_text,
            sentiment_score = EXCLUDED.sentiment_score,
            sentiment_label = EXCLUDED.sentiment_label,
            keywords = EXCLUDED.keywords,
            entities = EXCLUDED.entities
        RETURNING id;
        """

        params = (
            call_id,
            segment.get("segment_number", 0),
            segment.get("text", ""),
            segment.get("start_time", 0),
            segment.get("end_time", 0),
            segment.get("speaker"),
            segment.get("sentiment", {}).get("polarity"),
            segment.get("sentiment", {}).get("label"),
            segment.get("sentiment", {}).get("confidence"),
            segment.get("keywords", []),
            json.dumps(segment.get("entities", {}))
        )

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            cursor.connection.commit()
            result = cursor.fetchone()
            return result["id"]

    def save_insights_to_db(self, insights: Dict, call_id: int):
        """
        Save call insights to database

        Args:
            insights: Insights dictionary
            call_id: ID of the earnings call
        """
        sql = """
        INSERT INTO call_insights (
            call_id, overall_sentiment, key_topics,
            risk_mentions, opportunity_mentions,
            guidance_changes, summary_text, highlights
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (call_id) DO UPDATE SET
            overall_sentiment = EXCLUDED.overall_sentiment,
            key_topics = EXCLUDED.key_topics,
            risk_mentions = EXCLUDED.risk_mentions,
            opportunity_mentions = EXCLUDED.opportunity_mentions,
            summary_text = EXCLUDED.summary_text,
            highlights = EXCLUDED.highlights;
        """

        params = (
            call_id,
            insights.get("overall_sentiment"),
            insights.get("key_topics", []),
            insights.get("risk_mentions", 0),
            insights.get("opportunity_mentions", 0),
            insights.get("guidance_changes"),
            insights.get("summary_text"),
            json.dumps(insights.get("highlights", {}))
        )

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            cursor.connection.commit()


if __name__ == "__main__":
    # Example usage
    service = SemanticSearchService()
    print("Semantic search service ready")