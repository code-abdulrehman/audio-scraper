"""
Enhanced Main downloader class for Quran Audio Scraper with FIXED Error Handling
"""

import os
import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging

from utils import (
    DownloadStats, setup_logging, load_quran_data, get_surah_by_id,
    generate_audio_url, create_download_directory, download_audio_async,
    create_audio_metadata, create_zip_file, cleanup_temp_files,
    format_file_size, format_duration, get_download_progress
)
from constants import CONCURRENT_DOWNLOADS, DEFAULT_DOWNLOAD_DIR


class QuranAudioDownloader:
    """Enhanced class for downloading Quran audio files with FIXED error handling"""
    
    def __init__(self, download_dir: str = DEFAULT_DOWNLOAD_DIR, log_dir: str = "logs"):
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.logger = setup_logging(log_dir)
        self.quran_data = load_quran_data()
        self.stats = DownloadStats()
        self.progress_callback: Optional[Callable] = None
        
        # Enhanced download state tracking
        self.download_state = {
            'current_surah': None,
            'current_verse': None,
            'current_word': None,
            'total_files': 0,
            'completed_files': 0,
            'failed_files': 0,
            'start_time': None,
            'last_successful_file': None
        }
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
    
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = "", 
                        surah_id: int = None, verse_id: int = None, word_id: int = None):
        """Enhanced progress update with detailed information"""
        if self.progress_callback:
            try:
                progress = get_download_progress(current, total)
                self.progress_callback(progress, current, total, message, surah_id, verse_id, word_id)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def _get_surah_folder_name(self, surah_id: int, surah_name: str) -> str:
        """Generate folder name for surah"""
        return f"{surah_id:03d}_{surah_name.replace(' ', '_').replace("'", '').replace('-', '_')}"
    
    def _get_file_path(self, surah_id: int, surah_name: str, verse_id: int, word_id: int = None) -> str:
        """Generate file path for audio file with folder structure"""
        surah_folder = self._get_surah_folder_name(surah_id, surah_name)
        surah_path = os.path.join(self.download_dir, surah_folder)
        os.makedirs(surah_path, exist_ok=True)
        
        if word_id:
            filename = f"{surah_id:03d}_{verse_id:03d}_{word_id:03d}.mp3"
        else:
            filename = f"{surah_id:03d}_{verse_id:03d}_verse.mp3"
        
        return os.path.join(surah_path, filename)
    
    def _check_file_exists(self, file_path: str) -> bool:
        """Check if file already exists and has content"""
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0
    
    def _save_download_state(self, surah_id: int, verse_id: int, word_id: int = None):
        """Save current download state for resume functionality"""
        state_file = os.path.join(self.download_dir, f"download_state_{surah_id}.json")
        state = {
            'surah_id': surah_id,
            'last_verse': verse_id,
            'last_word': word_id,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            self.logger.error(f"Failed to save download state: {e}")
    
    def _load_download_state(self, surah_id: int) -> Dict:
        """Load download state for resume functionality"""
        state_file = os.path.join(self.download_dir, f"download_state_{surah_id}.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load download state: {e}")
        
        return {'surah_id': surah_id, 'last_verse': 0, 'last_word': 0}
    
    def _get_ayah_word_mapping(self, surah_id: int) -> Dict[int, int]:
        """Get word count for each ayah in a surah"""
        surah = get_surah_by_id(surah_id, self.quran_data)
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
    
    async def _download_word_with_retry(self, session: aiohttp.ClientSession, 
                                      surah_id: int, verse_id: int, word_id: int,
                                      file_path: str, max_retries: int = 3) -> tuple[bool, int]:
        """Download a single word with retry logic and 404 handling"""
        for attempt in range(max_retries):
            try:
                url = generate_audio_url(surah_id, verse_id, word_id)
                success, size = await download_audio_async(session, url, file_path, self.logger)
                
                if success:
                    return True, size
                else:
                    # Check if it's a 404 error (file doesn't exist)
                    if attempt == 0:  # Only log on first attempt
                        self.logger.warning(f"Word {surah_id:03d}_{verse_id:03d}_{word_id:03d} not found (404)")
                    return False, 0
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed for {surah_id:03d}_{verse_id:03d}_{word_id:03d}: {e}")
                if attempt == max_retries - 1:
                    return False, 0
                await asyncio.sleep(1)  # Wait before retry
        
        return False, 0
    
    async def download_word_by_word(self, session: aiohttp.ClientSession, 
                                  surah_id: int, surah_name: str,
                                  start_verse: int = None, end_verse: int = None,
                                  start_word: int = None, end_word: int = None,
                                  resume: bool = True) -> Dict:
        """FIXED: Download word by word with proper 404 handling and verse progression"""
        
        # Load previous state if resuming
        if resume:
            state = self._load_download_state(surah_id)
            if start_verse is None:
                start_verse = state.get('last_verse', 1)
            if start_word is None and state.get('last_word'):
                start_word = state.get('last_word', 1)
        
        # Get ayah-word mapping
        ayah_word_mapping = self._get_ayah_word_mapping(surah_id)
        
        if not ayah_word_mapping:
            raise ValueError(f"No word mapping found for Surah {surah_id}")
        
        # Calculate total files to download
        total_files = 0
        for verse_id, word_count in ayah_word_mapping.items():
            if start_verse and verse_id < start_verse:
                continue
            if end_verse and verse_id > end_verse:
                continue
            
            verse_start_word = start_word if verse_id == start_verse else 1
            verse_end_word = end_word if verse_id == end_verse else word_count
            
            total_files += max(0, verse_end_word - verse_start_word + 1)
        
        self.download_state.update({
            'current_surah': surah_id,
            'total_files': total_files,
            'completed_files': 0,
            'failed_files': 0,
            'start_time': time.time()
        })
        
        successful_downloads = 0
        failed_downloads = 0
        total_size = 0
        
        # FIXED: Download words with proper error handling
        for verse_id, word_count in ayah_word_mapping.items():
            if start_verse and verse_id < start_verse:
                continue
            if end_verse and verse_id > end_verse:
                break
            
            verse_start_word = start_word if verse_id == start_verse else 1
            verse_end_word = end_word if verse_id == end_verse else word_count
            
            self.logger.info(f"Processing verse {verse_id}: words {verse_start_word}-{verse_end_word}")
            
            # Track consecutive 404 errors for this verse
            consecutive_404s = 0
            max_consecutive_404s = 5  # Stop trying after 5 consecutive 404s
            
            for word_id in range(verse_start_word, verse_end_word + 1):
                # Check if file already exists
                file_path = self._get_file_path(surah_id, surah_name, verse_id, word_id)
                
                if self._check_file_exists(file_path):
                    self.logger.info(f"File already exists: {file_path}")
                    successful_downloads += 1
                    total_size += os.path.getsize(file_path)
                    self.download_state['completed_files'] += 1
                    consecutive_404s = 0  # Reset 404 counter
                    self._update_progress(
                        self.download_state['completed_files'], 
                        total_files,
                        f"Already exists: {surah_id:03d}_{verse_id:03d}_{word_id:03d}",
                        surah_id, verse_id, word_id
                    )
                    continue
                
                # Try to download the word
                success, size = await self._download_word_with_retry(session, surah_id, verse_id, word_id, file_path)
                
                if success:
                    successful_downloads += 1
                    total_size += size
                    self.download_state['completed_files'] += 1
                    self.download_state['last_successful_file'] = file_path
                    consecutive_404s = 0  # Reset 404 counter
                    
                    # Save state for resume
                    self._save_download_state(surah_id, verse_id, word_id)
                    
                    self.logger.info(f"Downloaded: {surah_id:03d}_{verse_id:03d}_{word_id:03d}")
                else:
                    failed_downloads += 1
                    self.download_state['failed_files'] += 1
                    consecutive_404s += 1
                    
                    self.logger.warning(f"Failed to download: {surah_id:03d}_{verse_id:03d}_{word_id:03d}")
                    
                    # FIXED: If we get too many consecutive 404s, move to next verse
                    if consecutive_404s >= max_consecutive_404s:
                        self.logger.info(f"Too many consecutive 404s ({consecutive_404s}) for verse {verse_id}, moving to next verse")
                        break  # Break out of word loop, move to next verse
                
                # Update progress
                self._update_progress(
                    self.download_state['completed_files'], 
                    total_files,
                    f"Downloading: {surah_id:03d}_{verse_id:03d}_{word_id:03d}",
                    surah_id, verse_id, word_id
                )
        
        # Clean up state file on completion
        if successful_downloads > 0:
            state_file = os.path.join(self.download_dir, f"download_state_{surah_id}.json")
            if os.path.exists(state_file):
                try:
                    os.remove(state_file)
                except:
                    pass
        
        duration = time.time() - self.download_state['start_time']
        
        return {
            'success': True,
            'surah_id': surah_id,
            'surah_name': surah_name,
            'download_type': 'word_by_word',
            'total_files': total_files,
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'total_size': total_size,
            'duration': duration,
            'start_verse': start_verse,
            'end_verse': end_verse,
            'start_word': start_word,
            'end_word': end_word
        }
    
    async def download_verse_by_verse(self, session: aiohttp.ClientSession,
                                    surah_id: int, surah_name: str,
                                    start_verse: int = None, end_verse: int = None,
                                    resume: bool = True) -> Dict:
        """Download verse by verse with resume functionality"""
        
        # Load previous state if resuming
        if resume:
            state = self._load_download_state(surah_id)
            if start_verse is None:
                start_verse = state.get('last_verse', 1)
        
        # Get surah data
        surah = get_surah_by_id(surah_id, self.quran_data)
        if not surah:
            raise ValueError(f"Surah {surah_id} not found")
        
        ayah_range = surah['ayah_range']
        total_verses = ayah_range[1] - ayah_range[0] + 1
        
        if start_verse is None:
            start_verse = ayah_range[0]
        if end_verse is None:
            end_verse = ayah_range[1]
        
        total_files = end_verse - start_verse + 1
        
        self.download_state.update({
            'current_surah': surah_id,
            'total_files': total_files,
            'completed_files': 0,
            'failed_downloads': 0,
            'start_time': time.time()
        })
        
        successful_downloads = 0
        failed_downloads = 0
        total_size = 0
        
        # Download verses
        for verse_id in range(start_verse, end_verse + 1):
            # Check if file already exists
            file_path = self._get_file_path(surah_id, surah_name, verse_id)
            
            if self._check_file_exists(file_path):
                self.logger.info(f"Verse file already exists: {file_path}")
                successful_downloads += 1
                total_size += os.path.getsize(file_path)
                self.download_state['completed_files'] += 1
                self._update_progress(
                    self.download_state['completed_files'],
                    total_files,
                    f"Already exists: Verse {verse_id}",
                    surah_id, verse_id
                )
                continue
            
            # For verse-by-verse, we'll use the first word URL as the verse URL
            url = generate_audio_url(surah_id, verse_id, 1)
            
            try:
                success, size = await download_audio_async(session, url, file_path, self.logger)
                
                if success:
                    successful_downloads += 1
                    total_size += size
                    self.download_state['completed_files'] += 1
                    self.download_state['last_successful_file'] = file_path
                    
                    # Save state for resume
                    self._save_download_state(surah_id, verse_id)
                    
                    self.logger.info(f"Downloaded verse: {verse_id}")
                else:
                    failed_downloads += 1
                    self.download_state['failed_files'] += 1
                    self.logger.warning(f"Failed to download verse: {verse_id}")
                
                # Update progress
                self._update_progress(
                    self.download_state['completed_files'],
                    total_files,
                    f"Downloading verse: {verse_id}",
                    surah_id, verse_id
                )
                
            except Exception as e:
                failed_downloads += 1
                self.download_state['failed_files'] += 1
                self.logger.error(f"Error downloading verse {verse_id}: {e}")
        
        # Clean up state file on completion
        if successful_downloads > 0:
            state_file = os.path.join(self.download_dir, f"download_state_{surah_id}.json")
            if os.path.exists(state_file):
                try:
                    os.remove(state_file)
                except:
                    pass
        
        duration = time.time() - self.download_state['start_time']
        
        return {
            'success': True,
            'surah_id': surah_id,
            'surah_name': surah_name,
            'download_type': 'verse_by_verse',
            'total_files': total_files,
            'successful_downloads': successful_downloads,
            'failed_downloads': failed_downloads,
            'total_size': total_size,
            'duration': duration,
            'start_verse': start_verse,
            'end_verse': end_verse
        }
    
    async def download_surah_async(self, surah_id: int, custom_dir: Optional[str] = None) -> Dict:
        """Original download method for backward compatibility"""
        return await self.download_surah_enhanced_async(surah_id, 'word_by_word', custom_dir=custom_dir)
    
    async def download_surah_enhanced_async(self, surah_id: int, download_type: str = 'word_by_word',
                                          start_verse: int = None, end_verse: int = None,
                                          start_word: int = None, end_word: int = None,
                                          resume: bool = True, custom_dir: Optional[str] = None) -> Dict:
        """Enhanced download with flexible options"""
        
        # Get surah data
        surah = get_surah_by_id(surah_id, self.quran_data)
        if not surah:
            raise ValueError(f"Surah {surah_id} not found")
        
        surah_name = surah['name_en']
        self.logger.info(f"Starting {download_type} download for Surah {surah_id}: {surah_name}")
        
        # Use custom directory if provided
        if custom_dir:
            self.download_dir = custom_dir
            os.makedirs(custom_dir, exist_ok=True)
        
        # Create async session
        connector = aiohttp.TCPConnector(limit=CONCURRENT_DOWNLOADS)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            if download_type == 'word_by_word':
                result = await self.download_word_by_word(
                    session, surah_id, surah_name, start_verse, end_verse, 
                    start_word, end_word, resume
                )
            elif download_type == 'verse_by_verse':
                result = await self.download_verse_by_verse(
                    session, surah_id, surah_name, start_verse, end_verse, resume
                )
            else:
                raise ValueError(f"Invalid download type: {download_type}")
        
        self.logger.info(f"Download completed: {result['successful_downloads']} successful, {result['failed_downloads']} failed")
        
        return result
    
    def download_surah(self, surah_id: int, download_type: str = 'word_by_word',
                      start_verse: int = None, end_verse: int = None,
                      start_word: int = None, end_word: int = None,
                      resume: bool = True, custom_dir: Optional[str] = None) -> Dict:
        """Enhanced synchronous wrapper for download"""
        return asyncio.run(self.download_surah_enhanced_async(
            surah_id, download_type, start_verse, end_verse, start_word, end_word, resume, custom_dir
        ))
    
    def get_surah_list(self) -> List[Dict]:
        """Get list of all surahs with enhanced information"""
        return [
            {
                'id': surah['surah_id'],
                'name_en': surah['name_en'],
                'name_ar': surah['name_ar'],
                'ayah_count': surah['ayah_range'][1] - surah['ayah_range'][0] + 1,
                'word_count': surah['word_range'][1] - surah['word_range'][0] + 1,
                'ayah_range': surah['ayah_range'],
                'word_range': surah['word_range']
            }
            for surah in self.quran_data
        ]
    
    def get_download_stats(self) -> Dict:
        """Get current download statistics"""
        return {
            'current_surah': self.download_state.get('current_surah'),
            'current_verse': self.download_state.get('current_verse'),
            'current_word': self.download_state.get('current_word'),
            'total_files': self.download_state.get('total_files', 0),
            'completed_files': self.download_state.get('completed_files', 0),
            'failed_files': self.download_state.get('failed_files', 0),
            'last_successful_file': self.download_state.get('last_successful_file'),
            'start_time': self.download_state.get('start_time'),
            'total_requests': self.stats.total_requests,
            'successful_downloads': self.stats.successful_downloads,
            'failed_downloads': self.stats.failed_downloads,
            'total_size': self.stats.total_size,
            'formatted_size': format_file_size(self.stats.total_size),
            'duration': self.stats.get_duration(),
            'formatted_duration': format_duration(self.stats.get_duration()),
            'speed': self.stats.get_speed(),
            'average_speed': self.stats.get_average_speed()
        }
    
    def get_surah_progress(self, surah_id: int) -> Dict:
        """Get progress for a specific surah"""
        surah_folder = None
        for surah in self.quran_data:
            if surah['surah_id'] == surah_id:
                surah_folder = self._get_surah_folder_name(surah_id, surah['name_en'])
                break
        
        if not surah_folder:
            return {'error': f'Surah {surah_id} not found'}
        
        surah_path = os.path.join(self.download_dir, surah_folder)
        
        if not os.path.exists(surah_path):
            return {'downloaded_files': 0, 'total_estimated': 0}
        
        downloaded_files = len([f for f in os.listdir(surah_path) if f.endswith('.mp3')])
        
        # Estimate total files based on surah data
        surah = get_surah_by_id(surah_id, self.quran_data)
        if surah:
            ayah_range = surah['ayah_range']
            word_range = surah['word_range']
            total_ayahs = ayah_range[1] - ayah_range[0] + 1
            total_words = word_range[1] - word_range[0] + 1
            estimated_total = total_words  # Assuming word-by-word download
        else:
            estimated_total = 0
        
        return {
            'downloaded_files': downloaded_files,
            'total_estimated': estimated_total,
            'progress_percentage': (downloaded_files / estimated_total * 100) if estimated_total > 0 else 0
        }
