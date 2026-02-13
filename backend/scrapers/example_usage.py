"""
Upwork Scraper - Example Usage Script
=====================================

This script demonstrates how to use the UpworkScraper for various scraping tasks.

Run with:
    python example_usage.py
"""

import asyncio
import json
from upwork_scraper import UpworkScraper, ScraperConfig, JobListing, TalentProfile, Project


async def example_basic_job_search():
    """Example: Basic job search."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Job Search")
    print("="*60)

    async with UpworkScraper() as scraper:
        jobs = await scraper.search_jobs("python developer", max_pages=1)

        print(f"\nFound {len(jobs)} jobs:\n")
        for i, job in enumerate(jobs[:5], 1):
            print(f"{i}. {job.title}")
            print(f"   Budget: {job.budget or 'Not specified'}")
            print(f"   Type: {job.job_type or 'Unknown'}")
            print(f"   Skills: {', '.join(job.skills[:5]) if job.skills else 'None'}")
            print(f"   Proposals: {job.proposals_count or 'N/A'}")
            print(f"   URL: {job.url}")
            print()

        # Save to JSON
        scraper.save_to_json(jobs, "python_jobs.json")

    return jobs


async def example_talent_search():
    """Example: Search for freelancers."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Talent/Freelancer Search")
    print("="*60)

    config = ScraperConfig(
        headless=True,
        max_pages=1,
        output_dir="./outputs"
    )

    async with UpworkScraper(config) as scraper:
        talent = await scraper.search_talent("react developer")

        print(f"\nFound {len(talent)} freelancers:\n")
        for i, t in enumerate(talent[:5], 1):
            print(f"{i}. {t.name} - {t.title}")
            print(f"   Rate: {t.hourly_rate or 'Not specified'}")
            print(f"   Rating: {t.rating}/5" if t.rating else "   Rating: N/A")
            print(f"   Jobs: {t.jobs_completed or 'N/A'}")
            print(f"   Skills: {', '.join(t.skills[:5]) if t.skills else 'None'}")
            print(f"   Badges: {', '.join(t.badges) if t.badges else 'None'}")
            print()

        scraper.save_to_json(talent, "react_talent.json")

    return talent


async def example_project_search():
    """Example: Search Project Catalog."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Project Catalog Search")
    print("="*60)

    async with UpworkScraper() as scraper:
        projects = await scraper.search_projects("logo design", max_pages=1)

        print(f"\nFound {len(projects)} projects:\n")
        for i, p in enumerate(projects[:5], 1):
            print(f"{i}. {p.title}")
            print(f"   Price: {p.price or 'Contact for price'}")
            print(f"   Delivery: {p.delivery_time or 'Not specified'}")
            print(f"   By: {p.freelancer_name or 'Unknown'}")
            print(f"   Rating: {p.rating}/5" if p.rating else "   Rating: N/A")
            print(f"   Skills: {', '.join(p.skills[:5]) if p.skills else 'None'}")
            print()

        scraper.save_to_json(projects, "logo_projects.json")

    return projects


async def example_with_filters():
    """Example: Search with custom filters."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Job Search with Filters")
    print("="*60)

    async with UpworkScraper() as scraper:
        # Apply filters to search
        filters = {
            "duration": "3_to_6_months",
            "workload": "40+_hrs_week"
        }

        jobs = await scraper.search_jobs(
            "full stack developer",
            max_pages=1,
            filters=filters
        )

        print(f"\nFound {len(jobs)} jobs with filters:\n")
        for i, job in enumerate(jobs[:3], 1):
            print(f"{i}. {job.title}")
            print(f"   Duration: {job.duration or 'Not specified'}")
            print(f"   Remote: {'Yes' if job.remote else 'No'}")
            print(f"   Budget: {job.budget or 'Not specified'}")
            print()

    return jobs


async def example_custom_config():
    """Example: Use custom scraper configuration."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Custom Configuration")
    print("="*60)

    config = ScraperConfig(
        headless=True,           # Run in background
        timeout=60000,           # 60 second timeout
        max_retries=5,           # Retry 5 times on failure
        retry_delay=3000,        # Wait 3 seconds between retries
        rate_limit_delay=2000,   # Wait 2 seconds between requests
        max_pages=2,             # Max 2 pages
        output_dir="./data"      # Custom output directory
    )

    async with UpworkScraper(config) as scraper:
        jobs = await scraper.search_jobs("data scientist", max_pages=1)

        print(f"\nWith custom config, found {len(jobs)} jobs")
        print(f"Data saved to: {config.output_dir}")

    return jobs


async def example_data_analysis():
    """Example: Analyze scraped data."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Data Analysis")
    print("="*60)

    async with UpworkScraper() as scraper:
        jobs = await scraper.search_jobs("web developer", max_pages=2)

        # Analyze the data
        if jobs:
            # Budget statistics
            budgets = [j.budget_max for j in jobs if j.budget_max]
            if budgets:
                avg_budget = sum(budgets) / len(budgets)
                min_budget = min(budgets)
                max_budget = max(budgets)

                print(f"\nBudget Analysis ({len(budgets)} jobs with budget):")
                print(f"  Average: ${avg_budget:.2f}")
                print(f"  Min: ${min_budget:.2f}")
                print(f"  Max: ${max_budget:.2f}")

            # Job type distribution
            job_types = {}
            for job in jobs:
                if job.job_type:
                    job_types[job.job_type] = job_types.get(job.job_type, 0) + 1

            print(f"\nJob Type Distribution:")
            for job_type, count in job_types.items():
                print(f"  {job_type}: {count}")

            # Common skills
            all_skills = {}
            for job in jobs:
                for skill in job.skills:
                    all_skills[skill] = all_skills.get(skill, 0) + 1

            top_skills = sorted(all_skills.items(), key=lambda x: x[1], reverse=True)[:10]
            print(f"\nTop 10 Skills:")
            for skill, count in top_skills:
                print(f"  {skill}: {count}")


async def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("UPWORK SCRAPER - EXAMPLE USAGE")
    print("="*60)

    try:
        # Run examples
        await example_basic_job_search()
        # await example_talent_search()
        # await example_project_search()
        # await example_with_filters()
        # await example_custom_config()
        # await example_data_analysis()

        print("\n" + "="*60)
        print("All examples completed!")
        print("="*60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
