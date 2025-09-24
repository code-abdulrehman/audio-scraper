"""
Streamlit application for Quran Audio Scraper - Compact Version
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
import re
from urllib.parse import urlparse

from downloader import QuranAudioDownloader
from constants import MESSAGES, DEFAULT_DOWNLOAD_DIR
from utils import format_file_size, format_duration
from log_parser import render_log_parser
from statistics_component import render_statistics_component
from ui_components import (
    render_compact_download_options, 
    render_compact_progress_display, 
    render_compact_results,
    render_compact_sidebar
)


# Page configuration - Force light mode
st.set_page_config(
    page_title="Quran Audio Scraper",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FIXED CSS - Using proper Streamlit CSS injection with higher specificity
st.markdown("""
<style>
    /* Force light mode with higher specificity */
    .stApp {
        color: #262730 !important;
        background-color: #ffffff !important;
    }
    
    .stApp > header {
        background-color: #ffffff !important;
    }
    
    .stSidebar {
        background-color: #f8f9fa !important;
    }
    
    .stSidebar .stSelectbox > div > div {
        background-color: #ffffff !important;
    }
    
    .stSidebar .stTextInput > div > div > input {
        background-color: #ffffff !important;
    }
    
    .stSidebar .stButton > button {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d1d5db !important;
    }
    
    .stSidebar .stButton > button:hover {
        background-color: #f3f4f6 !important;
    }
    
    /* FIXED: Custom container styles with higher specificity */
    .main-header {
        text-align: center !important;
        color: #2E8B57 !important;
        margin-bottom: 2rem !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1) !important;
        font-size: 2.5rem !important;
        font-weight: bold !important;
    }
    
    .stats-container {
        background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf6 100%) !important;
        padding: 1.5rem !important;
        border-radius: 1rem !important;
        margin: 1rem 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    .progress-container {
        background: linear-gradient(135deg, #e8f4fd 0%, #e3f2fd 100%) !important;
        padding: 1.5rem !important;
        border-radius: 1rem !important;
        margin: 1rem 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        border: 1px solid #bbdefb !important;
    }
    
    .log-container {
        background-color: #f8f9fa !important;
        padding: 1rem !important;
        border-radius: 0.5rem !important;
        max-height: 400px !important;
        overflow-y: auto !important;
        border: 1px solid #dee2e6 !important;
    }
    
    .options-container {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%) !important;
        padding: 1.5rem !important;
        border-radius: 1rem !important;
        margin: 1rem 0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        border: 1px solid #ffc107 !important;
    }
    
    .metric-success {
        color: #28a745 !important;
        font-weight: bold !important;
    }
    
    .metric-danger {
        color: #dc3545 !important;
        font-weight: bold !important;
    }
    
    .metric-warning {
        color: #ffc107 !important;
        font-weight: bold !important;
    }
    
    .metric-info {
        color: #17a2b8 !important;
        font-weight: bold !important;
    }
    
    .progress-text {
        font-size: 1.2rem !important;
        font-weight: bold !important;
        color: #2E8B57 !important;
    }
    
    .status-text {
        font-size: 1rem !important;
        color: #666 !important;
        font-style: italic !important;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #28a745 0%, #20c997 50%, #17a2b8 100%) !important;
    }
    
    /* Force light mode for all components */
    .stSelectbox > div > div {
        background-color: #ffffff !important;
    }
    
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
    }
    
    .stButton > button {
        background-color: #ffffff !important;
        color: #262730 !important;
        border: 1px solid #d1d5db !important;
    }
    
    .stButton > button:hover {
        background-color: #f3f4f6 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff !important;
        color: #262730 !important;
        padding: 0.5rem 1rem !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f6 !important;
    }
    
    /* Hide Streamlit footer */
    footer {
        display: none !important;
    }
    
    /* Custom footer styling */
    .custom-footer {
        position: fixed !important;
        left: 0 !important;
        bottom: 0 !important;
        width: 100% !important;
        background-color: #f8f9fa !important;
        color: #222 !important;
        text-align: center !important;
        padding: 10px 0 !important;
        font-size: 15px !important;
        z-index: 9999 !important;
        border-top: 1px solid #e0e0e0 !important;
    }
    
    .custom-footer a {
        color: #228B22 !important;
        text-decoration: underline !important;
        font-weight: 500 !important;
    }
    [data-baseweb="tab-panel"] {
        margin-top: 1rem;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 10px;
        background: #f7f7f7;
    }
 
    .e1nzilvr3 {
        display: none;
     }
     [data-testid="stHorizontalBlock"] {
        align-items: flex-end !important;
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
    if 'current_url' not in st.session_state:
        st.session_state.current_url = "https://audios.quranwbw.com/words/"
    if 'url_history' not in st.session_state:
        st.session_state.url_history = []
    if 'download_type' not in st.session_state:
        st.session_state.download_type = "word_by_word"
    if 'download_options' not in st.session_state:
        st.session_state.download_options = {
            'start_verse': None,
            'end_verse': None,
            'start_word': None,
            'end_word': None,
            'resume': True
        }
    if 'current_surah' not in st.session_state:
        st.session_state.current_surah = None
    if 'current_verse' not in st.session_state:
        st.session_state.current_verse = None
    if 'current_word' not in st.session_state:
        st.session_state.current_word = None


def create_downloader(download_dir: str, log_dir: str):
    """Create downloader instance"""
    try:
        return QuranAudioDownloader(download_dir, log_dir)
    except Exception as e:
        st.error(f"Failed to initialize downloader: {str(e)}")
        return None


def enhanced_progress_callback(progress: float, current: int, total: int, message: str = "",
                              surah_id: int = None, verse_id: int = None, word_id: int = None):
    """progress callback for downloads"""
    try:
        if hasattr(st.session_state, 'download_progress'):
            st.session_state.download_progress = progress
            st.session_state.download_message = message
            st.session_state.current_surah = surah_id
            st.session_state.current_verse = verse_id
            st.session_state.current_word = word_id
    except Exception as e:
        print(f"progress callback error: {e}")


def download_surah_enhanced_async(surah_id: int, download_dir: str, download_type: str,
                                start_verse: int = None, end_verse: int = None,
                                start_word: int = None, end_word: int = None,
                                resume: bool = True):
    """Download surah with enhanced options in background thread"""
    try:
        # Create a new downloader instance in the thread
        downloader = QuranAudioDownloader(download_dir, "logs")
        downloader.set_progress_callback(enhanced_progress_callback)
        
        # Run the download
        result = downloader.download_surah_enhanced(
            surah_id=surah_id,
            download_type=download_type,
            start_verse=start_verse,
            end_verse=end_verse,
            start_word=start_word,
            end_word=end_word,
            resume=resume
        )
        
        # Store result in session state
        st.session_state.download_stats = result
        st.session_state.download_in_progress = False
        st.session_state.download_message = "Download completed!"
        
    except Exception as e:
        st.session_state.download_in_progress = False
        st.session_state.download_message = f"Download failed: {str(e)}"


def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def main():
    """Main application function"""
    
    # Initialize session state
    initialize_session_state()
    
    # FIXED: Header with proper CSS class
    st.markdown('<h1 class="main-header">🕌 Quran Audio Scraper</h1>', unsafe_allow_html=True)

    # FIXED: URL Input Section using Streamlit containers instead of raw HTML
    with st.expander("🌐 Audio URL Configuration", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            url_input = st.text_input(
                "Base Audio URL",
                value=st.session_state.current_url,
                placeholder="https://audios.quranwbw.com/words/",
                help="Enter the base URL for audio files"
            )
            
            if url_input != st.session_state.current_url:
                st.session_state.current_url = url_input
                if url_input and url_input not in st.session_state.url_history:
                    st.session_state.url_history.append(url_input)
        
        with col2:
            st.write("") # Spacing
            if st.button("🔄 Validate URL", type="secondary"):
                if validate_url(st.session_state.current_url):
                    st.success("✅ URL is valid!")
                else:
                    st.error("❌ Invalid URL format")
        
        # URL History
        if st.session_state.url_history:
            st.write("**Recent URLs:**")
            for i, url in enumerate(reversed(st.session_state.url_history[-5:])):  # Show last 5
                if st.button(f"📎 {url[:50]}{'...' if len(url) > 50 else ''}", key=f"url_{i}"):
                    st.session_state.current_url = url
                    st.rerun()

    # FIXED: Footer using proper CSS class
    st.markdown("""
        <div class="custom-footer">
            © 2025 Quran Audio Scraper | Powered by <a href="https://github.com/code-abdulrehman">Abdulrehman</a>
        </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    download_dir = render_compact_sidebar(st.session_state.downloader, DEFAULT_DOWNLOAD_DIR)
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["📥 Download", "📋 Logs", "📊 Statistics"])
    
    with tab1:
        st.header("📥 Quran Audio Download")
        
        if not st.session_state.downloader:
            st.warning("⚠️ Please initialize the enhanced downloader first using the sidebar.")
            return
        
        # Render compact download options
        result = render_compact_download_options(st.session_state.downloader, download_dir)
        if result[0] is None:  # Error in validation
            return
        
        surah_id, surah_name, download_type, download_dir = result
        
        # Download Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start Download", 
                        disabled=st.session_state.download_in_progress,
                        type="primary",
                        use_container_width=True):
                
                st.session_state.download_in_progress = True
                st.session_state.download_progress = 0
                st.session_state.download_message = "Starting enhanced download..."
                
                # Start download in background thread
                thread = threading.Thread(
                    target=download_surah_enhanced_async,
                    args=(
                        surah_id, download_dir, download_type,
                        st.session_state.download_options['start_verse'],
                        st.session_state.download_options['end_verse'],
                        st.session_state.download_options['start_word'],
                        st.session_state.download_options['end_word'],
                        st.session_state.download_options['resume']
                    )
                )
                thread.daemon = True
                thread.start()
                st.session_state.download_thread = thread
                
                st.success(f"🎯 download started for Surah {surah_id}: {surah_name}")
        
        # Render compact progress and results
        render_compact_progress_display()
        render_compact_results(download_dir)
    
    with tab2:
        # Use the new enhanced log parser
        render_log_parser()
    
    with tab3:
        # Use the new statistics component
        render_statistics_component(st.session_state.downloader)


if __name__ == "__main__":
    main()
