"""
Data source registry declarations and helpers.

The registry acts as an authoritative catalogue for all external systems the CLI
can interact with. Each entry captures both human-authored metadata (priority,
status, documentation references) and machine-usable properties (supported
protocols, capability flags, authentication requirements).

The module supports loading descriptors from YAML documents to keep day-to-day
maintenance approachable for non-developers while still providing typed access
for Python code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, MutableMapping, Optional, Sequence

import yaml


class RegistryLoadError(RuntimeError):
    """Raised when a registry YAML file cannot be parsed or validated."""


class DataSourcePriority(str, Enum):
    """Qualitative priority tiers mirroring the specification's definitions."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class DataSourceStatus(str, Enum):
    """Lifecycle state for individual data sources."""

    ACTIVE = "active"
    TRIAL = "trial"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


@dataclass(slots=True)
class DataSourceDescriptor:
    """
    Metadata and capabilities associated with a single data source.

    Parameters
    ----------
    source_id:
        Unique identifier used across the application.
    name:
        Human-friendly display name.
    category:
        Broad classification (e.g. ``standard``, ``academic``, ``code``,
        ``environment``).
    priority:
        Priority tier reflecting integration importance.
    description:
        Short summary of why the source matters.
    protocols:
        Interaction methods supported by the source (e.g. ``REST``, ``SPARQL``,
        ``XLSX``).
    base_urls:
        Helpful base endpoints for developers integrating the source.
    authentication:
        Description of credential requirements (``none``, ``api-key``,
        ``oauth``).
    requires_credentials:
        Indicates whether runtime credentials are mandatory for the source to
        function. Used to toggle commands automatically.
    status:
        Lifecycle status. ``blocked`` entries must include ``blocked_reason``.
    blocked_reason:
        Additional context when a source is deliberately disabled (e.g. ToS
        violations).
    capabilities:
        Free-form feature flags describing supported behaviours such as
        ``list-goals`` or ``carbon-intensity``.
    tags:
        Keywords for quick filtering (e.g. ``["sdg", "un"]``).
    notes:
        Optional markdown-formatted notes.
    references:
        External references or specification sections backing the metadata.
    """

    source_id: str
    name: str
    category: str
    priority: DataSourcePriority
    description: str
    protocols: Sequence[str] = field(default_factory=tuple)
    base_urls: Sequence[str] = field(default_factory=tuple)
    authentication: str = "none"
    requires_credentials: bool = False
    status: DataSourceStatus = DataSourceStatus.ACTIVE
    blocked_reason: Optional[str] = None
    capabilities: Sequence[str] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)
    notes: Optional[str] = None
    references: Sequence[str] = field(default_factory=tuple)

    def validate(self) -> None:
        """Validate internal consistency of the descriptor."""

        if self.status == DataSourceStatus.BLOCKED and not self.blocked_reason:
            raise RegistryLoadError(f"Data source '{self.source_id}' is blocked but missing a blocked_reason.")
        if not self.source_id or not self.source_id.isidentifier():
            raise RegistryLoadError(f"Data source '{self.source_id}' must be a valid identifier (letters, digits, underscore).")

    def to_json(self) -> str:
        """Return a JSON representation useful for CLI output."""

        payload = {
            "id": self.source_id,
            "name": self.name,
            "category": self.category,
            "priority": self.priority.value,
            "description": self.description,
            "protocols": list(self.protocols),
            "base_urls": list(self.base_urls),
            "authentication": self.authentication,
            "requires_credentials": self.requires_credentials,
            "status": self.status.value,
            "blocked_reason": self.blocked_reason,
            "capabilities": list(self.capabilities),
            "tags": list(self.tags),
            "notes": self.notes,
            "references": list(self.references),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


class DataSourceRegistry:
    """In-memory catalogue of :class:`DataSourceDescriptor` entries."""

    def __init__(self) -> None:
        self._entries: MutableMapping[str, DataSourceDescriptor] = {}

    def register(self, descriptor: DataSourceDescriptor) -> None:
        """Register or overwrite a descriptor in the catalogue."""

        descriptor.validate()
        self._entries[descriptor.source_id] = descriptor

    def unregister(self, source_id: str) -> None:
        """Remove a descriptor from the catalogue."""

        self._entries.pop(source_id, None)

    def get(self, source_id: str) -> Optional[DataSourceDescriptor]:
        """Retrieve a descriptor if present."""

        return self._entries.get(source_id)

    def require(self, source_id: str) -> DataSourceDescriptor:
        """Retrieve a descriptor or raise an informative error."""

        descriptor = self.get(source_id)
        if descriptor is None:
            raise KeyError(f"Data source '{source_id}' is not registered.")
        return descriptor

    def list(self, *, status: Optional[DataSourceStatus] = None) -> List[DataSourceDescriptor]:
        """Return registered descriptors optionally filtered by status."""

        items = self._entries.values()
        if status:
            return [item for item in items if item.status == status]
        return list(items)

    def iter_enabled(self, *, allow_blocked: bool = False) -> Iterator[DataSourceDescriptor]:
        """
        Iterate enabled descriptors.

        Parameters
        ----------
        allow_blocked:
            When ``True`` blocked entries are included. This is primarily useful
            for auditing commands.
        """

        for descriptor in self._entries.values():
            if descriptor.status == DataSourceStatus.BLOCKED and not allow_blocked:
                continue
            yield descriptor

    @classmethod
    def from_yaml(cls, path: Path | str) -> "DataSourceRegistry":
        """Load descriptors from a YAML document."""

        location = Path(path)
        if not location.exists():
            raise RegistryLoadError(f"Registry file '{location}' does not exist.")

        try:
            with location.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
        except yaml.YAMLError as exc:  # pragma: no cover - depends on PyYAML
            raise RegistryLoadError(f"Failed to parse '{location}': {exc}") from exc

        if not isinstance(payload, list):
            raise RegistryLoadError(f"Registry file '{location}' must contain a list of data sources.")

        registry = cls()
        for entry in payload:
            descriptor = cls._descriptor_from_payload(entry, origin=location)
            registry.register(descriptor)
        return registry

    @staticmethod
    def _descriptor_from_payload(entry: Dict[str, object], *, origin: Path) -> DataSourceDescriptor:
        """Convert a YAML mapping into a descriptor instance."""

        if not isinstance(entry, dict):
            raise RegistryLoadError(f"Invalid entry in '{origin}': expected mapping, got {type(entry)!r}")

        try:
            descriptor = DataSourceDescriptor(
                source_id=str(entry["id"]),
                name=str(entry.get("name", entry["id"])),
                category=str(entry.get("category", "misc")),
                priority=DataSourcePriority(str(entry.get("priority", "P4"))),
                description=str(entry.get("description", "")),
                protocols=tuple(_ensure_list(entry.get("protocols"))),
                base_urls=tuple(_ensure_list(entry.get("base_urls"))),
                authentication=str(entry.get("authentication", "none")),
                requires_credentials=bool(entry.get("requires_credentials", False)),
                status=DataSourceStatus(str(entry.get("status", DataSourceStatus.ACTIVE.value))),
                blocked_reason=_optional_str(entry.get("blocked_reason")),
                capabilities=tuple(_ensure_list(entry.get("capabilities"))),
                tags=tuple(_ensure_list(entry.get("tags"))),
                notes=_optional_str(entry.get("notes")),
                references=tuple(_ensure_list(entry.get("references"))),
            )
        except KeyError as exc:
            raise RegistryLoadError(f"Missing required key {exc!s} in '{origin}'.") from exc
        except ValueError as exc:
            raise RegistryLoadError(f"Invalid field in '{origin}': {exc}") from exc

        descriptor.validate()
        return descriptor


def _ensure_list(value: object | None) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _optional_str(value: object | None) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
