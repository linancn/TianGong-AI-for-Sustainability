"""
Prompt template resolution utilities shared across CLI commands and workflows.

The helpers here provide a deterministic way to pick reusable prompt templates
for LLM-enabled features (e.g. Deep Research or the planned ``research
synthesize`` command). Templates live under ``specs/prompts/`` and can be
selected via aliases (e.g. ``default``) or by passing an explicit filesystem
path.
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
    "default": ("default.md", "en"),
    "default-en": ("default.md", "en"),
    "en": ("default.md", "en"),
    "research": ("default.md", "en"),
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
        filename, lang = _ALIAS_MAP["default"]
        return "default", _PROMPT_DIR / filename, lang

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
        Alias (e.g. ``default``) or path to a Markdown file. When ``None`` the
        helper picks the default alias.
    language:
        Optional language hint used only to annotate ad-hoc paths; all registered
        aliases resolve to the English template.
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
