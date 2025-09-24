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
    """class to track download statistics"""
    
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
    """Create download directory for specific surah (legacy method)"""
    surah_dir = os.path.join(base_dir, f"surah_{surah_id:03d}")
    os.makedirs(surah_dir, exist_ok=True)
    return surah_dir


def create_enhanced_download_directory(base_dir: str, surah_id: int, surah_name: str) -> str:
    """Create enhanced download directory with surah name"""
    surah_folder = f"{surah_id:03d}_{surah_name.replace(' ', '_').replace("'", '').replace('-', '_')}"
    surah_dir = os.path.join(base_dir, surah_folder)
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
    """Download a single audio file asynchronously with better error handling"""
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
    """Create ZIP file with all audio files and metadata (legacy method)"""
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
    """Clean up temporary files after creating ZIP (legacy method)"""
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
    return ((current / total) * 100)


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


# utility functions for new features

def save_download_state(download_dir: str, surah_id: int, verse_id: int, word_id: int = None) -> bool:
    """Save download state to file for resume functionality"""
    state_file = os.path.join(download_dir, f"download_state_{surah_id}.json")
    state = {
        'surah_id': surah_id,
        'last_verse': verse_id,
        'last_word': word_id,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
        return True
    except Exception as e:
        print(f"Failed to save download state: {e}")
        return False


def load_download_state(download_dir: str, surah_id: int) -> Dict:
    """Load download state from file for resume functionality"""
    state_file = os.path.join(download_dir, f"download_state_{surah_id}.json")
    
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load download state: {e}")
    
    return {'surah_id': surah_id, 'last_verse': 0, 'last_word': 0}


def cleanup_download_state(download_dir: str, surah_id: int) -> bool:
    """Clean up download state file after successful completion"""
    state_file = os.path.join(download_dir, f"download_state_{surah_id}.json")
    
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            return True
        except Exception as e:
            print(f"Failed to cleanup download state: {e}")
            return False
    return True


def get_surah_folder_name(surah_id: int, surah_name: str) -> str:
    """Generate standardized folder name for surah"""
    return f"{surah_id:03d}_{surah_name.replace(' ', '_').replace("'", '').replace('-', '_')}"


def get_audio_file_path(download_dir: str, surah_id: int, surah_name: str, verse_id: int, word_id: int = None) -> str:
    """Generate file path for audio file with enhanced folder structure"""
    surah_folder = get_surah_folder_name(surah_id, surah_name)
    surah_path = os.path.join(download_dir, surah_folder)
    os.makedirs(surah_path, exist_ok=True)
    
    if word_id:
        filename = f"{surah_id:03d}_{verse_id:03d}_{word_id:03d}.mp3"
    else:
        filename = f"{surah_id:03d}_{verse_id:03d}_verse.mp3"
    
    return os.path.join(surah_path, filename)


def check_file_exists_and_valid(file_path: str) -> bool:
    """Check if file exists and has valid content"""
    return os.path.exists(file_path) and os.path.getsize(file_path) > 0


def get_surah_download_progress(download_dir: str, surah_id: int, quran_data: List[Dict]) -> Dict:
    """Get download progress for a specific surah"""
    surah = get_surah_by_id(surah_id, quran_data)
    if not surah:
        return {'error': f'Surah {surah_id} not found'}
    
    surah_folder = get_surah_folder_name(surah_id, surah['name_en'])
    surah_path = os.path.join(download_dir, surah_folder)
    
    if not os.path.exists(surah_path):
        return {'downloaded_files': 0, 'total_estimated': 0, 'progress_percentage': 0}
    
    downloaded_files = len([f for f in os.listdir(surah_path) if f.endswith('.mp3')])
    
    # Estimate total files based on surah data
    ayah_range = surah['ayah_range']
    word_range = surah['word_range']
    total_ayahs = ayah_range[1] - ayah_range[0] + 1
    total_words = word_range[1] - word_range[0] + 1
    estimated_total = total_words  # Assuming word-by-word download
    
    progress_percentage = (downloaded_files / estimated_total * 100) if estimated_total > 0 else 0
    
    return {
        'downloaded_files': downloaded_files,
        'total_estimated': estimated_total,
        'progress_percentage': progress_percentage,
        'surah_name': surah['name_en'],
        'surah_folder': surah_folder
    }


def validate_download_range(surah_id: int, start_verse: int, end_verse: int, 
                          start_word: int = None, end_word: int = None, 
                          quran_data: List[Dict] = None) -> Tuple[bool, str]:
    """Validate download range parameters"""
    if quran_data is None:
        quran_data = load_quran_data()
    
    surah = get_surah_by_id(surah_id, quran_data)
    if not surah:
        return False, f"Surah {surah_id} not found"
    
    ayah_range = surah['ayah_range']
    
    # Validate verse range
    if start_verse < ayah_range[0] or start_verse > ayah_range[1]:
        return False, f"Start verse {start_verse} is out of range ({ayah_range[0]}-{ayah_range[1]})"
    
    if end_verse < ayah_range[0] or end_verse > ayah_range[1]:
        return False, f"End verse {end_verse} is out of range ({ayah_range[0]}-{ayah_range[1]})"
    
    if start_verse > end_verse:
        return False, "Start verse cannot be greater than end verse"
    
    # Validate word range if provided
    if start_word is not None and end_word is not None:
        if start_word < 1:
            return False, "Start word must be at least 1"
        if end_word < start_word:
            return False, "End word cannot be less than start word"
    
    return True, "Valid range"


def calculate_estimated_files(surah_id: int, start_verse: int, end_verse: int,
                            start_word: int = None, end_word: int = None,
                            download_type: str = 'word_by_word',
                            quran_data: List[Dict] = None) -> int:
    """Calculate estimated number of files to download"""
    if quran_data is None:
        quran_data = load_quran_data()
    
    surah = get_surah_by_id(surah_id, quran_data)
    if not surah:
        return 0
    
    if download_type == 'verse_by_verse':
        return end_verse - start_verse + 1
    
    # For word-by-word downloads
    ayah_range = surah['ayah_range']
    word_range = surah['word_range']
    total_ayahs = ayah_range[1] - ayah_range[0] + 1
    total_words = word_range[1] - word_range[0] + 1
    
    # Calculate words per ayah (approximate)
    words_per_ayah = total_words // total_ayahs
    
    total_files = 0
    for verse_id in range(start_verse, end_verse + 1):
        if verse_id == ayah_range[1]:  # Last ayah
            words_in_verse = total_words - (words_per_ayah * (total_ayahs - 1))
        else:
            words_in_verse = words_per_ayah
        
        verse_start_word = start_word if verse_id == start_verse else 1
        verse_end_word = end_word if verse_id == end_verse else words_in_verse
        
        total_files += max(0, verse_end_word - verse_start_word + 1)
    
    return total_files


def get_download_summary(download_dir: str, quran_data: List[Dict] = None) -> Dict:
    """Get summary of all downloads"""
    if quran_data is None:
        quran_data = load_quran_data()
    
    summary = {
        'total_surahs_downloaded': 0,
        'total_files': 0,
        'total_size': 0,
        'surahs': []
    }
    
    if not os.path.exists(download_dir):
        return summary
    
    for surah in quran_data:
        surah_id = surah['surah_id']
        surah_name = surah['name_en']
        surah_folder = get_surah_folder_name(surah_id, surah_name)
        surah_path = os.path.join(download_dir, surah_folder)
        
        if os.path.exists(surah_path):
            files = [f for f in os.listdir(surah_path) if f.endswith('.mp3')]
            if files:
                total_size = sum(os.path.getsize(os.path.join(surah_path, f)) for f in files)
                
                summary['total_surahs_downloaded'] += 1
                summary['total_files'] += len(files)
                summary['total_size'] += total_size
                
                summary['surahs'].append({
                    'surah_id': surah_id,
                    'surah_name': surah_name,
                    'files_count': len(files),
                    'size': total_size,
                    'formatted_size': format_file_size(total_size)
                })
    
    return summary


def get_ayah_word_mapping(surah_id: int, quran_data: List[Dict] = None) -> Dict[int, int]:
    """Get word count for each ayah in a surah"""
    if quran_data is None:
        quran_data = load_quran_data()
    
    surah = get_surah_by_id(surah_id, quran_data)
    if not surah:
        return {}
    
    ayah_range = surah['ayah_range']
    word_range = surah['word_range']
    total_ayahs = ayah_range[1] - ayah_range[0] + 1
    total_words = word_range[1] - word_range[0] + 1
    
    # Calculate words per ayah (approximate)
    words_per_ayah = total_words // total_ayahs
    
    ayah_word_mapping = {}
    
    for ayah_id in range(ayah_range[0], ayah_range[1] + 1):
        # For the last ayah, include all remaining words
        if ayah_id == ayah_range[1]:
            words_in_ayah = total_words - (words_per_ayah * (total_ayahs - 1))
        else:
            words_in_ayah = words_per_ayah
        
        ayah_word_mapping[ayah_id] = words_in_ayah
    
    return ayah_word_mapping


def create_download_metadata(surah_id: int, surah_name: str, download_type: str,
                           start_verse: int = None, end_verse: int = None,
                           start_word: int = None, end_word: int = None,
                           total_files: int = 0, successful_downloads: int = 0,
                           failed_downloads: int = 0, total_size: int = 0,
                           duration: float = 0) -> Dict:
    """Create comprehensive download metadata"""
    return {
        'surah_id': surah_id,
        'surah_name': surah_name,
        'download_type': download_type,
        'start_verse': start_verse,
        'end_verse': end_verse,
        'start_word': start_word,
        'end_word': end_word,
        'total_files': total_files,
        'successful_downloads': successful_downloads,
        'failed_downloads': failed_downloads,
        'total_size': total_size,
        'formatted_size': format_file_size(total_size),
        'duration': duration,
        'formatted_duration': format_duration(duration),
        'timestamp': datetime.now().isoformat(),
        'success_rate': (successful_downloads / total_files * 100) if total_files > 0 else 0
    }


def save_download_metadata(download_dir: str, surah_id: int, metadata: Dict) -> bool:
    """Save download metadata to JSON file"""
    surah_folder = get_surah_folder_name(surah_id, metadata['surah_name'])
    surah_path = os.path.join(download_dir, surah_folder)
    metadata_file = os.path.join(surah_path, 'download_metadata.json')
    
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Failed to save download metadata: {e}")
        return False


def load_download_metadata(download_dir: str, surah_id: int, surah_name: str) -> Dict:
    """Load download metadata from JSON file"""
    surah_folder = get_surah_folder_name(surah_id, surah_name)
    surah_path = os.path.join(download_dir, surah_folder)
    metadata_file = os.path.join(surah_path, 'download_metadata.json')
    
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load download metadata: {e}")
    
    return {}


def get_file_list(download_dir: str, surah_id: int, surah_name: str) -> List[str]:
    """Get list of all downloaded files for a surah"""
    surah_folder = get_surah_folder_name(surah_id, surah_name)
    surah_path = os.path.join(download_dir, surah_folder)
    
    if not os.path.exists(surah_path):
        return []
    
    files = [f for f in os.listdir(surah_path) if f.endswith('.mp3')]
    return sorted(files)


def get_surah_statistics(download_dir: str, surah_id: int, surah_name: str) -> Dict:
    """Get comprehensive statistics for a surah download"""
    surah_folder = get_surah_folder_name(surah_id, surah_name)
    surah_path = os.path.join(download_dir, surah_folder)
    
    if not os.path.exists(surah_path):
        return {
            'surah_id': surah_id,
            'surah_name': surah_name,
            'downloaded_files': 0,
            'total_size': 0,
            'formatted_size': '0 B',
            'files': []
        }
    
    files = get_file_list(download_dir, surah_id, surah_name)
    total_size = sum(os.path.getsize(os.path.join(surah_path, f)) for f in files)
    
    return {
        'surah_id': surah_id,
        'surah_name': surah_name,
        'downloaded_files': len(files),
        'total_size': total_size,
        'formatted_size': format_file_size(total_size),
        'files': files[:10],  # Show first 10 files
        'all_files_count': len(files)
    }
