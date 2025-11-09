"""Adapters interacting with environmental and real-time data sources."""

from .google_earth_engine import GoogleEarthEngineCLIAdapter
from .grid_intensity import GridIntensityCLIAdapter

__all__ = ["GridIntensityCLIAdapter", "GoogleEarthEngineCLIAdapter"]
