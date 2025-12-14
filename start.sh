#!/bin/bash
# Startup script for Railway deployment
# Sets up xvfb for headed mode and starts the application

set -e

echo "=========================================="
echo "Setting up xvfb for virtual display..."
echo "=========================================="

# Start xvfb in the background
echo "Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension RANDR &
XVFB_PID=$!

# Wait for xvfb to start
echo "Waiting for xvfb to initialize..."
sleep 3

# Check if xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Failed to start xvfb"
    echo "xvfb process died immediately after starting"
    exit 1
fi

# Verify xvfb is actually working
echo "Verifying display accessibility..."
if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    echo "ERROR: xvfb started but display :99 is not accessible"
    kill $XVFB_PID 2>/dev/null || true
    exit 1
fi

echo "✓ xvfb started successfully on display :99"
echo "✓ Display verified and accessible"

# Set DISPLAY environment variable for this session and all child processes
export DISPLAY=:99

# Verify DISPLAY is set
echo "DISPLAY environment variable: $DISPLAY"
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY variable is not set!"
    exit 1
fi

# Double-check DISPLAY is accessible
echo "Final verification of DISPLAY..."
DISPLAY_INFO=$(xdpyinfo -display :99 2>&1 | head -1)
echo "Display info: $DISPLAY_INFO"

echo "=========================================="
echo "Starting Gunicorn server with DISPLAY=:99"
echo "=========================================="

# Start the application with DISPLAY explicitly set in environment
# This ensures all Gunicorn workers inherit the DISPLAY variable
exec env DISPLAY=:99 gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 --worker-class gevent --access-logfile - --error-logfile - --log-level info app:app

