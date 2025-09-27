"""
Transcription Service using OpenAI Whisper
Transcribes audio files and segments them for analysis
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import openai
from pydub import AudioSegment
from pydub.silence import split_on_silence
import tempfile


class TranscriptionService:
    """Service for transcribing audio files using OpenAI Whisper"""

    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        """
        Initialize transcription service

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Whisper model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None

        # Create output directory
        self.output_path = Path("./transcriptions")
        self.output_path.mkdir(parents=True, exist_ok=True)

    def _split_audio_by_duration(
        self,
        audio_file: str,
        chunk_duration_ms: int = 600000  # 10 minutes default
    ) -> List[Tuple[int, int, str]]:
        """
        Split audio file into chunks by duration

        Args:
            audio_file: Path to audio file
            chunk_duration_ms: Duration of each chunk in milliseconds

        Returns:
            List of tuples (start_ms, end_ms, chunk_file_path)
        """
        # Load audio file
        audio = AudioSegment.from_file(audio_file)
        chunks = []

        # Split into chunks
        for i in range(0, len(audio), chunk_duration_ms):
            start_ms = i
            end_ms = min(i + chunk_duration_ms, len(audio))
            chunk = audio[start_ms:end_ms]

            # Save chunk to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                chunk.export(tmp.name, format="mp3")
                chunks.append((start_ms, end_ms, tmp.name))

        return chunks

    def _split_audio_by_silence(
        self,
        audio_file: str,
        min_silence_len: int = 1000,
        silence_thresh: int = -40
    ) -> List[Tuple[int, int, str]]:
        """
        Split audio file by detecting silence

        Args:
            audio_file: Path to audio file
            min_silence_len: Minimum length of silence to split on (ms)
            silence_thresh: Silence threshold in dBFS

        Returns:
            List of tuples (start_ms, end_ms, chunk_file_path)
        """
        # Load audio file
        audio = AudioSegment.from_file(audio_file)

        # Split on silence
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=500  # Keep 500ms of silence
        )

        # Save chunks and track timestamps
        chunk_files = []
        current_ms = 0

        for chunk in chunks:
            start_ms = current_ms
            end_ms = current_ms + len(chunk)

            # Save chunk to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                chunk.export(tmp.name, format="mp3")
                chunk_files.append((start_ms, end_ms, tmp.name))

            current_ms = end_ms

        return chunk_files

    def transcribe_with_whisper_api(
        self,
        audio_file: str,
        language: str = "pt",
        response_format: str = "verbose_json"
    ) -> Optional[Dict]:
        """
        Transcribe audio using OpenAI Whisper API

        Args:
            audio_file: Path to audio file
            language: Language code (pt for Portuguese)
            response_format: API response format

        Returns:
            Transcription data or None if failed
        """
        if not self.client:
            print("❌ OpenAI API key not configured")
            return None

        try:
            print(f"🎙️ Transcribing: {audio_file}")

            # Check file size (API limit is 25MB)
            file_size = os.path.getsize(audio_file) / (1024 * 1024)  # Convert to MB

            if file_size > 25:
                # Need to split the file
                print(f"📄 File too large ({file_size:.1f}MB), splitting into chunks...")
                chunks = self._split_audio_by_duration(audio_file)
                transcriptions = []

                for i, (start_ms, end_ms, chunk_file) in enumerate(chunks):
                    print(f"  Processing chunk {i+1}/{len(chunks)}...")

                    with open(chunk_file, "rb") as f:
                        response = self.client.audio.transcriptions.create(
                            model=self.model,
                            file=f,
                            language=language,
                            response_format=response_format
                        )

                    # Add chunk info to response
                    chunk_data = response.model_dump() if hasattr(response, 'model_dump') else response
                    chunk_data["start_ms"] = start_ms
                    chunk_data["end_ms"] = end_ms
                    transcriptions.append(chunk_data)

                    # Clean up temporary file
                    os.unlink(chunk_file)

                # Combine transcriptions
                combined = {
                    "text": " ".join([t.get("text", "") for t in transcriptions]),
                    "language": language,
                    "duration": sum([t.get("duration", 0) for t in transcriptions]),
                    "segments": []
                }

                # Combine segments with adjusted timestamps
                for chunk in transcriptions:
                    if "segments" in chunk:
                        for seg in chunk["segments"]:
                            seg["start"] += chunk["start_ms"] / 1000
                            seg["end"] += chunk["start_ms"] / 1000
                            combined["segments"].append(seg)

                return combined

            else:
                # Single file transcription
                with open(audio_file, "rb") as f:
                    response = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=f,
                        language=language,
                        response_format=response_format
                    )

                return response.model_dump() if hasattr(response, 'model_dump') else response

        except Exception as e:
            print(f"❌ Transcription failed: {str(e)}")
            return None

    def transcribe_with_local_whisper(
        self,
        audio_file: str,
        language: str = "pt",
        model_size: str = "base"
    ) -> Optional[Dict]:
        """
        Transcribe audio using local Whisper model (fallback option)

        Args:
            audio_file: Path to audio file
            language: Language code
            model_size: Whisper model size (tiny, base, small, medium, large)

        Returns:
            Transcription data or None if failed
        """
        try:
            import whisper

            print(f"🎙️ Loading Whisper model: {model_size}")
            model = whisper.load_model(model_size)

            print(f"🎙️ Transcribing locally: {audio_file}")
            result = model.transcribe(
                audio_file,
                language=language,
                verbose=True
            )

            return result

        except ImportError:
            print("❌ Local Whisper not installed. Install with: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"❌ Local transcription failed: {str(e)}")
            return None

    def segment_transcription(
        self,
        transcription: Dict,
        segment_duration: float = 30.0
    ) -> List[Dict]:
        """
        Segment transcription into smaller chunks for analysis

        Args:
            transcription: Transcription data from Whisper
            segment_duration: Target duration for each segment in seconds

        Returns:
            List of segment dictionaries
        """
        segments = []

        if "segments" in transcription:
            # Use existing segments from Whisper
            current_segment = {
                "text": "",
                "start": 0,
                "end": 0,
                "words": []
            }

            for seg in transcription["segments"]:
                # Check if adding this segment exceeds duration
                if current_segment["text"] and \
                   (seg["end"] - current_segment["start"]) > segment_duration:
                    # Save current segment
                    segments.append(current_segment)
                    # Start new segment
                    current_segment = {
                        "text": seg["text"],
                        "start": seg["start"],
                        "end": seg["end"],
                        "words": seg.get("words", [])
                    }
                else:
                    # Add to current segment
                    if not current_segment["text"]:
                        current_segment["start"] = seg["start"]
                    current_segment["text"] += " " + seg["text"]
                    current_segment["end"] = seg["end"]
                    current_segment["words"].extend(seg.get("words", []))

            # Add final segment
            if current_segment["text"]:
                segments.append(current_segment)

        else:
            # No segments available, create one from full text
            segments = [{
                "text": transcription.get("text", ""),
                "start": 0,
                "end": transcription.get("duration", 0),
                "words": []
            }]

        # Clean and format segments
        formatted_segments = []
        for i, seg in enumerate(segments):
            formatted_segments.append({
                "segment_number": i + 1,
                "text": seg["text"].strip(),
                "start_time": seg["start"],
                "end_time": seg["end"],
                "duration": seg["end"] - seg["start"],
                "word_count": len(seg["text"].split())
            })

        return formatted_segments

    def save_transcription(
        self,
        transcription: Dict,
        company: str,
        year: int,
        quarter: int
    ) -> str:
        """
        Save transcription to file

        Args:
            transcription: Transcription data
            company: Company symbol
            year: Year
            quarter: Quarter

        Returns:
            Path to saved file
        """
        filename = f"{company}_{year}Q{quarter}_transcription.json"
        filepath = self.output_path / filename

        # Add metadata
        transcription["metadata"] = {
            "company": company,
            "year": year,
            "quarter": quarter,
            "transcribed_at": datetime.now().isoformat(),
            "model": self.model
        }

        # Save to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(transcription, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved transcription: {filepath}")
        return str(filepath)

    def process_audio_file(
        self,
        audio_file: str,
        company: str,
        year: int,
        quarter: int,
        use_api: bool = True
    ) -> Optional[str]:
        """
        Complete pipeline to process an audio file

        Args:
            audio_file: Path to audio file
            company: Company symbol
            year: Year
            quarter: Quarter
            use_api: Use OpenAI API (True) or local Whisper (False)

        Returns:
            Path to saved transcription or None if failed
        """
        # Check if already transcribed
        output_file = self.output_path / f"{company}_{year}Q{quarter}_transcription.json"
        if output_file.exists():
            print(f"✓ Already transcribed: {output_file}")
            return str(output_file)

        # Transcribe audio
        if use_api:
            transcription = self.transcribe_with_whisper_api(audio_file)
        else:
            transcription = self.transcribe_with_local_whisper(audio_file)

        if not transcription:
            return None

        # Segment transcription
        segments = self.segment_transcription(transcription)
        transcription["processed_segments"] = segments

        # Save transcription
        return self.save_transcription(transcription, company, year, quarter)


if __name__ == "__main__":
    # Example usage
    service = TranscriptionService()

    # Test with a sample audio file
    # result = service.process_audio_file(
    #     audio_file="path/to/audio.mp3",
    #     company="PETR4",
    #     year=2025,
    #     quarter=2,
    #     use_api=True
    # )
    print("Transcription service ready")