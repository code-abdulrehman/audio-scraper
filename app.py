"""
Streamlit application for Quran Audio Scraper
"""

import streamlit as st
import os
import json
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import queue
import sys

from downloader import QuranAudioDownloader
from constants import MESSAGES, DEFAULT_DOWNLOAD_DIR
from utils import format_file_size, format_duration


# Page configuration
st.set_page_config(
    page_title="Quran Audio Scraper",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E8B57;
        margin-bottom: 2rem;
    }
    .stats-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .progress-container {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .log-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        max-height: 400px;
        overflow-y: auto;
    }
    footer {
        display: none;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'downloader' not in st.session_state:
        st.session_state.downloader = None
    if 'download_in_progress' not in st.session_state:
        st.session_state.download_in_progress = False
    if 'download_progress' not in st.session_state:
        st.session_state.download_progress = 0
    if 'download_message' not in st.session_state:
        st.session_state.download_message = ""
    if 'download_stats' not in st.session_state:
        st.session_state.download_stats = {}
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'progress_queue' not in st.session_state:
        st.session_state.progress_queue = queue.Queue()
    if 'download_thread' not in st.session_state:
        st.session_state.download_thread = None


def create_downloader(download_dir: str, log_dir: str):
    """Create downloader instance"""
    try:
        return QuranAudioDownloader(download_dir, log_dir)
    except Exception as e:
        st.error(f"Failed to initialize downloader: {str(e)}")
        return None


def progress_callback(progress: float, current: int, total: int, message: str):
    """Progress callback for downloads - thread-safe"""
    try:
        # Use a simple approach - store in session state directly
        if hasattr(st.session_state, 'download_progress'):
            st.session_state.download_progress = progress
            st.session_state.download_message = f"{message} ({current}/{total})"
    except Exception as e:
        print(f"Progress callback error: {e}")


def download_surah_async(surah_id: int, download_dir: str):
    """Download surah in background thread"""
    try:
        # Create a new downloader instance in the thread
        downloader = QuranAudioDownloader(download_dir, "logs")
        downloader.set_progress_callback(progress_callback)
        
        # Run the download
        result = downloader.download_surah(surah_id, download_dir)
        
        # Store result in session state
        st.session_state.download_stats = result
        st.session_state.download_in_progress = False
        st.session_state.download_message = "Download completed!"
        
    except Exception as e:
        st.session_state.download_in_progress = False
        st.session_state.download_message = f"Download failed: {str(e)}"


def main():
    """Main application function"""
    
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🕌 Quran Audio Scraper</h1>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
        <style>
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #f8f9fa;
            color: #222;
            text-align: center;
            padding: 10px 0;
            font-size: 15px;
            z-index: 9999;
            border-top: 1px solid #e0e0e0;
        }
        .footer a {
            color: #228B22;
            text-decoration: underline;
            font-weight: 500;
        }
        </style>
        <div class="footer">
            © 2025 Quran Audio Scraper | Powered by <a href="https://github.com/code-abdulrehman">Abdulrehman</a>
        </div>
    """, unsafe_allow_html=True)
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        
        # Download directory selection
        download_dir = st.text_input(
            "Download Directory",
            value=DEFAULT_DOWNLOAD_DIR,
            help="Directory where audio files will be downloaded"
        )
        
        # Create downloader
        if st.button("Initialize Downloader"):
            st.session_state.downloader = create_downloader(download_dir, "logs")
            if st.session_state.downloader:
                st.success("Downloader initialized successfully!")
        
        # Show current stats
        if st.session_state.downloader:
            stats = st.session_state.downloader.get_download_stats()
            st.subheader("Current Stats")
            st.metric("Total Requests", stats['total_requests'])
            st.metric("Successful Downloads", stats['successful_downloads'])
            st.metric("Failed Downloads", stats['failed_downloads'])
            st.metric("Total Size", stats['formatted_size'])
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["Download", "Progress", "Logs"])
    
    with tab1:
        st.header("Download Audio Files")
        
        if not st.session_state.downloader:
            st.warning("Please initialize the downloader first using the sidebar.")
            return
        
        # Get surah list
        surah_list = st.session_state.downloader.get_surah_list()
        
        # Create DataFrame for better display
        df = pd.DataFrame(surah_list)
        
        # Surah selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_surah = st.selectbox(
                MESSAGES['select_surah'],
                options=df.index,
                format_func=lambda x: f"{df.iloc[x]['id']:03d} - {df.iloc[x]['name_en']} ({df.iloc[x]['name_ar']})"
            )
        
        with col2:
            st.metric("Ayah Count", df.iloc[selected_surah]['ayah_count'])
        
        # Download button
        if st.button("Download Audio Files", disabled=st.session_state.download_in_progress):
            surah_id = df.iloc[selected_surah]['id']
            surah_name = df.iloc[selected_surah]['name_en']
            
            st.session_state.download_in_progress = True
            st.session_state.download_progress = 0
            st.session_state.download_message = "Starting download..."
            
            # Start download in background thread
            thread = threading.Thread(
                target=download_surah_async,
                args=(surah_id, download_dir)
            )
            thread.daemon = True
            thread.start()
            st.session_state.download_thread = thread
            
            st.success(f"Download started for Surah {surah_id}: {surah_name}")
    
    with tab2:
        st.header("Download Progress")
        
        if st.session_state.download_in_progress:
            st.markdown('<div class="progress-container">', unsafe_allow_html=True)
            
            # Progress bar
            progress_bar = st.progress(st.session_state.download_progress / 100)
            
            # Progress text
            st.write(f"**Progress:** {st.session_state.download_progress:.1f}%")
            st.write(f"**Status:** {st.session_state.download_message}")
            
            # Check if thread is still alive
            if st.session_state.download_thread and not st.session_state.download_thread.is_alive():
                st.session_state.download_in_progress = False
            
            # Auto-refresh every 3 seconds
            time.sleep(3)
            st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.download_stats:
            st.markdown('<div class="stats-container">', unsafe_allow_html=True)
            
            stats = st.session_state.download_stats
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Surah ID", stats['surah_id'])
                st.metric("Surah Name", stats['surah_name'])
            
            with col2:
                st.metric("Total Files", stats['total_files'])
                st.metric("Successful", stats['successful_downloads'])
            
            with col3:
                st.metric("Failed", stats['failed_downloads'])
                st.metric("Total Size", format_file_size(stats['total_size']))
            
            with col4:
                st.metric("Duration", format_duration(stats['duration']))
                st.metric("ZIP File", os.path.basename(stats['zip_path']))
            
            # Download link
            if os.path.exists(stats['zip_path']):
                with open(stats['zip_path'], 'rb') as f:
                    st.download_button(
                        label="Download ZIP File",
                        data=f.read(),
                        file_name=os.path.basename(stats['zip_path']),
                        mime="application/zip"
                    )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        else:
            st.info("No download in progress. Start a download from the Download tab.")
    
    with tab3:
        st.header("Download Logs")
        
        # Log file selection
        log_dir = "logs"
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            
            if log_files:
                selected_log = st.selectbox("Select Log File", log_files)
                log_path = os.path.join(log_dir, selected_log)
                
                # Display log content
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    st.markdown('<div class="log-container">', unsafe_allow_html=True)
                    st.text(log_content)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Download log button
                    st.download_button(
                        label="Download Log File",
                        data=log_content,
                        file_name=selected_log,
                        mime="text/plain"
                    )
                
                except Exception as e:
                    st.error(f"Error reading log file: {str(e)}")
            else:
                st.info("No log files found.")
        else:
            st.info("Log directory not found.")


if __name__ == "__main__":
    main()
