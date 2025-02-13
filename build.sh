#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y \
    poppler-utils \
    python3-opencv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    python3-dev

# Upgrade pip and install build tools
python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies with specific order
pip install --no-cache-dir numpy
pip install --no-cache-dir torch torchvision
pip install --no-cache-dir -r requirements.txt

# Create required directories
mkdir -p uploads
mkdir -p logs
