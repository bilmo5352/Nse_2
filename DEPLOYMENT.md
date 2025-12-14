# Railway Deployment Guide - Headed Mode Fix

## Problem
Railway runs in a headless Linux environment without an X server. When trying to run Playwright in headed mode, you get the error:
```
Missing X server or $DISPLAY
Looks like you launched a headed browser without having a XServer running.
```

## Solution
We use **xvfb** (X Virtual Framebuffer) to create a virtual display, allowing headed mode to work on Railway.

## How It Works

1. **Startup Script (`start.sh`)**: 
   - Starts xvfb on display `:99` before the application
   - Sets `DISPLAY=:99` environment variable
   - Starts Gunicorn server

2. **Browser Utils (`browser_utils.py`)**:
   - Checks if `DISPLAY` environment variable is set
   - If not set on Linux, falls back to headless mode
   - If set, allows headed mode to work

3. **Updated Scrapers**:
   - Both `dashbord.py` and `finiancialReport.py` use `get_browser_launch_args()`
   - Automatically handles headed mode in headless environments

## Files Modified

- ✅ `start.sh` - Startup script that launches xvfb
- ✅ `browser_utils.py` - Utility to handle display detection
- ✅ `dashbord.py` - Updated to use browser utils
- ✅ `finiancialReport.py` - Updated to use browser utils
- ✅ `Procfile` - Uses startup script
- ✅ `nixpacks.toml` - Includes xvfb packages and uses startup script
- ✅ `railway.json` - Updated start command

## Deployment

1. **Push to Railway**: The deployment will automatically:
   - Install xvfb via nixpacks
   - Run `start.sh` which sets up the virtual display
   - Start the Flask API

2. **Environment Variables** (optional):
   - `HEADLESS_MODE=false` - Keep headed mode (default)
   - The startup script handles xvfb automatically

## Testing

After deployment, test the endpoints:
```bash
curl "https://your-app.railway.app/api/dashboard?symbol=RELIANCE"
curl "https://your-app.railway.app/api/financial-report?symbol=TCS"
```

The browser will run in headed mode using the virtual display, allowing the scraping to work correctly.

## Troubleshooting

If you still get display errors:
1. Check Railway logs to see if xvfb started successfully
2. Verify `DISPLAY=:99` is set in the environment
3. Check that xvfb packages are installed (should be automatic via nixpacks)

## Notes

- The virtual display is not visible (it's virtual)
- Functionality is identical to a real display
- Scraping works exactly as if you had a real display
- This is the standard solution for running GUI applications on headless servers

