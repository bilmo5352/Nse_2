# Headed Mode Setup - DISPLAY Configuration

## Overview
This application is configured to run in **headed mode** (not headless) with a virtual display (xvfb) on Railway.

## How It Works

### 1. Startup Script (`start.sh`)
- Starts xvfb (X Virtual Framebuffer) on display `:99`
- Verifies xvfb is running and accessible
- Sets `DISPLAY=:99` environment variable
- Exports DISPLAY to all child processes
- Starts Gunicorn with `DISPLAY=:99` explicitly set

### 2. Application Startup (`app.py`)
- Checks if `DISPLAY` is set on Linux
- Verifies display accessibility using `xdpyinfo`
- Logs warnings if DISPLAY is not set
- Confirms headed mode configuration

### 3. Browser Launch (`browser_utils.py`)
- Checks if `DISPLAY` is available when headed mode is requested
- **Raises RuntimeError** if headed mode is requested but DISPLAY is not set
- **Does NOT fall back to headless mode** - fails with clear error instead
- Returns `headless=False` when DISPLAY is available

### 4. Scrapers (`dashbord.py`, `finiancialReport.py`)
- Use `get_browser_launch_args()` to determine headless/headed mode
- Log whether running in HEADED or HEADLESS mode
- Launch browser with `headless=False` when DISPLAY is available

## Verification Steps

### On Startup, You Should See:
```
==========================================
Setting up xvfb for virtual display...
==========================================
Starting Xvfb on display :99...
Waiting for xvfb to initialize...
Verifying display accessibility...
✓ xvfb started successfully on display :99
✓ Display verified and accessible
DISPLAY environment variable: :99
Final verification of DISPLAY...
Display info: [display info]
==========================================
Starting Gunicorn server with DISPLAY=:99
==========================================
```

### In Application Logs:
```
✓ DISPLAY environment variable is set: :99
✓ Display :99 is accessible and working
[INFO] Running in HEADED mode with DISPLAY=:99
```

## If DISPLAY Is Not Set

The application will **fail with a clear error** instead of silently falling back to headless:

```
RuntimeError: ERROR: Headed mode requested but DISPLAY environment variable is not set.
This means xvfb (X Virtual Framebuffer) is not running.
The startup script (start.sh) should start xvfb and set DISPLAY=:99.
...
Cannot proceed with headed mode - the page requires a display to load correctly.
```

## Configuration Files

- **`start.sh`**: Sets up xvfb and DISPLAY
- **`Procfile`**: Runs `start.sh`
- **`nixpacks.toml`**: Installs xvfb packages
- **`browser_utils.py`**: Validates DISPLAY and enforces headed mode
- **`app.py`**: Verifies DISPLAY on startup

## Key Points

✅ **DISPLAY is always set** before Gunicorn starts
✅ **Headed mode is enforced** - no silent fallback to headless
✅ **Clear error messages** if DISPLAY is missing
✅ **Verification at multiple levels** (startup script, app startup, browser launch)
✅ **All workers inherit DISPLAY** via `env DISPLAY=:99`

## Testing

After deployment, check Railway logs for:
1. xvfb startup confirmation
2. DISPLAY variable verification
3. "Running in HEADED mode" messages
4. Successful browser launches

The browser will run in headed mode using the virtual display, allowing the NSE pages to load correctly.

