#!/usr/bin/env python3
"""
Test script to simulate Railway production environment
"""

import os
import sys

def test_imports():
    """Test if all ML dependencies can be imported"""
    print("🧪 Testing imports...")

    try:
        print("  ✓ Importing sentence_transformers...")
        from sentence_transformers import SentenceTransformer
        print("    Version:", SentenceTransformer.__version__ if hasattr(SentenceTransformer, '__version__') else "OK")
    except ImportError as e:
        print(f"    ❌ Failed: {e}")
        return False

    try:
        print("  ✓ Importing textblob...")
        from textblob import TextBlob
        print("    OK")
    except ImportError as e:
        print(f"    ❌ Failed: {e}")
        return False

    try:
        print("  ✓ Importing nltk...")
        import nltk
        print("    Version:", nltk.__version__)
    except ImportError as e:
        print(f"    ❌ Failed: {e}")
        return False

    try:
        print("  ✓ Importing numpy...")
        import numpy
        print("    Version:", numpy.__version__)
    except ImportError as e:
        print(f"    ❌ Failed: {e}")
        return False

    print("\n✅ All imports successful!")
    return True

def test_semantic_search():
    """Test if semantic search service can be initialized"""
    print("\n🧪 Testing Semantic Search Service...")

    try:
        from api.semantic_search import SemanticSearchService
        service = SemanticSearchService()
        print("  ✅ SemanticSearchService initialized successfully!")
        return True
    except Exception as e:
        print(f"  ❌ Failed to initialize: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n🧪 Testing Database Connection...")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("  ⚠️ DATABASE_URL not set, skipping database test")
        return None

    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM call_segments")
        count = cursor.fetchone()[0]
        print(f"  ✅ Database connected! Found {count} segments in call_segments table")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 Railway Production Environment Test")
    print("=" * 60)

    # Test imports
    imports_ok = test_imports()

    # Test semantic search
    semantic_ok = test_semantic_search()

    # Test database
    db_ok = test_database_connection()

    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"  - ML Dependencies: {'✅ OK' if imports_ok else '❌ Failed'}")
    print(f"  - Semantic Search: {'✅ OK' if semantic_ok else '❌ Failed'}")
    if db_ok is not None:
        print(f"  - Database: {'✅ OK' if db_ok else '❌ Failed'}")
    print("=" * 60)

    return 0 if (imports_ok and semantic_ok) else 1

if __name__ == "__main__":
    sys.exit(main())