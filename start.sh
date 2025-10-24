#!/bin/bash

# Stock Tracker App Startup Script

echo "Starting Stock Tracker App..."
echo "=============================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements if needed
echo "Installing/updating requirements..."
pip install -r requirements.txt

# Start the Streamlit app
echo "Starting Streamlit app..."
echo "The app will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop the app"
echo ""

streamlit run app.py
