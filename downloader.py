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
        self.quran_data = self._load_enhanced_quran_data()
        self.surah_names = self._load_surah_names()
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
    
    def _load_enhanced_quran_data(self) -> Dict:
        """Load enhanced Quran data from JSON file"""
        try:
            with open("quran_data.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error("quran_data.json not found")
            return {"surahs": []}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in quran_data.json: {e}")
            return {"surahs": []}
    
    def _load_surah_names(self) -> Dict:
        """Load surah names from JSON file"""
        try:
            with open("quran_surah_names.json", 'r', encoding='utf-8') as f:
                surah_list = json.load(f)
                return {surah['id']: surah for surah in surah_list}
        except FileNotFoundError:
            self.logger.error("quran_surah_names.json not found")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format in quran_surah_names.json: {e}")
            return {}
    
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = "", 
                        surah_id: int = None, verse_id: int = None, word_id: int = None):
        """Update progress and call callback if set"""
        progress = (current / total * 100) if total > 0 else 0
        
        self.download_state.update({
            'current_surah': surah_id,
            'current_verse': verse_id,
            'current_word': word_id,
            'completed_files': current,
            'total_files': total
        })
        
        if self.progress_callback:
            self.progress_callback(progress, current, total, message, surah_id, verse_id, word_id)
    
    def get_surah_list(self) -> List[Dict]:
        """Get list of all surahs with enhanced information"""
        surah_list = []
        
        for surah_data in self.quran_data.get('surahs', []):
            surah_id = int(surah_data['surah_id'])
            surah_name_data = self.surah_names.get(surah_data['surah_id'], {})
            
            surah_info = {
                'id': surah_id,
                'name_en': surah_name_data.get('name_en', f'Surah {surah_id}'),
                'name_ar': surah_name_data.get('name_ar', ''),
                'ayah_count': surah_data['verse_count'],
                'word_count': surah_data['total_words'],
                'total_letters': surah_data.get('total_letters', 0),
                'ayah_range': (1, surah_data['verse_count']),
                'word_range': (1, surah_data['total_words']),
                'folder_id': surah_data['folder_id'],
                'verses': surah_data['verses']
            }
            surah_list.append(surah_info)
        
        return surah_list
    
    def get_surah_by_id(self, surah_id: int) -> Optional[Dict]:
        """Get surah data by ID"""
        for surah_data in self.quran_data.get('surahs', []):
            if int(surah_data['surah_id']) == surah_id:
                surah_name_data = self.surah_names.get(surah_data['surah_id'], {})
                return {
                    'id': surah_id,
                    'name_en': surah_name_data.get('name_en', f'Surah {surah_id}'),
                    'name_ar': surah_name_data.get('name_ar', ''),
                    'ayah_count': surah_data['verse_count'],
                    'word_count': surah_data['total_words'],
                    'total_letters': surah_data.get('total_letters', 0),
                    'ayah_range': (1, surah_data['verse_count']),
                    'word_range': (1, surah_data['total_words']),
                    'folder_id': surah_data['folder_id'],
                    'verses': surah_data['verses']
                }
        return None
    
    def estimate_files_for_range(self, surah_id: int, download_type: str, 
                                start_verse: int = None, end_verse: int = None,
                                start_word: int = None, end_word: int = None) -> int:
        """Estimate number of files for given range"""
        surah_data = self.get_surah_by_id(surah_id)
        if not surah_data:
            return 0
        
        if download_type == "verse_by_verse":
            # For verse-by-verse, one file per verse
            if start_verse and end_verse:
                return end_verse - start_verse + 1
            else:
                return surah_data['ayah_count']
        
        elif download_type == "word_by_word":
            # For word-by-word, count words in specified verses
            total_words = 0
            verses = surah_data['verses']
            
            start_verse = start_verse or 1
            end_verse = end_verse or surah_data['ayah_count']
            
            for verse in verses:
                verse_id = verse['verse_id']
                if start_verse <= verse_id <= end_verse:
                    verse_words = verse['verse_words']
                    if start_word and end_word:
                        # Limit words within verse
                        word_start = max(1, start_word)
                        word_end = min(verse_words, end_word)
                        if word_start <= word_end:
                            total_words += (word_end - word_start + 1)
                    else:
                        total_words += verse_words
            
            return total_words
        
        return 0
    
    def get_surah_progress(self, surah_id: int) -> Dict:
        """Get download progress for a specific surah - FIXED to return percentage (0-100)"""
        surah_folder = f"{surah_id:03d}_{self.surah_names.get(str(surah_id).zfill(3), {}).get('name_en', f'Surah_{surah_id}').replace(' ', '_').replace("'", '').replace('-', '_')}"
        surah_dir = os.path.join(self.download_dir, surah_folder)
        
        if not os.path.exists(surah_dir):
            return {'downloaded_files': 0, 'total_files': 0, 'progress': 0}
        
        downloaded_files = len([f for f in os.listdir(surah_dir) if f.endswith('.mp3')])
        total_files = self.estimate_files_for_range(surah_id, "word_by_word")
        
        # FIXED: Return progress as percentage (0-100) instead of decimal (0-1)
        progress_percentage = (downloaded_files / total_files * 100) if total_files > 0 else 0
        
        return {
            'downloaded_files': downloaded_files,
            'total_files': total_files,
            'progress': progress_percentage  # Return as percentage 0-100
        }
    
    async def download_surah_enhanced_async(self, surah_id: int, download_type: str = "word_by_word",
                                          start_verse: int = None, end_verse: int = None,
                                          start_word: int = None, end_word: int = None,
                                          resume: bool = True, custom_dir: str = None) -> Dict:
        """Enhanced async download with better error handling and 404 management"""
        
        start_time = time.time()
        surah_data = self.get_surah_by_id(surah_id)
        
        if not surah_data:
            raise ValueError(f"Surah {surah_id} not found")
        
        surah_name = surah_data['name_en']
        folder_id = surah_data['folder_id']
        
        # Create download directory
        if custom_dir:
            download_dir = custom_dir
        else:
            surah_folder = f"{surah_id:03d}_{surah_name.replace(' ', '_').replace("'", '').replace('-', '_')}"
            download_dir = os.path.join(self.download_dir, surah_folder)
        
        os.makedirs(download_dir, exist_ok=True)
        
        # Calculate total files and setup ranges
        total_files = self.estimate_files_for_range(surah_id, download_type, start_verse, end_verse, start_word, end_word)
        self.download_state.update({
            'total_files': total_files,
            'completed_files': 0,
            'failed_files': 0,
            'start_time': start_time
        })
        
        self.logger.info(f"Starting download for Surah {surah_id}: {surah_name}")
        self.logger.info(f"Estimated {total_files} audio files to download")
        
        successful_downloads = 0
        failed_downloads = 0
        total_size = 0
        consecutive_404s = 0
        max_consecutive_404s = 5  # Stop after 5 consecutive 404s in a verse
        
        # Process verses
        verses = surah_data['verses']
        start_verse = start_verse or 1
        end_verse = end_verse or surah_data['ayah_count']
        
        for verse_data in verses:
            verse_id = verse_data['verse_id']
            
            if verse_id < start_verse or verse_id > end_verse:
                continue
            
            verse_words = verse_data['verse_words']
            self.logger.info(f"Processing Ayah {verse_id}: {verse_words} words")
            
            consecutive_404s = 0  # Reset for each verse
            
            # Process words in verse
            word_start = start_word or 1
            word_end = end_word or verse_words
            
            for word_id in range(word_start, min(word_end + 1, verse_words + 1)):
                # Generate URL
                url = f"https://audios.quranwbw.com/words/{folder_id}/{surah_id:03d}_{verse_id:03d}_{word_id:03d}.mp3"
                
                # Check if file already exists (resume functionality)
                filename = f"{surah_id:03d}_{verse_id:03d}_{word_id:03d}.mp3"
                file_path = os.path.join(download_dir, filename)
                
                if resume and os.path.exists(file_path):
                    successful_downloads += 1
                    total_size += os.path.getsize(file_path)
                    self._update_progress(successful_downloads + failed_downloads, total_files, 
                                        f"Resumed: {filename}", surah_id, verse_id, word_id)
                    continue
                
                # Download file
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                
                                successful_downloads += 1
                                total_size += len(content)
                                consecutive_404s = 0  # Reset counter on success
                                
                                self._update_progress(successful_downloads + failed_downloads, total_files, 
                                                    f"Downloaded: {filename}", surah_id, verse_id, word_id)
                                
                            elif response.status == 404:
                                consecutive_404s += 1
                                failed_downloads += 1
                                self.logger.warning(f"HTTP 404 for {url}")
                                
                                # If too many consecutive 404s, skip remaining words in this verse
                                if consecutive_404s >= max_consecutive_404s:
                                    self.logger.warning(f"404 error detected in Ayah {verse_id}, skipping remaining words in this verse")
                                    break
                                
                            else:
                                failed_downloads += 1
                                self.logger.error(f"HTTP {response.status} for {url}")
                            
                            self._update_progress(successful_downloads + failed_downloads, total_files, 
                                                f"Processing: {filename}", surah_id, verse_id, word_id)
                
                except Exception as e:
                    failed_downloads += 1
                    self.logger.error(f"Error downloading {url}: {str(e)}")
                    self._update_progress(successful_downloads + failed_downloads, total_files, 
                                        f"Error: {filename}", surah_id, verse_id, word_id)
            
            # Log verse completion
            downloaded_words = min(word_end, verse_words) - word_start + 1 - consecutive_404s
            self.logger.info(f"Downloaded {downloaded_words} words for Ayah {verse_id}")
        
        # Final statistics
        duration = time.time() - start_time
        
        result = {
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
            'duration': duration
        }
        
        self.logger.info(f"Download completed: {successful_downloads} successful, {failed_downloads} failed")
        self.logger.info(f"Total size: {format_file_size(total_size)}")
        self.logger.info(f"Duration: {format_duration(duration)}")
        
        return result
    
    def download_surah_enhanced(self, surah_id: int, download_type: str = "word_by_word",
                               start_verse: int = None, end_verse: int = None,
                               start_word: int = None, end_word: int = None,
                               resume: bool = True, custom_dir: str = None) -> Dict:
        """Enhanced synchronous wrapper for download"""
        return asyncio.run(self.download_surah_enhanced_async(
            surah_id, download_type, start_verse, end_verse, start_word, end_word, resume, custom_dir
        ))
    
    def get_download_stats(self) -> Dict:
        """Get current download statistics"""
        return {
            'current_surah': self.download_state.get('current_surah'),
            'current_verse': self.download_state.get('current_verse'),
            'current_word': self.download_state.get('current_word'),
            'total_files': self.download_state.get('total_files', 0),
            'completed_files': self.download_state.get('completed_files', 0),
            'failed_files': self.download_state.get('failed_files', 0),
            'start_time': self.download_state.get('start_time'),
            'last_successful_file': self.download_state.get('last_successful_file')
        }
