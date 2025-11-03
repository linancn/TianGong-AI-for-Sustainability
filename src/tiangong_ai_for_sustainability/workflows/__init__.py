"""Workflow helpers that orchestrate multi-step research pipelines."""

from .citation_template import run_citation_template_workflow, run_lca_citation_workflow
from .deep_research import run_deep_lca_report, run_deep_research_template
from .metrics import run_trending_metrics_workflow
from .papers import run_paper_search
from .simple import run_simple_workflow
from .synthesize import run_synthesis_workflow

__all__ = [
    "run_simple_workflow",
    "run_citation_template_workflow",
    "run_lca_citation_workflow",
    "run_deep_research_template",
    "run_deep_lca_report",
    "run_trending_metrics_workflow",
    "run_synthesis_workflow",
    "run_paper_search",
]
