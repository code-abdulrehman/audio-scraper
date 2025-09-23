"""
Utility functions for the Quran Audio Scraper
"""

import os
import json
import zipfile
import logging
import requests
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
import time
import numpy as np

from constants import (
    AUDIO_URL_TEMPLATE, AUDIO_EXTENSION, ZIP_EXTENSION, JSON_EXTENSION,
    MAX_RETRIES, TIMEOUT, CONCURRENT_DOWNLOADS, DEFAULT_DOWNLOAD_DIR
)


class DownloadStats:
    """Class to track download statistics"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.total_size = 0
        self.start_time = None
        self.end_time = None
        self.speed_history = []
    
    def start(self):
        self.start_time = time.time()
    
    def end(self):
        self.end_time = time.time()
    
    def get_duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def get_speed(self):
        duration = self.get_duration()
        if duration > 0:
            return self.total_size / duration / 1024 / 1024  # MB/s
        return 0
    
    def add_speed_sample(self, speed):
        self.speed_history.append(speed)
        # Keep only last 10 samples
        if len(self.speed_history) > 10:
            self.speed_history.pop(0)
    
    def get_average_speed(self):
        if self.speed_history:
            return sum(self.speed_history) / len(self.speed_history)
        return 0


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """Setup logging configuration"""
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('quran_scraper')
    logger.setLevel(logging.INFO)
    
    # Create file handler
    log_file = os.path.join(log_dir, f"quran_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def load_quran_data(json_file: str = "quran_data.json") -> List[Dict]:
    """Load Quran data from JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Quran data file '{json_file}' not found")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in '{json_file}'")


def get_surah_by_id(surah_id: int, quran_data: List[Dict]) -> Optional[Dict]:
    """Get surah data by ID"""
    for surah in quran_data:
        if surah['surah_id'] == surah_id:
            return surah
    return None


def generate_audio_url(surah_id: int, ayah_id: int, word_id: int) -> str:
    """Generate audio URL for specific word using correct QuranWBW structure"""
    # For QuranWBW, the folder ID is typically the same as surah_id
    # But we need to handle special cases where surahs might be in different folders
    folder_id = surah_id
    
    return AUDIO_URL_TEMPLATE.format(
        folder_id=folder_id,
        surah_id=surah_id,
        ayah_id=ayah_id,
        word_id=word_id
    )


def create_download_directory(base_dir: str, surah_id: int) -> str:
    """Create download directory for specific surah"""
    surah_dir = os.path.join(base_dir, f"surah_{surah_id:03d}")
    os.makedirs(surah_dir, exist_ok=True)
    return surah_dir


def download_audio_file(url: str, file_path: str, logger: logging.Logger) -> bool:
    """Download a single audio file"""
    try:
        response = requests.get(url, timeout=TIMEOUT, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}")
        return False


async def download_audio_async(session: aiohttp.ClientSession, url: str, file_path: str, logger: logging.Logger) -> Tuple[bool, int]:
    """Download a single audio file asynchronously"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as response:
            if response.status == 200:
                content = await response.read()
                with open(file_path, 'wb') as f:
                    f.write(content)
                return True, len(content)
            elif response.status == 404:
                logger.warning(f"HTTP 404 for {url}")
                return False, 0
            else:
                logger.warning(f"HTTP {response.status} for {url}")
                return False, 0
    except aiohttp.ClientError as e:
        logger.error(f"Client error downloading {url}: {str(e)}")
        return False, 0
    except Exception as e:
        logger.error(f"Failed to download {url}: {str(e)}")
        return False, 0


def create_audio_metadata(surah_id: int, ayah_id: int, word_id: int, audio_file: str) -> Dict:
    """Create metadata for audio file - ensure all values are JSON serializable"""
    return {
        "surah_id": int(surah_id),  # Convert to int to avoid int64
        "ayah_id": int(ayah_id),    # Convert to int to avoid int64
        "word_id": int(word_id),    # Convert to int to avoid int64
        "audio_file": str(audio_file)
    }


def create_zip_file(surah_dir: str, surah_id: int, metadata: List[Dict], logger: logging.Logger) -> str:
    """Create ZIP file with all audio files and metadata"""
    zip_path = os.path.join(os.path.dirname(surah_dir), f"surah_{surah_id:03d}.zip")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all audio files
            for root, dirs, files in os.walk(surah_dir):
                for file in files:
                    if file.endswith(AUDIO_EXTENSION):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, surah_dir)
                        zipf.write(file_path, arcname)
            
            # Add metadata JSON - ensure all values are JSON serializable
            serializable_metadata = []
            for item in metadata:
                serializable_item = {
                    "surah_id": int(item["surah_id"]),
                    "ayah_id": int(item["ayah_id"]),
                    "word_id": int(item["word_id"]),
                    "audio_file": str(item["audio_file"])
                }
                serializable_metadata.append(serializable_item)
            
            metadata_json = json.dumps(serializable_metadata, indent=2, ensure_ascii=False)
            zipf.writestr("metadata.json", metadata_json)
        
        logger.info(f"Created ZIP file: {zip_path}")
        return zip_path
    except Exception as e:
        logger.error(f"Failed to create ZIP file: {str(e)}")
        raise


def cleanup_temp_files(surah_dir: str, logger: logging.Logger):
    """Clean up temporary files after creating ZIP"""
    try:
        import shutil
        shutil.rmtree(surah_dir)
        logger.info(f"Cleaned up temporary directory: {surah_dir}")
    except Exception as e:
        logger.error(f"Failed to cleanup temp files: {str(e)}")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_download_progress(current: int, total: int) -> float:
    """Calculate download progress percentage"""
    if total == 0:
        return 0.0
    return (current / total) * 100


def estimate_word_count_for_ayah(surah_id: int, ayah_id: int, total_words: int, total_ayahs: int) -> int:
    """Estimate word count for a specific ayah based on surah statistics"""
    # This is a rough estimation - in reality, word counts vary per ayah
    # For now, we'll use a simple average, but this should be improved with actual data
    base_words_per_ayah = total_words // total_ayahs
    
    # Add some variation based on ayah position (middle ayahs tend to be longer)
    if ayah_id <= total_ayahs // 3:
        # First third - slightly shorter
        return max(1, base_words_per_ayah - 2)
    elif ayah_id >= (total_ayahs * 2) // 3:
        # Last third - slightly shorter
        return max(1, base_words_per_ayah - 1)
    else:
        # Middle third - average or slightly longer
        return base_words_per_ayah + 1
