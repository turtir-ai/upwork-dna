# Upwork Scraper Service

A robust async scraper for extracting data from Upwork using Playwright and BeautifulSoup4.

## Features

- **Job Search**: Scrape job listings with budgets, skills, client info
- **Talent Search**: Scrape freelancer profiles with rates, ratings, badges
- **Project Catalog**: Scrape pre-packaged projects with pricing
- **Rate Limiting**: Built-in delays to avoid blocking
- **Retry Logic**: Automatic retries for network errors
- **Stealth Mode**: Anti-detection measures
- **Async/Await**: Fast concurrent scraping
- **Data Export**: JSON export and database integration

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```python
import asyncio
from upwork_scraper import UpworkScraper, ScraperConfig

async def main():
    # Create scraper with default config
    async with UpworkScraper() as scraper:
        # Search for jobs
        jobs = await scraper.search_jobs("python developer", max_pages=2)
        print(f"Found {len(jobs)} jobs")

        for job in jobs[:5]:
            print(f"  - {job.title}")
            print(f"    Budget: {job.budget}")
            print(f"    URL: {job.url}")
            print(f"    Skills: {', '.join(job.skills[:3])}")
            print()

        # Save to JSON
        scraper.save_to_json(jobs, "jobs.json")

asyncio.run(main())
```

## Configuration

```python
from upwork_scraper import ScraperConfig

config = ScraperConfig(
    headless=False,           # Show browser (useful for debugging)
    timeout=60000,            # Page load timeout (ms)
    slow_mo=500,              # Slow down actions (ms)
    max_retries=5,            # Retry attempts
    retry_delay=3000,         # Delay between retries (ms)
    rate_limit_delay=2000,    # Delay between requests (ms)
    max_pages=10,             # Max pages to scrape
    save_to_file=True,        # Auto-save to file
    output_dir="./data"       # Output directory
)

scraper = UpworkScraper(config)
```

## Job Search Examples

### Basic Job Search

```python
async with UpworkScraper() as scraper:
    jobs = await scraper.search_jobs("react developer")

    for job in jobs:
        print(f"{job.title}")
        print(f"  Budget: {job.budget_min} - {job.budget_max}")
        print(f"  Type: {job.job_type}")
        print(f"  Skills: {job.skills}")
        print(f"  Client Verified: {job.client_payment_verified}")
        print(f"  Proposals: {job.proposals_count}")
        print()
```

### Job Search with Filters

```python
filters = {
    "job_type": "hourly",
    "duration": "3-6 months",
    "workload": "40+ hrs/week"
}

jobs = await scraper.search_jobs("data analyst", filters=filters)
```

### Job Data Structure

```python
@dataclass
class JobListing:
    title: str
    url: str
    description: str
    budget: Optional[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    job_type: Optional[str]      # hourly, fixed
    duration: Optional[str]
    skills: List[str]
    client_verified: bool
    client_payment_verified: bool
    client_spent: Optional[str]
    client_hires: Optional[int]
    posted_date: Optional[str]
    proposals_count: Optional[int]
    interviewing: Optional[int]
    invites_sent: Optional[int]
    remote: bool
```

## Talent Search Examples

### Basic Talent Search

```python
async with UpworkScraper() as scraper:
    talent = await scraper.search_talent("full stack developer")

    for t in talent:
        print(f"{t.name} - {t.title}")
        print(f"  Rate: ${t.hourly_rate_min}/hr")
        print(f"  Rating: {t.rating}/5")
        print(f"  Jobs: {t.jobs_completed}")
        print(f"  Skills: {', '.join(t.skills[:5])}")
        print(f"  Badges: {t.badges}")
        print()
```

### Talent Data Structure

```python
@dataclass
class TalentProfile:
    name: str
    url: str
    title: str
    hourly_rate: Optional[str]
    hourly_rate_min: Optional[float]
    hourly_rate_max: Optional[float]
    skills: List[str]
    badges: List[str]
    rating: Optional[float]
    jobs_completed: Optional[int]
    success_score: Optional[float]
    hours_worked: Optional[float]
    portfolio_items: Optional[int]
    bio: Optional[str]
    location: Optional[str]
    english_level: Optional[str]
```

