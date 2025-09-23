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
import re
from urllib.parse import urlparse

from downloader import QuranAudioDownloader
from constants import MESSAGES, DEFAULT_DOWNLOAD_DIR
from utils import format_file_size, format_duration


# Page configuration - Force light mode
st.set_page_config(
    page_title="Quran Audio Scraper",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force light mode CSS
st.markdown("""
<style>
    /* Force light mode */
    .stApp {
        color: #262730;
        background-color: #ffffff;
    }
    
    .stApp > header {
        background-color: #ffffff;
    }
    
    .stSidebar {
        background-color: #f8f9fa;
    }
    
    .stSidebar .stSelectbox > div > div {
        background-color: #ffffff;
    }
    
    .stSidebar .stTextInput > div > div > input {
        background-color: #ffffff;
    }
    
    .stSidebar .stButton > button {
        background-color: #ffffff;
        color: #262730;
        border: 1px solid #d1d5db;
    }
    
    .stSidebar .stButton > button:hover {
        background-color: #f3f4f6;
    }
    
    /* Main content styling */
    .main-header {
        text-align: center;
        color: #2E8B57;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .stats-container {
        background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf6 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    .progress-container {
        background: linear-gradient(135deg, #e8f4fd 0%, #e3f2fd 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #bbdefb;
    }
    
    .log-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #dee2e6;
    }
    
    .url-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f4 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #dee2e6;
    }
    
    .metric-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .metric-danger {
        color: #dc3545;
        font-weight: bold;
    }
    
    .metric-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .metric-info {
        color: #17a2b8;
        font-weight: bold;
    }
    
    .progress-text {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2E8B57;
    }
    
    .status-text {
        font-size: 1rem;
        color: #666;
        font-style: italic;
    }
    
    footer {
        display: none;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #28a745 0%, #20c997 50%, #17a2b8 100%);
    }
    
    /* Force light mode for all components */
    .stSelectbox > div > div {
        background-color: #ffffff;
    }
    
    .stTextInput > div > div > input {
        background-color: #ffffff;
    }
    
    .stButton > button {
        background-color: #ffffff;
        color: #262730;
        border: 1px solid #d1d5db;
    }
    
    .stButton > button:hover {
        background-color: #f3f4f6;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: #ffffff;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        color: #262730;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #f0f2f6;
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
        st.session_state.current_url = ""
    if 'url_history' not in st.session_state:
        st.session_state.url_history = []


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
    
    # Header
    st.markdown('<h1 class="main-header">🕌 Quran Audio Scraper</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("🌐 Audio URL Configuration")
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
        if st.button("�� Validate URL", type="secondary"):
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
    
    st.markdown('</div>', unsafe_allow_html=True)

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
    
    # Sidebar - Removed Current Stats section
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Download directory selection
        download_dir = st.text_input(
            "📁 Download Directory",
            value=DEFAULT_DOWNLOAD_DIR,
            help="Directory where audio files will be downloaded"
        )
        
        # Create downloader
        if st.button("🚀 Initialize Downloader", type="primary"):
            st.session_state.downloader = create_downloader(download_dir, "logs")
            if st.session_state.downloader:
                st.success("✅ Downloader initialized successfully!")
    
    # Main content - Only Download and Logs tabs (removed Progress tab)
    tab1, tab2 = st.tabs(["📥 Download", "📋 Logs"])
    
    with tab1:
        st.header("📥 Download Audio Files")
        
        if not st.session_state.downloader:
            st.warning("⚠️ Please initialize the downloader first using the sidebar.")
            return
        
        # Get surah list
        surah_list = st.session_state.downloader.get_surah_list()
        
        # Create DataFrame for better display
        df = pd.DataFrame(surah_list)
        
        # Surah selection with enhanced UI
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            selected_surah = st.selectbox(
                "🕌 " + MESSAGES['select_surah'],
                options=df.index,
                format_func=lambda x: f"{df.iloc[x]['id']:03d} - {df.iloc[x]['name_en']} ({df.iloc[x]['name_ar']})"
            )
        
        with col2:
            st.metric("📖 Ayah Count", df.iloc[selected_surah]['ayah_count'])
        
        with col3:
            st.metric("🆔 Surah ID", df.iloc[selected_surah]['id'])
        
        # Enhanced download button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Download Audio Files", 
                        disabled=st.session_state.download_in_progress,
                        type="primary",
                        use_container_width=True):
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
                
                st.success(f"🎯 Download started for Surah {surah_id}: {surah_name}")
        
        # Progress and loading display in Download tab
        if st.session_state.download_in_progress:
            
            
            # Check if thread is still alive
            if st.session_state.download_thread and not st.session_state.download_thread.is_alive():
                st.session_state.download_in_progress = False
            
            # Auto-refresh with spinner
            with st.spinner("Downloading..."):
                time.sleep(2)
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Show download results in Download tab
        elif st.session_state.download_stats:
            st.markdown('<div class="stats-container">', unsafe_allow_html=True)
            
            stats = st.session_state.download_stats
            
            # Enhanced completion stats with colors
            st.subheader("🎉 Download Completed!")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🆔 Surah ID", stats['surah_id'])
                st.metric("📖 Surah Name", stats['surah_name'])
            
            with col2:
                st.metric("📁 Total Files", stats['total_files'])
                st.metric("✅ Successful", stats['successful_downloads'], 
                         delta=f"+{stats['successful_downloads']}", delta_color="normal")
            
            with col3:
                st.metric("❌ Failed", stats['failed_downloads'], 
                         delta=f"+{stats['failed_downloads']}" if stats['failed_downloads'] > 0 else "0", 
                         delta_color="inverse")
                st.metric("💾 Total Size", format_file_size(stats['total_size']))
            
            with col4:
                st.metric("⏱️ Duration", format_duration(stats['duration']))
                st.metric("📦 ZIP File", os.path.basename(stats['zip_path']))
            
            # Enhanced download link
            if os.path.exists(stats['zip_path']):
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    with open(stats['zip_path'], 'rb') as f:
                        st.download_button(
                            label="📥 Download ZIP File",
                            data=f.read(),
                            file_name=os.path.basename(stats['zip_path']),
                            mime="application/zip",
                            type="primary",
                            use_container_width=True
                        )
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.header("📋 Download Logs")
        
        # Enhanced log selection
        log_dir = "logs"
        if os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
            
            if log_files:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    selected_log = st.selectbox("📄 Select Log File", log_files)
                    log_path = os.path.join(log_dir, selected_log)
                
                with col2:
                    if os.path.exists(log_path):
                        file_size = os.path.getsize(log_path)
                        st.metric("📏 File Size", format_file_size(file_size))
                
                # Display log content with enhanced styling
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    st.markdown('<div class="log-container">', unsafe_allow_html=True)
                    st.text(log_content)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Enhanced download log button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            label="📥 Download Log File",
                            data=log_content,
                            file_name=selected_log,
                            mime="text/plain",
                            type="secondary",
                            use_container_width=True
                        )
                
                except Exception as e:
                    st.error(f"❌ Error reading log file: {str(e)}")
            else:
                st.info("📝 No log files found.")
        else:
            st.info("📁 Log directory not found.")


if __name__ == "__main__":
    main()
