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
- `headless` (optional): Run browser in headless mode (default: true; enforced if `FORCE_HEADLESS=true`)
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
- `headless` (optional): Run browser in headless mode (default: true; enforced if `FORCE_HEADLESS=true`)
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

**Equity Quote:**
```bash
curl "http://localhost:5000/api/equity-quote?symbol=RELIANCE"
```

**Financial Report:**
```bash
curl "http://localhost:5000/api/financial-report?symbol=RELIANCE"
```

**With optional parameters:**
```bash
# Equity Quote with screenshot
curl "http://localhost:5000/api/equity-quote?symbol=RELIANCE&take_screenshot=true"

# Financial Report with visible browser
curl "http://localhost:5000/api/financial-report?symbol=RELIANCE&headless=false"
```

### Using Python:

```python
import requests

# Equity Quote
response = requests.get('http://localhost:5000/api/equity-quote', params={
    'symbol': 'RELIANCE',
    'headless': 'true'
})
print(response.json())

# Financial Report
response = requests.get('http://localhost:5000/api/financial-report', params={
    'symbol': 'RELIANCE'
})
print(response.json())
```

### Using Browser:

Simply open in your browser:
- `http://localhost:5000/api/equity-quote?symbol=RELIANCE`
- `http://localhost:5000/api/financial-report?symbol=RELIANCE`

## Notes

- The scrapers use Playwright with human-like behavior to avoid bot detection
- Scraping may take 10-30 seconds depending on page load times
- Screenshots and HTML files are saved to the `output` directory by default
- For production, set `headless=True` and `take_screenshot=False` to save resources

