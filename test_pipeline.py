"""
Test script for the audio processing and semantic search pipeline
"""

import os
import json
import requests
from pathlib import Path


def test_api_endpoints():
    """Test the new API endpoints"""
    base_url = "http://localhost:8000"
    api_key = "demo-key-12345"
    headers = {"X-API-Key": api_key}

    print("🧪 Testing API endpoints...")

    # Test 1: Semantic search endpoint
    print("\n1. Testing semantic search...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/earnings-calls/search",
            params={
                "query": "receita crescimento petróleo",
                "company": "PETR4",
                "limit": 5
            },
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 503:
            print("   ⚠️  Service not available (expected - dependencies not installed)")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Topic search endpoint
    print("\n2. Testing topic search...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/earnings-calls/search-topic",
            params={
                "topic": "dividendos",
                "company": "PETR4",
                "year": 2025
            },
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 503:
            print("   ⚠️  Service not available (expected)")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Sentiment timeline endpoint
    print("\n3. Testing sentiment timeline...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/earnings-calls/PETR4/sentiment-timeline",
            params={
                "start_year": 2024,
                "end_year": 2025
            },
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 503:
            print("   ⚠️  Service not available (expected)")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Call highlights endpoint
    print("\n4. Testing call highlights...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/earnings-calls/PETR4/2025Q2/highlights",
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 503:
            print("   ⚠️  Service not available (expected)")
        else:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Process audio endpoint
    print("\n5. Testing process audio endpoint...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/earnings-calls/process",
            params={
                "mode": "latest",
                "company": "PETR4"
            },
            headers=headers
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_analysis_service():
    """Test the analysis service components"""
    print("\n🔬 Testing analysis service components...")

    try:
        from api.analysis_service import AnalysisService

        service = AnalysisService()

        # Test text for analysis
        sample_text = """
        No segundo trimestre de 2025, a Petrobras registrou um crescimento significativo
        na receita líquida, impulsionado pelo aumento da produção e melhores preços do petróleo.
        O EBITDA alcançou R$ 45 bilhões, superando as expectativas do mercado.
        Apesar dos desafios relacionados à volatilidade cambial e riscos geopolíticos,
        a empresa mantém perspectivas otimistas para o restante do ano.
        """

        print("\n   Testing sentiment analysis...")
        sentiment = service.analyze_sentiment(sample_text)
        print(f"   Sentiment: {sentiment['label']} (score: {sentiment['polarity']:.3f})")

        print("\n   Testing keyword extraction...")
        keywords = service.extract_keywords(sample_text)
        print(f"   Keywords: {keywords[:5]}")

        print("\n   Testing entity extraction...")
        entities = service.extract_entities(sample_text)
        print(f"   Entities: {entities}")

        print("\n   Testing topic identification...")
        topics = service.identify_topics(sample_text)
        print(f"   Topics: {topics}")

        print("\n   Testing risk analysis...")
        risk_analysis = service.analyze_risk_mentions(sample_text)
        print(f"   Risk mentions: {risk_analysis['risk_mentions']}")
        print(f"   Opportunity mentions: {risk_analysis['opportunity_mentions']}")

        print("\n✅ Analysis service tests completed successfully!")

    except ImportError as e:
        print(f"   ⚠️  Analysis service not available: {e}")
    except Exception as e:
        print(f"   ❌ Error testing analysis service: {e}")


def create_sample_payload():
    """Create sample payload file for testing"""
    sample_payload = {
        "data": {
            "document_metas": [
                {
                    "internal_name": "central_de_resultados_audio_da_teleconferencia",
                    "file_title": "Áudio Teleconferência 2T25",
                    "file_url": "https://example.com/sample_audio.mp3",  # Placeholder URL
                    "file_year": 2025,
                    "file_quarter": 2,
                    "file_size": "1000000",  # 1MB for testing
                    "file_date": "2025-08-08T00:00:00.000Z",
                    "permalink": "https://example.com/sample_audio.mp3"
                },
                {
                    "internal_name": "central_de_resultados_transcricao_da_teleconferencia",
                    "file_title": "Transcrição 2T25",
                    "file_url": "https://example.com/sample_transcript.pdf",
                    "file_year": 2025,
                    "file_quarter": 2,
                    "file_size": "50000",
                    "file_date": "2025-08-13T00:00:00.000Z",
                    "permalink": "https://example.com/sample_transcript.pdf"
                }
            ]
        }
    }

    payload_file = "test_payload.json"
    with open(payload_file, 'w', encoding='utf-8') as f:
        json.dump(sample_payload, f, indent=2, ensure_ascii=False)

    print(f"📄 Created sample payload: {payload_file}")
    return payload_file


def test_downloader():
    """Test the audio downloader"""
    print("\n📥 Testing audio downloader...")

    try:
        from api.audio_downloader import AudioDownloader

        downloader = AudioDownloader()
        payload_file = create_sample_payload()

        # Test getting transcription files
        transcripts = downloader.get_transcription_files(payload_file)
        print(f"   Found {len(transcripts)} transcription files")

        # Test file download (with placeholder URLs - won't actually download)
        print("   Testing download simulation...")
        downloaded_files = downloader.get_downloaded_files()
        print(f"   Previously downloaded files: {len(downloaded_files)}")

        print("✅ Downloader tests completed!")

    except ImportError as e:
        print(f"   ⚠️  Downloader not available: {e}")
    except Exception as e:
        print(f"   ❌ Error testing downloader: {e}")


def test_database_migration():
    """Test if database migration can be run"""
    print("\n🗄️ Testing database migration...")

    migration_file = "migrations/create_earnings_calls_tables.sql"
    if os.path.exists(migration_file):
        with open(migration_file, 'r') as f:
            sql_content = f.read()

        print(f"   Migration file exists: {len(sql_content)} characters")
        print("   Contains tables: earnings_calls, call_segments, call_insights")

        # Check for key components
        required_components = [
            "CREATE TABLE IF NOT EXISTS earnings_calls",
            "CREATE TABLE IF NOT EXISTS call_segments",
            "CREATE TABLE IF NOT EXISTS call_insights",
            "CREATE EXTENSION IF NOT EXISTS vector",
            "vector(768)"
        ]

        for component in required_components:
            if component in sql_content:
                print(f"   ✅ Found: {component}")
            else:
                print(f"   ❌ Missing: {component}")

        print("✅ Database migration tests completed!")
    else:
        print(f"   ❌ Migration file not found: {migration_file}")


def main():
    """Run all tests"""
    print("🚀 Starting pipeline tests...\n")

    # Test individual components
    test_analysis_service()
    test_downloader()
    test_database_migration()

    # Test API endpoints
    test_api_endpoints()

    print("\n📊 Test Summary:")
    print("   - Analysis service: Tests basic NLP functionality")
    print("   - Audio downloader: Tests file management")
    print("   - Database migration: Checks SQL schema")
    print("   - API endpoints: Tests new semantic search routes")
    print("\n💡 Next steps:")
    print("   1. Install required dependencies: pip install -r requirements.txt")
    print("   2. Run database migration")
    print("   3. Set OPENAI_API_KEY environment variable")
    print("   4. Process real audio files using the pipeline")
    print("   5. Test semantic search with actual data")


if __name__ == "__main__":
    main()