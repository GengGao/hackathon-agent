#!/bin/bash
# HackathonHero - MacOS Setup Script
# One-liner setup for hackathon participants

set -e  # Exit on any error

echo "🚀 HackathonHero - MacOS Setup"
echo "================================"

# Detect architecture for Homebrew paths
if [[ $(uname -m) == 'arm64' ]]; then
    BREW_PREFIX="/opt/homebrew"
else
    BREW_PREFIX="/usr/local"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check and install Homebrew
if ! command_exists brew; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if ! grep -q 'eval "$(${BREW_PREFIX}/bin/brew shellenv)"' ~/.zshrc 2>/dev/null; then
        echo "eval \"\$(${BREW_PREFIX}/bin/brew shellenv)\"" >> ~/.zshrc
    fi
    eval "$(${BREW_PREFIX}/bin/brew shellenv)"
else
    echo "✅ Homebrew already installed"
fi

# Install Python 3.11+
if ! command_exists python3 || [[ "$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)" < "3.11" ]]; then
    echo "🐍 Installing Python 3.11+..."
    brew install python@3.11
    # Add to shell profile for future sessions
    PYTHON_PATH="${BREW_PREFIX}/opt/python@3.11/bin"
    if ! grep -q "export PATH=\"${PYTHON_PATH}:\$PATH\"" ~/.zshrc 2>/dev/null; then
        echo "export PATH=\"${PYTHON_PATH}:\$PATH\"" >> ~/.zshrc
    fi
    # Set PATH for current session
    export PATH="${PYTHON_PATH}:$PATH"
else
    echo "✅ Python 3.11+ already installed"
fi

# Install Node.js 22+
if ! command_exists node || [[ "$(node --version | cut -d'v' -f2 | cut -d. -f1)" < "22" ]]; then
    echo "📱 Installing Node.js 22+..."
    brew install node@22
    # Add to shell profile for future sessions
    NODE_PATH="${BREW_PREFIX}/opt/node@22/bin"
    if ! grep -q "export PATH=\"${NODE_PATH}:\$PATH\"" ~/.zshrc 2>/dev/null; then
        echo "export PATH=\"${NODE_PATH}:\$PATH\"" >> ~/.zshrc
    fi
    # Set PATH for current session
    export PATH="${NODE_PATH}:$PATH"
else
    echo "✅ Node.js 22+ already installed"
    # Ensure Node.js 22 is in PATH for current session even if already installed
    NODE_PATH="${BREW_PREFIX}/opt/node@22/bin"
    if [[ -d "${NODE_PATH}" ]]; then
        export PATH="${NODE_PATH}:$PATH"
    fi
fi

# Install Tesseract OCR
if ! command_exists tesseract; then
    echo "📖 Installing Tesseract OCR..."
    brew install tesseract
else
    echo "✅ Tesseract OCR already installed"
fi

# Install Ollama
if ! command_exists ollama; then
    echo "🤖 Installing Ollama..."
    brew install ollama
else
    echo "✅ Ollama already installed"
fi

# Verify all required tools are available
echo "🔍 Verifying installed dependencies..."
echo "Current PATH: $PATH"
echo "Node.js version: $(node --version 2>/dev/null || echo 'not found')"
echo "npm version: $(npm --version 2>/dev/null || echo 'not found')"
echo "Python version: $(python3 --version 2>/dev/null || echo 'not found')"

if ! command_exists python3; then
    echo "❌ Python3 not found in PATH. Please restart your terminal or run: source ~/.zshrc"
    exit 1
fi
if ! command_exists node; then
    echo "❌ Node.js not found in PATH. Please restart your terminal or run: source ~/.zshrc"
    echo "Expected Node.js path: ${BREW_PREFIX}/opt/node@22/bin"
    exit 1
fi
if ! command_exists npm; then
    echo "❌ npm not found in PATH. Please restart your terminal or run: source ~/.zshrc"
    exit 1
fi
echo "✅ All dependencies verified"

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
    python -c "from models.db import init_db; init_db()"
else
    echo "✅ Backend environment already exists, activating..."
    source .venv/bin/activate
    # Check if database needs initialization
    if [ ! -f "hackathon.db" ]; then
        echo "🗄 Initializing database..."
        python -c "from models.db import init_db; init_db()"
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
echo "   - Ollama (PID: auto-managed)"
echo "   - Backend (PID: $BACKEND_PID)"
echo "   - Frontend (PID: $FRONTEND_PID)"
echo ""
echo "To stop services: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Opening browser..."
if command_exists open; then
    open http://localhost:5173
elif command_exists xdg-open; then
    xdg-open http://localhost:5173
fi

echo ""
echo "🎉 Happy hacking! HackathonHero is ready to use."
