"""G-code analysis: layer parsing and print progress estimation.

Understands the two common slicer layer markers:
  - OrcaSlicer / PrusaSlicer: ``;LAYER_CHANGE`` followed by ``;Z:...``
  - Bambu Studio: ``;LAYER:<n>``

Also counts extruder moves and estimates progress by extruded volume
(E-axis accumulation), which works across slicers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

LAYER_CHANGE_RE = re.compile(r";LAYER_CHANGE")
LAYER_NUM_RE = re.compile(r";LAYER:(\d+)")
E_MOVE_RE = re.compile(r"E([-\d.]+)")
Z_MOVE_RE = re.compile(r"Z([\d.]+)")


@dataclass
class LayerInfo:
    """A single layer: its number, Z height and extruded volume range."""
    number: int
    z: Optional[float]
    start_e: float
    end_e: float
    move_count: int = 0

    @property
    def e_volume(self) -> float:
        return max(0.0, self.end_e - self.start_e)


@dataclass
class GCodeAnalysis:
    """Result of analyzing a G-code file."""
    filename: str = ""
    layers: List[LayerInfo] = field(default_factory=list)
    total_extruded: float = 0.0
    total_moves: int = 0
    max_z: float = 0.0

    @property
    def layer_count(self) -> int:
        return len(self.layers)

    def layer_at(self, e_position: float) -> Optional[LayerInfo]:
        """Return the layer currently being printed at an E position."""
        for layer in self.layers:
            if layer.start_e <= e_position <= layer.end_e:
                return layer
        return None

    def progress_at(self, e_position: float) -> float:
        """Fraction [0,1] of the print completed at an E position."""
        if self.total_extruded <= 0:
            return 0.0
        return min(1.0, max(0.0, e_position / self.total_extruded))


def parse_gcode(text: str, filename: str = "") -> GCodeAnalysis:
    """Parse G-code text into layer/volume structure."""
    analysis = GCodeAnalysis(filename=filename)
    current: Optional[LayerInfo] = None
    total_e = 0.0
    moves = 0
    max_z = 0.0

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("("):
            continue

        # layer boundary?
        if LAYER_CHANGE_RE.search(stripped):
            if current is not None:
                current.end_e = total_e
                analysis.layers.append(current)
            current = LayerInfo(
                number=len(analysis.layers), z=None,
                start_e=total_e, end_e=0.0,
            )
            zm = Z_MOVE_RE.search(stripped)
            if zm:
                current.z = float(zm.group(1))
        else:
            lm = LAYER_NUM_RE.search(stripped)
            if lm:
                if current is not None:
                    current.end_e = total_e
                    analysis.layers.append(current)
                current = LayerInfo(
                    number=int(lm.group(1)), z=None,
                    start_e=total_e, end_e=0.0,
                )

        # track Z height
        zm = Z_MOVE_RE.search(stripped)
        if zm:
            z = float(zm.group(1))
            if z > max_z:
                max_z = z
            if current is not None:
                current.z = z

        # track extrusion
        em = E_MOVE_RE.search(stripped)
        if em:
            total_e += float(em.group(1))
            moves += 1
            if current is not None:
                current.move_count += 1

    if current is not None:
        current.end_e = total_e
        analysis.layers.append(current)

    analysis.total_extruded = total_e
    analysis.total_moves = moves
    analysis.max_z = max_z
    return analysis


def parse_gcode_file(path: str) -> GCodeAnalysis:
    """Parse a G-code file from disk."""
    with open(path, "r", errors="ignore") as f:
        return parse_gcode(f.read(), filename=path)
