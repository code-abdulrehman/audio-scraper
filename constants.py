"""
Constants for the Quran Audio Scraper
"""

# Base URLs - Updated to match QuranWBW structure
BASE_URL = "https://audios.quranwbw.com/words"
AUDIO_URL_TEMPLATE = "https://audios.quranwbw.com/words/{folder_id}/{surah_id:03d}_{ayah_id:03d}_{word_id:03d}.mp3"

# Default directories
DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_LOG_DIR = "logs"

# File extensions
AUDIO_EXTENSION = ".mp3"
ZIP_EXTENSION = ".zip"
JSON_EXTENSION = ".json"
LOG_EXTENSION = ".log"

# Request settings
MAX_RETRIES = 3
TIMEOUT = 30
CONCURRENT_DOWNLOADS = 5

# Progress settings
PROGRESS_UPDATE_INTERVAL = 1  # seconds

# Log levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# UI Messages
MESSAGES = {
    'select_surah': 'Select a Surah to download',
    'select_directory': 'Select download directory (optional)',
    'download_started': 'Download started...',
    'download_completed': 'Download completed successfully!',
    'download_failed': 'Download failed. Check logs for details.',
    'no_surah_selected': 'Please select a surah to download',
    'invalid_directory': 'Invalid directory selected',
    'creating_zip': 'Creating ZIP file...',
    'processing_audio': 'Processing audio files...'
}

# Surah folder mapping (some surahs are in different folders)
SURAH_FOLDER_MAPPING = {
    # Most surahs are in their own folder, but some might be grouped
    # This mapping ensures we use the correct folder for each surah
}
