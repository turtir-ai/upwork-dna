"""
Upwork Scraper Service
=======================
A robust scraper for extracting data from Upwork using Playwright.

Supports:
- Job search scraping
- Talent search scraping
- Project catalog scraping

Author: Upwork Extension Team
License: MIT
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, quote, urlencode

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    from bs4 import BeautifulSoup
except ImportError as e:
    raise ImportError(
        "Required dependencies missing. Install with:\n"
        "pip install playwright beautifulsoup4\n"
        "playwright install chromium"
    ) from e


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class JobListing:
    """Represents a job listing from Upwork."""

    title: str
    url: str
    description: str
    budget: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    job_type: Optional[str] = None  # hourly, fixed, etc.
    duration: Optional[str] = None
    skills: List[str] = None
    client_verified: bool = False
    client_payment_verified: bool = False
    client_spent: Optional[str] = None
    client_hires: Optional[int] = None
    posted_date: Optional[str] = None
    proposals_count: Optional[int] = None
    interviewing: Optional[int] = None
    invites_sent: Optional[int] = None
    remote: bool = False

    def __post_init__(self):
        if self.skills is None:
            self.skills = []

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['scraped_at'] = datetime.now().isoformat()
        return data


@dataclass
class TalentProfile:
    """Represents a talent profile from Upwork."""

    name: str
    url: str
    title: str
    hourly_rate: Optional[str] = None
    hourly_rate_min: Optional[float] = None
    hourly_rate_max: Optional[float] = None
    skills: List[str] = None
    badges: List[str] = None
    rating: Optional[float] = None
    jobs_completed: Optional[int] = None
    success_score: Optional[float] = None
    hours_worked: Optional[float] = None
    portfolio_items: Optional[int] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    english_level: Optional[str] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.badges is None:
            self.badges = []

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['scraped_at'] = datetime.now().isoformat()
        return data


@dataclass
class Project:
    """Represents a project from Upwork Project Catalog."""

    title: str
    url: str
    description: str
    price: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    delivery_time: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    skills: List[str] = None
    freelancer_name: Optional[str] = None
    freelancer_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    sold_count: Optional[int] = None

    def __post_init__(self):
        if self.skills is None:
            self.skills = []

    def to_dict(self) -> Dict:
        data = asdict(self)
        data['scraped_at'] = datetime.now().isoformat()
        return data


# =============================================================================
# SCRAPER CONFIGURATION
# =============================================================================

@dataclass
class ScraperConfig:
    """Configuration for the scraper."""

    headless: bool = True
    timeout: int = 30000  # ms
    slow_mo: int = 0
    user_agent: Optional[str] = None
    max_retries: int = 3
    retry_delay: int = 2000  # ms
    rate_limit_delay: int = 1000  # ms between requests
    max_pages: int = 10
    save_to_file: bool = False
    output_dir: str = "./outputs"

    def __post_init__(self):
        if self.user_agent is None:
            self.user_agent = (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )


# =============================================================================
# MAIN SCRAPER CLASS
# =============================================================================

class UpworkScraper:
    """
    Main scraper class for extracting data from Upwork.

    Examples:
        >>> scraper = UpworkScraper()
        >>> jobs = await scraper.search_jobs("python developer", max_pages=2)
        >>> print(f"Found {len(jobs)} jobs")
        >>> await scraper.close()
    """

    # URL patterns
    BASE_URL = "https://www.upwork.com"
    JOBS_SEARCH_URL = f"{BASE_URL}/nx/search/jobs/"
    TALENT_SEARCH_URL = f"{BASE_URL}/nx/search/talent/"
    PROJECTS_URL = f"{BASE_URL}/search/projects/"

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the scraper.

        Args:
            config: ScraperConfig instance with settings
        """
        self.config = config or ScraperConfig()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._last_request_time = 0

        logger.info("UpworkScraper initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the browser and create a new context."""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        self.context = await self.browser.new_context(
            user_agent=self.config.user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )

        # Add stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.timeout)

        logger.info("Browser started successfully")

    async def close(self):
        """Close the browser and cleanup."""
        logger.info("Closing browser...")

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        logger.info("Browser closed")

    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = (now - self._last_request_time) * 1000

        if elapsed < self.config.rate_limit_delay:
            delay = (self.config.rate_limit_delay - elapsed) / 1000
            await asyncio.sleep(delay)

        self._last_request_time = asyncio.get_event_loop().time()

    async def _navigate_with_retry(self, url: str) -> bool:
        """
        Navigate to URL with retry logic.

        Args:
            url: Target URL

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.config.max_retries):
            try:
                await self._rate_limit()
                logger.info(f"Navigating to {url} (attempt {attempt + 1})")

                await self.page.goto(url, wait_until="networkidle", timeout=self.config.timeout)
                await asyncio.sleep(1)  # Wait for dynamic content

                # Check for CAPTCHA or blocks
                content = await self.page.content()
                if "captcha" in content.lower() or "access denied" in content.lower():
                    logger.warning("CAPTCHA or access denied detected")
                    if attempt < self.config.max_retries - 1:
                        await asyncio.sleep(self.config.retry_delay / 1000)
                        continue
                    return False

                return True

            except Exception as e:
                logger.error(f"Navigation failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay / 1000)
                else:
                    return False

        return False

    def _parse_budget(self, budget_str: str) -> tuple:
        """Parse budget string to min/max values."""
        budget_min = None
        budget_max = None

        if not budget_str:
            return budget_min, budget_max

        # Extract numbers
        numbers = re.findall(r'[\d,]+\.?\d*', budget_str.replace(',', ''))
        if len(numbers) >= 2:
            budget_min = float(numbers[0])
            budget_max = float(numbers[1])
        elif len(numbers) == 1:
            budget_max = float(numbers[0])

        return budget_min, budget_max

    # =========================================================================
    # JOB SEARCH METHODS
    # =========================================================================

    async def search_jobs(
        self,
        keyword: str,
        max_pages: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[JobListing]:
        """
        Search for jobs on Upwork.

        Args:
            keyword: Search keyword (e.g., "python developer")
            max_pages: Maximum number of pages to scrape
            filters: Optional filters dict (e.g., {"job_type": "hourly"})

        Returns:
            List of JobListing objects
        """
        max_pages = max_pages or self.config.max_pages
        all_jobs = []

        logger.info(f"Searching for jobs: '{keyword}' (max {max_pages} pages)")

        # Build URL with query parameters
        params = {"q": keyword}
        if filters:
            params.update(filters)

        url = f"{self.JOBS_SEARCH_URL}?{urlencode(params)}"

        for page_num in range(1, max_pages + 1):
            page_url = f"{url}&page={page_num}"

            if not await self._navigate_with_retry(page_url):
                logger.warning(f"Failed to load page {page_num}")
                continue

            jobs = await self._extract_jobs_from_page()
            all_jobs.extend(jobs)

            logger.info(f"Page {page_num}: Found {len(jobs)} jobs")

            if not jobs:
                break  # No more results

        logger.info(f"Total jobs found: {len(all_jobs)}")
        return all_jobs

    async def _extract_jobs_from_page(self) -> List[JobListing]:
        """Extract job listings from current page."""
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        jobs = []

        # Upwork uses dynamic rendering, try to find job cards
        # These selectors may need adjustment based on current HTML structure
        job_cards = soup.select('[data-qa="job-tile"]') or soup.select('.job-tile') or soup.select('section[data-test="JobTile"]')

        for card in job_cards:
            try:
                job = self._parse_job_card(card)
                if job and job.title:  # Only add if has a title
                    jobs.append(job)
            except Exception as e:
                logger.debug(f"Failed to parse job card: {e}")
                continue

        # Also try to extract from embedded JSON data
        if not jobs:
            jobs = await self._extract_jobs_from_json()

        return jobs

    def _parse_job_card(self, card) -> Optional[JobListing]:
        """Parse a single job card HTML element."""
        # Extract title
        title_elem = card.select_one('[data-qa="job-title"]') or card.select_one('h3') or card.select_one('.job-title')
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract URL
        url_elem = card.select_one('a[href*="/jobs/"]') or card.select_one('a[data-qa="job-title-link"]')
        url = ""
        if url_elem and url_elem.get('href'):
            url = urljoin(self.BASE_URL, url_elem['href'])

        # Extract description
        desc_elem = card.select_one('[data-qa="job-description"]') or card.select_one('.job-description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract budget
        budget_elem = card.select_one('[data-qa="job-type"]') or card.select_one('.budget')
        budget = budget_elem.get_text(strip=True) if budget_elem else None
        budget_min, budget_max = self._parse_budget(budget) if budget else (None, None)

        # Parse job type from budget string
        job_type = None
        if budget:
            if "hourly" in budget.lower():
                job_type = "hourly"
            elif "fixed" in budget.lower() or "budget" in budget.lower():
                job_type = "fixed"

        # Extract skills
        skills = []
        skill_elems = card.select('[data-qa="skill"]') or card.select('.skill-pill')
        for elem in skill_elems[:10]:  # Limit to first 10
            skill = elem.get_text(strip=True)
            if skill:
                skills.append(skill)

        # Extract client info
        verified = False
        payment_verified = False
        spent = None
        hires = None

        verified_elem = card.select_one('[data-qa="client-verified"]')
        if verified_elem:
            verified = True

        payment_elem = card.select_one('[data-qa="client-payment-verified"]')
        if payment_elem:
            payment_verified = True

        spent_elem = card.select_one('[data-qa="client-spent"]') or card.select_one('.client-spent')
        if spent_elem:
            spent = spent_elem.get_text(strip=True)

        # Extract proposals count
        proposals = None
        proposals_elem = card.select_one('[data-qa="proposal-count"]') or card.select_one('.proposals')
        if proposals_elem:
            proposals_match = re.search(r'(\d+)', proposals_elem.get_text())
            if proposals_match:
                proposals = int(proposals_match.group(1))

        return JobListing(
            title=title,
            url=url,
            description=description,
            budget=budget,
            budget_min=budget_min,
            budget_max=budget_max,
            job_type=job_type,
            skills=skills,
            client_verified=verified,
            client_payment_verified=payment_verified,
            client_spent=spent,
            client_hires=hires,
            proposals_count=proposals
        )

    async def _extract_jobs_from_json(self) -> List[JobListing]:
        """Extract jobs from embedded JSON data in the page."""
        jobs = []

        try:
            # Look for embedded JSON data
            content = await self.page.content()

            # Try to find JSON-LD or similar structured data
            json_patterns = [
                r'<script\s+type="application/ld\+json">(.*?)</script>',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'__UPWORK__\s*=\s*({.*?});'
            ]

            for pattern in json_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        # Process the JSON data structure
                        # This will vary based on Upwork's current implementation
                        jobs.extend(self._parse_jobs_from_json(data))
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            logger.debug(f"Failed to extract from JSON: {e}")

        return jobs

    def _parse_jobs_from_json(self, data: Dict) -> List[JobListing]:
        """Parse jobs from JSON data structure."""
        jobs = []

        # This is a placeholder - actual implementation depends on
        # Upwork's current JSON structure
        try:
            if 'jobs' in data:
                for job_data in data['jobs']:
                    job = JobListing(
                        title=job_data.get('title', ''),
                        url=job_data.get('url', ''),
                        description=job_data.get('description', ''),
                        budget=job_data.get('budget'),
                        skills=job_data.get('skills', [])
                    )
                    jobs.append(job)
        except Exception as e:
            logger.debug(f"Failed to parse JSON jobs: {e}")

        return jobs

    # =========================================================================
    # TALENT SEARCH METHODS
    # =========================================================================

    async def search_talent(
        self,
        keyword: str,
        max_pages: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[TalentProfile]:
        """
        Search for talent/freelancers on Upwork.

        Args:
            keyword: Search keyword (e.g., "python developer")
            max_pages: Maximum number of pages to scrape
            filters: Optional filters dict

        Returns:
            List of TalentProfile objects
        """
        max_pages = max_pages or self.config.max_pages
        all_talent = []

        logger.info(f"Searching for talent: '{keyword}' (max {max_pages} pages)")

        params = {"q": keyword}
        if filters:
            params.update(filters)

        url = f"{self.TALENT_SEARCH_URL}?{urlencode(params)}"

        for page_num in range(1, max_pages + 1):
            page_url = f"{url}&page={page_num}"

            if not await self._navigate_with_retry(page_url):
                logger.warning(f"Failed to load page {page_num}")
                continue

            talent = await self._extract_talent_from_page()
            all_talent.extend(talent)

            logger.info(f"Page {page_num}: Found {len(talent)} profiles")

            if not talent:
                break

        logger.info(f"Total talent found: {len(all_talent)}")
        return all_talent

    async def _extract_talent_from_page(self) -> List[TalentProfile]:
        """Extract talent profiles from current page."""
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        talent_list = []

        # Find talent profile cards
        cards = soup.select('[data-qa="talent-tile"]') or soup.select('.talent-tile') or soup.select('article[data-test="FreelancerTile"]')

        for card in cards:
            try:
                talent = self._parse_talent_card(card)
                if talent and talent.name:
                    talent_list.append(talent)
            except Exception as e:
                logger.debug(f"Failed to parse talent card: {e}")
                continue

        return talent_list

    def _parse_talent_card(self, card) -> Optional[TalentProfile]:
        """Parse a single talent card HTML element."""
        # Extract name
        name_elem = card.select_one('[data-qa="talent-name"]') or card.select_one('.talent-name') or card.select_one('h4')
        name = name_elem.get_text(strip=True) if name_elem else ""

        # Extract URL
        url_elem = card.select_one('a[href*="/profile/"]')
        url = ""
        if url_elem and url_elem.get('href'):
            url = urljoin(self.BASE_URL, url_elem['href'])

        # Extract title
        title_elem = card.select_one('[data-qa="talent-title"]') or card.select_one('.talent-title') or card.select_one('.profile-title')
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract hourly rate
        rate_elem = card.select_one('[data-qa="hourly-rate"]') or card.select_one('.hourly-rate')
        hourly_rate = rate_elem.get_text(strip=True) if rate_elem else None

        rate_min, rate_max = None, None
        if hourly_rate:
            numbers = re.findall(r'[\d,]+\.?\d*', hourly_rate.replace(',', ''))
            if len(numbers) >= 2:
                rate_min = float(numbers[0])
                rate_max = float(numbers[1])
            elif len(numbers) == 1:
                rate_min = float(numbers[0])

        # Extract skills
        skills = []
        skill_elems = card.select('[data-qa="skill"]') or card.select('.skill-pill') or card.select('.air3-badge')
        for elem in skill_elems[:10]:
            skill = elem.get_text(strip=True)
            if skill:
                skills.append(skill)

        # Extract badges
        badges = []
        badge_elems = card.select('[data-qa="badge"]') or card.select('.badge')
        for elem in badge_elems:
            badge = elem.get_text(strip=True)
            if badge:
                badges.append(badge)

        # Extract rating
        rating = None
        rating_elem = card.select_one('[data-qa="rating"]') or card.select_one('.rating')
        if rating_elem:
            rating_match = re.search(r'(\d+\.?\d*)', rating_elem.get_text())
            if rating_match:
                rating = float(rating_match.group(1))

        # Extract jobs completed
        jobs_completed = None
        jobs_elem = card.select_one('[data-qa="jobs-completed"]') or card.select_one('.jobs-completed')
        if jobs_elem:
            jobs_match = re.search(r'(\d+)', jobs_elem.get_text())
            if jobs_match:
                jobs_completed = int(jobs_match.group(1))

        return TalentProfile(
            name=name,
            url=url,
            title=title,
            hourly_rate=hourly_rate,
            hourly_rate_min=rate_min,
            hourly_rate_max=rate_max,
            skills=skills,
            badges=badges,
            rating=rating,
            jobs_completed=jobs_completed
        )

    # =========================================================================
    # PROJECT CATALOG METHODS
    # =========================================================================

    async def search_projects(
        self,
        keyword: str,
        max_pages: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[Project]:
        """
        Search for projects in Upwork Project Catalog.

        Args:
            keyword: Search keyword (e.g., "web development")
            max_pages: Maximum number of pages to scrape
            filters: Optional filters dict

        Returns:
            List of Project objects
        """
        max_pages = max_pages or self.config.max_pages
        all_projects = []

        logger.info(f"Searching for projects: '{keyword}' (max {max_pages} pages)")

        params = {"q": keyword}
        if filters:
            params.update(filters)

        url = f"{self.PROJECTS_URL}?{urlencode(params)}"

        for page_num in range(1, max_pages + 1):
            page_url = f"{url}&page={page_num}"

            if not await self._navigate_with_retry(page_url):
                logger.warning(f"Failed to load page {page_num}")
                continue

            projects = await self._extract_projects_from_page()
            all_projects.extend(projects)

            logger.info(f"Page {page_num}: Found {len(projects)} projects")

            if not projects:
                break

        logger.info(f"Total projects found: {len(all_projects)}")
        return all_projects

    async def _extract_projects_from_page(self) -> List[Project]:
        """Extract projects from current page."""
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        projects = []

        # Find project cards
        cards = soup.select('[data-qa="project-tile"]') or soup.select('.project-tile') or soup.select('article[class*="project"]')

        for card in cards:
            try:
                project = self._parse_project_card(card)
                if project and project.title:
                    projects.append(project)
            except Exception as e:
                logger.debug(f"Failed to parse project card: {e}")
                continue

        return projects

    def _parse_project_card(self, card) -> Optional[Project]:
        """Parse a single project card HTML element."""
        # Extract title
        title_elem = card.select_one('[data-qa="project-title"]') or card.select_one('h3') or card.select_one('.project-title')
        title = title_elem.get_text(strip=True) if title_elem else ""

        # Extract URL
        url_elem = card.select_one('a[href*="/projects/"]')
        url = ""
        if url_elem and url_elem.get('href'):
            url = urljoin(self.BASE_URL, url_elem['href'])

        # Extract description
        desc_elem = card.select_one('[data-qa="project-description"]') or card.select_one('.project-description')
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # Extract price
        price_elem = card.select_one('[data-qa="project-price"]') or card.select_one('.price') or card.select_one('.project-price')
        price = price_elem.get_text(strip=True) if price_elem else None

        price_min, price_max = None, None
        if price:
            numbers = re.findall(r'[\d,]+\.?\d*', price.replace(',', ''))
            if len(numbers) >= 1:
                price_min = float(numbers[0])
            if len(numbers) >= 2:
                price_max = float(numbers[1])

        # Extract delivery time
        delivery_elem = card.select_one('[data-qa="delivery-time"]') or card.select_one('.delivery-time')
        delivery_time = delivery_elem.get_text(strip=True) if delivery_elem else None

        # Extract skills
        skills = []
        skill_elems = card.select('[data-qa="skill"]') or card.select('.skill-tag')
        for elem in skill_elems[:10]:
            skill = elem.get_text(strip=True)
            if skill:
                skills.append(skill)

        # Extract freelancer info
        freelancer_name = None
        freelancer_url = None
        name_elem = card.select_one('[data-qa="freelancer-name"]') or card.select_one('.freelancer-name')
        if name_elem:
            freelancer_name = name_elem.get_text(strip=True)
            link = name_elem.select_one('a')
            if link and link.get('href'):
                freelancer_url = urljoin(self.BASE_URL, link['href'])

        return Project(
            title=title,
            url=url,
            description=description,
            price=price,
            price_min=price_min,
            price_max=price_max,
            delivery_time=delivery_time,
            skills=skills,
            freelancer_name=freelancer_name,
            freelancer_url=freelancer_url
        )

    # =========================================================================
    # DATABASE EXPORT
    # =========================================================================

    async def save_to_database(self, data: List[Any], table_name: str):
        """
        Save scraped data to database.

        Args:
            data: List of dataclass objects (JobListing, TalentProfile, or Project)
            table_name: Target table name
        """
        # Placeholder for database integration
        # This would connect to your actual database
        logger.info(f"Saving {len(data)} records to '{table_name}' table")

        # Example structure:
        # for item in data:
        #     await db.insert(table_name, item.to_dict())

        pass

    def save_to_json(self, data: List[Any], filename: str):
        """
        Save scraped data to JSON file.

        Args:
            data: List of dataclass objects
            filename: Output filename
        """
        import os

        os.makedirs(self.config.output_dir, exist_ok=True)
        filepath = os.path.join(self.config.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([item.to_dict() for item in data], f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(data)} records to {filepath}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Example usage of the scraper."""

    # Create scraper with custom config
    config = ScraperConfig(
        headless=False,  # Show browser for debugging
        max_pages=2,
        output_dir="./outputs"
    )

    async with UpworkScraper(config) as scraper:
        # Search for jobs
        jobs = await scraper.search_jobs("python developer", max_pages=2)
        print(f"\nFound {len(jobs)} jobs:")
        for job in jobs[:3]:
            print(f"  - {job.title}: {job.budget or 'Fixed price'}")

        # Save to JSON
        scraper.save_to_json(jobs, "jobs.json")

        # Search for talent
        talent = await scraper.search_talent("react developer", max_pages=1)
        print(f"\nFound {len(talent)} talent profiles:")
        for t in talent[:3]:
            print(f"  - {t.name}: {t.title}")

        # Save to JSON
        scraper.save_to_json(talent, "talent.json")

        # Search for projects
        projects = await scraper.search_projects("logo design", max_pages=1)
        print(f"\nFound {len(projects)} projects:")
        for p in projects[:3]:
            print(f"  - {p.title}: {p.price or 'Contact for price'}")

        # Save to JSON
        scraper.save_to_json(projects, "projects.json")


if __name__ == "__main__":
    asyncio.run(main())
