"""Cross-source analysis layer.

This package composes multiple data sources (e.g. FBI + Census) into derived
statistics. It performs NO import-time environment-variable validation: source
credentials are only required when an analysis function is actually called, at which
point the relevant source is lazily imported.
"""

from . import taxonomy
from .per_capita import per_capita_by_race

__all__ = ["per_capita_by_race", "taxonomy"]
