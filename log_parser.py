"""
Compact Log Parser Component for Quran Audio Scraper
"""

import streamlit as st
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd


class LogEntry:
    """Represents a single log entry with parsed information"""
    
    def __init__(self, raw_line: str, line_number: int):
        self.raw_line = raw_line.strip()
        self.line_number = line_number
        self.timestamp = None
        self.level = None
        self.message = None
        self.surah_id = None
        self.ayah_id = None
        self.word_id = None
        self.status = None
        self.url = None
        
        self._parse_line()
    
    def _parse_line(self):
        """Parse log line into components"""
        # Pattern: 2025-09-24 09:51:14,801 - quran_scraper - INFO - Starting download for Surah 1: The Opening
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - quran_scraper - (\w+) - (.+)'
        match = re.match(pattern, self.raw_line)
        
        if match:
            self.timestamp = match.group(1)
            self.level = match.group(2)
            self.message = match.group(3)
            
            # Extract additional info based on message content
            self._extract_metadata()
    
    def _extract_metadata(self):
        """Extract metadata from log message"""
        if not self.message:
            return
        
        # Extract Surah ID
        surah_match = re.search(r'Surah (\d+)', self.message)
        if surah_match:
            self.surah_id = int(surah_match.group(1))
        
        # Extract Ayah ID
        ayah_match = re.search(r'Ayah (\d+)', self.message)
        if ayah_match:
            self.ayah_id = int(ayah_match.group(1))
        
        # Extract Word ID
        word_match = re.search(r'(\d{3}_\d{3}_\d{3})', self.message)
        if word_match:
            parts = word_match.group(1).split('_')
            if len(parts) == 3:
                self.word_id = int(parts[2])
        
        # Extract URL
        url_match = re.search(r'https://[^\s]+', self.message)
        if url_match:
            self.url = url_match.group(0)
        
        # Determine status
        if 'HTTP 404' in self.message or '404 error' in self.message:
            self.status = 'error'
        elif 'Downloaded' in self.message or 'successfully' in self.message.lower():
            self.status = 'success'
        elif 'WARNING' in self.level:
            self.status = 'warning'
        elif 'Starting' in self.message or 'Processing' in self.message:
            self.status = 'info'
        else:
            self.status = 'info'
    
    def get_color(self) -> str:
        """Get color for this log entry"""
        color_map = {
            'error': '#ff4444',      # Red
            'success': '#44ff44',    # Green
            'warning': '#ffaa00',    # Orange/Yellow
            'info': '#888888'        # Gray
        }
        return color_map.get(self.status, '#888888')
    
    def get_icon(self) -> str:
        """Get icon for this log entry"""
        icon_map = {
            'error': '❌',
            'success': '✅',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        return icon_map.get(self.status, 'ℹ️')


class LogParser:
    """Compact log parser with filtering, search, and sorting capabilities"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.log_entries: List[LogEntry] = []
        self.filtered_entries: List[LogEntry] = []
    
    def load_log_file(self, log_file: str) -> bool:
        """Load and parse a log file"""
        try:
            log_path = os.path.join(self.log_dir, log_file)
            if not os.path.exists(log_path):
                return False
            
            self.log_entries = []
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():  # Skip empty lines
                        entry = LogEntry(line, line_num)
                        self.log_entries.append(entry)
            
            self.filtered_entries = self.log_entries.copy()
            return True
            
        except Exception as e:
            st.error(f"Error loading log file: {str(e)}")
            return False
    
    def filter_logs(self, 
                   level_filter: Optional[str] = None,
                   status_filter: Optional[str] = None,
                   surah_filter: Optional[int] = None,
                   search_text: Optional[str] = None,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None) -> List[LogEntry]:
        """Filter log entries based on criteria"""
        
        filtered = self.log_entries.copy()
        
        # Level filter
        if level_filter and level_filter != "All":
            filtered = [entry for entry in filtered if entry.level == level_filter]
        
        # Status filter
        if status_filter and status_filter != "All":
            filtered = [entry for entry in filtered if entry.status == status_filter]
        
        # Surah filter
        if surah_filter:
            filtered = [entry for entry in filtered if entry.surah_id == surah_filter]
        
        # Text search
        if search_text:
            search_lower = search_text.lower()
            filtered = [entry for entry in filtered 
                       if search_lower in entry.message.lower() or 
                          search_lower in entry.raw_line.lower()]
        
        # Date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                filtered = [entry for entry in filtered 
                           if entry.timestamp and 
                           datetime.strptime(entry.timestamp.split(',')[0], "%Y-%m-%d %H:%M:%S").date() >= from_date.date()]
            except:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                filtered = [entry for entry in filtered 
                           if entry.timestamp and 
                           datetime.strptime(entry.timestamp.split(',')[0], "%Y-%m-%d %H:%M:%S").date() <= to_date.date()]
            except:
                pass
        
        self.filtered_entries = filtered
        return filtered
    
    def sort_logs(self, sort_by: str = "timestamp", reverse: bool = False) -> List[LogEntry]:
        """Sort log entries"""
        if sort_by == "timestamp":
            self.filtered_entries.sort(key=lambda x: x.timestamp or "", reverse=reverse)
        elif sort_by == "level":
            level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
            self.filtered_entries.sort(key=lambda x: level_order.get(x.level, 5), reverse=reverse)
        elif sort_by == "surah":
            self.filtered_entries.sort(key=lambda x: x.surah_id or 0, reverse=reverse)
        elif sort_by == "status":
            status_order = {"info": 0, "success": 1, "warning": 2, "error": 3}
            self.filtered_entries.sort(key=lambda x: status_order.get(x.status, 4), reverse=reverse)
        
        return self.filtered_entries
    
    def get_statistics(self) -> Dict:
        """Get log statistics"""
        if not self.log_entries:
            return {}
        
        total_entries = len(self.log_entries)
        filtered_entries = len(self.filtered_entries)
        
        # Count by level
        level_counts = {}
        for entry in self.log_entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
        
        # Count by status
        status_counts = {}
        for entry in self.log_entries:
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        
        # Count by surah
        surah_counts = {}
        for entry in self.log_entries:
            if entry.surah_id:
                surah_counts[entry.surah_id] = surah_counts.get(entry.surah_id, 0) + 1
        
        return {
            'total_entries': total_entries,
            'filtered_entries': filtered_entries,
            'level_counts': level_counts,
            'status_counts': status_counts,
            'surah_counts': surah_counts
        }
    
    def export_filtered_logs(self) -> str:
        """Export filtered logs as text"""
        return '\n'.join([entry.raw_line for entry in self.filtered_entries])


def render_log_parser():
    """Render the compact log parser UI"""
    
    st.markdown("""
    <style>
    .log-entry {
        padding: 8px 12px;
        margin: 2px 0;
        border-radius: 6px;
        border-left: 4px solid;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        line-height: 1.4;
    }
    
    .log-entry-error {
        background-color: #ffeaea;
        border-left-color: #ff4444;
        color: #cc0000;
    }
    
    .log-entry-success {
        background-color: #eafaea;
        border-left-color: #44ff44;
        color: #006600;
    }
    
    .log-entry-warning {
        background-color: #fff8ea;
        border-left-color: #ffaa00;
        color: #cc6600;
    }
    
    .log-entry-info {
        background-color: #f5f5f5;
        border-left-color: #888888;
        color: #333333;
    }
    
    .log-stats {
        background: linear-gradient(135deg, #f0f2f6 0%, #e8eaf6 100%);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize log parser
    if 'log_parser' not in st.session_state:
        st.session_state.log_parser = LogParser()
    
    parser = st.session_state.log_parser
    
    # File selection
    with st.expander("📄 Log File Selection", expanded=True):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            st.error("📁 Log directory not found.")
            return
        
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        if not log_files:
            st.info("📝 No log files found.")
            return
        
        # Sort log files by modification time (newest first)
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_log = st.selectbox(
                "Select Log File",
                log_files,
                format_func=lambda x: f"{x} ({os.path.getsize(os.path.join(log_dir, x))} bytes)"
            )
        
        with col2:
            if st.button("🔄 Load Log", type="primary"):
                if parser.load_log_file(selected_log):
                    st.success("✅ Log loaded successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to load log file")
        
        # Load log if not already loaded or if file changed
        if not parser.log_entries or (hasattr(st.session_state, 'current_log_file') and 
                                     st.session_state.current_log_file != selected_log):
            if parser.load_log_file(selected_log):
                st.session_state.current_log_file = selected_log
    
    if not parser.log_entries:
        st.warning("⚠️ No log entries to display.")
        return
    
    # Statistics
    stats = parser.get_statistics()
    
    with st.expander("📊 Log Statistics", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📝 Total Entries", stats['total_entries'])
        
        with col2:
            st.metric("🔍 Filtered Entries", stats['filtered_entries'])
        
        with col3:
            error_count = stats['status_counts'].get('error', 0)
            st.metric("❌ Errors", error_count, delta=f"-{error_count}" if error_count > 0 else "0")
        
        with col4:
            success_count = stats['status_counts'].get('success', 0)
            st.metric("✅ Success", success_count, delta=f"+{success_count}" if success_count > 0 else "0")
    
    # Filters in accordion
    with st.expander("🔍 Filters & Search", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Level filter
            levels = ["All"] + list(stats['level_counts'].keys())
            level_filter = st.selectbox("📊 Log Level", levels)
            
            # Status filter
            statuses = ["All"] + list(stats['status_counts'].keys())
            status_filter = st.selectbox("🎯 Status", statuses)
        
        with col2:
            # Surah filter
            surahs = [None] + sorted([s for s in stats['surah_counts'].keys() if s])
            surah_filter = st.selectbox("🕌 Surah", surahs, format_func=lambda x: f"All Surahs" if x is None else f"Surah {x}")
            
            # Search text
            search_text = st.text_input("🔍 Search Text", placeholder="Search in log messages...")
        
        with col3:
            # Date filters
            date_from = st.date_input("📅 From Date", value=None)
            date_to = st.date_input("�� To Date", value=None)
            
            # Sort options
            sort_by = st.selectbox("🔄 Sort By", ["timestamp", "level", "surah", "status"])
            sort_reverse = st.checkbox("⬇️ Reverse Order")
        
        # Apply filters
        if st.button("🎯 Apply Filters", type="secondary"):
            parser.filter_logs(
                level_filter=level_filter if level_filter != "All" else None,
                status_filter=status_filter if status_filter != "All" else None,
                surah_filter=surah_filter,
                search_text=search_text if search_text else None,
                date_from=date_from.strftime("%Y-%m-%d") if date_from else None,
                date_to=date_to.strftime("%Y-%m-%d") if date_to else None
            )
            parser.sort_logs(sort_by, sort_reverse)
            st.rerun()
    
    # Display filtered logs
    st.subheader(f"📋 Log Entries ({len(parser.filtered_entries)} entries)")
    
    # Export button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📥 Export Filtered Logs", type="secondary", use_container_width=True):
            export_data = parser.export_filtered_logs()
            st.download_button(
                label="💾 Download Filtered Logs",
                data=export_data,
                file_name=f"filtered_{selected_log}",
                mime="text/plain",
                type="primary"
            )
    
    # Log entries display
    if parser.filtered_entries:
        # Pagination
        entries_per_page = 100
        total_pages = (len(parser.filtered_entries) - 1) // entries_per_page + 1
        
        if total_pages > 1:
            page = st.selectbox("📄 Page", range(1, total_pages + 1)) - 1
            start_idx = page * entries_per_page
            end_idx = min(start_idx + entries_per_page, len(parser.filtered_entries))
            display_entries = parser.filtered_entries[start_idx:end_idx]
        else:
            display_entries = parser.filtered_entries
        
        # Display entries
        for entry in display_entries:
            color_class = f"log-entry-{entry.status}"
            icon = entry.get_icon()
            
            # Create detailed display
            timestamp = entry.timestamp or "N/A"
            level = entry.level or "UNKNOWN"
            message = entry.message or entry.raw_line
            
            # Add metadata if available
            metadata = []
            if entry.surah_id:
                metadata.append(f"Surah {entry.surah_id}")
            if entry.ayah_id:
                metadata.append(f"Ayah {entry.ayah_id}")
            if entry.word_id:
                metadata.append(f"Word {entry.word_id}")
            
            metadata_str = f" [{', '.join(metadata)}]" if metadata else ""
            
            st.markdown(f"""
            <div class="log-entry {color_class}">
                <strong>{icon} {timestamp}</strong> - <strong>{level}</strong>{metadata_str}<br>
                {message}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔍 No log entries match the current filters.")
