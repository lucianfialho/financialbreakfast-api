#!/usr/bin/env python3
"""
Quarterly Audio Processor
Automatically processes the latest earnings call audio files
Designed to run every 3 months via scheduled job
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api.pipeline_orchestrator import PipelineOrchestrator


def fetch_latest_payload():
    """
    Fetch the latest document payload from Petrobras API
    This simulates getting fresh data each quarter
    """
    # In production, this would fetch from the actual API
    # For now, we'll create a payload based on current quarter
    current_date = datetime.now()
    year = current_date.year
    quarter = (current_date.month - 1) // 3 + 1

    # Mock payload structure - in production, this would be fetched from:
    # https://www.investidorpetrobras.com.br/api/documents or similar
    mock_payload = {
        "data": {
            "document_metas": [
                {
                    "internal_name": "central_de_resultados_audio_da_teleconferencia",
                    "file_title": f"Áudio Teleconferência {quarter}T{str(year)[2:]}",
                    "file_url": f"https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/audio-{year}q{quarter}",
                    "file_year": year,
                    "file_quarter": quarter,
                    "file_size": "100000000",  # ~100MB typical size
                    "file_date": current_date.isoformat(),
                    "permalink": f"https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/audio-{year}q{quarter}"
                },
                {
                    "internal_name": "central_de_resultados_transcricao_da_teleconferencia",
                    "file_title": f"Transcrição {quarter}T{str(year)[2:]}",
                    "file_url": f"https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/transcript-{year}q{quarter}",
                    "file_year": year,
                    "file_quarter": quarter,
                    "file_size": "500000",
                    "file_date": current_date.isoformat(),
                    "permalink": f"https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/transcript-{year}q{quarter}"
                }
            ]
        }
    }

    return mock_payload


def save_payload_to_file(payload, filename="quarterly_payload.json"):
    """Save payload to file for processing"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return filename


def send_notification(message, webhook_url=None):
    """
    Send notification about processing results
    Can be webhook, email, Slack, etc.
    """
    print(f"📢 NOTIFICATION: {message}")

    if webhook_url:
        try:
            requests.post(webhook_url, json={"text": message})
        except:
            pass  # Fail silently if webhook doesn't work


def main():
    """Main processing function"""
    print("🚀 Starting quarterly earnings call processor...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Step 1: Initialize orchestrator
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️ WARNING: OPENAI_API_KEY not set, will use local Whisper if available")

        orchestrator = PipelineOrchestrator(
            openai_api_key=openai_key,
            use_local_whisper=not bool(openai_key)
        )

        # Step 2: Fetch latest data
        print("📡 Fetching latest earnings call data...")
        payload = fetch_latest_payload()
        payload_file = save_payload_to_file(payload)

        # Step 3: Process files
        print("🎯 Processing audio files...")
        results = orchestrator.process_from_payload(
            payload_file=payload_file,
            mode="latest",  # Only process the most recent
            company="PETR4"
        )

        # Step 4: Generate summary
        successful = len([r for r in results if r.get("success")])
        total = len(results)

        if successful > 0:
            # Get latest result details
            latest_result = next((r for r in results if r.get("success")), {})
            sentiment = latest_result.get("overall_sentiment", 0)
            topics = latest_result.get("key_topics", [])

            summary = f"""
🎉 Quarterly Processing Complete!

📊 Results:
   - Files processed: {successful}/{total}
   - Overall sentiment: {sentiment:.3f}
   - Key topics: {', '.join(topics[:3])}

🔍 Semantic search updated with latest earnings call
🌐 Available at: https://financialbreakfast-production.up.railway.app/api/v1/earnings-calls/search
            """.strip()

            send_notification(summary, os.getenv("WEBHOOK_URL"))
            print(summary)

        else:
            error_msg = "❌ Quarterly processing failed - no files processed successfully"
            send_notification(error_msg, os.getenv("WEBHOOK_URL"))
            print(error_msg)
            return 1

        # Step 5: Cleanup
        if os.path.exists(payload_file):
            os.remove(payload_file)

        print("✅ Quarterly processing completed successfully!")
        return 0

    except Exception as e:
        error_msg = f"❌ Quarterly processing error: {str(e)}"
        send_notification(error_msg, os.getenv("WEBHOOK_URL"))
        print(error_msg)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)