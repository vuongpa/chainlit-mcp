#!/bin/bash

# Quick start script for chatbot-with-rag using uv
# This script will set up the environment and run the application

set -e  # Exit on any error

echo "🚀 Setting up chatbot-with-rag with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ uv is installed"

# Create virtual environment and sync dependencies
echo "📦 Creating virtual environment and installing dependencies..."
uv sync

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.sample" ]; then
        echo "📝 Creating .env file from template..."
        cp .env.sample .env
        echo "⚠️  Please edit .env file and add your API keys:"
        echo "   - OPENAI_API_KEY (for OpenAI models and embeddings)"
        echo "   - ANTHROPIC_API_KEY (for Claude models)"
        echo "   - ELEVENLABS_API_KEY (for text-to-speech, optional)"
        echo ""
        echo "You only need to set one LLM API key to get started."
        echo ""
        read -p "Press Enter to continue after setting up your API keys..."
    else
        echo "❌ .env.sample file not found. Please create a .env file with your API keys."
        exit 1
    fi
else
    echo "✅ .env file exists"
fi

# Activate virtual environment and run the application
echo "🎉 Setup complete! Starting the application..."
echo ""
echo "The application will start in a few seconds..."
echo "Open your browser to http://127.0.0.1:8000 when ready."
echo ""

# Use uv run to run the application in the virtual environment
uv run python src/main.py
