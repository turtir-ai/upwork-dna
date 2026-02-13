"""
LLM Integration module for Upwork DNA.
Connects to glm-bridge (localhost:8765) for AI-powered job analysis,
decision engine, and proposal generation.
"""
from .client import LLMClient, LLMError, LLMConnectionError, LLMResponseError
from .job_analyzer import JobAnalyzer, JobAnalysis
from .decision_engine import DecisionEngine, DecisionBatch
from .proposal_writer import ProposalWriter, Proposal
from .keyword_discoverer import KeywordDiscoverer, KeywordSuggestion
from .keyword_strategy import KeywordStrategyAdvisor, KeywordStrategyResult, ProfileFitScore

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMConnectionError",
    "LLMResponseError",
    "JobAnalyzer",
    "JobAnalysis",
    "DecisionEngine",
    "DecisionBatch",
    "ProposalWriter",
    "Proposal",
    "KeywordDiscoverer",
    "KeywordSuggestion",
    "KeywordStrategyAdvisor",
    "KeywordStrategyResult",
    "ProfileFitScore",
]
