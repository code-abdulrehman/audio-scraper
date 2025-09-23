#!/bin/bash

# Quran Audio Scraper Run Script

echo "🕌 Starting Quran Audio Scraper..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
echo "🔍 Checking requirements..."
python3 -c "import streamlit, requests, tqdm, aiohttp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Requirements not installed. Please run setup.sh first."
    exit 1
fi

# Create directories if they don't exist
mkdir -p downloads
mkdir -p logs

# Run the Streamlit app
echo "🚀 Starting Streamlit application..."
echo "📱 The app will open in your default browser."
echo "🔗 If it doesn't open automatically, go to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application."
echo ""

streamlit run app.py --server.port 8501 --server.address localhost
