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
        result = downloader.download_surah(
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
    with st.container():
        
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
                st.success("✅ downloader initialized successfully!")
        
        # Show current progress for any surah
        if st.session_state.downloader:
            st.markdown("### 📊 Current Progress")
            
            # Get list of surahs with progress
            surah_list = st.session_state.downloader.get_surah_list()
            
            # Show progress for first few surahs as example
            for surah in surah_list[:5]:  # Show first 5 surahs
                progress = st.session_state.downloader.get_surah_progress(surah['id'])
                if progress.get('downloaded_files', 0) > 0:
                    st.write(f"**{surah['name_en']}**: {progress['downloaded_files']} files")
    
    # Main content
    tab1, tab2 = st.tabs(["📥 Download", "📋 Logs"])
    
    with tab1:
        st.header("📥 Quran Audio Download")
        
        if not st.session_state.downloader:
            st.warning("⚠️ Please initialize the enhanced downloader first using the sidebar.")
            return
        
        # Get surah list
        surah_list = st.session_state.downloader.get_surah_list()
        df = pd.DataFrame(surah_list)

        with st.container():
            st.subheader("🎛️ Download Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Download Type Selection
                download_type = st.radio(
                    "📋 Download Type",
                    ["word_by_word", "verse_by_verse"],
                    format_func=lambda x: "🔤 Word by Word" if x == "word_by_word" else "📖 Verse by Verse",
                    help="Choose how to download the audio files"
                )
                st.session_state.download_type = download_type
            
            with col2:
                # Resume Option
                resume_download = st.checkbox(
                    "🔄 Resume Downloads",
                    value=True,
                    help="Resume from last successful file if interrupted"
                )
                st.session_state.download_options['resume'] = resume_download
            
            # Surah Selection
            st.subheader("🕌 Surah Selection")
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                selected_surah = st.selectbox(
                    "Select Surah",
                    options=df.index,
                    format_func=lambda x: f"{df.iloc[x]['id']:03d} - {df.iloc[x]['name_en']} ({df.iloc[x]['name_ar']})"
                )
            
            with col2:
                st.metric("📖 Verses", df.iloc[selected_surah]['ayah_count'])
            
            with col3:
                st.metric("🔤 Words", df.iloc[selected_surah]['word_count'])
            
            # Range Selection
            surah_data = df.iloc[selected_surah]
            ayah_range = surah_data['ayah_range']
            word_range = surah_data['word_range']
            
            st.subheader("📊 Range Selection")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Verse Range
                st.write("**Verse Range:**")
                verse_col1, verse_col2 = st.columns(2)
                
                with verse_col1:
                    start_verse = st.number_input(
                        "Start Verse",
                        min_value=ayah_range[0],
                        max_value=ayah_range[1],
                        value=ayah_range[0],
                        help=f"Starting verse (range: {ayah_range[0]}-{ayah_range[1]})"
                    )
                
                with verse_col2:
                    end_verse = st.number_input(
                        "End Verse",
                        min_value=ayah_range[0],
                        max_value=ayah_range[1],
                        value=ayah_range[1],
                        help=f"Ending verse (range: {ayah_range[0]}-{ayah_range[1]})"
                    )
                
                # Validate verse range
                if start_verse > end_verse:
                    st.error("Start verse cannot be greater than end verse!")
                    return
                
                st.session_state.download_options['start_verse'] = start_verse
                st.session_state.download_options['end_verse'] = end_verse
            
            with col2:
                # Word Range (only for word-by-word downloads)
                if download_type == "word_by_word":
                    st.write("**Word Range (Optional):**")
                    word_col1, word_col2 = st.columns(2)
                    
                    with word_col1:
                        start_word = st.number_input(
                            "Start Word",
                            min_value=1,
                            max_value=1000,
                            value=1,
                            help="Starting word number (leave as 1 for all words)"
                        )
                    
                    with word_col2:
                        end_word = st.number_input(
                            "End Word",
                            min_value=1,
                            max_value=1000,
                            value=1000,
                            help="Ending word number (leave as 1000 for all words)"
                        )
                    
                    # Validate word range
                    if start_word > end_word:
                        st.error("Start word cannot be greater than end word!")
                        return
                    
                    st.session_state.download_options['start_word'] = start_word
                    st.session_state.download_options['end_word'] = end_word
                else:
                    st.session_state.download_options['start_word'] = None
                    st.session_state.download_options['end_word'] = None
            
            # Download Summary
            st.subheader("📋 Download Summary")
            
            surah_id = surah_data['id']
            surah_name = surah_data['name_en']
            
            # Calculate estimated files
            if download_type == "word_by_word":
                estimated_files = (end_verse - start_verse + 1) * 10  # Rough estimate
                download_type_text = "Word by Word"
            else:
                estimated_files = end_verse - start_verse + 1
                download_type_text = "Verse by Verse"
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🆔 Surah", f"{surah_id:03d}")
            
            with col2:
                st.metric("📖 Verses", f"{start_verse}-{end_verse}")
            
            with col3:
                st.metric("📁 Type", download_type_text)
            
            with col4:
                st.metric("📊 Est. Files", estimated_files)
            
        
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
        
        # FIXED: Progress and loading display using proper container
        if st.session_state.download_in_progress:
        # Named container for download progress
            with st.container():
                st.markdown(
                    """
                    <style>
                    .download-box {
                        max-height: 150px;
                        overflow-y: auto;
                        padding: 0.5rem;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        background: #fafafa;
                        margin-bottom: 0.5rem;
                    }
                    .status-box {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 0.5rem;
                        background: #f9f9f9;
                        border-radius: 6px;
                        border: 1px solid #ddd;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns([1, 1])

                with col1:
                    if hasattr(st.session_state, "current_surah") and st.session_state.current_surah:
                        current_info = f"📖 Surah {st.session_state.current_surah}"
                        if getattr(st.session_state, "current_verse", None):
                            current_info += f", Ayah {st.session_state.current_verse}"
                        if getattr(st.session_state, "current_word", None):
                            current_info += f", Word {st.session_state.current_word}"

                        st.markdown(
                            f"""
                            <div class="download-box">
                                🔄 <strong>Current:</strong> {current_info}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                         # thread check
                    if (
                        st.session_state.download_thread
                        and not st.session_state.download_thread.is_alive()
                    ):
                        st.session_state.download_in_progress = False

                    # auto-refresh with spinner
                    with st.spinner("Downloading..."):
                        time.sleep(2)
                        st.rerun()


                with col2:
                    status = "🟢 Active" if (
                        st.session_state.download_thread
                        and st.session_state.download_thread.is_alive()
                    ) else "🔴 Inactive"

                    st.markdown(
                        f"""
                        <div class="status-box">
                            <span>{status}</span>
                            <span>⏱️ {datetime.now().strftime('%H:%M:%S')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


        
        # FIXED: Show download results using proper container
        elif st.session_state.download_stats:
            with st.container():
                st.markdown('<div class="stats-container">', unsafe_allow_html=True)
                
                stats = st.session_state.download_stats
                
                # completion stats with colors
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
                    st.metric("�� Type", stats['download_type'].replace('_', ' ').title())
                
                # Show download details
                st.subheader("📊 Download Details")
                
                if stats['download_type'] == 'word_by_word':
                    st.write(f"**Word Range:** {stats.get('start_word', 'All')} - {stats.get('end_word', 'All')}")
                st.write(f"**Verse Range:** {stats.get('start_verse', 'All')} - {stats.get('end_verse', 'All')}")
                st.write(f"**Resume Enabled:** {'Yes' if st.session_state.download_options['resume'] else 'No'}")
                
                # Show folder structure info
                surah_folder = f"{stats['surah_id']:03d}_{stats['surah_name'].replace(' ', '_').replace("'", '').replace('-', '_')}"
                download_path = os.path.join(download_dir, surah_folder)
                
                if os.path.exists(download_path):
                    st.success(f"📁 Files saved to: `{download_path}`")
                    
                    # Show some example files
                    files = [f for f in os.listdir(download_path) if f.endswith('.mp3')]
                    if files:
                        st.write("**Sample files:**")
                        for file in sorted(files)[:5]:  # Show first 5 files
                            st.write(f"  - {file}")
                        if len(files) > 5:
                            st.write(f"  - ... and {len(files) - 5} more files")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.header("📋 Download Logs")
        
        # log selection
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
                
                # FIXED: Display log content using proper container
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    with st.container():
                        st.markdown('<div class="log-container">', unsafe_allow_html=True)
                        st.text(log_content)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # download log button
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
