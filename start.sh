#!/bin/bash
# Startup script for Railway deployment
# Sets up xvfb for headed mode and starts the application

set -e

# Make sure we're in the right directory
cd "$(dirname "$0")" || exit 1

echo "=========================================="
echo "Setting up xvfb for virtual display..."
echo "=========================================="

DISPLAY_NUM=99
LOCK_FILE="/tmp/.X${DISPLAY_NUM}-lock"
PID_FILE="/tmp/.X${DISPLAY_NUM}-pid"

# Function to check if xvfb is actually running
check_xvfb_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            # Check if it's actually an xvfb process
            if ps -p "$pid" -o comm= | grep -q "Xvfb"; then
                return 0  # xvfb is running
            fi
        fi
    fi
    return 1  # xvfb is not running
}

# Function to cleanup stale lock files
cleanup_stale_lock() {
    if [ -f "$LOCK_FILE" ]; then
        echo "Found lock file $LOCK_FILE, checking if process is alive..."
        if ! check_xvfb_running; then
            echo "xvfb process is not running, removing stale lock file..."
            rm -f "$LOCK_FILE" "$PID_FILE"
            return 0
        else
            echo "xvfb is already running, will use existing instance"
            return 1
        fi
    fi
    return 0
}

# Check if xvfb is already running and accessible
if xdpyinfo -display :${DISPLAY_NUM} >/dev/null 2>&1; then
    echo "✓ xvfb is already running on display :${DISPLAY_NUM} and is accessible"
    export DISPLAY=:${DISPLAY_NUM}
elif check_xvfb_running; then
    echo "✓ xvfb process is running, waiting for display to become accessible..."
    sleep 2
    if xdpyinfo -display :${DISPLAY_NUM} >/dev/null 2>&1; then
        echo "✓ Display :${DISPLAY_NUM} is now accessible"
        export DISPLAY=:${DISPLAY_NUM}
    else
        echo "⚠ xvfb process exists but display is not accessible, cleaning up..."
        cleanup_stale_lock
    fi
else
    # Clean up stale lock files
    cleanup_stale_lock
    
    # Start xvfb
    echo "Starting Xvfb on display :${DISPLAY_NUM}..."
    Xvfb :${DISPLAY_NUM} -screen 0 1920x1080x24 -ac +extension RANDR -nolisten tcp &
    XVFB_PID=$!
    
    # Save PID
    echo $XVFB_PID > "$PID_FILE"
    
    # Wait for xvfb to start
    echo "Waiting for xvfb to initialize..."
    sleep 3
    
    # Check if xvfb is running
    if ! kill -0 $XVFB_PID 2>/dev/null; then
        echo "ERROR: Failed to start xvfb"
        echo "xvfb process died immediately after starting"
        rm -f "$PID_FILE" "$LOCK_FILE"
        exit 1
    fi
    
    # Verify xvfb is actually working
    echo "Verifying display accessibility..."
    if ! xdpyinfo -display :${DISPLAY_NUM} >/dev/null 2>&1; then
        echo "ERROR: xvfb started but display :${DISPLAY_NUM} is not accessible"
        kill $XVFB_PID 2>/dev/null || true
        rm -f "$PID_FILE" "$LOCK_FILE"
        exit 1
    fi
    
    echo "✓ xvfb started successfully on display :${DISPLAY_NUM}"
    echo "✓ Display verified and accessible"
    export DISPLAY=:${DISPLAY_NUM}
fi

# Verify DISPLAY is set
echo "DISPLAY environment variable: $DISPLAY"
if [ -z "$DISPLAY" ]; then
    echo "ERROR: DISPLAY variable is not set!"
    exit 1
fi

# Final verification
echo "Final verification of DISPLAY..."
DISPLAY_INFO=$(xdpyinfo -display $DISPLAY 2>&1 | head -1 || echo "Display check failed")
echo "Display info: $DISPLAY_INFO"

echo "=========================================="
echo "Starting Gunicorn server with DISPLAY=$DISPLAY"
echo "=========================================="

# Start the application with DISPLAY explicitly set in environment
# This ensures all Gunicorn workers inherit the DISPLAY variable
exec env DISPLAY=$DISPLAY gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 --worker-class gevent --access-logfile - --error-logfile - --log-level info app:app

