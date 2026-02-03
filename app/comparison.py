"""
comparison.py
This module implements the core comparison logic between nameplate and
submittal equipment data. It normalises units, applies tolerance rules and
categorises each attribute into compliance categories.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import math

from .extraction import EquipmentData, AttributeValue


@dataclass
class ComparisonResult:
    """Holds the result of comparing a single equipment attribute."""

    field: str
    nameplate_value: Optional[str]
    submittal_value: Optional[str]
    status: str
    comment: str
    nameplate_source: Optional[Dict[str, Any]] = None
    submittal_source: Optional[Dict[str, Any]] = None


def normalise_power(value: float, unit: Optional[str]) -> float:
    """Convert power to kW. Supports kW, kVA (treated as kW for now) and W."""
    if unit is None:
        return value
    unit = unit.lower()
    if unit == "w":
        return value / 1000.0
    if unit in ("kw", "kva"):
        return value
    # Unknown unit – return as-is
    return value


def normalise_voltage(value: float, unit: Optional[str]) -> float:
    """Normalise voltage (V/VAC/volts). Returns volts."""
    return value  # All units treated as volts


def normalise_current(value: float, unit: Optional[str]) -> float:
    """Normalise current (A/amps). Returns amps."""
    return value


def normalise_frequency(value: float, unit: Optional[str]) -> float:
    """Normalise frequency (Hz). Returns hertz."""
    return value


def compare_numeric(n_value: Optional[float], n_unit: Optional[str], s_value: Optional[float], s_unit: Optional[str], tolerance_pct: float = 5.0) -> Tuple[str, str]:
    """Compare numeric values with tolerance.

    Args:
        n_value: Nameplate numeric value.
        n_unit: Nameplate unit.
        s_value: Submittal numeric value.
        s_unit: Submittal unit.
        tolerance_pct: Allowed deviation in percentage for minor deviations.

    Returns:
        (status, comment)
    """
    if n_value is None and s_value is None:
        return "Not Found", "Value missing in both nameplate and submittal."
    if n_value is None:
        return "Non-Compliant", "No value on nameplate."
    if s_value is None:
        return "Non-Compliant", "No value in submittal."

    # Compute absolute values after normalisation – units are assumed compatible
    n_val = n_value
    s_val = s_value
    if n_val == 0 and s_val == 0:
        return "Compliant", "Both values are zero."
    if s_val == 0:
        # Avoid division by zero. If nameplate is not zero then non-compliant
        return (
            "Non-Compliant",
            f"Submittal value is zero while nameplate is {n_val}.",
        )
    diff_pct = abs(n_val - s_val) / s_val * 100.0
    if diff_pct < 1e-6:
        return "Compliant", "Values are identical."
    if diff_pct <= tolerance_pct:
        return ("Minor Deviation", f"Difference of {diff_pct:.2f}% within tolerance.")
    return ("Non-Compliant", f"Difference of {diff_pct:.2f}% exceeds tolerance.")


def compare_attribute(nameplate_attr: AttributeValue, submittal_attr: AttributeValue, field: str) -> ComparisonResult:
    """Compare a single attribute between nameplate and submittal.

    Args:
        nameplate_attr: The attribute from the nameplate.
        submittal_attr: The attribute from the submittal.
        field: Name of the field being compared.

    Returns:
        A `ComparisonResult` summarising the outcome.
    """
    np_val = nameplate_attr.value
    np_unit = nameplate_attr.unit
    sm_val = submittal_attr.value
    sm_unit = submittal_attr.unit
    status = ""
    comment = ""

    # Determine if numeric or categorical
    numeric_fields = {"voltage", "current", "power", "frequency"}
    if field in numeric_fields:
        # Normalise values for comparison
        if field == "power":
            np_norm = normalise_power(np_val, np_unit) if np_val is not None else None
            sm_norm = normalise_power(sm_val, sm_unit) if sm_val is not None else None
        elif field == "voltage":
            np_norm = normalise_voltage(np_val, np_unit) if np_val is not None else None
            sm_norm = normalise_voltage(sm_val, sm_unit) if sm_val is not None else None
        elif field == "current":
            np_norm = normalise_current(np_val, np_unit) if np_val is not None else None
            sm_norm = normalise_current(sm_val, sm_unit) if sm_val is not None else None
        else:  # frequency
            np_norm = normalise_frequency(np_val, np_unit) if np_val is not None else None
            sm_norm = normalise_frequency(sm_val, sm_unit) if sm_val is not None else None
        status, comment = compare_numeric(np_norm, np_unit, sm_norm, sm_unit)
        nameplate_str = f"{np_val} {np_unit}" if np_val is not None else None
        submittal_str = f"{sm_val} {sm_unit}" if sm_val is not None else None
    else:
        # Categorical comparison (manufacturer, model, serial, ip, certification)
        if np_val is None and sm_val is None:
            status = "Not Found"
            comment = "Value missing in both nameplate and submittal."
        elif np_val is None:
            status = "Non-Compliant"
            comment = "No value on nameplate."
        elif sm_val is None:
            status = "Non-Compliant"
            comment = "No value in submittal."
        else:
            if str(np_val).strip().lower() == str(sm_val).strip().lower():
                status = "Compliant"
                comment = "Values match."
            else:
                status = "Non-Compliant"
                comment = f"Nameplate value '{np_val}' differs from submittal value '{sm_val}'."
        nameplate_str = str(np_val) if np_val is not None else None
        submittal_str = str(sm_val) if sm_val is not None else None

    return ComparisonResult(
        field=field,
        nameplate_value=nameplate_str,
        submittal_value=submittal_str,
        status=status,
        comment=comment,
        nameplate_source=nameplate_attr.source,
        submittal_source=submittal_attr.source,
    )


def compare_equipment(nameplate: EquipmentData, submittal: EquipmentData) -> List[ComparisonResult]:
    """Compare two equipment data objects field by field.

    Returns a list of comparison results.
    """
    results: List[ComparisonResult] = []
    for field_name in nameplate.__dataclass_fields__:  # type: ignore
        np_attr = getattr(nameplate, field_name)
        sm_attr = getattr(submittal, field_name)
        results.append(compare_attribute(np_attr, sm_attr, field_name))
    return results
