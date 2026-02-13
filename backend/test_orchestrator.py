import tempfile
import unittest

from orchestrator import (
    OrchestratorService,
    compute_fit_score,
    compute_safety_score,
    parse_money_value,
)


class OrchestratorScoringTests(unittest.TestCase):
    def test_parse_money_value_supports_ranges_and_k(self):
        self.assertAlmostEqual(parse_money_value("$500-$1,500"), 1000.0)
        self.assertAlmostEqual(parse_money_value("2k"), 2000.0)

    def test_fit_score_ai_data_profile(self):
        text = "AI Data Analyst with Python SQL ETL dashboard and LLM analytics"
        score = compute_fit_score(text)
        self.assertGreaterEqual(score, 60.0)

    def test_safety_score_flags_suspicious_jobs(self):
        safe = compute_safety_score(
            payment_verified=True,
            client_spend=2500,
            proposals=8,
            budget_value=600,
            description="Detailed project scope with milestones and clear deliverables.",
        )
        risky = compute_safety_score(
            payment_verified=False,
            client_spend=0,
            proposals=80,
            budget_value=5,
            description="Contact on telegram for upfront fee and crypto wallet transfer.",
        )
        self.assertGreater(safe, risky)
        self.assertGreaterEqual(safe, 60.0)
        self.assertLess(risky, 50.0)

    def test_column_mapping_variants(self):
        service = OrchestratorService(data_root=tempfile.gettempdir())
        row = {
            "job_title": "Python Data Analyst",
            "detail_summary": "Need ETL and dashboard automation with SQL",
            "detail_job_url": "https://www.upwork.com/jobs/~0123456789",
            "payment_verified": "true",
            "client_spend": "$1200",
            "hourly_rate": "$45/hr",
            "proposals": "10 to 15",
            "keyword": "ai data analyst",
        }
        normalized = service._normalize_job_row(row, "fallback keyword")
        self.assertEqual(normalized["keyword"], "ai data analyst")
        self.assertTrue(normalized["payment_verified"])
        self.assertEqual(normalized["job_key"], "~0123456789")
        self.assertGreater(normalized["budget_value"], 40)

    def test_draft_builder_outputs_hooks(self):
        service = OrchestratorService(data_root=tempfile.gettempdir())
        row = {
            "title": "AI Dashboard Build",
            "description": "Need Python + SQL ETL dashboard for analytics",
            "url": "https://www.upwork.com/jobs/~0abc",
            "budget": "$500",
            "keyword": "ai data analyst",
        }
        job = service._normalize_job_row(row, "ai data analyst")
        # Build a light in-memory job object shape using dict-style access helper.
        class JobObj:
            def __init__(self, payload):
                self.title = payload["title"]
                self.description = payload["description"]
                self.skills = payload["skills"]
                self.proposals = payload["proposals"]
                self.budget_value = payload["budget_value"]

        draft = service._build_rule_based_draft(JobObj(job), fit_score=85, safety_score=75)
        self.assertTrue(draft["cover_letter_draft"])
        self.assertGreater(len(draft["hook_points"]), 0)


if __name__ == "__main__":
    unittest.main()
