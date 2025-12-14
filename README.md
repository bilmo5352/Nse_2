# NSE Scraper API

A production-ready Flask API for scraping NSE (National Stock Exchange) equity dashboard and financial reports.

## Features

- **Dashboard Scraping**: Scrape equity quote data by searching from NSE homepage
- **Financial Report Scraping**: Extract financial results comparison data
- **Headed Mode**: Runs with visible browser by default (can be configured)
- **Production Ready**: Configured for Railway deployment with proper logging and error handling

## API Endpoints

### 1. Dashboard Endpoint
```
GET /api/dashboard?symbol=RELIANCE
```

**Query Parameters:**
- `symbol` (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
- `headless` (optional): Run browser in headless mode (default: false - headed mode)
- `take_screenshot` (optional): Save screenshot (default: true)
- `output_dir` (optional): Output directory path

### 2. Financial Report Endpoint
```
GET /api/financial-report?symbol=RELIANCE
```

**Query Parameters:**
- `symbol` (required): Stock symbol (e.g., RELIANCE, TCS, INFY)
- `headless` (optional): Run browser in headless mode (default: false - headed mode)
- `output_dir` (optional): Output directory path

### 3. Health Check
```
GET /health
```

### 4. API Documentation
```
GET /
```

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   playwright install-deps chromium
   ```

2. **Run the server:**
   ```bash
   python app.py
   ```

3. **Test the API:**
   ```bash
   curl "http://localhost:5000/api/dashboard?symbol=RELIANCE"
   curl "http://localhost:5000/api/financial-report?symbol=TCS"
   ```

## Railway Deployment

### Prerequisites
- Railway account
- Git repository with your code

### Deployment Steps

1. **Connect your repository to Railway:**
   - Go to [Railway](https://railway.app)
   - Create a new project
   - Connect your Git repository

2. **Configure Environment Variables (optional):**
   - `FLASK_ENV`: Set to `production` (default: `production`)
   - `FLASK_DEBUG`: Set to `False` (default: `False`)
   - `HEADLESS_MODE`: Set to `false` for headed mode (default: `false`)
   - `OUTPUT_DIR`: Output directory path (default: `output`)
   - `PORT`: Server port (Railway sets this automatically)

3. **Deploy:**
   - Railway will automatically detect the `Procfile` and deploy
   - The build process will:
     - Install Python dependencies
     - Install Playwright browsers
     - Install browser dependencies

4. **Monitor:**
   - Check logs in Railway dashboard
   - Use the `/health` endpoint to verify the API is running

### Important Notes for Railway

- **Headed Mode**: Railway runs in a headless Linux environment. For headed mode to work, the `nixpacks.toml` includes `xvfb-run` which provides a virtual display. However, you may need to set `HEADLESS_MODE=true` if headed mode doesn't work.
- **Memory**: Playwright browsers require significant memory. Ensure your Railway plan has adequate resources.
- **Timeouts**: The API has a 300-second timeout for long-running scraping operations.

## Project Structure

```
.
├── app.py                 # Flask API application
├── dashbord.py           # Dashboard scraper
├── finiancialReport.py   # Financial report scraper
├── requirements.txt      # Python dependencies
├── Procfile              # Railway process file
├── runtime.txt           # Python version
├── railway.json          # Railway configuration
├── nixpacks.toml         # Nixpacks build configuration
└── output/               # Output directory for scraped files
```

## Environment Variables

| Variable | Default | Description |
|---------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment |
| `FLASK_DEBUG` | `False` | Enable debug mode |
| `HEADLESS_MODE` | `false` | Run browsers in headless mode |
| `OUTPUT_DIR` | `output` | Directory for output files |
| `PORT` | `5000` | Server port (Railway sets automatically) |

## Response Format

### Success Response
```json
{
  "status": "success",
  "symbol": "RELIANCE",
  "data": { ... },
  "screenshot": "path/to/screenshot.png",
  "html": "path/to/html.html",
  "json": "path/to/json.json",
  "timestamp": "20241214_123456",
  "elapsed_time_seconds": 45.23
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Error message here",
  "elapsed_time_seconds": 12.45
}
```

## License

MIT
