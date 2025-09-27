"""
Audio Downloader Service
Downloads and manages earnings call audio files from Petrobras IR API
"""

import os
import json
import requests
from typing import List, Dict, Optional, Literal
from datetime import datetime
from pathlib import Path
import hashlib
from urllib.parse import urlparse

class AudioDownloader:
    """Service for downloading earnings call audio files"""

    def __init__(self, base_path: str = "./downloads/audio"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.base_path / "metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """Load download metadata from file"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {"downloads": {}}

    def _save_metadata(self):
        """Save download metadata to file"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def _get_file_hash(self, url: str) -> str:
        """Generate unique hash for URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _format_filename(self, company: str, year: int, quarter: int, extension: str = "mp3") -> str:
        """Format filename for audio file"""
        return f"{company}_{year}Q{quarter}_audio.{extension}"

    def is_downloaded(self, url: str) -> bool:
        """Check if file has already been downloaded"""
        file_hash = self._get_file_hash(url)
        return file_hash in self.metadata["downloads"]

    def download_file(
        self,
        url: str,
        company: str,
        year: int,
        quarter: int,
        force: bool = False
    ) -> Optional[Dict]:
        """
        Download a single audio file

        Args:
            url: Download URL for the audio file
            company: Company symbol (e.g., PETR4)
            year: Year of the earnings call
            quarter: Quarter (1-4)
            force: Force re-download even if file exists

        Returns:
            Dict with download info or None if failed
        """
        file_hash = self._get_file_hash(url)

        # Check if already downloaded
        if not force and self.is_downloaded(url):
            print(f"✓ Already downloaded: {company} {quarter}T{str(year)[2:]}")
            return self.metadata["downloads"][file_hash]

        # Determine file extension from URL
        parsed = urlparse(url)
        extension = "mp3"  # Default
        if "." in parsed.path:
            extension = parsed.path.split(".")[-1].lower()
            if extension not in ["mp3", "mp4", "m4a", "wav"]:
                extension = "mp3"

        filename = self._format_filename(company, year, quarter, extension)
        filepath = self.base_path / filename

        try:
            print(f"⏬ Downloading: {company} {quarter}T{str(year)[2:]} from {url[:50]}...")

            # Download with streaming for large files
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Get file size
            total_size = int(response.headers.get('content-length', 0))

            # Download in chunks
            chunk_size = 8192
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress indicator
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"  Progress: {progress:.1f}% ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)", end='\r')

            print()  # New line after progress

            # Save metadata
            download_info = {
                "url": url,
                "company": company,
                "year": year,
                "quarter": quarter,
                "filename": filename,
                "filepath": str(filepath),
                "size_bytes": os.path.getsize(filepath),
                "downloaded_at": datetime.now().isoformat(),
                "extension": extension
            }

            self.metadata["downloads"][file_hash] = download_info
            self._save_metadata()

            print(f"✅ Downloaded: {filename} ({download_info['size_bytes']/1024/1024:.1f}MB)")
            return download_info

        except requests.RequestException as e:
            print(f"❌ Failed to download {company} {quarter}T{str(year)[2:]}: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error downloading {company} {quarter}T{str(year)[2:]}: {str(e)}")
            return None

    def download_from_payload(
        self,
        payload_file: str,
        mode: Literal["latest", "all"] = "latest",
        company: str = "PETR4"
    ) -> List[Dict]:
        """
        Download audio files from a payload JSON file

        Args:
            payload_file: Path to JSON file containing document metadata
            mode: "latest" to download only most recent, "all" for all files
            company: Company symbol to filter

        Returns:
            List of download info dictionaries
        """
        # Load payload data
        with open(payload_file, 'r') as f:
            data = json.load(f)

        # Extract audio files
        audio_files = []
        documents = data.get("data", {}).get("document_metas", [])

        for doc in documents:
            # Filter for audio files
            if doc.get("internal_name") == "central_de_resultados_audio_da_teleconferencia":
                if doc.get("file_url") or doc.get("permalink"):
                    audio_files.append({
                        "url": doc.get("permalink") or doc.get("file_url"),
                        "year": doc.get("file_year"),
                        "quarter": doc.get("file_quarter"),
                        "title": doc.get("file_title"),
                        "size": doc.get("file_size", "0"),
                        "date": doc.get("file_date")
                    })

        # Sort by date (most recent first)
        audio_files.sort(key=lambda x: (x["year"], x["quarter"]), reverse=True)

        # Filter based on mode
        if mode == "latest" and audio_files:
            audio_files = [audio_files[0]]

        # Download files
        results = []
        for audio in audio_files:
            # Skip if file size is 0 or URL is missing
            if audio["size"] == "0" or not audio["url"]:
                print(f"⚠️  Skipping {audio['title']}: No valid file available")
                continue

            result = self.download_file(
                url=audio["url"],
                company=company,
                year=audio["year"],
                quarter=audio["quarter"]
            )

            if result:
                results.append(result)

        print(f"\n📊 Downloaded {len(results)} audio file(s)")
        return results

    def get_downloaded_files(self, company: Optional[str] = None) -> List[Dict]:
        """
        Get list of downloaded files

        Args:
            company: Optional company filter

        Returns:
            List of download info dictionaries
        """
        files = list(self.metadata["downloads"].values())

        if company:
            files = [f for f in files if f["company"] == company]

        # Sort by date
        files.sort(key=lambda x: (x["year"], x["quarter"]), reverse=True)

        return files

    def get_transcription_files(self, payload_file: str) -> List[Dict]:
        """
        Extract available transcription files from payload

        Args:
            payload_file: Path to JSON file containing document metadata

        Returns:
            List of transcription file info
        """
        with open(payload_file, 'r') as f:
            data = json.load(f)

        transcripts = []
        documents = data.get("data", {}).get("document_metas", [])

        for doc in documents:
            # Filter for transcription files
            if doc.get("internal_name") == "central_de_resultados_transcricao_da_teleconferencia":
                if doc.get("file_url") or doc.get("permalink"):
                    transcripts.append({
                        "url": doc.get("permalink") or doc.get("file_url"),
                        "year": doc.get("file_year"),
                        "quarter": doc.get("file_quarter"),
                        "title": doc.get("file_title"),
                        "size": doc.get("file_size", "0"),
                        "date": doc.get("file_date")
                    })

        # Sort by date (most recent first)
        transcripts.sort(key=lambda x: (x["year"], x["quarter"]), reverse=True)

        return transcripts


if __name__ == "__main__":
    # Example usage
    downloader = AudioDownloader()

    # Create sample payload file for testing
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
                    "file_date": "2025-08-08T00:00:00.000Z"
                }
            ]
        }
    }

    # Save sample payload
    with open("sample_audio_payload.json", "w") as f:
        json.dump(sample_payload, f, indent=2)

    # Test download
    results = downloader.download_from_payload("sample_audio_payload.json", mode="latest")
    print(f"Downloaded files: {results}")