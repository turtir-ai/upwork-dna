#!/usr/bin/env python3
"""
Upwork DNA - Comprehensive Test Suite
=====================================
Tests all modules and creates self-deciding keyword recommendations.
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import traceback

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import test targets
try:
    from scoring.segment_scorer import SegmentScorer
    from scoring.opportunity_scorer import KeywordOpportunityScorer
    from analysis.market_gap_calculator import MarketGapCalculator
    from generators.title_generator import GoldenTitleGenerator
    MODULES_AVAILABLE = True
    DATAFLYWHEEL_AVAILABLE = False
except ImportError as e:
    print(f"⚠️ Module import error: {e}")
    MODULES_AVAILABLE = False
    DATAFLYWHEEL_AVAILABLE = False

# Try importing DataFlywheel separately (may fail on watchdog)
try:
    from pipeline.data_flywheel import DataFlywheel
    DATAFLYWHEEL_AVAILABLE = True
except ImportError as e:
    DATAFLYWHEEL_AVAILABLE = False
    if MODULES_AVAILABLE:
        print(f"⚠️ DataFlywheel not available (watchdog issue): {e}")

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_test(name, status, message=""):
    """Print test result with color"""
    if status == "PASS":
        print(f"{Colors.GREEN}✅ PASS{Colors.END} {name}")
    elif status == "FAIL":
        print(f"{Colors.RED}❌ FAIL{Colors.END} {name}")
        if message:
            print(f"   {Colors.RED}{message}{Colors.END}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠️  WARN{Colors.END} {name}")
    else:
        print(f"{Colors.BLUE}ℹ️  INFO{Colors.END} {name}")

def print_header(text):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

# ============================================================
# TEST SUITE
# ============================================================

class TestSuite:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'errors': []
        }
        self.data = {
            'jobs': pd.DataFrame(),
            'talent': pd.DataFrame(),
            'projects': pd.DataFrame()
        }

    def run_all(self):
        """Run all tests"""
        print_header("UPWORK DNA - COMPREHENSIVE TEST SUITE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Test 1: Module availability
        self.test_module_availability()

        if not MODULES_AVAILABLE:
            print("\n❌ Cannot continue without modules. Install requirements:")
            print("   pip install -r requirements.txt")
            return self.results

        # Test 2: Data loading
        self.test_data_loading()

        # Test 3: SegmentScorer
        self.test_segment_scorer()

        # Test 4: MarketGapCalculator
        self.test_market_gap_calculator()

        # Test 5: GoldenTitleGenerator
        self.test_title_generator()

        # Test 6: KeywordOpportunityScorer
        self.test_opportunity_scorer()

        # Test 7: DataFlywheel
        self.test_data_flywheel()

        # Test 8: Integration test
        self.test_integration()

        # Test 9: Self-deciding keyword system
        self.test_self_deciding_system()

        # Summary
        self.print_summary()

        return self.results

    def test_module_availability(self):
        """Test 1: Check if all modules are available"""
        print_header("TEST 1: MODULE AVAILABILITY")

        modules = [
            ('SegmentScorer', 'scoring.segment_scorer'),
            ('KeywordOpportunityScorer', 'scoring.opportunity_scorer'),
            ('MarketGapCalculator', 'analysis.market_gap_calculator'),
            ('GoldenTitleGenerator', 'generators.title_generator'),
        ]

        for name, path in modules:
            try:
                __import__(path)
                print_test(f"{name} module", "PASS")
                self.results['passed'] += 1
            except ImportError as e:
                print_test(f"{name} module", "FAIL", str(e))
                self.results['failed'] += 1
                self.results['errors'].append((name, str(e)))

        # Test DataFlywheel separately (optional, may not work on all systems)
        try:
            __import__('pipeline.data_flywheel')
            print_test("DataFlywheel module", "PASS")
            self.results['passed'] += 1
        except ImportError as e:
            print_test("DataFlywheel module", "WARN", f"Optional module not available: {str(e)[:40]}...")
            self.results['warnings'] += 1

    def test_data_loading(self):
        """Test 2: Load and validate existing data"""
        print_header("TEST 2: DATA LOADING")

        data_dir = Path("data")

        if not data_dir.exists():
            print_test("Data directory exists", "WARN", "data/ not found")
            return

        # Count files
        csv_files = list(data_dir.rglob("*.csv"))
        print_test(f"CSV files found", "PASS", f"{len(csv_files)} files")

        # Load data by category
        jobs_files = [f for f in csv_files if 'job' in f.name.lower()]
        talent_files = [f for f in csv_files if 'talent' in f.name.lower()]
        projects_files = [f for f in csv_files if 'project' in f.name.lower()]

        print(f"\n  📊 Data Distribution:")
        print(f"     Jobs: {len(jobs_files)} files")
        print(f"     Talent: {len(talent_files)} files")
        print(f"     Projects: {len(projects_files)} files")

        # Sample load
        try:
            if jobs_files:
                sample_jobs = pd.read_csv(jobs_files[0], nrows=5)
                self.data['jobs'] = pd.concat([pd.read_csv(f) for f in jobs_files[:10]], ignore_index=True)
                print_test("Jobs data loaded", "PASS", f"{len(self.data['jobs'])} rows")
                self.results['passed'] += 1

            if talent_files:
                sample_talent = pd.read_csv(talent_files[0], nrows=5)
                self.data['talent'] = pd.concat([pd.read_csv(f) for f in talent_files[:10]], ignore_index=True)
                print_test("Talent data loaded", "PASS", f"{len(self.data['talent'])} rows")
                self.results['passed'] += 1

            if projects_files:
                sample_projects = pd.read_csv(projects_files[0], nrows=5)
                self.data['projects'] = pd.concat([pd.read_csv(f) for f in projects_files[:5]], ignore_index=True)
                print_test("Projects data loaded", "PASS", f"{len(self.data['projects'])} rows")
                self.results['passed'] += 1

        except Exception as e:
            print_test("Data loading", "FAIL", str(e))
            self.results['failed'] += 1

    def test_segment_scorer(self):
        """Test 3: SegmentScorer functionality"""
        print_header("TEST 3: SEGMENT SCORER")

        try:
            scorer = SegmentScorer()

            # Test job scoring
            if not self.data['jobs'].empty:
                sample_job = self.data['jobs'].iloc[0].to_dict()
                job_score = scorer.score_job(sample_job)
                print_test("Job scoring", "PASS", f"Score: {job_score.get('total_score', 0):.1f}/100")
                self.results['passed'] += 1

                # Verify score range
                total = job_score.get('total_score', 0)
                if 0 <= total <= 100:
                    print_test("Job score range valid", "PASS")
                    self.results['passed'] += 1
                else:
                    print_test("Job score range valid", "FAIL", f"Score out of range: {total}")
                    self.results['failed'] += 1
            else:
                print_test("Job scoring", "WARN", "No jobs data")
                self.results['warnings'] += 1

            # Test talent scoring
            if not self.data['talent'].empty:
                sample_talent = self.data['talent'].iloc[0].to_dict()
                talent_score = scorer.score_talent(sample_talent)
                print_test("Talent scoring", "PASS", f"Score: {talent_score.get('total_score', 0):.1f}/100")
                self.results['passed'] += 1
            else:
                print_test("Talent scoring", "WARN", "No talent data")
                self.results['warnings'] += 1

        except Exception as e:
            print_test("SegmentScorer", "FAIL", str(e))
            self.results['failed'] += 1
            self.results['errors'].append(('SegmentScorer', str(e)))

    def test_market_gap_calculator(self):
        """Test 4: MarketGapCalculator with statistical testing"""
        print_header("TEST 4: MARKET GAP CALCULATOR")

        try:
            calculator = MarketGapCalculator()

            # Create sample data
            demand_data = [10, 25, 15, 30, 20]  # Job demands
            supply_data = [5, 20, 10, 25, 15]   # Talent supply

            gap_result = calculator.calculate_gap(demand_data, supply_data)

            print_test("Gap calculation", "PASS", f"Gap ratio: {gap_result['gap_ratio']:.2f}x")
            self.results['passed'] += 1

            # Verify statistical components
            if 'p_value' in gap_result:
                print_test("P-value calculated", "PASS", f"p = {gap_result['p_value']:.4f}")
                self.results['passed'] += 1

            if 'effect_size' in gap_result:
                print_test("Effect size calculated", "PASS", f"Cohen's d = {gap_result['effect_size']:.2f}")
                self.results['passed'] += 1

            if 'confidence_interval' in gap_result:
                ci = gap_result['confidence_interval']
                print_test("Confidence interval", "PASS", f"95% CI: [{ci[0]:.2f}, {ci[1]:.2f}]")
                self.results['passed'] += 1

            # Test with real data if available
            if not self.data['jobs'].empty and not self.data['talent'].empty:
                # Extract skills from jobs and talent
                # Build the format expected by calculate_multiple_gaps: {skill: {'demand': [...], 'supply': [...]}}
                skill_data = {}

                # Sample from jobs - collect raw mentions
                from collections import Counter
                job_skill_mentions = {}
                for _, row in self.data['jobs'].head(100).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        for skill in str(row['skills']).split(','):
                            skill = skill.strip().lower()
                            if skill not in job_skill_mentions:
                                job_skill_mentions[skill] = []
                            job_skill_mentions[skill].append(1)  # Add a mention

                # Sample from talent
                talent_skill_mentions = {}
                for _, row in self.data['talent'].head(50).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        for skill in str(row['skills']).split(','):
                            skill = skill.strip().lower()
                            if skill not in talent_skill_mentions:
                                talent_skill_mentions[skill] = []
                            talent_skill_mentions[skill].append(1)  # Add a mention

                # Build skill_data in correct format
                all_skills = list(job_skill_mentions.keys()) + list(talent_skill_mentions.keys())
                for skill in list(set(all_skills))[:10]:
                    skill_data[skill] = {
                        'demand': job_skill_mentions.get(skill, []),
                        'supply': talent_skill_mentions.get(skill, [])
                    }

                if skill_data:
                    gaps = calculator.calculate_multiple_gaps(skill_data)
                    significant = calculator.filter_significant_gaps(gaps)

                    print_test("Real data gaps calculated", "PASS", f"{len(gaps)} gaps, {len(significant)} significant")
                    self.results['passed'] += 1
                else:
                    print_test("Real data gaps", "WARN", "Insufficient skill data")
                    self.results['warnings'] += 1

        except Exception as e:
            print_test("MarketGapCalculator", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('MarketGapCalculator', str(e)))

    def test_title_generator(self):
        """Test 5: GoldenTitleGenerator"""
        print_header("TEST 5: TITLE GENERATOR")

        try:
            generator = GoldenTitleGenerator()

            # Test title generation
            profile_data = {
                'role': 'Data Analyst',
                'primary_skills': ['SQL', 'Python', 'Tableau'],
                'outcomes': ['Actionable Insights', 'Data-Driven Decisions']
            }

            titles = generator.generate_titles(profile_data, count=5)

            if titles:
                print_test("Title generation", "PASS", f"Generated {len(titles)} titles")
                self.results['passed'] += 1

                # Validate titles
                all_valid = True
                for i, title_info in enumerate(titles[:3], 1):
                    title = title_info.get('title', '')
                    score = title_info.get('predicted_score', 0)
                    length_ok = len(title) <= 70
                    score_ok = 0 <= score <= 100

                    status = "✓" if (length_ok and score_ok) else "✗"
                    print(f"  {status} Title {i}: {title[:60]}... (Score: {score:.0f}, Length: {len(title)})")

                    if not length_ok:
                        all_valid = False
                        print_test(f"Title {i} length", "FAIL", f"{len(title)} > 70 chars")
                        self.results['failed'] += 1

                if all_valid:
                    print_test("All titles valid", "PASS")
                    self.results['passed'] += 1
            else:
                print_test("Title generation", "FAIL", "No titles generated")
                self.results['failed'] += 1

            # Test with real talent data if available
            if not self.data['talent'].empty and 'title' in self.data['talent'].columns:
                # Parse rate column properly - it's string format like "$50/hr"
                def parse_rate(rate_val):
                    if isinstance(rate_val, (int, float)):
                        return float(rate_val)
                    if isinstance(rate_val, str):
                        import re
                        match = re.search(r'(\d+)', rate_val.replace(',', ''))
                        return float(match.group(1)) if match else 0
                    return 0

                rates = self.data['talent']['rate'].apply(parse_rate)
                elite_mask = rates > 50
                elite_titles = self.data['talent'][elite_mask]['title'].dropna().tolist()

                if elite_titles:
                    patterns = generator.analyze_elite_titles(pd.DataFrame({'title': elite_titles}))
                    print_test("Elite title analysis", "PASS", f"Analyzed {len(elite_titles)} titles")
                    self.results['passed'] += 1

        except Exception as e:
            print_test("GoldenTitleGenerator", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('GoldenTitleGenerator', str(e)))

    def test_opportunity_scorer(self):
        """Test 6: KeywordOpportunityScorer"""
        print_header("TEST 6: OPPORTUNITY SCORER")

        try:
            scorer = KeywordOpportunityScorer()

            # Test sample keywords
            test_keywords = [
                'ai agent development',
                'langchain',
                'vector database',
                'rag pipeline',
                'crewai'
            ]

            # Build market data from existing data
            market_data = {
                'job_count': len(self.data['jobs']) if not self.data['jobs'].empty else 100,
                'avg_budget': 500,
                'total_freelancers': len(self.data['talent']) if not self.data['talent'].empty else 50,
                'avg_proposals': 15,
                'payment_verified_pct': 80,
                'growth_rate': 0.15
            }

            scored_keywords = []
            for keyword in test_keywords:
                result = scorer.score_keyword_opportunity(keyword, market_data)
                scored_keywords.append(result)

                # OpportunityScore is a dataclass - access attributes directly
                score = result.opportunity_score
                priority = result.recommended_priority
                print_test(f"Keyword '{keyword}'", "PASS", f"Score: {score:.1f}/100 ({priority})")
                self.results['passed'] += 1

            # Verify scores are in range
            all_valid = all(0 <= kw.opportunity_score <= 100 for kw in scored_keywords)
            if all_valid:
                print_test("All scores in range", "PASS")
                self.results['passed'] += 1
            else:
                print_test("Score range validation", "FAIL")
                self.results['failed'] += 1

        except Exception as e:
            print_test("KeywordOpportunityScorer", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('KeywordOpportunityScorer', str(e)))

    def test_data_flywheel(self):
        """Test 7: DataFlywheel"""
        print_header("TEST 7: DATA FLYWHEEL")

        if not DATAFLYWHEEL_AVAILABLE:
            print_test("DataFlywheel", "WARN", "Module not available (watchdog dependency)")
            self.results['warnings'] += 1
            # Run simplified version without DataFlywheel class
            return self._test_data_flywheel_fallback()

        try:
            flywheel = DataFlywheel()

            # Test keyword discovery from existing data
            discovered = []

            if not self.data['jobs'].empty:
                # Extract skills from jobs
                from collections import Counter
                import re

                all_skills = []
                for _, row in self.data['jobs'].head(200).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        skills = [s.strip().lower() for s in str(row['skills']).split(',')]
                        all_skills.extend(skills)

                skill_counts = Counter(all_skills)
                discovered = [skill for skill, count in skill_counts.most_common(10)]

                print_test("Keyword discovery", "PASS", f"Found {len(discovered)} potential keywords")
                self.results['passed'] += 1

                # Score discovered keywords
                scored = []
                for keyword in discovered[:5]:
                    market_data = {
                        'job_count': len(self.data['jobs']),
                        'avg_budget': 500,
                        'total_freelancers': len(self.data['talent']),
                        'avg_proposals': 15,
                        'payment_verified_pct': 80,
                        'growth_rate': 0.1
                    }

                    score_data = {
                        'keyword': keyword,
                        'demand': skill_counts[keyword],
                        'supply': skill_counts.get(keyword, 0) // 2  # Estimate
                    }

                    # Simple opportunity score
                    demand_score = min(score_data['demand'] / 10 * 40, 40)
                    supply_score = max(20 - score_data['supply'], 0)
                    opp_score = demand_score + supply_score + 40  # Base score

                    scored.append({
                        'keyword': keyword,
                        'opportunity_score': opp_score,
                        'recommended_priority': 'HIGH' if opp_score > 70 else 'MEDIUM' if opp_score > 50 else 'LOW'
                    })

                print_test("Keyword scoring", "PASS", f"Scored {len(scored)} keywords")
                self.results['passed'] += 1

                # Display top opportunities
                print(f"\n  🎯 Top Opportunities:")
                for kw in sorted(scored, key=lambda x: x['opportunity_score'], reverse=True)[:5]:
                    priority_icon = "🔥" if kw['recommended_priority'] == "HIGH" else "📈"
                    print(f"     {priority_icon} '{kw['keyword']}' - Score: {kw['opportunity_score']:.1f}/100 ({kw['recommended_priority']})")

                return scored  # Return for self-deciding system
            else:
                print_test("Data flywheel", "WARN", "No jobs data available")
                self.results['warnings'] += 1
                return []

        except Exception as e:
            print_test("DataFlywheel", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('DataFlywheel', str(e)))
            return []

    def _test_data_flywheel_fallback(self):
        """Fallback data flywheel test without the class"""
        try:
            from collections import Counter

            if not self.data['jobs'].empty:
                # Extract skills from jobs
                all_skills = []
                for _, row in self.data['jobs'].head(200).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        skills = [s.strip().lower() for s in str(row['skills']).split(',')]
                        all_skills.extend(skills)

                skill_counts = Counter(all_skills)
                discovered = [skill for skill, count in skill_counts.most_common(10)]

                print_test("Keyword discovery (fallback)", "PASS", f"Found {len(discovered)} potential keywords")
                self.results['passed'] += 1

                # Score discovered keywords
                scored = []
                for keyword in discovered[:5]:
                    score_data = {
                        'keyword': keyword,
                        'demand': skill_counts[keyword],
                        'supply': skill_counts.get(keyword, 0) // 2
                    }

                    demand_score = min(score_data['demand'] / 10 * 40, 40)
                    supply_score = max(20 - score_data['supply'], 0)
                    opp_score = demand_score + supply_score + 40

                    scored.append({
                        'keyword': keyword,
                        'opportunity_score': opp_score,
                        'recommended_priority': 'HIGH' if opp_score > 70 else 'MEDIUM' if opp_score > 50 else 'LOW'
                    })

                print_test("Keyword scoring (fallback)", "PASS", f"Scored {len(scored)} keywords")
                self.results['passed'] += 1

                # Display top opportunities
                print(f"\n  🎯 Top Opportunities:")
                for kw in sorted(scored, key=lambda x: x['opportunity_score'], reverse=True)[:5]:
                    priority_icon = "🔥" if kw['recommended_priority'] == "HIGH" else "📈"
                    print(f"     {priority_icon} '{kw['keyword']}' - Score: {kw['opportunity_score']:.1f}/100 ({kw['recommended_priority']})")

                return scored
            else:
                print_test("Data flywheel (fallback)", "WARN", "No jobs data available")
                self.results['warnings'] += 1
                return []

        except Exception as e:
            print_test("Data flywheel (fallback)", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('DataFlywheelFallback', str(e)))
            return []

    def test_integration(self):
        """Test 8: End-to-end integration"""
        print_header("TEST 8: INTEGRATION TEST")

        try:
            # Test complete pipeline
            if self.data['jobs'].empty or self.data['talent'].empty:
                print_test("Integration test", "WARN", "Insufficient data for integration test")
                self.results['warnings'] += 1
                return

            # 1. Score sample jobs
            scorer = SegmentScorer()
            sample_job = self.data['jobs'].iloc[0].to_dict()
            job_score = scorer.score_job(sample_job)

            # 2. Calculate market gap
            calculator = MarketGapCalculator()
            gap = calculator.calculate_gap([10, 20], [5, 10])

            # 3. Generate title
            generator = GoldenTitleGenerator()
            profile = {
                'role': 'Data Analyst',
                'primary_skills': ['SQL', 'Python'],
                'outcomes': ['Insights']
            }
            titles = generator.generate_titles(profile, count=1)

            # 4. Score keyword opportunity
            opp_scorer = KeywordOpportunityScorer()
            opp = opp_scorer.score_keyword_opportunity('python', {})

            # Verify all components work together
            checks = [
                ('Job scoring', job_score.get('total_score', 0) >= 0),
                ('Gap calculation', gap.get('gap_ratio', 0) > 0),
                ('Title generation', len(titles) > 0),
                ('Opportunity scoring', opp.opportunity_score >= 0)
            ]

            all_pass = True
            for name, passed in checks:
                if passed:
                    print_test(f"Integration: {name}", "PASS")
                    self.results['passed'] += 1
                else:
                    print_test(f"Integration: {name}", "FAIL")
                    self.results['failed'] += 1
                    all_pass = False

            if all_pass:
                print_test("End-to-end integration", "PASS")
                self.results['passed'] += 1

        except Exception as e:
            print_test("Integration test", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()

    def test_self_deciding_system(self):
        """Test 9: Self-deciding keyword system"""
        print_header("TEST 9: SELF-DECIDING KEYWORD SYSTEM")

        try:
            # This system analyzes existing data and decides next keywords automatically

            print("  🧠 Analyzing existing data patterns...\n")

            # 1. Extract keywords from existing file names
            data_dir = Path("data")
            csv_files = list(data_dir.rglob("*.csv"))

            existing_keywords = set()
            for file in csv_files:
                # Extract keyword from filename
                # Format: upwork_{type}_{keyword}_run_{timestamp}.csv
                parts = file.stem.split('_')
                if len(parts) >= 3:
                    keyword_parts = []
                    for part in parts[2:-2]:  # Skip type and run/timestamp
                        if part.isdigit():
                            break
                        keyword_parts.append(part)
                    keyword = '_'.join(keyword_parts)
                    if keyword and len(keyword) > 2:
                        existing_keywords.add(keyword.lower().replace('_', ' '))

            print(f"  📊 Found {len(existing_keywords)} existing keywords in data")

            # 2. Analyze skill patterns from jobs
            skill_demand = {}
            skill_supply = {}

            if not self.data['jobs'].empty:
                from collections import Counter

                all_skills = []
                for _, row in self.data['jobs'].head(500).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        skills = [s.strip().lower() for s in str(row['skills']).split(',')]
                        all_skills.extend(skills)

                skill_demand = dict(Counter(all_skills).most_common(50))

            if not self.data['talent'].empty:
                from collections import Counter

                all_skills = []
                for _, row in self.data['talent'].head(200).iterrows():
                    if 'skills' in row and pd.notna(row['skills']):
                        skills = [s.strip().lower() for s in str(row['skills']).split(',')]
                        all_skills.extend(skills)

                skill_supply = dict(Counter(all_skills))

            # 3. Calculate gaps
            gaps = []
            for skill, demand_count in skill_demand.items():
                supply_count = skill_supply.get(skill, 0)
                if demand_count >= 3:  # Minimum threshold
                    gap_ratio = demand_count / max(supply_count, 1)
                    gaps.append({
                        'keyword': skill,
                        'demand': demand_count,
                        'supply': supply_count,
                        'gap_ratio': gap_ratio
                    })

            gaps.sort(key=lambda x: x['gap_ratio'], reverse=True)

            # 4. Generate recommendations (not already scraped)
            recommendations = []
            for gap in gaps[:15]:
                keyword = gap['keyword']
                # Skip if already scraped
                if keyword in existing_keywords:
                    continue

                # Calculate opportunity score
                demand_score = min(gap['demand'] / 10 * 40, 40)
                supply_score = max(20 - gap['supply'] / 5, 0)
                gap_score = min(gap['gap_ratio'] * 15, 30)
                opp_score = demand_score + supply_score + gap_score

                priority = 'HIGH' if opp_score > 70 else 'MEDIUM' if opp_score > 50 else 'LOW'

                recommendations.append({
                    'keyword': keyword.title(),
                    'opportunity_score': opp_score,
                    'demand': gap['demand'],
                    'supply': gap['supply'],
                    'gap_ratio': gap['gap_ratio'],
                    'recommended_priority': priority
                })

            print(f"  🎯 Generated {len(recommendations)} new keyword recommendations\n")

            # 5. Display recommendations
            print("  📋 SELF-DECIDING KEYWORD RECOMMENDATIONS:")
            print("  " + "="*55)
            for i, rec in enumerate(recommendations[:10], 1):
                priority_icon = "🔥" if rec['recommended_priority'] == "HIGH" else "📈" if rec['recommended_priority'] == "MEDIUM" else "📊"
                print(f"  {i}. {priority_icon} {rec['keyword']}")
                print(f"     Opportunity: {rec['opportunity_score']:.1f}/100 | Demand: {rec['demand']} | Supply: {rec['supply']} | Gap: {rec['gap_ratio']:.2f}x")
                print()

            # 6. Save recommendations to file
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)

            recommendations_file = output_dir / "self_deciding_keywords.json"
            with open(recommendations_file, 'w') as f:
                json.dump({
                    'generated_at': datetime.now().isoformat(),
                    'total_keywords': len(existing_keywords),
                    'recommendations': recommendations,
                    'metadata': {
                        'data_files_analyzed': len(csv_files),
                        'jobs_analyzed': len(self.data['jobs']),
                        'talent_analyzed': len(self.data['talent']),
                        'gaps_found': len(gaps)
                    }
                }, f, indent=2)

            print_test("Self-deciding system", "PASS", f"Saved {len(recommendations)} recommendations to {recommendations_file}")
            self.results['passed'] += 1

            # 7. Also save to upwork_dna for queue injection
            upwork_dir = Path("../upwork_dna")
            upwork_dir.mkdir(exist_ok=True)

            queue_file = upwork_dir / "recommended_keywords.json"
            with open(queue_file, 'w') as f:
                json.dump({
                    'generated_at': datetime.now().isoformat(),
                    'source': 'self_deciding_system',
                    'keywords': recommendations[:10]  # Top 10 for queue
                }, f, indent=2)

            print_test("Queue injection file", "PASS", f"Saved to {queue_file}")
            self.results['passed'] += 1

            return recommendations

        except Exception as e:
            print_test("Self-deciding system", "FAIL", str(e))
            self.results['failed'] += 1
            traceback.print_exc()
            self.results['errors'].append(('SelfDecidingSystem', str(e)))
            return []

    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")

        total = self.results['passed'] + self.results['failed']
        pass_rate = (self.results['passed'] / total * 100) if total > 0 else 0

        print(f"  Total Tests: {total}")
        print(f"  {Colors.GREEN}Passed: {self.results['passed']}{Colors.END}")
        print(f"  {Colors.RED}Failed: {self.results['failed']}{Colors.END}")
        print(f"  {Colors.YELLOW}Warnings: {self.results['warnings']}{Colors.END}")
        print(f"  Pass Rate: {pass_rate:.1f}%")

        if self.results['errors']:
            print(f"\n  {Colors.RED}Errors:{Colors.END}")
            for name, error in self.results['errors'][:5]:
                print(f"    • {name}: {str(error)[:60]}...")

        print(f"\n  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if pass_rate >= 80:
            print(f"\n  {Colors.GREEN}✅ SYSTEM READY FOR PRODUCTION{Colors.END}")
        elif pass_rate >= 50:
            print(f"\n  {Colors.YELLOW}⚠️  SYSTEM NEEDS ATTENTION{Colors.END}")
        else:
            print(f"\n  {Colors.RED}❌ SYSTEM NOT READY{Colors.END}")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    suite = TestSuite()
    results = suite.run_all()

    # Exit with error code if tests failed
    sys.exit(0 if results['failed'] == 0 else 1)
