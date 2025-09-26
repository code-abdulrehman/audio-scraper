"""
UI Components for Quran Audio Scraper
"""

import streamlit as st
import os
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List
from utils import format_file_size, format_duration


def create_downloader(download_dir: str, log_dir: str):
    """Create downloader instance"""
    from downloader import QuranAudioDownloader
    try:
        return QuranAudioDownloader(download_dir, log_dir)
    except Exception as e:
        st.error(f"Failed to initialize downloader: {str(e)}")
        return None


def render_compact_download_options(downloader, download_dir: str):
    """Render compact download options in accordion"""
    
    with st.expander("🎛️ Download Options", expanded=True):
        # Set default download type to word_by_word
        download_type = "word_by_word"
        st.session_state.download_type = download_type
        
        # Set default resume to True
        st.session_state.download_options['resume'] = True
        
        # Surah Selection
        surah_list = downloader.get_surah_list()
        df = pd.DataFrame(surah_list)
        
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
                return None, None, None, None
            
            st.session_state.download_options['start_verse'] = start_verse
            st.session_state.download_options['end_verse'] = end_verse
        
        with col2:
            # Word Range (for word-by-word downloads)
            st.write("**Word Range (Optional):**")
            word_col1, word_col2 = st.columns(2)
            
            with word_col1:
                start_word = st.number_input(
                    "Start Word",
                    min_value=1,
                    max_value=word_range[1],
                    value=1,
                    help=f"Starting word number (range: 1-{word_range[1]})"
                )
            
            with word_col2:
                end_word = st.number_input(
                    "End Word",
                    min_value=1,
                    max_value=word_range[1],
                    value=word_range[1],
                    help=f"Ending word number (range: 1-{word_range[1]})"
                )
            
            # Validate word range
            if start_word > end_word:
                st.error("Start word cannot be greater than end word!")
                return None, None, None, None
            
            st.session_state.download_options['start_word'] = start_word
            st.session_state.download_options['end_word'] = end_word
        
        # Download Summary
        surah_id = surah_data['id']
        surah_name = surah_data['name_en']
        
        # Calculate estimated files using the new method
        estimated_files = downloader.estimate_files_for_range(
            surah_id, download_type, start_verse, end_verse, 
            st.session_state.download_options.get('start_word'), 
            st.session_state.download_options.get('end_word')
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🆔 Surah", f"{surah_id:03d}")
        
        with col2:
            st.metric("📖 Verses", f"{start_verse}-{end_verse}")
        
        with col3:
            st.metric("📁 Type", "Word by Word")
        
        with col4:
            st.metric("📊 Est. Files", estimated_files)
        
        return surah_id, surah_name, download_type, download_dir


def render_compact_progress_display():
    """Render compact progress display"""
    
    if st.session_state.download_in_progress:
        with st.expander("🔄 Download Progress", expanded=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                if hasattr(st.session_state, "current_surah") and st.session_state.current_surah:
                    current_info = f"📖 Surah {st.session_state.current_surah}"
                    if getattr(st.session_state, "current_verse", None):
                        current_info += f", Ayah {st.session_state.current_verse}"
                    if getattr(st.session_state, "current_word", None):
                        current_info += f", Word {st.session_state.current_word}"

                    st.info(f"🔄 **Current:** {current_info}")
                    
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

                st.info(f"**Status:** {status} | **Time:** {datetime.now().strftime('%H:%M:%S')}")


def render_compact_results(download_dir: str):
    """Render compact download results"""
    
    if st.session_state.download_stats:
        with st.expander("🎉 Download Results", expanded=True):
            stats = st.session_state.download_stats
            
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
                st.metric("📁 Type", stats['download_type'].replace('_', ' ').title())
            
            # Show download details
            if stats['download_type'] == 'word_by_word':
                st.write(f"**Word Range:** {stats.get('start_word', 'All')} - {stats.get('end_word', 'All')}")
            st.write(f"**Verse Range:** {stats.get('start_verse', 'All')} - {stats.get('end_verse', 'All')}")
            st.write(f"**Resume Enabled:** Yes")
            
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


def render_compact_sidebar(downloader, download_dir: str):
    """Render compact sidebar"""
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Download directory selection
        download_dir = st.text_input(
            "📁 Download Directory",
            value=download_dir,
            help="Directory where audio files will be downloaded"
        )
        
        # Create downloader
        if st.button("🚀 Initialize Downloader", type="primary"):
            st.session_state.downloader = create_downloader(download_dir, "logs")
            if st.session_state.downloader:
                st.success("✅ downloader initialized successfully!")
        
        # Show current progress for any surah
        if st.session_state.downloader:
            with st.expander("📊 Current Progress", expanded=False):
                # Get list of surahs with progress
                surah_list = st.session_state.downloader.get_surah_list()
                
                # Show progress for first few surahs as example
                for surah in surah_list[:5]:  # Show first 5 surahs
                    progress = st.session_state.downloader.get_surah_progress(surah['id'])
                    if progress.get('downloaded_files', 0) > 0:
                        st.write(f"**{surah['name_en']}**: {progress['downloaded_files']} files")
        
        return download_dir
