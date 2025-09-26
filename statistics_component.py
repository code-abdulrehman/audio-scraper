"""
Statistics Component for Quran Audio Scraper
"""

import streamlit as st
import pandas as pd
from typing import List, Dict


def render_statistics_component(downloader):
    """Render the statistics component with enhanced data"""
    
    st.markdown("""
    <style>
    .stats-accordion {
        background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf6 100%);
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    
    .stats-metric {
        background: white;
        padding: 1rem;
        border-radius: 6px;
        margin: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2E8B57;
    }
    
    .arabic-text {
        font-family: 'Arial', sans-serif;
        font-size: 1.2rem;
        color: #2E8B57;
        font-weight: bold;
        direction: rtl;
        text-align: right;
    }
    
    .progress-bar {
        background: linear-gradient(90deg, #28a745 0%, #20c997 50%, #17a2b8 100%);
        height: 8px;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not downloader:
        st.info("📊 Initialize the downloader to see statistics.")
        return
    
    surah_list = downloader.get_surah_list()
    
    # Overall Statistics
    with st.expander("📊 Overall Statistics", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        total_surahs = len(surah_list)
        total_verses = sum(surah['ayah_count'] for surah in surah_list)
        total_words = sum(surah['word_count'] for surah in surah_list)
        total_letters = sum(surah.get('total_letters', 0) for surah in surah_list)
        
        with col1:
            st.metric("🕌 Total Surahs", total_surahs)
        
        with col2:
            st.metric("📖 Total Verses", total_verses)
        
        with col3:
            st.metric("🔤 Total Words", total_words)
        
        with col4:
            st.metric("📝 Total Letters", total_letters)
    
    # Download Progress Statistics
    with st.expander("📥 Download Progress", expanded=True):
        # Count downloaded surahs
        downloaded_surahs = 0
        total_downloaded_files = 0
        total_downloaded_size = 0
        
        for surah in surah_list:
            progress = downloader.get_surah_progress(surah['id'])
            if progress.get('downloaded_files', 0) > 0:
                downloaded_surahs += 1
                total_downloaded_files += progress.get('downloaded_files', 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📁 Downloaded Files", total_downloaded_files)
        
        with col2:
            st.metric("📥 Downloaded Surahs", downloaded_surahs, delta=f"{downloaded_surahs}/{total_surahs}")
        
        with col3:
            completion_rate = (downloaded_surahs / total_surahs * 100) if total_surahs > 0 else 0
            st.metric("📈 Completion Rate", f"{completion_rate:.1f}%")
    
    # Detailed Progress by Surah
    with st.expander("📈 Progress by Surah", expanded=False):
        progress_data = []
        
        for surah in surah_list:
            progress = downloader.get_surah_progress(surah['id'])
            
            # Get Arabic name from surah data
            arabic_name = surah.get('name_ar', '')
            total_letters = surah.get('total_letters', 0)
            
            # Fix progress calculation - ensure it's between 0 and 100
            progress_percent = progress.get('progress', 0)
            if progress_percent > 100:
                progress_percent = 100.0
            elif progress_percent < 0:
                progress_percent = 0.0
            
            progress_data.append({
                'Surah ID': surah['id'],
                'English Name': surah['name_en'],
                'Arabic Name': arabic_name,
                'Total Verses': surah['ayah_count'],
                'Total Words': surah['word_count'],
                'Total Letters': total_letters,
                'Downloaded Files': progress.get('downloaded_files', 0),
                'Progress %': round(progress_percent, 1),
                'Status': '✅ Complete' if progress_percent >= 100 else 
                         '🔄 In Progress' if progress.get('downloaded_files', 0) > 0 else '⏸️ Not Started'
            })
        
        if progress_data:
            progress_df = pd.DataFrame(progress_data)
            
            # Display with custom formatting
            st.dataframe(
                progress_df,
                use_container_width=True,
                column_config={
                    "Surah ID": st.column_config.NumberColumn(
                        "Surah ID",
                        help="Surah number",
                        width="small"
                    ),
                    "English Name": st.column_config.TextColumn(
                        "English Name",
                        help="English name of the surah",
                        width="medium"
                    ),
                    "Arabic Name": st.column_config.TextColumn(
                        "Arabic Name",
                        help="Arabic name of the surah",
                        width="small"
                    ),
                    "Total Verses": st.column_config.NumberColumn(
                        "Verses",
                        help="Number of verses",
                        width="small"
                    ),
                    "Total Words": st.column_config.NumberColumn(
                        "Words",
                        help="Number of words",
                        width="small"
                    ),
                    "Total Letters": st.column_config.NumberColumn(
                        "Letters",
                        help="Number of letters",
                        width="small"
                    ),
                    "Downloaded Files": st.column_config.NumberColumn(
                        "Downloaded",
                        help="Number of downloaded files",
                        width="small"
                    ),
                    "Progress %": st.column_config.ProgressColumn(
                        "Progress",
                        help="Download progress percentage",
                        min_value=0,
                        max_value=100,
                        width="medium"
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        help="Download status",
                        width="small"
                    )
                }
            )
    
    # Surah Details Modal
    with st.expander("🔍 Surah Details", expanded=False):
        selected_surah_id = st.selectbox(
            "Select Surah for Details",
            options=[surah['id'] for surah in surah_list],
            format_func=lambda x: f"{x:03d} - {next(s['name_en'] for s in surah_list if s['id'] == x)}"
        )
        
        if selected_surah_id:
            surah_data = next(s for s in surah_list if s['id'] == selected_surah_id)
            progress = downloader.get_surah_progress(selected_surah_id)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"""
                <div class="stats-metric">
                    <h4>📖 {surah_data['name_en']}</h4>
                    <p class="arabic-text">{surah_data.get('name_ar', '')}</p>
                    <p><strong>Surah ID:</strong> {surah_data['id']:03d}</p>
                    <p><strong>Total Verses:</strong> {surah_data['ayah_count']}</p>
                    <p><strong>Total Words:</strong> {surah_data['word_count']}</p>
                    <p><strong>Total Letters:</strong> {surah_data.get('total_letters', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                downloaded_files = progress.get('downloaded_files', 0)
                total_files = progress.get('total_files', 0)
                progress_percent = progress.get('progress', 0)
                
                # Fix progress calculation
                if progress_percent > 100:
                    progress_percent = 100.0
                elif progress_percent < 0:
                    progress_percent = 0.0
                
                st.markdown(f"""
                <div class="stats-metric">
                    <h4>📊 Download Progress</h4>
                    <p><strong>Downloaded Files:</strong> {downloaded_files}</p>
                    <p><strong>Total Files:</strong> {total_files}</p>
                    <p><strong>Progress:</strong> {progress_percent:.1f}%</p>
                    <div class="progress-bar" style="width: {progress_percent}%"></div>
                    <p><strong>Status:</strong> {'✅ Complete' if progress_percent >= 100 else '🔄 In Progress' if downloaded_files > 0 else '⏸️ Not Started'}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Export Statistics
    with st.expander("📤 Export Statistics", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export Progress Data", type="secondary"):
                # Create export data
                export_data = []
                for surah in surah_list:
                    progress = downloader.get_surah_progress(surah['id'])
                    progress_percent = progress.get('progress', 0)
                    
                    # Fix progress calculation for export
                    if progress_percent > 100:
                        progress_percent = 100.0
                    elif progress_percent < 0:
                        progress_percent = 0.0
                    
                    export_data.append({
                        'Surah ID': surah['id'],
                        'English Name': surah['name_en'],
                        'Arabic Name': surah.get('name_ar', ''),
                        'Total Verses': surah['ayah_count'],
                        'Total Words': surah['word_count'],
                        'Total Letters': surah.get('total_letters', 0),
                        'Downloaded Files': progress.get('downloaded_files', 0),
                        'Total Files': progress.get('total_files', 0),
                        'Progress %': round(progress_percent, 1)
                    })
                
                export_df = pd.DataFrame(export_data)
                csv = export_df.to_csv(index=False)
                
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name="quran_download_progress.csv",
                    mime="text/csv",
                    type="primary"
                )
        
        with col2:
            if st.button("📋 Copy Summary", type="secondary"):
                summary = f"""
Quran Audio Download Statistics:
- Total Surahs: {total_surahs}
- Total Verses: {total_verses}
- Total Words: {total_words}
- Total Letters: {total_letters}
- Downloaded Surahs: {downloaded_surahs}
- Downloaded Files: {total_downloaded_files}
- Completion Rate: {completion_rate:.1f}%
                """.strip()
                
                st.code(summary)
                st.success("📋 Summary copied to clipboard!")
