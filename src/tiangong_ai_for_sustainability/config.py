"""
Secret management helpers shared across TianGong automation modules.

Secrets are loaded from ``.secrets/secret.toml`` by default. The lookup order is:

1. Explicit ``TIANGONG_SECRETS_PATH`` environment variable.
2. Project-relative ``.secrets/secret.toml`` (both from CWD and the package root).
3. Project-relative ``.secrets/secrets.toml``.
4. Fallback to ``.secrets/secrets.example.toml`` for scaffolding values.

Call :func:`load_secrets` to retrieve a :class:`SecretsBundle` instance and the
underlying ``dict`` as needed.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass(slots=True)
class OpenAISettings:
    """Model and credential information for OpenAI usage."""

    api_key: Optional[str] = None
    default_model: Optional[str] = None
    chat_model: Optional[str] = None
    deep_research_model: Optional[str] = None

    def resolve_chat_model(self) -> Optional[str]:
        """Best-effort chat model fallback chain."""
        return self.chat_model or self.default_model

    def resolve_deep_research_model(self) -> Optional[str]:
        """Best-effort deep research model fallback chain."""
        return self.deep_research_model or self.default_model or self.chat_model


@dataclass(slots=True)
class SecretsBundle:
    """Lightweight container for parsed secret values."""

    source_path: Optional[Path]
    data: Dict[str, Dict[str, object]]
    openai: OpenAISettings


def _candidate_paths() -> Iterable[Path]:
    env_override = os.getenv("TIANGONG_SECRETS_PATH")
    if env_override:
        yield Path(env_override).expanduser()

    package_root = Path(__file__).resolve().parents[3]
    cwd = Path.cwd()

    def secrets_paths(base: Path) -> Iterable[Path]:
        secrets_dir = base / ".secrets"
        for filename in ("secret.toml", "secrets.toml"):
            yield secrets_dir / filename
        yield secrets_dir / "secrets.example.toml"

    seen: set[Path] = set()
    for base in (cwd, package_root):
        for candidate in secrets_paths(base):
            if candidate not in seen:
                seen.add(candidate)
                yield candidate


def _load_toml(path: Path) -> Dict[str, Dict[str, object]]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _extract_openai_settings(raw: Dict[str, Dict[str, object]]) -> OpenAISettings:
    section = raw.get("openai", {}) if isinstance(raw, dict) else {}
    if not isinstance(section, dict):
        section = {}

    def _extract(key: str) -> Optional[str]:
        value = section.get(key)
        return str(value) if isinstance(value, str) and value else None

    return OpenAISettings(
        api_key=_extract("api_key"),
        default_model=_extract("model"),
        chat_model=_extract("chat_model"),
        deep_research_model=_extract("deep_research_model"),
    )


def load_secrets(strict: bool = False) -> SecretsBundle:
    """
    Attempt to load secrets from the configured locations.

    Parameters
    ----------
    strict:
        When ``True`` the function raises ``FileNotFoundError`` if no secrets file is
        discovered. Defaults to ``False`` for ease of use in development environments.
    """

    for path in _candidate_paths():
        if path.is_file():
            data = _load_toml(path)
            return SecretsBundle(source_path=path, data=data, openai=_extract_openai_settings(data))

    if strict:
        raise FileNotFoundError("No secrets file found. Configure TIANGONG_SECRETS_PATH or .secrets/secret.toml.")

    return SecretsBundle(source_path=None, data={}, openai=OpenAISettings())
