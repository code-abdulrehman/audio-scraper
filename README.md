# 🕌 Quran Audio Scraper

A comprehensive Streamlit application for downloading Quran audio files with real-time progress tracking, enhanced UI, error handling, and organized file management.

## ✨ Features

- **🎨 Enhanced UI**: Beautiful, responsive interface with real-time progress tracking
- **📊 Live Progress**: Real-time download progress with visual indicators and stats
- **🌐 URL Management**: Editable URL input with validation and history
- **⚡ Async Downloads**: Fast concurrent downloads with configurable limits
- **📈 Statistics**: Detailed download statistics with color-coded metrics
- **🐳 Docker Support**: Easy deployment with Docker and Docker Compose
- **📁 Auto Organization**: Automatic ZIP file creation with metadata
- **📋 Comprehensive Logging**: Real-time logging with downloadable log files
- **🔄 Auto-Refresh**: Live updates during download process
- **🎯 Error Handling**: Robust error handling with retry mechanisms

## 🚀 Quick Start

### 🐳 Docker Setup (Recommended)

#### Using Docker Compose (Easiest)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd audio_scraper
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

3. **Access the application:**
   - Open your browser and go to: **http://localhost:8501**
   - The application will be running in the background

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

#### Using Docker Build

1. **Build the Docker image:**
   ```bash
   docker build -t quran-audio-scraper .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name quran-scraper \
     -p 8501:8501 \
     -v $(pwd)/downloads:/app/downloads \
     -v $(pwd)/logs:/app/logs \
     quran-audio-scraper
   ```

3. **Access the application:**
   - URL: **http://localhost:8501**
   - Container name: `quran-scraper`

4. **Stop and remove:**
   ```bash
   docker stop quran-scraper
   docker rm quran-scraper
   ```

### 💻 Local Setup (Without Docker)

#### Prerequisites

- **Python 3.8+** (recommended: Python 3.10 or higher)
- **Internet connection**
- **4GB+ RAM** (for efficient concurrent downloads)

#### Automatic Setup

1. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Start the application:**
   ```bash
   ./run.sh
   ```

3. **Access the application:**
   - Open browser: **http://localhost:8501**

#### Manual Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create directories:**
   ```bash
   mkdir -p downloads logs
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   ```

5. **Access the application:**
   - Local: **http://localhost:8501**
   - Network: **http://your-ip:8501**

## 🌐 Network Configuration

### Port and Host Information

| Setup Type | Default Host | Default Port | Access URL |
|------------|--------------|--------------|------------|
| **Docker Compose** | 0.0.0.0 | 8501 | http://localhost:8501 |
| **Docker Run** | 0.0.0.0 | 8501 | http://localhost:8501 |
| **Local Development** | localhost | 8501 | http://localhost:8501 |
| **Network Access** | 0.0.0.0 | 8501 | http://your-ip:8501 |

### Custom Port Configuration

#### Docker Compose
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8501"  # External:Internal
```

#### Docker Run
```bash
docker run -p 8080:8501 quran-audio-scraper
```

#### Local Setup
```bash
streamlit run app.py --server.port=8080
```

### Network Access Setup

To allow access from other devices on your network:

#### Docker (Already configured)
```bash
# Docker automatically binds to 0.0.0.0
docker-compose up -d
```

#### Local Setup
```bash
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Access from other devices: `http://your-computer-ip:8501`

## 📱 Usage Guide

### 1. Initial Setup
1. **Access the application** in your browser
2. **Configure the base URL** in the URL input section
3. **Initialize the downloader** using the sidebar
4. **Select download directory** (optional)

### 2. URL Configuration
- **Base URL Input**: Enter or edit the audio source URL
- **URL Validation**: Click "Validate URL" to check format
- **URL History**: Access recently used URLs
- **Auto-save**: URLs are automatically saved to history

### 3. Download Process
1. **Select a Surah** from the dropdown (114 surahs available)
2. **View Ayah count** and Surah details
3. **Click "Download Audio Files"** to start
4. **Monitor progress** in the Progress tab
5. **Download ZIP file** when complete

### 4. Progress Monitoring
- **Real-time progress bar** with percentage
- **Live status updates** with current operation
- **Download statistics** (successful/failed files)
- **Speed and time estimates**
- **Auto-refresh** every 2 seconds

### 5. Statistics Dashboard
- **Total requests** and **success rate**
- **File counts** with color-coded metrics
- **Download size** and **duration**
- **Error tracking** and **performance metrics**

## 📁 Project Structure

```
audio_scraper/
├── 🐳 Docker Configuration
│   ├── Dockerfile                 # Docker container configuration
│   ├── docker-compose.yml         # Docker Compose setup
│   └── .dockerignore              # Docker ignore patterns
├── 🚀 Application Core
│   ├── app.py                     # Main Streamlit application
│   ├── downloader.py              # Core downloader class
│   ├── utils.py                   # Utility functions
│   └── constants.py               # Configuration constants
├── 📊 Data & Configuration
│   ├── quran_data.json            # Quran metadata (114 surahs)
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment variables template
├── 🛠️ Scripts
│   ├── setup.sh                   # Automated setup script
│   └── run.sh                     # Application runner script
├── 📁 Directories (auto-created)
│   ├── downloads/                 # Downloaded files and ZIPs
│   ├── logs/                      # Application logs
│   └── venv/                      # Python virtual environment
└── 📚 Documentation
    └── README.md                  # This comprehensive guide
```

## ⚙️ Configuration Options

### Environment Variables

