"""
Semantic Search Service with ML embeddings
Optimized for Railway deployment with caching and performance improvements
"""

import os
import json
import psycopg2
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import pickle
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

try:
    from api.database import get_db_connection, get_db_cursor
except ImportError:
    from database import get_db_connection, get_db_cursor


class SemanticSearchService:
    """Service for semantic search on earnings call transcriptions with ML embeddings"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize semantic search service with caching

        Args:
            model_name: Name of sentence transformer model
        """
        self.model_name = model_name
        self.embedding_model = None
        self.embeddings_cache = {}

        if ML_AVAILABLE:
            self._load_model()
        else:
            print("⚠️ ML dependencies not available, falling back to text search")

    def _load_model(self):
        """Load the sentence transformer model with error handling"""
        try:
            print(f"🤖 Loading model {self.model_name}...")
            self.embedding_model = SentenceTransformer(self.model_name)
            print("✅ Model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            self.embedding_model = None

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text with caching"""
        if not self.embedding_model:
            return None

        # Create cache key
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]

        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            self.embeddings_cache[cache_key] = embedding
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def search_similar_segments(
        self,
        query: str,
        company_symbol: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Search for similar segments using ML embeddings or fallback to text search

        Args:
            query: Search query text
            company_symbol: Optional filter by company
            limit: Maximum number of results
            threshold: Similarity threshold 0-1

        Returns:
            List of similar segments with metadata
        """
        # Try ML search first, fallback to text search
        if self.embedding_model:
            return self._ml_search(query, company_symbol, limit, threshold)
        else:
            return self._text_search(query, company_symbol, limit)

    def _ml_search(
        self,
        query: str,
        company_symbol: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """ML-based semantic search with embeddings"""
        query_embedding = self._get_embedding(query)

        if query_embedding is None:
            return self._text_search(query, company_symbol, limit)

        # Get all segments with basic filtering
        sql = """
        SELECT
            cs.id,
            cs.text_content,
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
            ec.call_date
        FROM call_segments cs
        JOIN earnings_calls ec ON cs.call_id = ec.id
        WHERE cs.text_content IS NOT NULL AND LENGTH(cs.text_content) > 10
        """

        params = []

        if company_symbol:
            sql += " AND ec.company_symbol = %s"
            params.append(company_symbol)

        sql += " ORDER BY cs.id LIMIT 1000"  # Limit for performance

        # Execute query
        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

        # Calculate similarities
        scored_results = []
        for row in results:
            text_embedding = self._get_embedding(row["text_content"])

            if text_embedding is not None:
                similarity = self._cosine_similarity(query_embedding, text_embedding)

                if similarity >= threshold:
                    scored_results.append({
                        "similarity": similarity,
                        "data": row
                    })

        # Sort by similarity and limit
        scored_results.sort(key=lambda x: x["similarity"], reverse=True)
        scored_results = scored_results[:limit]

        # Format results
        segments = []
        for item in scored_results:
            row = item["data"]
            segments.append({
                "id": row["id"],
                "text": row["text_content"],
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
                "similarity_score": round(item["similarity"], 3),
                "search_type": "ml_embedding"
            })

        return segments

    def _text_search(
        self,
        query: str,
        company_symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Fallback PostgreSQL full-text search"""
        sql = """
        SELECT
            cs.id,
            cs.text_content,
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
            ts_rank(to_tsvector('portuguese', cs.text_content), plainto_tsquery('portuguese', %s)) as similarity
        FROM call_segments cs
        JOIN earnings_calls ec ON cs.call_id = ec.id
        WHERE
            to_tsvector('portuguese', cs.text_content) @@ plainto_tsquery('portuguese', %s)
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
                "text": row["text_content"],
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
                "similarity_score": round(row["similarity"], 3),
                "search_type": "text_search"
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
        Search segments by topic/keyword using ML or text search
        """
        return self.search_similar_segments(
            query=topic,
            company_symbol=company_symbol,
            limit=limit,
            threshold=0.3  # Lower threshold for topic search
        )

    def get_sentiment_timeline(
        self,
        company_symbol: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None
    ) -> List[Dict]:
        """Get sentiment timeline (same as lite version)"""
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

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

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
        """Get highlights from a specific earnings call (same as lite version)"""
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
                    text_content,
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
                    text_content,
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
            "ml_enabled": self.embedding_model is not None,
            "positive_highlights": [
                {
                    "text": seg["text_content"][:300] + "...",
                    "sentiment_score": seg["sentiment_score"],
                    "timestamp": seg["timestamp_start"],
                    "keywords": seg["keywords"] or []
                }
                for seg in positive_segments
            ],
            "negative_highlights": [
                {
                    "text": seg["text_content"][:300] + "...",
                    "sentiment_score": seg["sentiment_score"],
                    "timestamp": seg["timestamp_start"],
                    "keywords": seg["keywords"] or []
                }
                for seg in negative_segments
            ]
        }

        return highlights


if __name__ == "__main__":
    # Test the service
    service = SemanticSearchService()
    print(f"ML Available: {ML_AVAILABLE}")
    print(f"Model loaded: {service.embedding_model is not None}")