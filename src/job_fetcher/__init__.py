"""VC portfolio software engineering job fetcher."""

from .models import Job
from .pipeline import deduplicate

__all__ = ["Job", "deduplicate"]