Create `.env` file for custom configuration:
```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

Available variables:
```bash
# Server Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Download Configuration
DEFAULT_DOWNLOAD_DIR=downloads
CONCURRENT_DOWNLOADS=5
MAX_RETRIES=3
TIMEOUT=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=logs
```

### Application Constants

Edit `constants.py` for advanced configuration:
- **Audio URLs** and **API endpoints**
- **Request timeouts** and **retry limits**
- **Concurrent download** limits
- **File extensions** and **naming patterns**
- **UI messages** and **labels**

## 🔧 Advanced Features

### Custom Audio Sources
```python
# In constants.py
BASE_URL = "https://your-audio-source.com"
AUDIO_URL_TEMPLATE = "https://your-audio-source.com/path/{surah_id:03d}_{ayah_id:03d}_{word_id:03d}.mp3"
```

### Progress Callbacks
```python
def custom_progress_callback(progress, current, total, message):
    print(f"Custom: {progress:.1f}% - {message}")

downloader.set_progress_callback(custom_progress_callback)
```

### Batch Downloads
```python
# Download multiple surahs
for surah_id in [1, 2, 3]:
    result = downloader.download_surah(surah_id)
    print(f"Surah {surah_id}: {result['successful_downloads']} files")
```

## 🐛 Troubleshooting

### Common Issues

#### 🐳 Docker Issues

**Port already in use:**
```bash
# Check what's using the port
sudo netstat -tulpn | grep :8501

# Kill the process or use different port
docker-compose down
docker-compose up -d
```

**Permission denied (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo
sudo docker-compose up -d
```

**Container won't start:**
```bash
# Check logs
docker-compose logs quran-scraper

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 💻 Local Setup Issues

**"quran_data.json not found":**
```bash
# Ensure file exists in project root
ls -la quran_data.json

# Download if missing
wget <source-url>/quran_data.json
```

**"Module not found" errors:**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**"Permission denied" for downloads:**
```bash
# Fix directory permissions
mkdir -p downloads logs
chmod 755 downloads logs

# Run with proper permissions
sudo chown -R $USER:$USER downloads logs
```

#### 🌐 Network Issues

**Can't access from other devices:**
```bash
# Check firewall (Linux)
sudo ufw allow 8501

# Check firewall (Windows)
# Add inbound rule for port 8501

# Verify server address
streamlit run app.py --server.address=0.0.0.0
```

**Download failures:**
```bash
# Check internet connection
ping google.com

# Verify audio URL
curl -I "https://audios.quranwbw.com/words/001/001_001_001.mp3"

# Check logs for details
tail -f logs/quran_downloader.log
```

#### ⚡ Performance Issues

**Slow downloads:**
```bash
# Reduce concurrent downloads in constants.py
CONCURRENT_DOWNLOADS = 3

# Increase timeout
TIMEOUT = 60
```

**High memory usage:**
```bash
# Monitor usage
docker stats quran-scraper

# Limit container memory
docker run --memory=1g quran-audio-scraper
```

### Log Analysis

**View real-time logs:**
```bash
# Docker
docker-compose logs -f quran-scraper

# Local
tail -f logs/quran_downloader.log
```

**Log levels and meanings:**
- **INFO**: Normal operations
- **WARNING**: Minor issues (e.g., retries)
- **ERROR**: Failed downloads or system errors
- **CRITICAL**: Application-breaking issues

## 📈 Performance Optimization

### Docker Performance
```yaml
# docker-compose.yml optimizations
services:
  quran-scraper:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
```

### Download Optimization
```python
# constants.py tuning
CONCURRENT_DOWNLOADS = 5    # Adjust based on network
TIMEOUT = 30               # Increase for slow networks
MAX_RETRIES = 3            # Balance between reliability and speed
```

### Memory Optimization
```python
# Enable streaming for large files
STREAM_DOWNLOADS = True
CHUNK_SIZE = 8192
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd audio_scraper

# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install development tools
pip install black isort flake8 pytest

# Run tests
pytest tests/

# Format code
black .
isort .
```

### Adding Features
1. **Fork** the repository
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** and **add tests**
4. **Run quality checks**: `black . && isort . && flake8`
5. **Commit changes**: `git commit -m "Add new feature"`
6. **Submit pull request**

## 📞 Support & Resources

### Getting Help
1. **Check logs** for detailed error information
2. **Review troubleshooting** section above
3. **Search existing issues** in the repository
4. **Create new issue** with:
   - OS and Python version
   - Setup method (Docker/Local)
   - Complete error logs
   - Steps to reproduce

### Useful Commands

**Docker Management:**
```bash
# View running containers
docker ps

# Restart application
docker-compose restart

# Update application
docker-compose pull && docker-compose up -d

# Clean up
docker system prune -a
```

**Application Management:**
```bash
# Check application status
curl http://localhost:8501/_stcore/health

# Monitor logs
tail -f logs/quran_downloader.log

# Check disk usage
du -sh downloads/ logs/
```

## 📄 License

This project is open source and available under the **MIT License**.

## 🙏 Acknowledgments

- **Quran data** from authentic Islamic sources
- **Streamlit** for the excellent web framework
- **Python community** for amazing libraries
- **Docker** for containerization support
- **Contributors** and **users** for feedback and improvements

---

## 🔗 Quick Links

- **Application**: http://localhost:8501
- **Health Check**: http://localhost:8501/_stcore/health
- **Documentation**: This README
- **Issues**: Repository issues page
- **Releases**: Repository releases page

**📝 Note**: This tool is for educational and personal use. Please respect the terms of service of audio source websites and ensure you have proper permissions for downloading content.

---

**⭐ If this project helps you, please consider giving it a star!**
