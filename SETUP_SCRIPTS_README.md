# HackathonHero Complete Setup & Run Scripts

**TRUE one-liner scripts** - Run once, get HackathonHero fully running with browser auto-opened!

## 🚀 Complete One-Liner Commands

### MacOS
```bash
curl -fsSL https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-macos.sh | bash
```

### Linux (Ubuntu/Debian/CentOS/Arch)
```bash
curl -fsSL https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-linux.sh | bash
```

### Windows (PowerShell as Administrator)
```powershell
# Download and run the setup script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/genggao/hackathon-agent/main/setup-windows.ps1" -OutFile "setup-windows.ps1"
.\setup-windows.ps1
```

## 📋 What These Scripts Do (COMPLETE Automation)

### ✅ Automated Installation
- **Python 3.11+**: Required for backend API
- **Node.js 22+**: Required for frontend React app
- **Tesseract OCR**: For image text extraction
- **Ollama**: Local LLM runtime
- **Git**: Version control (if not present)

### ✅ Project Setup
- Clone HackathonHero repository
- Set up Python virtual environment
- Install backend dependencies (FastAPI, SQLite, etc.)
- Install frontend dependencies (React, Tailwind, etc.)
- Initialize database with migrations

### ✅ AUTO-RUN Services
- **Start Ollama service** in background
- **Download default model** (gpt-oss:20b)
- **Start backend server** (http://localhost:8000)
- **Start frontend server** (http://localhost:5173)
- **Auto-open browser** to HackathonHero

### ✅ Result
**After running the script, HackathonHero opens automatically in your browser - ready to use!** 🎉

## 🔧 Service Management

### Stopping Services
If you need to stop the background services:

#### MacOS/Linux
```bash
# Find and kill the processes
kill $(pgrep -f "uvicorn|npm|ollama")
```

#### Windows
```powershell
# Stop background jobs
Get-Job | Stop-Job
Get-Job | Remove-Job
```

### Restarting Services
Simply re-run the setup script, or manually start services:

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn main:app --reload

# Frontend (new terminal)
cd frontend && npm run dev

# Ollama (new terminal)
ollama serve
```

## 🔧 Script Details

### MacOS (`setup-macos.sh`)
- Uses Homebrew for package management
- Installs all dependencies via `brew`
- Sets up Python virtual environment
- Handles PATH updates for shell

### Linux (`setup-linux.sh`)
- Auto-detects package manager (apt/dnf/pacman)
- Installs system packages appropriately
- Handles different Linux distributions
- Uses official Ollama installation script

### Windows (`setup-windows.ps1`)
- Uses winget (Windows 11+) or Chocolatey
- Downloads Ollama installer (requires manual completion)
- PowerShell-native virtual environment setup
- Handles Windows-specific path requirements

## 🐛 Troubleshooting

### Common Issues

#### Permission Denied (MacOS/Linux)
```bash
chmod +x setup-*.sh
```

#### Python Version Issues
If you have multiple Python versions:
```bash
# MacOS/Linux
python3.11 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.\venv\Scripts\activate
```

#### Ollama Won't Start
```bash
# Kill existing processes
pkill ollama

# Start fresh
ollama serve
```

#### Port Already in Use
Backend uses port 8000, frontend uses 5173:
```bash
# Find what's using the port
lsof -i :8000
lsof -i :5173

# Kill the process
kill -9 <PID>
```

### Manual Installation
If automated scripts fail, see [README.md](README.md) for manual setup instructions.

## 🎯 For Hackathon Organizers

These scripts are perfect for:
- **Quick Demos**: Get running in 5-10 minutes
- **Judge Evaluation**: Easy setup for evaluation
- **Participant Onboarding**: Minimal technical barrier
- **Offline Events**: Everything runs locally

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. See the main [README.md](README.md) for detailed instructions
3. Check GitHub Issues for known problems

**Happy Hacking! 🚀**
