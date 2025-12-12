# NSE Scraper API

Flask API for scraping NSE (National Stock Exchange) equity quotes and financial reports.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Running the API

```bash
python app.py
```

The API will start on `http://localhost:5000`

## API Endpoints

### 1. Equity Quote Endpoint

**GET** `/api/equity-quote`

Scrapes NSE equity quote page and extracts comprehensive stock data.

**Query Parameters:**
- `symbol` (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
- `name` (required): Company slug exactly as in NSE URL (e.g., `Reliance-Industries-Limited`)
  - Find this by visiting NSE website - the URL will show the format: `/equity/{SYMBOL}/{COMPANY-NAME}`
- `headless` (optional): Run browser in headless mode (default: true)
  - Set to `false` to see browser window (useful for debugging)
  - Query parameter takes precedence over environment variable
- `take_screenshot` (optional): Save screenshot (default: false)
- `output_dir` (optional): Output directory path

**Response:**
```json
{
    "status": "success",
    "symbol": "RELIANCE",
    "url": "...",
    "data": {
        "symbol": "RELIANCE",
        "last_price": "2,450.00",
        "change": "+25.50",
        "percent_change": "+1.05%",
        "open": "2,425.00",
        "high": "2,460.00",
        "low": "2,420.00",
        "prev_close": "2,424.50",
        "vwap": "2,440.00",
        "traded_volume_lakhs": "1,234.56",
        "traded_value_cr": "3,012.34",
        ...
    },
    "screenshot": "output/...",
    "html": "output/...",
    "json": "output/...",
    "timestamp": "20240101_120000"
}
```

### 2. Financial Report Endpoint

**GET** `/api/financial-report`

Scrapes NSE financial results comparison page for a given stock symbol.

**Query Parameters:**
- `symbol` (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
- `headless` (optional): Run browser in headless mode (default: true)
  - Set to `false` to see browser window (useful for debugging)
  - Query parameter takes precedence over environment variable
- `output_dir` (optional): Output directory path

**Response:**
```json
{
    "status": "success",
    "symbol": "RELIANCE",
    "parsed_data": {
        "status": "success",
        "company": {
            "name": "Reliance Industries Limited",
            "symbol": "RELIANCE"
        },
        "quarters": ["31-Mar-2024", "31-Dec-2023", ...],
        "sections": [
            {
                "section_name": "Income",
                "line_items": [
                    {
                        "name": "Total Income",
                        "values": ["123456", "234567", ...],
                        "is_total": true
                    }
                ]
            }
        ],
        ...
    },
    "screenshot": "output/...",
    "html": "output/...",
    "json": "output/...",
    "timestamp": "20240101_120000"
}
```

### 3. Health Check

**GET** `/health`

Returns API health status.

## Example Usage

### Using curl:

**Equity Quote (requires both symbol and name):**
```bash
curl "http://localhost:5000/api/equity-quote?symbol=RELIANCE&name=Reliance-Industries-Limited"
```

**Financial Report:**
```bash
curl "http://localhost:5000/api/financial-report?symbol=RELIANCE"
```

**With optional parameters:**
```bash
# Equity Quote with screenshot and visible browser
curl "http://localhost:5000/api/equity-quote?symbol=RELIANCE&name=Reliance-Industries-Limited&headless=false&take_screenshot=true"

# Financial Report with visible browser (for debugging)
curl "http://localhost:5000/api/financial-report?symbol=RELIANCE&headless=false"
```

### Using Python:

```python
import requests

# Equity Quote (requires both symbol and name)
response = requests.get('http://localhost:5000/api/equity-quote', params={
    'symbol': 'RELIANCE',
    'name': 'Reliance-Industries-Limited',
    'headless': 'true',  # Set to 'false' to see browser window
    'take_screenshot': 'false'
})
print(response.json())

# Financial Report
response = requests.get('http://localhost:5000/api/financial-report', params={
    'symbol': 'RELIANCE',
    'headless': 'true'  # Set to 'false' to see browser window
})
print(response.json())
```

### Using Browser:

Simply open in your browser:
- `http://localhost:5000/api/equity-quote?symbol=RELIANCE&name=Reliance-Industries-Limited`
- `http://localhost:5000/api/financial-report?symbol=RELIANCE`

**Note:** For the equity quote endpoint, you must provide both `symbol` and `name` parameters. The `name` should match the company slug in the NSE URL (e.g., `Reliance-Industries-Limited` for RELIANCE).

## Notes

- The scrapers use Playwright with human-like behavior to avoid bot detection
- Scraping may take 30-90 seconds depending on page load times (timeout set to 90 seconds)
- Screenshots and HTML files are saved to the `output` directory by default
- **Equity Quote Endpoint**: Requires both `symbol` and `name` parameters. The `name` should be the company slug from the NSE URL (e.g., `Reliance-Industries-Limited`)
- **Headless Mode**: 
  - Default is `headless=true` (browser runs in background)
  - Set `headless=false` in query params to see the browser window (useful for debugging)
  - In production (Railway), headless mode is enforced automatically
- **For production**: Set `headless=true` and `take_screenshot=false` to save resources

## Deployment

The API is configured for deployment on Railway with:
- Docker support (see `Dockerfile`)
- Gevent workers for better async handling
- 10-minute timeout for long-running scraping operations
- Automatic headless mode enforcement in production

## Finding Company Name/Slug for Equity Quote

To find the correct `name` parameter for a stock:
1. Visit NSE website: `https://www.nseindia.com/get-quote/equity/{SYMBOL}`
2. The URL will redirect to: `https://www.nseindia.com/get-quote/equity/{SYMBOL}/{COMPANY-NAME}`
3. Use the `{COMPANY-NAME}` part as the `name` parameter

Example:
- Symbol: `RELIANCE`
- NSE URL: `https://www.nseindia.com/get-quote/equity/RELIANCE/Reliance-Industries-Limited`
- Use: `name=Reliance-Industries-Limited`

