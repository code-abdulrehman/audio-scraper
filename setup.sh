#!/bin/bash

# Quran Audio Scraper Setup Script

echo "🕌 Setting up Quran Audio Scraper..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing requirements..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p downloads
mkdir -p logs

# Check if quran_data.json exists
if [ ! -f "quran_data.json" ]; then
    echo "❌ quran_data.json not found. Please ensure it's in the current directory."
    exit 1
fi

echo "✅ Setup completed successfully!"
echo ""
echo "To run the application:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run the app: streamlit run app.py"
echo ""
echo "Or use the run.sh script: ./run.sh"
