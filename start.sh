#!/bin/bash

export PATH="/opt/local/bin:$PATH"


PROJECT_DIR="/Volumes/PNY 480G/GitHub/Tutorial/media_press"

cd "$PROJECT_DIR"


source "$PROJECT_DIR/venv/bin/activate"

echo "🚀 Launch of Media Press..."

python3 press.py

echo "✅ Media Press has completed its work."