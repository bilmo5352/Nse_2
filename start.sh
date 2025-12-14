#!/bin/bash
# Startup script for Railway deployment
# Sets up xvfb for headed mode and starts the application

set -e

echo "Starting xvfb for virtual display..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension RANDR &
XVFB_PID=$!

# Wait for xvfb to start
sleep 2

# Check if xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Failed to start xvfb"
    exit 1
fi

echo "xvfb started successfully on display :99"
export DISPLAY=:99

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 --worker-class gevent --access-logfile - --error-logfile - --log-level info app:app