## Project Catalog Examples

### Basic Project Search

```python
async with UpworkScraper() as scraper:
    projects = await scraper.search_projects("logo design")

    for p in projects:
        print(f"{p.title}")
        print(f"  Price: ${p.price_min} - ${p.price_max}")
        print(f"  Delivery: {p.delivery_time}")
        print(f"  By: {p.freelancer_name}")
        print(f"  Rating: {p.rating}/5 ({p.reviews_count} reviews)")
        print()
```

### Project Data Structure

```python
@dataclass
class Project:
    title: str
    url: str
    description: str
    price: Optional[str]
    price_min: Optional[float]
    price_max: Optional[float]
    delivery_time: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    skills: List[str]
    freelancer_name: Optional[str]
    freelancer_url: Optional[str]
    rating: Optional[float]
    reviews_count: Optional[int]
    sold_count: Optional[int]
```

## URL Patterns

The scraper uses these Upwork URL patterns:

```
Jobs:     https://www.upwork.com/nx/search/jobs/?q={keyword}
Talent:   https://www.upwork.com/nx/search/talent/?q={keyword}
Projects: https://www.upwork.com/search/projects/?q={keyword}
```

You can add additional query parameters:

```python
# Add custom filters
filters = {
    "duration": "less_than_1_week",
    "workload": "as_needed",
    "hourly_rate": "40-80"
}

jobs = await scraper.search_jobs("web developer", filters=filters)
```

## Error Handling

The scraper includes built-in error handling:

```python
# Configure retries and delays
config = ScraperConfig(
    max_retries=5,           # Retry failed requests 5 times
    retry_delay=3000,        # Wait 3 seconds between retries
    rate_limit_delay=2000    # Wait 2 seconds between requests
)

async with UpworkScraper(config) as scraper:
    # Scraper will automatically handle:
    # - Network timeouts
    # - CAPTCHA detection
    # - Access denied responses
    jobs = await scraper.search_jobs("python developer")
```

## Data Export

### JSON Export

```python
jobs = await scraper.search_jobs("react developer")
scraper.save_to_json(jobs, "react_jobs.json")
```

### Database Export

```python
# Custom database integration
async def save_to_db(data, table_name):
    # Your database logic here
    for item in data:
        await db.insert(table_name, item.to_dict())

await save_to_db(jobs, "jobs")
```

## Rate Limiting

To avoid blocking, the scraper includes rate limiting:

```python
config = ScraperConfig(
    rate_limit_delay=2000,  # 2 seconds between requests
)

# Scraper automatically applies delays between page loads
```

## Debugging

For debugging, run with visible browser:

```python
config = ScraperConfig(
    headless=False,    # Show browser window
    slow_mo=500,       # Slow down actions
    timeout=60000      # Longer timeout
)

async with UpworkScraper(config) as scraper:
    jobs = await scraper.search_jobs("python developer", max_pages=1)
```

## Output Files

Scraped data is saved to the configured output directory:

```
outputs/
├── jobs.json          # Job listings
├── talent.json        # Freelancer profiles
└── projects.json      # Project catalog items
```

## Troubleshooting

### Playwright Not Found

```bash
# Install Playwright browsers
playwright install chromium
```

### SSL Certificate Errors

```python
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Pass to browser launch config
```

### CAPTCHA Detected

The scraper will log CAPTCHA detection and retry. For persistent CAPTCHAs:

1. Slow down rate limiting (`rate_limit_delay=5000`)
2. Use residential proxies
3. Consider official Upwork API

### No Data Extracted

Upwork frequently changes their HTML structure. If extraction fails:

1. Check browser dev tools for current selectors
2. Update selector patterns in `_parse_job_card()`
3. Check for JSON data in page source

## License

MIT License

## Disclaimer

This scraper is for educational and research purposes. Always respect Upwork's Terms of Service and robots.txt. Consider using the official Upwork API for production use.
