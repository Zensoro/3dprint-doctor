# Writing Detector Plugins

Print Doctor's `check` command runs a set of **detectors**, each of which can
add issues to a report. Detectors are pluggable — you can extend analysis
without touching the core.

## The interface

A detector is a subclass of `MeshDetector` with a `detect()` method:

```python
from typing import List
import trimesh
from print_doctor import MeshDetector, register_detector
from print_doctor.models import Issue, Severity


class MyDetector(MeshDetector):
    name = "my_detector"

    def detect(self, mesh: trimesh.Trimesh) -> List[Issue]:
        issues = []
        if something_wrong(mesh):
            issues.append(Issue(
                name="my_issue",
                description="what is wrong and why",
                severity=Severity.WARNING,
                location="where",
                suggestion="how to fix",
            ))
        return issues
```

## Registering

### In-app (simplest)

```python
register_detector(MyDetector)
```

This works anywhere — your own script, a sitecustomize, or a helper package
you import before running analysis.

### Via entry points (installed packages)

Declare your detector in `pyproject.toml`:

```toml
[project.entry-points."print_doctor.detectors"]
my_detector = "my_package.detectors:MyDetector"
```

Print Doctor discovers it automatically when analysis runs.

## Using it

```bash
# Run all detectors (built-in + plugins)
print-doctor check model.stl

# Run only specific detectors
print-doctor check model.stl -D structural -D my_detector

# List what's available
print-doctor detectors
```

## Guidelines for detector authors

- **Explainable** — every issue must say *why* (evidence) and *how to fix*.
- **Don't crash analysis** — if your detector throws, it is skipped; other
  detectors still run. But raise only for genuinely unexpected conditions.
- **Severity matters** — use `Severity.ERROR` for print-blocking issues,
  `Severity.WARNING` for risky, `Severity.INFO` for cosmetic.
- **Keep it fast** — detectors run on every `check`; heavy analysis should be
  opt-in via an option.

## Example

A real detector that flags tiny disconnected blobs:

```python
class BlobDetector(MeshDetector):
    name = "blobs"

    def detect(self, mesh):
        bodies = mesh.split()
        if len(bodies) > 1:
            tiny = [b for b in bodies if b.volume < 1e-3 * mesh.volume]
            if tiny:
                return [Issue(
                    name="tiny_blobs",
                    description=f"{len(tiny)} tiny disconnected pieces",
                    severity=Severity.WARNING,
                    location="scattered",
                    suggestion="Remove or merge the tiny components",
                )]
        return []
```

!!! tip
    Plugins can be shipped as independent PyPI packages. The `check` report,
    JSON output, and `--detector` filter all work with plugin issues.
