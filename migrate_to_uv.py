#!/usr/bin/env python3
"""
Migration script to help users transition from pip to uv.
This script will help set up the uv environment and sync dependencies.
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, shell: bool = False) -> bool:
    """Run a command and return True if successful."""
    try:
        result = subprocess.run(
            command.split() if not shell else command,
            shell=shell,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run: {command}")
        print(f"Error: {e.stderr}")
        return False


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    """Main migration function."""
    print("🚀 Migrating chatbot-with-rag from pip to uv...")
    
    # Check if uv is installed
    if not check_uv_installed():
        print("❌ uv is not installed. Please install it first:")
        print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("   Or visit: https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)
    
    print("✅ uv is installed")
    
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        print("❌ pyproject.toml not found. Make sure you're in the project root directory.")
        sys.exit(1)
    
    print("✅ pyproject.toml found")
    
    # Remove existing virtual environment if it exists
    venv_path = Path(".venv")
    if venv_path.exists():
        print("🗑️  Removing existing .venv directory...")
        import shutil
        shutil.rmtree(venv_path)
    
    # Create new virtual environment with uv
    print("📦 Creating new virtual environment with uv...")
    if not run_command("uv venv .venv"):
        sys.exit(1)
    
    # Sync dependencies
    print("⬇️  Installing dependencies...")
    if not run_command("uv sync"):
        sys.exit(1)
    
    print("\n🎉 Migration completed successfully!")
    print("\nNext steps:")
    print("1. Activate your virtual environment:")
    print("   source .venv/bin/activate")
    print("2. Copy your .env file:")
    print("   cp .env.sample .env")
    print("3. Edit .env with your API keys")
    print("4. Run the application:")
    print("   python src/main.py")
    print("\nFor development, you can install dev dependencies with:")
    print("   uv sync --dev")


if __name__ == "__main__":
    main()
