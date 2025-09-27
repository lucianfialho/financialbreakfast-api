"""
Pipeline Orchestrator
Complete pipeline to process audio files from download to semantic search
"""

import os
import json
from typing import Dict, List, Optional, Literal
from datetime import datetime
from pathlib import Path

from api.audio_downloader import AudioDownloader
from api.transcription_service import TranscriptionService
from api.analysis_service import AnalysisService
from api.semantic_search import SemanticSearchService
from api.database import get_db_cursor


class PipelineOrchestrator:
    """Orchestrates the complete audio processing pipeline"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        use_local_whisper: bool = False
    ):
        """
        Initialize pipeline services

        Args:
            openai_api_key: OpenAI API key for Whisper transcription
            use_local_whisper: Use local Whisper instead of API
        """
        self.downloader = AudioDownloader()
        self.transcriber = TranscriptionService(api_key=openai_api_key)
        self.analyzer = AnalysisService()
        self.search_service = SemanticSearchService()
        self.use_local_whisper = use_local_whisper

        # Create output directories
        self.output_dir = Path("./pipeline_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_earnings_call_metadata(
        self,
        company: str,
        year: int,
        quarter: int,
        audio_url: str,
        transcript_url: Optional[str] = None,
        file_size: Optional[int] = None,
        call_date: Optional[str] = None
    ) -> int:
        """
        Save earnings call metadata to database

        Args:
            company: Company symbol
            year: Year
            quarter: Quarter
            audio_url: URL to audio file
            transcript_url: URL to transcript file (optional)
            file_size: Size of audio file in bytes
            call_date: Date of the call

        Returns:
            Call ID
        """
        sql = """
        INSERT INTO earnings_calls (
            company_symbol, year, quarter, audio_url,
            transcript_url, file_size, call_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (company_symbol, year, quarter) DO UPDATE SET
            audio_url = EXCLUDED.audio_url,
            transcript_url = EXCLUDED.transcript_url,
            file_size = EXCLUDED.file_size,
            call_date = EXCLUDED.call_date
        RETURNING id;
        """

        params = (
            company, year, quarter, audio_url,
            transcript_url, file_size,
            datetime.fromisoformat(call_date.replace('Z', '+00:00')).date() if call_date else None
        )

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            cursor.connection.commit()
            result = cursor.fetchone()
            return result["id"]

    def mark_call_as_processed(self, call_id: int):
        """Mark earnings call as processed"""
        sql = "UPDATE earnings_calls SET processed_at = CURRENT_TIMESTAMP WHERE id = %s"

        with get_db_cursor() as cursor:
            cursor.execute(sql, (call_id,))
            cursor.connection.commit()

    def process_single_file(
        self,
        audio_info: Dict,
        company: str = "PETR4"
    ) -> Dict:
        """
        Process a single audio file through the complete pipeline

        Args:
            audio_info: Dictionary with audio file information
            company: Company symbol

        Returns:
            Dictionary with processing results
        """
        year = audio_info.get("year", 2025)
        quarter = audio_info.get("quarter", 1)
        audio_url = audio_info.get("url")

        print(f"\n🚀 Processing {company} {quarter}T{str(year)[2:]} earnings call...")

        try:
            # Step 1: Save metadata to database
            print("📝 Saving metadata to database...")
            call_id = self.save_earnings_call_metadata(
                company=company,
                year=year,
                quarter=quarter,
                audio_url=audio_url,
                file_size=int(audio_info.get("size", 0)),
                call_date=audio_info.get("date")
            )

            # Step 2: Download audio file
            print("⏬ Downloading audio file...")
            download_result = self.downloader.download_file(
                url=audio_url,
                company=company,
                year=year,
                quarter=quarter,
                force=False
            )

            if not download_result:
                return {"error": "Failed to download audio file", "call_id": call_id}

            audio_filepath = download_result["filepath"]

            # Step 3: Transcribe audio
            print("🎙️ Transcribing audio...")
            transcription_file = self.transcriber.process_audio_file(
                audio_file=audio_filepath,
                company=company,
                year=year,
                quarter=quarter,
                use_api=not self.use_local_whisper
            )

            if not transcription_file:
                return {"error": "Failed to transcribe audio", "call_id": call_id}

            # Load transcription
            with open(transcription_file, 'r', encoding='utf-8') as f:
                transcription_data = json.load(f)

            segments = transcription_data.get("processed_segments", [])

            # Step 4: Analyze segments
            print("🧠 Analyzing segments for sentiment and embeddings...")
            processed_segments = []

            for segment in segments:
                # Process each segment with analysis
                processed_segment = self.analyzer.process_segment(segment)
                processed_segments.append(processed_segment)

                # Save segment to database
                self.search_service.save_segment_to_db(processed_segment, call_id)

            # Step 5: Generate call insights
            print("📊 Generating call insights...")
            insights = self.analyzer.generate_call_insights(processed_segments)

            # Save insights to database
            self.search_service.save_insights_to_db(insights, call_id)

            # Step 6: Mark as processed
            self.mark_call_as_processed(call_id)

            # Save processed data
            output_file = self.output_dir / f"{company}_{year}Q{quarter}_processed.json"
            processed_data = {
                "call_id": call_id,
                "metadata": {
                    "company": company,
                    "year": year,
                    "quarter": quarter,
                    "processed_at": datetime.now().isoformat()
                },
                "download_info": download_result,
                "transcription_file": transcription_file,
                "segments": processed_segments,
                "insights": insights
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Processing complete! Results saved to {output_file}")

            return {
                "success": True,
                "call_id": call_id,
                "segments_processed": len(processed_segments),
                "overall_sentiment": insights.get("overall_sentiment"),
                "key_topics": insights.get("key_topics"),
                "output_file": str(output_file)
            }

        except Exception as e:
            print(f"❌ Error processing {company} {quarter}T{str(year)[2:]}: {str(e)}")
            return {"error": str(e), "call_id": call_id}

    def process_from_payload(
        self,
        payload_file: str,
        mode: Literal["latest", "all"] = "latest",
        company: str = "PETR4"
    ) -> List[Dict]:
        """
        Process audio files from a payload JSON file

        Args:
            payload_file: Path to JSON file with document metadata
            mode: Process "latest" file only or "all" files
            company: Company symbol

        Returns:
            List of processing results
        """
        print(f"🎯 Starting pipeline for {company} - mode: {mode}")

        # Get audio files from payload
        transcripts = self.downloader.get_transcription_files(payload_file)
        audio_downloads = self.downloader.download_from_payload(
            payload_file=payload_file,
            mode=mode,
            company=company
        )

        if not audio_downloads:
            print("❌ No audio files to process")
            return []

        # Process each downloaded file
        results = []
        for download_info in audio_downloads:
            # Find corresponding transcript if available
            transcript_url = None
            for transcript in transcripts:
                if (transcript["year"] == download_info["year"] and
                    transcript["quarter"] == download_info["quarter"]):
                    transcript_url = transcript["url"]
                    break

            # Create audio info dict
            audio_info = {
                "year": download_info["year"],
                "quarter": download_info["quarter"],
                "url": download_info.get("url"),
                "size": download_info.get("size_bytes", 0),
                "date": None  # Would need to be extracted from download_info
            }

            # Process the file
            result = self.process_single_file(audio_info, company)
            results.append(result)

        # Summary
        successful = len([r for r in results if r.get("success")])
        print(f"\n📈 Pipeline Summary:")
        print(f"   Total files: {len(results)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(results) - successful}")

        return results

    def create_sample_payload(self, output_file: str = "sample_payload.json"):
        """
        Create a sample payload file for testing

        Args:
            output_file: Path to save sample payload
        """
        sample_payload = {
            "data": {
                "document_metas": [
                    {
                        "internal_name": "central_de_resultados_audio_da_teleconferencia",
                        "file_title": "Áudio Teleconferência 2T25",
                        "file_url": "https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/632a612a-62ef-8db3-12ed-cfb0d1afa001?origin=1",
                        "file_year": 2025,
                        "file_quarter": 2,
                        "file_size": "102823553",
                        "file_date": "2025-08-08T00:00:00.000Z",
                        "permalink": "https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/632a612a-62ef-8db3-12ed-cfb0d1afa001?origin=1"
                    },
                    {
                        "internal_name": "central_de_resultados_transcricao_da_teleconferencia",
                        "file_title": "Transcrição 2T25",
                        "file_url": "https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/50a877f0-1915-b41e-4660-f253de99add9?origin=1",
                        "file_year": 2025,
                        "file_quarter": 2,
                        "file_size": "473317",
                        "file_date": "2025-08-13T00:00:00.000Z",
                        "permalink": "https://api.mziq.com/mzfilemanager/v2/d/25fdf098-34f5-4608-b7fa-17d60b2de47d/50a877f0-1915-b41e-4660-f253de99add9?origin=1"
                    }
                ]
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_payload, f, indent=2, ensure_ascii=False)

        print(f"✅ Sample payload created: {output_file}")
        return output_file


if __name__ == "__main__":
    # Example usage
    orchestrator = PipelineOrchestrator()

    # Create sample payload for testing
    payload_file = orchestrator.create_sample_payload()

    # Process files
    # results = orchestrator.process_from_payload(
    #     payload_file=payload_file,
    #     mode="latest",
    #     company="PETR4"
    # )

    print("Pipeline orchestrator ready for use!")