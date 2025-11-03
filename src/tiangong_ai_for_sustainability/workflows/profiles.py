"""
Domain profiles that parameterise reusable research workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable, Sequence


@dataclass(slots=True, frozen=True, kw_only=True)
class CitationProfile:
    """
    Configuration for a deterministic citation workflow.
    """

    slug: str
    display_name: str
    focus_description: str
    default_keywords: Sequence[str]
    search_phrase: str
    concept_ids: Sequence[str] = ()
    question_context: str = ""
    gap_suffix: str = ""
    required_keywords: Sequence[str] = ()
    chart_topic_title: str | None = None
    chart_question_title: str | None = None

    def normalised_keywords(self) -> Sequence[str]:
        return tuple(kw.strip().lower() for kw in self.default_keywords if isinstance(kw, str) and kw.strip())

    def topic_chart_title(self) -> str:
        if self.chart_topic_title:
            return self.chart_topic_title
        return f"Emerging {self.display_name} topics by citation momentum"

    def question_chart_title(self) -> str:
        if self.chart_question_title:
            return self.chart_question_title
        return f"Top {self.display_name} questions by citation count"


@dataclass(slots=True, frozen=True, kw_only=True)
class DeepResearchProfile(CitationProfile):
    """
    Extension of :class:`CitationProfile` with Deep Research synthesis metadata.
    """

    deep_report_title: str
    prompt_question: str
    prompt_follow_ups: Sequence[str]
    prompt_context_template: str
    prompt_instructions: str = (
        "Synthesize the findings into concise sections that complement the "
        "deterministic citation scan provided in the context. Highlight citation "
        "leaders, accelerating themes, and unanswered questions."
    )

    def with_overrides(self, **overrides: object) -> "DeepResearchProfile":
        return replace(self, **overrides)

    def final_report_filename(self) -> str:
        return f"{self.slug}_deep_report.md"

    def citation_report_filename(self) -> str:
        return f"{self.slug}_citations.md"

    def chart_filename(self) -> str:
        return f"{self.slug}_trends.png"

    def dataset_filename(self) -> str:
        return f"{self.slug}_citations.json"


LCA_DEFAULT_KEYWORDS = (
    "life cycle assessment",
    "lca",
    "sustainability",
    "planetary boundaries",
    "sustainable development goals",
    "sdg",
)

LCA_DEEP_RESEARCH_PROFILE = DeepResearchProfile(
    slug="lca",
    display_name="LCA × Planetary Boundaries",
    focus_description=(
        "Peer-reviewed LCA journals intersecting planetary boundaries and the "
        "Sustainable Development Goals, filtered via OpenAlex (concept-driven) "
        "with Semantic Scholar enrichment when available."
    ),
    default_keywords=LCA_DEFAULT_KEYWORDS,
    required_keywords=("life cycle assessment",),
    search_phrase="life cycle assessment sustainability",
    concept_ids=("C2778706760",),
    question_context="life cycle assessment",
    gap_suffix=" with LCA framing.",
    chart_topic_title="Emerging LCA topics by citation momentum",
    chart_question_title="Top LCA questions by citation count",
    deep_report_title="LCA × Planetary Boundaries Deep Research",
    prompt_question=("Investigate how recent peer-reviewed life cycle assessment (LCA) research " "connects planetary boundaries with the Sustainable Development Goals."),
    prompt_follow_ups=(
        "Which research questions attract the highest citation energy and why?",
        "Which LCA sub-topics show accelerating citation trends in the last few years?",
        "Where do clear research gaps remain that could yield high impact if addressed?",
    ),
    prompt_context_template=("Time horizon: last {years} years. Assume the deterministic citation scan has " "already filtered relevant journals and returns structured summaries."),
)

CITATION_PROFILES: Dict[str, CitationProfile] = {
    LCA_DEEP_RESEARCH_PROFILE.slug: LCA_DEEP_RESEARCH_PROFILE,
}

DEEP_RESEARCH_PROFILES: Dict[str, DeepResearchProfile] = {
    LCA_DEEP_RESEARCH_PROFILE.slug: LCA_DEEP_RESEARCH_PROFILE,
}


def list_citation_profiles() -> Iterable[CitationProfile]:
    return CITATION_PROFILES.values()


def get_citation_profile(slug: str) -> CitationProfile:
    try:
        profile = CITATION_PROFILES[slug]
    except KeyError as exc:
        raise KeyError(f"Unknown citation profile '{slug}'.") from exc
    return profile


def get_deep_research_profile(slug: str) -> DeepResearchProfile:
    try:
        profile = DEEP_RESEARCH_PROFILES[slug]
    except KeyError as exc:
        raise KeyError(f"Unknown deep research profile '{slug}'.") from exc
    return profile
