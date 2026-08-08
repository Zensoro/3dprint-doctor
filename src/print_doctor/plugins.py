"""Plugin architecture for mesh detectors.

Print Doctor supports third-party detectors via a small plugin system:

- A detector is a subclass of :class:`MeshDetector` implementing
  :meth:`MeshDetector.detect`, returning a list of :class:`Issue`.
- Detectors are discovered in two ways:
  1. Entry points in the ``print_doctor.detectors`` group (the standard way
     for installed packages).
  2. Explicit registration via :func:`register_detector` / :func:`load_plugins`
     (for in-app plugins and tests).

Built-in detectors use the same interface, so `check` treats every detector
identically.
"""
from typing import Dict, List, Type

import trimesh

from print_doctor.models import Issue

# Registry of detector classes keyed by name. Entry-point discovered
# detectors are merged in at load time.
_REGISTRY: Dict[str, Type["MeshDetector"]] = {}


class MeshDetector:
    """Base class for mesh detectors.

    Subclass and implement :meth:`detect`. Optionally set a ``name``
    (defaults to the class name) used in issue reports and enablement.
    """

    name: str = ""

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        """Run detection and return issues found.

        Args:
            mesh: The mesh to analyze

        Returns:
            List of Issue (empty if none)
        """
        raise NotImplementedError

    # -- convenience -------------------------------------------------
    @property
    def display_name(self) -> str:
        return self.name or self.__class__.__name__

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MeshDetector {self.display_name}>"


def register_detector(cls: Type[MeshDetector]) -> Type[MeshDetector]:
    """Register a detector class by name (decorator or direct call)."""
    name = getattr(cls, "name", "") or cls.__name__
    _REGISTRY[name] = cls
    return cls


def get_registered_detectors() -> Dict[str, Type[MeshDetector]]:
    """Return a copy of the current registry."""
    return dict(_REGISTRY)


def load_plugins() -> Dict[str, Type[MeshDetector]]:
    """Discover entry-point detectors and merge into the registry.

    Scans the ``print_doctor.detectors`` entry-point group and registers
    any found classes. Returns the merged registry.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return dict(_REGISTRY)

    eps = entry_points()
    # entry_points() may be a SelectableGroups or a flat sequence across
    # Python versions.
    if hasattr(eps, "select"):
        group = eps.select(group="print_doctor.detectors")
    else:
        group = [ep for ep in eps if ep.group == "print_doctor.detectors"]

    for ep in group:
        try:
            cls = ep.load()
            register_detector(cls)
        except Exception:
            # A broken plugin must not break `check`
            continue
    return dict(_REGISTRY)


def run_detectors(mesh: trimesh.Trimesh) -> List[Issue]:
    """Run all registered detectors against a mesh and merge issues.

    Also calls :func:`load_plugins` so entry-point detectors are picked up.
    """
    load_plugins()
    issues: List[Issue] = []
    for cls in _REGISTRY.values():
        try:
            detector = cls()
            issues.extend(detector.detect(mesh))
        except Exception:
            # One failing detector should not abort analysis
            continue
    return issues
