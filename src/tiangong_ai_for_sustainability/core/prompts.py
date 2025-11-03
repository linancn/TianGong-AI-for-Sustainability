"""
Prompt template resolution utilities shared across CLI commands and workflows.

The helpers here provide a deterministic way to pick reusable prompt templates
for LLM-enabled features (e.g. Deep Research or the planned ``research
synthesize`` command). Templates live under ``specs/prompts/`` and can be
selected via aliases (``default``, ``default-cn``) or by passing an explicit
filesystem path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional


class PromptTemplateError(RuntimeError):
    """Raised when a requested prompt template cannot be resolved."""


@dataclass(slots=True)
class LoadedPromptTemplate:
    """Container bundling a prompt template's metadata and raw content."""

    identifier: str
    path: Path
    language: str
    content: str

    def render(self, variables: Mapping[str, str] | None = None) -> str:
        """
        Apply simple ``{{placeholder}}`` substitutions to the template content.

        Parameters
        ----------
        variables:
            Key-value pairs used to replace placeholders. Missing keys are left
            untouched.
        """

        if not variables:
            return self.content
        rendered = self.content
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_DIR = _REPO_ROOT / "specs" / "prompts"

_ALIAS_MAP: Dict[str, tuple[str, str]] = {
    "default": ("research_template.md", "en"),
    "default-en": ("research_template.md", "en"),
    "en": ("research_template.md", "en"),
    "research": ("research_template.md", "en"),
    "default-cn": ("research_template_CN.md", "zh"),
    "cn": ("research_template_CN.md", "zh"),
    "zh": ("research_template_CN.md", "zh"),
    "zh-cn": ("research_template_CN.md", "zh"),
}


def available_prompt_templates() -> Mapping[str, Path]:
    """Return a mapping of registered aliases to template file paths."""

    return {alias: _PROMPT_DIR / entry[0] for alias, entry in _ALIAS_MAP.items()}


def _resolve_path(identifier: Optional[str], language: Optional[str]) -> tuple[str, Path, str]:
    if identifier:
        alias = identifier.strip().lower()
    else:
        alias = ""

    if alias in _ALIAS_MAP:
        filename, lang = _ALIAS_MAP[alias]
        return alias, _PROMPT_DIR / filename, lang

    if not identifier:
        lang_key = (language or "en").lower()
        alias = "default-cn" if lang_key.startswith(("zh", "cn")) else "default"
        filename, lang = _ALIAS_MAP[alias]
        return alias, _PROMPT_DIR / filename, lang

    path = Path(identifier).expanduser()
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    inferred_language = (language or "en").lower()
    return identifier, path, inferred_language


def load_prompt_template(identifier: Optional[str], *, language: Optional[str] = None) -> LoadedPromptTemplate:
    """
    Load a prompt template by alias or filesystem path.

    Parameters
    ----------
    identifier:
        Alias (e.g. ``default-cn``) or path to a Markdown file. When ``None`` the
        helper picks an alias based on the requested language.
    language:
        Optional language hint (``en``, ``zh``). Used to choose between English
        and Chinese defaults and to annotate ad-hoc paths.
    """

    resolved_identifier, path, lang = _resolve_path(identifier, language)

    if not path.is_file():
        raise PromptTemplateError(f"Prompt template '{resolved_identifier}' not found at {path}.")

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PromptTemplateError(f"Prompt template '{resolved_identifier}' is not valid UTF-8: {exc}") from exc

    return LoadedPromptTemplate(
        identifier=resolved_identifier or path.stem,
        path=path,
        language=lang,
        content=content,
    )
