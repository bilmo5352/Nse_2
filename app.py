"""
Flask API for NSE Equity Quote and Financial Report Scraping

Endpoints:
    GET /api/dashboard?symbol=RELIANCE - Scrape equity quote data (dashboard)
    GET /api/financial-report?symbol=RELIANCE - Scrape financial report data
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import logging
from datetime import datetime
from dashbord import scrape_with_homepage_search
from finiancialReport import scrape_with_search

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for all origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configuration from environment variables
FLASK_ENV = os.getenv('FLASK_ENV', 'production')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
DEFAULT_HEADLESS = os.getenv('HEADLESS_MODE', 'false').lower() == 'true'
OUTPUT_DIR = os.getenv('OUTPUT_DIR', os.path.join(os.path.dirname(__file__), "output"))
PORT = int(os.getenv('PORT', 5000))

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Check DISPLAY environment variable if we're on Linux and not in headless mode
import platform
if platform.system() == 'Linux' and not DEFAULT_HEADLESS:
    display = os.environ.get('DISPLAY')
    if not display:
        logger.warning("✗ DISPLAY environment variable is NOT set on Linux!")
        logger.info("Attempting to start xvfb and set DISPLAY...")
        
        # Try to start xvfb programmatically
        try:
            import subprocess
            import time
            
            # Check if xvfb is already running on :99
            check_result = subprocess.run(
                ['xdpyinfo', '-display', ':99'],
                capture_output=True,
                timeout=2
            )
            
            if check_result.returncode == 0:
                logger.info("✓ xvfb is already running on display :99")
                os.environ['DISPLAY'] = ':99'
                display = ':99'
            else:
                # Start xvfb
                logger.info("Starting xvfb on display :99...")
                xvfb_process = subprocess.Popen(
                    ['Xvfb', ':99', '-screen', '0', '1920x1080x24', '-ac', '+extension', 'RANDR'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Wait for xvfb to start
                time.sleep(2)
                
                # Verify it's running
                if xvfb_process.poll() is None:
                    # Process is still running, verify display
                    verify_result = subprocess.run(
                        ['xdpyinfo', '-display', ':99'],
                        capture_output=True,
                        timeout=2
                    )
                    if verify_result.returncode == 0:
                        os.environ['DISPLAY'] = ':99'
                        display = ':99'
                        logger.info("✓ xvfb started successfully and DISPLAY=:99 is now set")
                    else:
                        logger.error("✗ xvfb started but display :99 is not accessible")
                else:
                    logger.error("✗ xvfb process died immediately after starting")
        except FileNotFoundError:
            logger.error("✗ xvfb (Xvfb) command not found. Make sure xvfb is installed.")
        except Exception as e:
            logger.error(f"✗ Failed to start xvfb: {e}")
    
    if display:
        logger.info(f"✓ DISPLAY environment variable is set: {display}")
        # Verify display is accessible
        try:
            import subprocess
            result = subprocess.run(
                ['xdpyinfo', '-display', display],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                logger.info(f"✓ Display {display} is accessible and working")
            else:
                logger.warning(f"⚠ Display {display} is set but may not be accessible")
        except Exception as e:
            logger.warning(f"⚠ Could not verify display accessibility: {e}")
    else:
        logger.error("✗ DISPLAY could not be set. Headed mode will fail.")
        logger.error("✗ Check Railway logs and ensure xvfb packages are installed.")

logger.info(f"Starting NSE Scraper API in {FLASK_ENV} mode")
logger.info(f"Default headless mode: {DEFAULT_HEADLESS}")
logger.info(f"Output directory: {OUTPUT_DIR}")


def run_async(coro):
    """Helper function to run async functions in Flask with gevent compatibility"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Run the coroutine
    try:
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        # If there's a runtime error, create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    """
    Scrape NSE equity quote data (dashboard) by searching from homepage.
    
    Query Parameters:
        symbol (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
        headless (optional): Run browser in headless mode (default: from env or false - headed mode)
        take_screenshot (optional): Save screenshot (default: true)
        output_dir (optional): Output directory path
    
    Example:
        GET /api/dashboard?symbol=RELIANCE
    
    Response:
        {
            "status": "success",
            "symbol": "RELIANCE",
            "data": { ... parsed equity data ... },
            "screenshot": "path/to/screenshot.png",
            "html": "path/to/html.html",
            "json": "path/to/json.json"
        }
    """
    start_time = datetime.now()
    try:
        # Get symbol from query parameters
        symbol = request.args.get('symbol')
        
        if not symbol:
            logger.warning("Dashboard request missing symbol parameter")
            return jsonify({
                "status": "error",
                "error": "Missing required query parameter: 'symbol'"
            }), 400
        
        symbol = symbol.upper().strip()
        logger.info(f"Dashboard request received for symbol: {symbol}")
        
        # Headless: check query parameter first, then env variable, default to False (headed mode)
        headless_param = request.args.get('headless')
        if headless_param is not None:
            headless = headless_param.lower() == 'true'
        else:
            # Use environment variable default, but default to False (headed mode)
            headless = DEFAULT_HEADLESS
        
        logger.info(f"Running dashboard scraper in {'headless' if headless else 'headed'} mode")
        
        # Screenshot: default to True
        take_screenshot = request.args.get('take_screenshot', 'true').lower() == 'true'
        output_dir = request.args.get('output_dir', OUTPUT_DIR)
        
        # Run the async scraper from dashbord.py
        result = run_async(
            scrape_with_homepage_search(
                symbol=symbol,
                output_dir=output_dir,
                headless=headless,
                take_screenshot=take_screenshot
            )
        )
        
        if result.get('status') == 'error':
            error_msg = result.get('error', 'Unknown error occurred')
            logger.error(f"Dashboard scraping failed for {symbol}: {error_msg}")
            return jsonify({
                "status": "error",
                "error": error_msg
            }), 500
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Dashboard scraping completed for {symbol} in {elapsed_time:.2f}s")
        
        # Return success response with parsed data
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "url": result.get('url'),
            "data": result.get('data', {}),
            "screenshot": result.get('screenshot'),
            "html": result.get('html'),
            "json": result.get('json'),
            "timestamp": result.get('timestamp'),
            "elapsed_time_seconds": round(elapsed_time, 2)
        }), 200
        
    except Exception as e:
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.exception(f"Exception in dashboard endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "elapsed_time_seconds": round(elapsed_time, 2)
        }), 500


@app.route('/api/financial-report', methods=['GET'])
def get_financial_report():
    """
    Scrape NSE financial results comparison data.
    
    Query Parameters:
        symbol (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
        headless (optional): Run browser in headless mode (default: from env or false - headed mode)
        output_dir (optional): Output directory path
    
    Example:
        GET /api/financial-report?symbol=RELIANCE
    
    Response:
        {
            "status": "success",
            "symbol": "RELIANCE",
            "parsed_data": { ... financial data ... },
            "screenshot": "path/to/screenshot.png",
            "html": "path/to/html.html",
            "json": "path/to/json.json"
        }
    """
    start_time = datetime.now()
    try:
        # Get symbol from query parameters
        symbol = request.args.get('symbol')
        
        if not symbol:
            logger.warning("Financial report request missing symbol parameter")
            return jsonify({
                "status": "error",
                "error": "Missing required query parameter: 'symbol'"
            }), 400
        
        symbol = symbol.upper().strip()
        logger.info(f"Financial report request received for symbol: {symbol}")
        
        output_dir = request.args.get('output_dir', OUTPUT_DIR)
        
        # Headless: check query parameter first, then env variable, default to False (headed mode)
        headless_param = request.args.get('headless')
        if headless_param is not None:
            headless = headless_param.lower() == 'true'
        else:
            # Use environment variable default, but default to False (headed mode)
            headless = DEFAULT_HEADLESS
        
        logger.info(f"Running financial report scraper in {'headless' if headless else 'headed'} mode")
        
        # Fixed NSE financial results URL
        url = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results-comparision"
        
        # Run the async scraper
        result = run_async(
            scrape_with_search(
                url=url,
                search_term=symbol,
                output_dir=output_dir,
                headless=headless
            )
        )
        
        if result.get('status') == 'error':
            error_msg = result.get('error', 'Unknown error occurred')
            logger.error(f"Financial report scraping failed for {symbol}: {error_msg}")
            return jsonify({
                "status": "error",
                "error": error_msg
            }), 500
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Financial report scraping completed for {symbol} in {elapsed_time:.2f}s")
        
        # Return success response with parsed data
        return jsonify({
            "status": "success",
            "symbol": result.get('search_term'),
            "parsed_data": result.get('parsed_data', {}),
            "screenshot": result.get('screenshot'),
            "html": result.get('html'),
            "json": result.get('json'),
            "timestamp": result.get('timestamp'),
            "elapsed_time_seconds": round(elapsed_time, 2)
        }), 200
        
    except Exception as e:
        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.exception(f"Exception in financial report endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "elapsed_time_seconds": round(elapsed_time, 2)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "NSE Scraper API is running"
    }), 200


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint"""
    return jsonify({
        "name": "NSE Scraper API",
        "version": "2.0.0",
        "description": "API for scraping NSE equity dashboard and financial reports",
        "endpoints": {
            "GET /api/dashboard": {
                "description": "Scrape NSE equity quote data (dashboard) by searching from homepage",
                "required_params": ["symbol"],
                "optional_params": ["headless (default=false - headed mode)", "take_screenshot (default=true)", "output_dir"],
                "example": "/api/dashboard?symbol=RELIANCE"
            },
            "GET /api/financial-report": {
                "description": "Scrape NSE financial results comparison",
                "required_params": ["symbol"],
                "optional_params": ["headless (default=false - headed mode)", "output_dir"],
                "example": "/api/financial-report?symbol=RELIANCE"
            },
            "GET /health": "Health check endpoint"
        },
        "note": "Both endpoints run in headed mode (browser visible) by default. Set headless=true to run in headless mode."
    }), 200


if __name__ == '__main__':
    # For local development
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=PORT)
else:
    # For production (gunicorn)
    logger.info("Running in production mode with gunicorn")

