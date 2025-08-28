#!/bin/bash
# HackathonHero - Linux Setup Script
# One-liner setup for hackathon participants

set -e  # Exit on any error

echo "🚀 HackathonHero - Linux Setup"
echo "==============================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect distribution
if command_exists apt; then
    PACKAGE_MANAGER="apt"
    UPDATE_CMD="sudo apt update"
    INSTALL_CMD="sudo apt install -y"
    PYTHON_PACKAGE="python3.11 python3.11-venv python3-pip"
elif command_exists dnf; then
    PACKAGE_MANAGER="dnf"
    UPDATE_CMD="sudo dnf check-update || true"
    INSTALL_CMD="sudo dnf install -y"
    PYTHON_PACKAGE="python3.11 python3-pip"
elif command_exists pacman; then
    PACKAGE_MANAGER="pacman"
    UPDATE_CMD="sudo pacman -Sy"
    INSTALL_CMD="sudo pacman -S --noconfirm"
    PYTHON_PACKAGE="python python-pip"
else
    echo "❌ Unsupported package manager. Please install dependencies manually."
    exit 1
fi

echo "📦 Using $PACKAGE_MANAGER package manager"

# Update package list
echo "🔄 Updating package list..."
$UPDATE_CMD

# Install Python 3.11+
if ! command_exists python3 || [[ "$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)" < "3.11" ]]; then
    echo "🐍 Installing Python 3.11+..."
    $INSTALL_CMD $PYTHON_PACKAGE
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        $INSTALL_CMD python3.11-venv
    fi
else
    echo "✅ Python 3.11+ already installed"
fi

# Install Node.js 22+
if ! command_exists node || [[ "$(node --version | cut -d'v' -f2 | cut -d. -f1)" < "22" ]]; then
    echo "📱 Installing Node.js 22+..."
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        $INSTALL_CMD nodejs
    elif [[ "$PACKAGE_MANAGER" == "dnf" ]]; then
        $INSTALL_CMD nodejs npm
    elif [[ "$PACKAGE_MANAGER" == "pacman" ]]; then
        $INSTALL_CMD nodejs npm
    fi
else
    echo "✅ Node.js 22+ already installed"
fi

# Install Tesseract OCR
if ! command_exists tesseract; then
    echo "📖 Installing Tesseract OCR..."
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        $INSTALL_CMD tesseract-ocr tesseract-ocr-eng
    elif [[ "$PACKAGE_MANAGER" == "dnf" ]]; then
        $INSTALL_CMD tesseract tesseract-langpack-eng
    elif [[ "$PACKAGE_MANAGER" == "pacman" ]]; then
        $INSTALL_CMD tesseract tesseract-data-eng
    fi
else
    echo "✅ Tesseract OCR already installed"
fi

# Install Ollama
if ! command_exists ollama; then
    echo "🤖 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✅ Ollama already installed"
fi

# Check if we're already in the repository or need to clone/navigate
if [ -f "backend/main.py" ] && [ -f "frontend/package.json" ]; then
    echo "✅ Already in HackathonHero repository directory"
else
    if [ ! -d "hackathon-agent" ]; then
        echo "📥 Cloning HackathonHero repository..."
        git clone https://github.com/genggao/hackathon-agent.git
        cd hackathon-agent
    else
        echo "✅ Repository already cloned"
        cd hackathon-agent
    fi
fi

# Setup backend
echo "🔧 Setting up backend..."
cd backend
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/activate" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python3 -c "from models.db import init_db; init_db()"
else
    echo "✅ Backend environment already exists, activating..."
    source .venv/bin/activate
    # Check if database needs initialization
    if [ ! -f "hackathon.db" ]; then
        echo "🗄 Initializing database..."
        python3 -c "from models.db import init_db; init_db()"
    fi
fi
cd ..

# Setup frontend
echo "🎨 Setting up frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
else
    echo "✅ Frontend dependencies already installed"
fi
cd ..

echo ""
echo "🎉 Setup Complete! Starting HackathonHero..."
echo "=============================================="
echo ""

# Start Ollama service
echo "🤖 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!
sleep 3

# Pull default model
echo "📥 Pulling default model (gpt-oss:20b)..."
ollama pull gpt-oss:20b

# Start backend server
echo "🔧 Starting backend server..."
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 5

# Start frontend server
echo "🎨 Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to compile and start
sleep 10

echo ""
echo "🚀 HackathonHero is now running!"
echo "================================"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔗 Backend API: http://localhost:8000/api"
echo ""
echo "📋 Services running in background:"
echo "   - Ollama (PID: $OLLAMA_PID)"
echo "   - Backend (PID: $BACKEND_PID)"
echo "   - Frontend (PID: $FRONTEND_PID)"
echo ""
echo "To stop services: kill $OLLAMA_PID $BACKEND_PID $FRONTEND_PID"
echo ""

# Try to open browser
echo "Opening browser..."
if command_exists xdg-open; then
    xdg-open http://localhost:5173 2>/dev/null &
elif command_exists firefox; then
    firefox http://localhost:5173 &
elif command_exists google-chrome; then
    google-chrome http://localhost:5173 &
elif command_exists chromium-browser; then
    chromium-browser http://localhost:5173 &
else
    echo "Browser not found. Please open http://localhost:5173 manually."
fi

echo ""
echo "🎉 Happy hacking! HackathonHero is ready to use."
