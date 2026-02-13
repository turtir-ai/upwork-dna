"""
Example usage and testing of SegmentScorer for Upwork market analysis.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.segment_scorer import SegmentScorer
import pandas as pd


def example_job_scoring():
    """Example: Score individual jobs."""
    print("=" * 60)
    print("EXAMPLE 1: Job Scoring")
    print("=" * 60)

    scorer = SegmentScorer()

    # Example job data
    example_jobs = [
        {
            'budget': '$500-$1000',
            'client_rating': 4.8,
            'total_spent': '$15000',
            'payment_verified': True,
            'proposals': 5,
            'posted': '2 hours ago',
            'skills': 'Python, Machine Learning, TensorFlow',
            'experience_level': 'Expert'
        },
        {
            'budget': '$50',
            'client_rating': 3.5,
            'total_spent': '$100',
            'payment_verified': False,
            'proposals': 50,
            'posted': '2 weeks ago',
            'skills': 'Data Entry',
            'experience_level': 'Entry'
        }
    ]

    for i, job in enumerate(example_jobs, 1):
        print(f"\n--- Job {i} ---")
        result = scorer.score_job(job, niche='General')
        print(f"Composite Score: {result['composite_score']}/100")
        print(f"\n{result['breakdown']}")


def example_talent_scoring():
    """Example: Score individual talent."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Talent Scoring")
    print("=" * 60)

    scorer = SegmentScorer()

    # Example talent data
    example_talents = [
        {
            'rate': '$85/hr',
            'detail_badges': 'Top Rated Plus,Expert',
            'detail_job_success': 98,
            'portfolio_count': 25,
            'skills': 'Python,PyTorch,MLOps,GraphQL,Rust'
        },
        {
            'rate': '$20/hr',
            'detail_badges': '',
            'detail_job_success': 85,
            'portfolio_count': 2,
            'skills': 'Data Entry,Excel'
        }
    ]

    for i, talent in enumerate(example_talents, 1):
        print(f"\n--- Talent {i} ---")
        result = scorer.score_talent(talent, niche='General')
        print(f"Composite Score: {result['composite_score']}/100")
        print(f"\n{result['breakdown']}")


def example_batch_scoring():
    """Example: Score from actual CSV data."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Batch Scoring from CSV")
    print("=" * 60)

    import glob

    # Find a jobs CSV file
    jobs_files = glob.glob('data/upwork_jobs_*.csv')
    if not jobs_files:
        print("No jobs data files found in data/ directory")
        return

    # Load first jobs file
    jobs_df = pd.read_csv(jobs_files[0])
    print(f"\nLoaded {len(jobs_df)} jobs from {os.path.basename(jobs_files[0])}")

    scorer = SegmentScorer()

    # Score first 5 jobs
    print("\n--- Top 5 Jobs by Score ---")
    job_scores = []
    for idx, row in jobs_df.head(5).iterrows():
        result = scorer.score_job(row.to_dict(), niche='General')
        job_scores.append({
            'title': row.get('title', 'N/A')[:50],
            'score': result['composite_score']
        })
        print(f"{result['composite_score']:.1f}/100 - {row.get('title', 'N/A')[:50]}")

    # Find a talent CSV file
    talent_files = glob.glob('data/upwork_talent_*.csv')
    if talent_files:
        talent_df = pd.read_csv(talent_files[0])
        print(f"\nLoaded {len(talent_df)} talent profiles from {os.path.basename(talent_files[0])}")

        print("\n--- Top 5 Talent by Score ---")
        for idx, row in talent_df.head(5).iterrows():
            result = scorer.score_talent(row.to_dict(), niche='General')
            print(f"{result['composite_score']:.1f}/100 - {row.get('name', row.get('title', 'N/A'))}")


def main():
    """Run all examples."""
    example_job_scoring()
    example_talent_scoring()
    # example_batch_scoring()  # Uncomment to test with real data

    print("\n" + "=" * 60)
    print("SegmentScorer Examples Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
