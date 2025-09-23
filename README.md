# 🕌 Quran Audio Scraper

A comprehensive Streamlit application for downloading Quran audio files with progress tracking, error handling, and organized file management.

## ✨ Features

- **Interactive UI**: User-friendly Streamlit interface with dropdown selection
- **Progress Tracking**: Real-time download progress with speed monitoring
- **Error Handling**: Robust error handling with automatic retry mechanisms
- **Organized Downloads**: Automatic ZIP file creation with metadata
- **Logging System**: Comprehensive logging for all operations
- **Async Downloads**: Fast concurrent downloads with configurable limits
- **Directory Management**: Custom download directory selection
- **Statistics**: Detailed download statistics and performance metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Internet connection
- `quran_data.json` file (included)

### Installation

1. **Clone or download the project**
2. **Run the setup script:**
   ```bash
   ./setup.sh
   ```

3. **Start the application:**
   ```bash
   ./run.sh
   ```

### Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Create directories
mkdir -p downloads logs

# Run the application
streamlit run app.py
```

## 📱 Usage

1. **Open the application** in your browser (usually http://localhost:8501)
2. **Initialize the downloader** using the sidebar
3. **Select a Surah** from the dropdown menu
4. **Choose download directory** (optional, defaults to `downloads/`)
5. **Click "Download Audio Files"** to start the download
6. **Monitor progress** in the Progress tab
7. **View logs** in the Logs tab
8. **Download the ZIP file** when complete

## 📁 Project Structure

```
audio_scraper/
├── app.py                 # Main Streamlit application
├── downloader.py          # Core downloader class
├── utils.py              # Utility functions
├── constants.py          # Configuration constants
├── quran_data.json       # Quran metadata
├── requirements.txt      # Python dependencies
├── setup.sh             # Setup script
├── run.sh               # Run script
├── .env.example         # Environment variables example
├── README.md            # This file
├── downloads/           # Download directory (created automatically)
└── logs/               # Log files directory (created automatically)
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

### Constants

Modify `constants.py` to adjust:
- Download URLs
- Request timeouts
- Concurrent download limits
- File extensions
- Log levels

## 📊 Features Details

### Download Process

1. **Surah Selection**: Choose from 114 surahs with English and Arabic names
2. **URL Generation**: Automatic URL generation for each word audio file
3. **Concurrent Downloads**: Configurable concurrent download limits
4. **Progress Tracking**: Real-time progress updates with speed monitoring
5. **Error Handling**: Automatic retry for failed downloads
6. **ZIP Creation**: Automatic ZIP file creation with metadata
7. **Cleanup**: Temporary file cleanup after ZIP creation

### File Organization

Each downloaded surah creates:
- `surah_XXX.zip`: Contains all audio files and metadata
- `metadata.json`: File mapping with surah_id, ayah_id, word_id, and file paths
- Individual audio files: `001_001_001.mp3` format

### Logging

Comprehensive logging includes:
- Download progress
- Error messages
- Performance metrics
- Request statistics
- File operations

## 🔧 Advanced Usage

### Custom Download Directory

```python
from downloader import QuranAudioDownloader

downloader = QuranAudioDownloader(download_dir="custom/path")
result = downloader.download_surah(surah_id=1, custom_dir="another/path")
```

### Progress Callback

```python
def my_progress_callback(progress, current, total, message):
    print(f"Progress: {progress:.1f}% - {message}")

downloader.set_progress_callback(my_progress_callback)
```

### Statistics

```python
stats = downloader.get_download_stats()
print(f"Downloaded: {stats['successful_downloads']} files")
print(f"Total size: {stats['formatted_size']}")
print(f"Speed: {stats['speed']:.2f} MB/s")
```

## 🐛 Troubleshooting

### Common Issues

1. **"quran_data.json not found"**
   - Ensure the file is in the project root directory

2. **"Failed to initialize downloader"**
   - Check internet connection
   - Verify Python dependencies are installed

3. **"Download failed"**
   - Check logs for specific error messages
   - Verify the audio URL template is correct
   - Check network connectivity

4. **"Permission denied"**
   - Ensure write permissions for download directory
   - Run with appropriate user permissions

### Log Analysis

Check log files in the `logs/` directory for detailed error information:
- Download failures
- Network issues
- File system errors
- Performance metrics

## 📈 Performance

- **Concurrent Downloads**: Configurable (default: 5)
- **Retry Mechanism**: Automatic retry for failed requests
- **Memory Efficient**: Streaming downloads for large files
- **Progress Updates**: Real-time progress tracking
- **Speed Monitoring**: Download speed calculation and history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Quran data from authentic sources
- Streamlit for the excellent web framework
- Python community for the amazing libraries

## 📞 Support

For issues and questions:
1. Check the logs for error details
2. Review the troubleshooting section
3. Create an issue with detailed information

---

**Note**: This tool is for educational and personal use. Please respect the terms of service of the audio source website.

sudo docker build -t quran-adio-scraper .