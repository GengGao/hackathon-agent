#!/usr/bin/env python3
"""Installation script for LangExtract integration."""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {cmd}")
        print(f"   Error: {e.stderr}")
        return False

def check_ollama():
    """Check if Ollama is running and has required models."""
    print("🔍 Checking Ollama setup...")

    # Check if Ollama is running
    try:
        result = subprocess.run("ollama list", shell=True, check=True, capture_output=True, text=True)
        print("✅ Ollama is running")

        # Check for gpt-oss:20b model
        if "gpt-oss:20b" in result.stdout:
            print("✅ gpt-oss:20b model is available")
            return True
        else:
            print("⚠️  gpt-oss:20b model not found")
            print("   Run: ollama pull gpt-oss:20b")
            return False

    except subprocess.CalledProcessError:
        print("❌ Ollama is not running or not installed")
        print("   Please install Ollama from https://ollama.com")
        print("   Then run: ollama pull gpt-oss:20b")
        return False

def install_dependencies():
    """Install required Python dependencies."""
    print("📦 Installing Python dependencies...")

    # Install LangExtract
    if not run_command("pip install langextract>=0.1.0", "Installing LangExtract"):
        return False

    # Install other dependencies if needed
    requirements_path = Path(__file__).parent / "requirements.txt"
    if requirements_path.exists():
        if not run_command(f"pip install -r {requirements_path}", "Installing requirements"):
            return False

    return True

def run_migrations():
    """Run database migrations."""
    print("🗄️  Running database migrations...")

    try:
        # Add current directory to Python path
        sys.path.insert(0, str(Path(__file__).parent))

        from models.db import init_db
        init_db()
        print("✅ Database migrations completed")
        return True

    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def test_installation():
    """Test the installation."""
    print("🧪 Testing installation...")

    try:
        # Test import
        from extractors.rule_extractor import RuleExtractor

        # Test initialization
        extractor = RuleExtractor()
        print(f"✅ RuleExtractor initialized (LangExtract available: {extractor.langextract_available})")

        # Test basic extraction
        test_text = "Rule 1.1 – Test\nThis is a test rule for eligibility."
        results = extractor._safe_extract(test_text)
        print(f"✅ Basic extraction test passed ({len(results)} results)")

        return True

    except Exception as e:
        print(f"❌ Installation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main installation process."""
    print("🚀 LangExtract Integration Installation\n")

    steps = [
        ("Checking Ollama setup", check_ollama),
        ("Installing dependencies", install_dependencies),
        ("Running migrations", run_migrations),
        ("Testing installation", test_installation)
    ]

    failed_steps = []

    for step_name, step_func in steps:
        print(f"\n{'='*50}")
        if not step_func():
            failed_steps.append(step_name)

    print(f"\n{'='*50}")
    print("INSTALLATION SUMMARY:")

    if not failed_steps:
        print("🎉 Installation completed successfully!")
        print("\nNext steps:")
        print("1. Run: python test_rule_extraction.py")
        print("2. Start your application to test the enhanced RAG system")
        return 0
    else:
        print("⚠️  Installation completed with issues:")
        for step in failed_steps:
            print(f"   ❌ {step}")
        print("\nPlease resolve the issues above and run the installation again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())