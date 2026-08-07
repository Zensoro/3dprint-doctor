"""Rule-based root cause attribution for detected print defects.

Combines detected defect types with user-provided print parameter
hints (material, layer height, temperature, retraction...) to rank
likely root causes and suggest parameter changes.
"""
from typing import List, Dict, Any

from print_doctor.models import Defect, DefectType, RootCause

# cause -> (defect types it explains, fix suggestion template)
_CAUSE_RULES: List[Dict[str, Any]] = [
    {
        "cause": "Retraction distance too low (or off)",
        "fix": "Increase retraction distance by 0.5-1.0 mm (e.g. 4 -> 5 mm for direct drive, 6 -> 7 mm for bowden)",
        "defects": {DefectType.STRINGING},
    },
    {
        "cause": "Nozzle temperature too high",
        "fix": "Lower nozzle temperature by 5-10 C",
        "defects": {DefectType.STRINGING, DefectType.COLOR_BLEEDING},
    },
    {
        "cause": "Bed adhesion too weak / bed not level",
        "fix": "Re-level the bed, clean the build surface, raise bed temperature by 5-10 C",
        "defects": {DefectType.FIRST_LAYER_FAILURE, DefectType.WARPING},
    },
    {
        "cause": "Bed temperature too low (part cools unevenly)",
        "fix": "Raise bed temperature by 5-10 C or add a draft shield / enclosure",
        "defects": {DefectType.WARPING},
    },
    {
        "cause": "Z-axis mechanical issue (binding, backlash, or Z-step misconfiguration)",
        "fix": "Lubricate/straighten Z leadscrews, check Z belt/screw tightness and motor currents",
        "defects": {DefectType.LAYER_SHIFT},
    },
    {
        "cause": "Layer height inconsistent with nozzle (too small layer for 0.4mm nozzle)",
        "fix": "Use layer height between 0.12 and 0.32 mm for a 0.4 mm nozzle",
        "defects": {DefectType.LAYER_SHIFT},
    },
    {
        "cause": "Under-extrusion: flow rate too low or partial clog",
        "fix": "Increase flow rate 5-10%, check nozzle for partial clog, verify filament diameter",
        "defects": {DefectType.UNDER_EXTRUSION},
    },
    {
        "cause": "Over-extrusion: flow rate too high or nozzle temp too low (poor melt)",
        "fix": "Decrease flow rate 5-10%, raise nozzle temperature 5 C",
        "defects": {DefectType.OVER_EXTRUSION},
    },
    {
        "cause": "Filament contamination / wrong material loaded",
        "fix": "Purge nozzle and reload clean filament of a single type/color",
        "defects": {DefectType.COLOR_BLEEDING},
    },
    {
        "cause": "Print speed too high or cooling insufficient",
        "fix": "Lower print speed 20-30% or increase part cooling fan",
        "defects": {DefectType.STRINGING, DefectType.WARPING, DefectType.OVER_EXTRUSION},
    },
]

# Parameter hints that weaken a cause's likelihood
_PARAMETER_HINTS: Dict[str, Dict[DefectType, str]] = {
    "temperature": {
        DefectType.STRINGING: "nozzle temperature already low",
        DefectType.COLOR_BLEEDING: "temperature already low",
    },
}


def attribute_causes(
    defects: List[Defect],
    hints: Dict[str, str] = None,
) -> List[RootCause]:
    """Rank root causes for the detected defects.

    Each detected defect votes for every cause that can explain it.
    Causes are scored by the number of votes weighted by defect
    confidence. Optional hints (e.g. {"temperature": "low"}) adjust
    likelihood.

    Args:
        defects: Detected defects
        hints: Optional print parameter hints provided by the user

    Returns:
        Ranked list of RootCause
    """
    hints = hints or {}

    scores: Dict[str, float] = {}
    for rule in _CAUSE_RULES:
        matching = [d for d in defects if d.type in rule["defects"]]
        if not matching:
            continue
        score = sum(d.confidence for d in matching) / len(matching)
        for d in matching:
            if d.type in _PARAMETER_HINTS.get("temperature", {}):
                pass  # hint logic below

        for param, value in hints.items():
            for d in matching:
                lowered = _PARAMETER_HINTS.get(param, {}).get(d.type)
                if lowered and value.lower() in ("low", "already low", "low already"):
                    score *= 0.5

        scores[rule["cause"]] = score

    causes = [
        RootCause(
            cause=cause,
            likelihood=min(0.95, score),
            fix=next(r["fix"] for r in _CAUSE_RULES if r["cause"] == cause),
        )
        for cause, score in sorted(
            scores.items(), key=lambda kv: kv[1], reverse=True
        )
    ]
    return causes
