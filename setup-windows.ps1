# HackathonHero - Windows Setup Script
# One-liner setup for hackathon participants

param(
    [switch]$SkipAdminCheck = $false
)

Write-Host "🚀 HackathonHero - Windows Setup" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Check if running as administrator
if (-not $SkipAdminCheck) {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "⚠️  Please run this script as Administrator for proper installation." -ForegroundColor Yellow
        Read-Host "Press Enter to continue anyway, or Ctrl+C to cancel"
    }
}

# Function to check if command exists
function Test-Command($cmdname) {
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Function to install with winget or chocolatey
function Install-Package {
    param([string]$PackageName, [string]$WingetId = "", [string]$ChocoId = "")

    if (Test-Command winget) {
        if ($WingetId) {
            Write-Host "📦 Installing $PackageName via winget..."
            winget install --id $WingetId --accept-source-agreements --accept-package-agreements
        } else {
            Write-Host "📦 Installing $PackageName via winget..."
            winget install $PackageName --accept-source-agreements --accept-package-agreements
        }
    } elseif (Test-Command choco) {
        if ($ChocoId) {
            Write-Host "📦 Installing $PackageName via chocolatey..."
            choco install $ChocoId -y
        } else {
            Write-Host "📦 Installing $PackageName via chocolatey..."
            choco install $PackageName -y
        }
    } else {
        Write-Host "❌ Neither winget nor chocolatey found. Please install $PackageName manually." -ForegroundColor Red
        return $false
    }
    return $true
}

# Check and install Python 3.11+
$pythonVersion = $null
if (Test-Command python) {
    $pythonVersion = python --version 2>&1
} elseif (Test-Command python3) {
    $pythonVersion = python3 --version 2>&1
}

if (-not $pythonVersion -or $pythonVersion -notmatch "Python (\d+)\.(\d+)") {
    Write-Host "🐍 Installing Python 3.11+..."
    $installed = Install-Package -PackageName "Python 3.11" -WingetId "Python.Python.3.11" -ChocoId "python311"
    if (-not $installed) {
        Write-Host "Please install Python 3.11+ manually from https://python.org" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Python already installed: $pythonVersion" -ForegroundColor Green
}

# Check and install Node.js 22+
$nodeVersion = $null
if (Test-Command node) {
    $nodeVersion = node --version
}

if (-not $nodeVersion -or [int]$nodeVersion.Split('.')[0].TrimStart('v') -lt 22) {
    Write-Host "📱 Installing Node.js 22+..."
    $installed = Install-Package -PackageName "Node.js" -WingetId "OpenJS.NodeJS" -ChocoId "nodejs"
    if (-not $installed) {
        Write-Host "Please install Node.js 22+ manually from https://nodejs.org" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Node.js already installed: $nodeVersion" -ForegroundColor Green
}

# Install Tesseract OCR
if (-not (Test-Command tesseract)) {
    Write-Host "📖 Installing Tesseract OCR..."
    $installed = Install-Package -PackageName "Tesseract OCR" -WingetId "UB-Mannheim.TesseractOCR" -ChocoId "tesseract"
    if (-not $installed) {
        Write-Host "Please install Tesseract OCR manually from https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Tesseract OCR already installed" -ForegroundColor Green
}

# Install Git if not present
if (-not (Test-Command git)) {
    Write-Host "📦 Installing Git..."
    $installed = Install-Package -PackageName "Git" -WingetId "Git.Git" -ChocoId "git"
    if (-not $installed) {
        Write-Host "Please install Git manually from https://git-scm.com" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ Git already installed" -ForegroundColor Green
}

# Install Ollama
if (-not (Test-Command ollama)) {
    Write-Host "🤖 Installing Ollama..."
    try {
        # Download and install Ollama
        $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
        $tempPath = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $tempPath
        Write-Host "Running Ollama installer... Please complete the installation manually."
        Start-Process $tempPath -Wait
        Remove-Item $tempPath -ErrorAction SilentlyContinue
    } catch {
        Write-Host "❌ Failed to download Ollama. Please install manually from https://ollama.com" -ForegroundColor Red
    }
} else {
    Write-Host "✅ Ollama already installed" -ForegroundColor Green
}

# Check if we're already in the repository or need to clone/navigate
if ((Test-Path "backend\main.py") -and (Test-Path "frontend\package.json")) {
    Write-Host "✅ Already in HackathonHero repository directory" -ForegroundColor Green
} else {
    if (-not (Test-Path "hackathon-agent")) {
        Write-Host "📥 Cloning HackathonHero repository..."
        git clone https://github.com/genggao/hackathon-agent.git
        Set-Location hackathon-agent
    } else {
        Write-Host "✅ Repository already cloned" -ForegroundColor Green
        Set-Location hackathon-agent
    }
}

# Setup backend
Write-Host "🔧 Setting up backend..."
Set-Location backend
if (-not (Test-Path ".venv") -or -not (Test-Path ".venv\Scripts\Activate")) {
    Write-Host "🐍 Creating Python virtual environment..."
    python -m venv .venv
    & ".venv\Scripts\Activate"
    pip install -r requirements.txt
    python -c "from models.db import init_db; init_db()"
} else {
    Write-Host "✅ Backend environment already exists, activating..." -ForegroundColor Green
    & ".venv\Scripts\Activate"
    # Check if database needs initialization
    if (-not (Test-Path "hackathon.db")) {
        Write-Host "🗄️ Initializing database..."
        python -c "from models.db import init_db; init_db()"
    }
}
Set-Location ..

# Setup frontend
Write-Host "🎨 Setting up frontend..."
Set-Location frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing frontend dependencies..."
    npm install
} else {
    Write-Host "✅ Frontend dependencies already installed" -ForegroundColor Green
}
Set-Location ..

Write-Host ""
Write-Host "🎉 Setup Complete! Starting HackathonHero..." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""

# Start Ollama service (may require manual start)
Write-Host "🤖 Starting Ollama service..." -ForegroundColor Yellow
try {
    $ollamaJob = Start-Job -ScriptBlock {
        ollama serve
    }
    Start-Sleep 3
    Write-Host "✅ Ollama service started in background" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama service may need manual start. Please run 'ollama serve' in a separate terminal." -ForegroundColor Yellow
}

# Pull default model
Write-Host "📥 Pulling default model (gpt-oss:20b)..." -ForegroundColor Yellow
try {
    ollama pull gpt-oss:20b
    Write-Host "✅ Model downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Model download may have failed. You can run 'ollama pull gpt-oss:20b' manually later." -ForegroundColor Yellow
}

# Start backend server
Write-Host "🔧 Starting backend server..." -ForegroundColor Yellow
Set-Location backend
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    & ".venv\Scripts\Activate"
    uvicorn main:app --reload --host 0.0.0.0
}
Set-Location ..
Start-Sleep 5

# Start frontend server
Write-Host "🎨 Starting frontend server..." -ForegroundColor Yellow
Set-Location frontend
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    npm run dev
}
Set-Location ..

# Wait for frontend to compile and start
Start-Sleep 10

Write-Host ""
Write-Host "🚀 HackathonHero is now running!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Frontend: http://localhost:5173" -ForegroundColor Blue
Write-Host "🔗 Backend API: http://localhost:8000/api" -ForegroundColor Blue
Write-Host ""
Write-Host "📋 Services running in background:" -ForegroundColor Cyan
Write-Host "   - Ollama (Job ID: $($ollamaJob.Id))"
Write-Host "   - Backend (Job ID: $($backendJob.Id))"
Write-Host "   - Frontend (Job ID: $($frontendJob.Id))"
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Yellow
Write-Host "   Stop-Job $($ollamaJob.Id), $($backendJob.Id), $($frontendJob.Id); Remove-Job $($ollamaJob.Id), $($backendJob.Id), $($frontendJob.Id)"
Write-Host ""

# Try to open browser
Write-Host "Opening browser..." -ForegroundColor Yellow
try {
    Start-Process "http://localhost:5173"
    Write-Host "✅ Browser opened successfully" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not open browser automatically. Please visit http://localhost:5173 manually." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Happy hacking! HackathonHero is ready to use." -ForegroundColor Green
