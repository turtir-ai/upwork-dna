# Upwork DNA Backend

FastAPI backend for Upwork DNA with Playwright scraping capabilities.

## Features

- **Queue System**: Manage scraping jobs with priority queue
- **Multi-type Scraping**: Jobs, Talent (freelancers), and Projects
- **Background Processing**: Async scraping with status tracking
- **SQLite Database**: Store scraped data persistently
- **REST API**: Full REST API with auto-generated docs
- **CORS Enabled**: Ready for Next.js frontend integration
- **Existing Scraper Integration**: Uses the proven `upwork_scraper` from `scrapers/` directory

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to backend directory
cd /Users/dev/Documents/upworkextension/backend

# Run the startup script (installs everything)
./startup.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit settings (optional)
nano .env
```

### 3. Start the Server

```bash
# Using startup script
./startup.sh

# Or manually
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

## API Endpoints

### Queue Management

- `POST /queue` - Add keyword to queue
- `GET /queue` - Get all queue items
- `DELETE /queue/{id}` - Remove queue item
- `DELETE /queue/keyword/{keyword}` - Remove by keyword

### Scraping

- `POST /scrape` - Start scraping job
- `GET /scrape/status/{job_id}` - Get scraping status
- `GET /scrape/active` - Get active jobs

### Results

- `GET /results` - Get all scraped data
- `GET /results/{keyword}` - Get data for keyword
- `GET /jobs` - Get all jobs
- `GET /talent` - Get all talent
- `GET /projects` - Get all projects

### System

- `GET /status` - System status
- `GET /health` - Health check

## Example Usage

### Add to Queue

```bash
curl -X POST "http://localhost:8000/queue" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "python developer",
    "job_type": "jobs",
    "priority": 1
  }'
```

### Start Scraping

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "python developer",
    "job_type": "jobs",
    "max_pages": 3
  }'
```

### Get Results

```bash
# Get all results for keyword
curl "http://localhost:8000/results/python%20developer"

# Get only jobs
curl "http://localhost:8000/jobs?keyword=python%20developer&limit=50"
```

### Check Status

```bash
# System status
curl "http://localhost:8000/status"

# Scraping job status
curl "http://localhost:8000/scrape/status/{job_id}"
```

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── database.py          # SQLAlchemy models & DB config
├── models.py            # Pydantic models
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── startup.sh           # Startup script
├── README.md            # This file
├── scrapers/            # Existing scraper module
│   ├── upwork_scraper.py    # Main scraper implementation
│   ├── example_usage.py     # Usage examples
│   ├── requirements.txt     # Scraper dependencies
│   └── README.md            # Scraper documentation
└── upwork_dna.db        # SQLite database (created on first run)
```

## Database Schema

### queue
- id, keyword, status, job_type, priority, created_at, updated_at

### jobs
- id, keyword, title, description, url, budget, budget_min, budget_max, job_type, duration, skills, client_verified, client_payment_verified, client_spent, client_hires, posted_date, proposals_count, interviewing, invites_sent, remote, scraped_at

### talent
- id, keyword, name, url, title, hourly_rate, hourly_rate_min, hourly_rate_max, skills, badges, rating, jobs_completed, success_score, hours_worked, portfolio_items, bio, location, english_level, description, country, scraped_at

### projects
- id, keyword, title, url, description, price, price_min, price_max, delivery_time, category, subcategory, skills, freelancer_name, freelancer_url, rating, reviews_count, sold_count, scraped_at

### scraping_jobs
- id, job_id, keyword, status, job_type, total_items, processed_items, error_message, started_at, completed_at, created_at

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./upwork_dna.db | Database connection string |
| API_HOST | 0.0.0.0 | API server host |
| API_PORT | 8000 | API server port |
| API_RELOAD | True | Enable auto-reload |
| CORS_ORIGINS | ["http://localhost:3000"] | CORS allowed origins |
| SCRAPER_HEADLESS | True | Run browser in headless mode |
| SCRAPER_TIMEOUT | 30000 | Page load timeout (ms) |
| SCRAPER_DELAY | 1000 | Delay between page loads (ms) |

## Integration with Existing Scraper

This backend integrates with the existing `upwork_scraper` module in the `scrapers/` directory. The scraper provides:

- **Robust Data Extraction**: Using Playwright and BeautifulSoup4
- **Rate Limiting**: Built-in delays to avoid blocking
- **Retry Logic**: Automatic retries for network errors
- **Stealth Mode**: Anti-detection measures
- **Rich Data Models**: Comprehensive data structures for jobs, talent, and projects

For more details on the scraper, see `scrapers/README.md`.

## Troubleshooting

### Playwright Browsers Not Found

```bash
playwright install chromium
```

### Port Already in Use

```bash
# Change port in .env or
uvicorn main:app --port 8001
```

### Database Locked

```bash
# Delete database and restart
rm upwork_dna.db
./startup.sh
```

### Import Errors

```bash
# Ensure you're in the backend directory
cd /Users/dev/Documents/upworkextension/backend
source venv/bin/activate
pip install -r requirements.txt
```

## Development

```bash
# Run with hot reload
uvicorn main:app --reload

# Check API docs
open http://localhost:8000/docs

# View database
sqlite3 upwork_dna.db
.tables
SELECT * FROM jobs LIMIT 10;
```

## Testing the Scraper Directly

You can test the scraper independently:

```bash
cd scrapers
python example_usage.py
```

## Next.js Integration

The backend is ready to integrate with a Next.js frontend. Set the frontend's API base URL to:

```
http://localhost:8000
```

Example fetch call:

```javascript
const response = await fetch('http://localhost:8000/jobs?limit=20');
const data = await response.json();
```

## License

MIT
