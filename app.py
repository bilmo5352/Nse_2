"""
Flask API for NSE Equity Quote and Financial Report Scraping

Endpoints:
    GET /api/equity-quote?symbol=RELIANCE - Scrape equity quote data
    GET /api/financial-report?symbol=RELIANCE - Scrape financial report data
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import urllib.parse
from equity_quote_run import scrape_equity_quote
from finiancialReport import scrape_with_search

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Default output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_async(coro):
    """Helper function to run async functions in Flask"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@app.route('/api/equity-quote', methods=['GET'])
def get_equity_quote():
    """
    Scrape NSE equity quote data.
    
    Query Parameters:
        symbol (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
        name   (required): Company slug as shown in NSE URL (e.g., Reliance-Industries-Limited)
        headless (optional): Run browser in headless mode (default: true)
        take_screenshot (optional): Save screenshot (default: false)
    
    Example:
        GET /api/equity-quote?symbol=RELIANCE
    
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
    try:
        # Get symbol and name from query parameters
        symbol = request.args.get('symbol')
        company_name = request.args.get('name')
        
        if not symbol:
            return jsonify({
                "status": "error",
                "error": "Missing required query parameter: 'symbol'"
            }), 400
        if not company_name:
            return jsonify({
                "status": "error",
                "error": "Missing required query parameter: 'name' (e.g., Reliance-Industries-Limited)"
            }), 400
        
        symbol = symbol.upper().strip()
        # Normalize the company slug: strip, replace spaces with hyphens, URL-encode safely
        company_slug = company_name.strip().replace(" ", "-")
        company_slug = urllib.parse.quote(company_slug, safe="-")
        
        # Construct NSE equity quote URL from symbol + name
        # Format: https://www.nseindia.com/get-quote/equity/{SYMBOL}/{COMPANY-SLUG}
        url = f"https://www.nseindia.com/get-quote/equity/{symbol}/{company_slug}"
        
        # Get optional parameters (default headless=True)
        headless = request.args.get('headless', 'true').lower() == 'true'
        take_screenshot = request.args.get('take_screenshot', 'false').lower() == 'true'  # Default to False to save resources
        output_dir = request.args.get('output_dir', OUTPUT_DIR)
        
        # Run the async scraper
        result = run_async(
            scrape_equity_quote(
                url=url,
                output_dir=output_dir,
                headless=headless,
                take_screenshot=take_screenshot
            )
        )
        
        if result.get('status') == 'error':
            return jsonify({
                "status": "error",
                "error": result.get('error', 'Unknown error occurred')
            }), 500
        
        # Return success response with parsed data
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "url": result.get('url'),
            "data": result.get('data', {}),
            "screenshot": result.get('screenshot'),
            "html": result.get('html'),
            "json": result.get('json'),
            "timestamp": result.get('timestamp')
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route('/api/financial-report', methods=['GET'])
def get_financial_report():
    """
    Scrape NSE financial results comparison data.
    
    Query Parameters:
        symbol (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
        headless (optional): Run browser in headless mode (default: true)
    
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
    try:
        # Get symbol from query parameters
        symbol = request.args.get('symbol')
        
        if not symbol:
            return jsonify({
                "status": "error",
                "error": "Missing required query parameter: 'symbol'"
            }), 400
        
        symbol = symbol.upper().strip()
        output_dir = request.args.get('output_dir', OUTPUT_DIR)
        headless = request.args.get('headless', 'true').lower() == 'true'  # Default to headless=True
        
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
            return jsonify({
                "status": "error",
                "error": result.get('error', 'Unknown error occurred')
            }), 500
        
        # Return success response with parsed data
        return jsonify({
            "status": "success",
            "symbol": result.get('search_term'),
            "parsed_data": result.get('parsed_data', {}),
            "screenshot": result.get('screenshot'),
            "html": result.get('html'),
            "json": result.get('json'),
            "timestamp": result.get('timestamp')
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
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
        "version": "1.0.0",
        "endpoints": {
            "GET /api/equity-quote": {
                "description": "Scrape NSE equity quote data",
                "required_params": ["symbol", "name (company slug, e.g., Reliance-Industries-Limited)"],
                "optional_params": ["headless (default=true)", "take_screenshot", "output_dir"],
                "example": "/api/equity-quote?symbol=RELIANCE&name=Reliance-Industries-Limited&headless=true"
            },
            "GET /api/financial-report": {
                "description": "Scrape NSE financial results comparison",
                "required_params": ["symbol"],
                "optional_params": ["headless (default=true)", "output_dir"],
                "example": "/api/financial-report?symbol=RELIANCE&headless=true"
            },
            "GET /health": "Health check endpoint"
        }
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

