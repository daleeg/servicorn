"""Minimal pkg_resources compatibility layer for legacy dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

__all__ = ["DistributionNotFound", "Distribution", "get_distribution"]


class DistributionNotFound(Exception):
    """Raised when a requested distribution is not installed."""


@dataclass(frozen=True)
class Distribution:
    """Subset of the setuptools distribution API used by legacy packages."""

    project_name: str
    version: str


def get_distribution(project_name: str) -> Distribution:
    try:
        installed_version = version(project_name)
    except PackageNotFoundError as exc:
        raise DistributionNotFound(str(exc)) from exc
    return Distribution(project_name=project_name, version=installed_version)
