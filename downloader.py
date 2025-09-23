"""
Main downloader class for Quran Audio Scraper
"""

import os
import asyncio
import aiohttp
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
    """Main class for downloading Quran audio files"""
    
    def __init__(self, download_dir: str = DEFAULT_DOWNLOAD_DIR, log_dir: str = "logs"):
        self.download_dir = download_dir
        self.log_dir = log_dir
        self.logger = setup_logging(log_dir)
        self.quran_data = load_quran_data()
        self.stats = DownloadStats()
        self.progress_callback: Optional[Callable] = None
        
        # Create download directory
        os.makedirs(download_dir, exist_ok=True)
    
    def set_progress_callback(self, callback: Callable):
        """Set progress callback function"""
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = ""):
        """Update progress if callback is set"""
        if self.progress_callback:
            try:
                progress = get_download_progress(current, total)
                self.progress_callback(progress, current, total, message)
            except Exception as e:
                # Log the error but don't crash the download
                self.logger.error(f"Progress callback error: {e}")
    
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
    
    async def download_surah_async(self, surah_id: int, custom_dir: Optional[str] = None) -> Dict:
        """Download all audio files for a specific surah asynchronously"""
        
        # Get surah data
        surah = get_surah_by_id(surah_id, self.quran_data)
        if not surah:
            raise ValueError(f"Surah with ID {surah_id} not found")
        
        self.logger.info(f"Starting download for Surah {surah_id}: {surah['name_en']}")
        
        # Setup directories
        base_dir = custom_dir if custom_dir else self.download_dir
        surah_dir = create_download_directory(base_dir, surah_id)
        
        # Initialize stats
        self.stats.start()
        
        # Get ayah-word mapping
        ayah_word_mapping = self._get_ayah_word_mapping(surah_id)
        
        # Calculate total estimated files
        total_estimated = sum(ayah_word_mapping.values())
        self.logger.info(f"Estimated {total_estimated} audio files to download")
        
        # Create async session
        connector = aiohttp.TCPConnector(limit=CONCURRENT_DOWNLOADS)
        timeout = aiohttp.ClientTimeout(total=30)
        
        metadata = []
        current_file = 0
        verses_processed = 0
        verses_with_404s = 0
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Process each ayah
            for ayah_id, word_count in ayah_word_mapping.items():
                verses_processed += 1
                
                self.logger.info(f"Processing Ayah {ayah_id}: {word_count} words")
                
                # Try to download words for this ayah
                ayah_successful = 0
                ayah_failed = 0
                found_404 = False
                
                # Download words for this ayah (word IDs start from 1 for each ayah)
                for word_position in range(1, word_count + 1):
                    url = generate_audio_url(surah_id, ayah_id, word_position)
                    filename = f"{surah_id:03d}_{ayah_id:03d}_{word_position:03d}.mp3"
                    file_path = os.path.join(surah_dir, filename)
                    
                    # Try to download this word
                    success, size = await download_audio_async(session, url, file_path, self.logger)
                    
                    if success:
                        metadata.append(create_audio_metadata(surah_id, ayah_id, word_position, filename))
                        self.stats.successful_downloads += 1
                        self.stats.total_size += size
                        ayah_successful += 1
                    else:
                        self.stats.failed_downloads += 1
                        ayah_failed += 1
                        
                        # Check if this is a 404 error (word doesn't exist)
                        # If we get a 404, it means we've reached the end of valid words for this ayah
                        if ayah_failed >= 3:  # Stop after 3 consecutive failures
                            found_404 = True
                            self.logger.warning(f"404 error detected in Ayah {ayah_id}, skipping remaining words in this verse")
                            break
                    
                    self.stats.total_requests += 1
                    current_file += 1
                    
                    # Update progress
                    self._update_progress(current_file, total_estimated, f"Downloading Ayah {ayah_id}, Word {word_position}")
                
                if found_404:
                    verses_with_404s += 1
                
                self.logger.info(f"Downloaded {ayah_successful} words for Ayah {ayah_id}")
        
        # End stats
        self.stats.end()
        
        self.logger.info(f"Download completed: {self.stats.successful_downloads} successful, {self.stats.failed_downloads} failed")
        self.logger.info(f"Verses processed: {verses_processed}, Verses with 404s: {verses_with_404s}")
        
        # Create ZIP file
        self._update_progress(100, 100, "Creating ZIP file...")
        zip_path = create_zip_file(surah_dir, surah_id, metadata, self.logger)
        
        # Cleanup temp files
        cleanup_temp_files(surah_dir, self.logger)
        
        # Final progress update
        self._update_progress(100, 100, "Download completed!")
        
        return {
            'success': True,
            'surah_id': surah_id,
            'surah_name': surah['name_en'],
            'zip_path': zip_path,
            'total_files': self.stats.total_requests,
            'successful_downloads': self.stats.successful_downloads,
            'failed_downloads': self.stats.failed_downloads,
            'total_size': self.stats.total_size,
            'duration': self.stats.get_duration(),
            'verses_processed': verses_processed,
            'verses_with_404s': verses_with_404s,
            'metadata': metadata
        }
    
    def download_surah(self, surah_id: int, custom_dir: Optional[str] = None) -> Dict:
        """Download all audio files for a specific surah (synchronous wrapper)"""
        return asyncio.run(self.download_surah_async(surah_id, custom_dir))
    
    def get_surah_list(self) -> List[Dict]:
        """Get list of all surahs"""
        return [
            {
                'id': surah['surah_id'],
                'name_en': surah['name_en'],
                'name_ar': surah['name_ar'],
                'ayah_count': surah['ayah_range'][1] - surah['ayah_range'][0] + 1
            }
            for surah in self.quran_data
        ]
    
    def get_download_stats(self) -> Dict:
        """Get current download statistics"""
        return {
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
