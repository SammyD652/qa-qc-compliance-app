"""
extraction.py
This module is responsible for converting raw OCR output into a structured
representation suitable for comparison. It defines a normalised JSON schema
for equipment attributes and provides helper functions to parse common
parameters from free-form text.

The goal of this layer is to encapsulate the messy reality of text parsing
while presenting a clean, predictable API to the comparison engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
import re


@dataclass
class AttributeValue:
    """Represents a normalised attribute extracted from a document.

    The source dictionary holds metadata about where the value was found,
    such as the page number or bounding box. This enables explainability
    during reporting.
    """

    value: Optional[Any]
    unit: Optional[str] = None
    source: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.unit, str):
            self.unit = self.unit.strip()


@dataclass
class EquipmentData:
    """Defines the normalised schema for equipment information."""

    manufacturer: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    model: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    serial_number: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    voltage: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    current: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    power: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    frequency: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    ip_rating: AttributeValue = field(default_factory=lambda: AttributeValue(None))
    certification: AttributeValue = field(default_factory=lambda: AttributeValue(None))

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to a serialisable dictionary."""
        return {
            field_name: {
                "value": getattr(self, field_name).value,
                "unit": getattr(self, field_name).unit,
                "source": getattr(self, field_name).source,
            }
            for field_name in self.__dataclass_fields__  # type: ignore
        }


def parse_numeric_with_unit(text: str, patterns: Tuple[str, ...]) -> Tuple[Optional[float], Optional[str]]:
    """Generic helper to extract numeric values with units.

    Args:
        text: The text in which to search for patterns.
        patterns: A tuple of regular expression patterns. Each should contain two
            capturing groups: one for the numeric value and another for the unit.

    Returns:
        A tuple `(value, unit)` if found, otherwise `(None, None)`.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace(",", ""))
            except ValueError:
                continue
            unit = match.group(2)
            return value, unit
    return None, None


def parse_nameplate_text(text: str) -> EquipmentData:
    """Parse free-form text extracted from a nameplate into structured data.

    Args:
        text: The concatenated text recognised from the nameplate.

    Returns:
        An `EquipmentData` instance with extracted values where possible.
    """
    data = EquipmentData()
    lower = text.lower()
    # Manufacturer: look for common patterns like 'manufacturer: XXX' or 'mfr: XXX'
    mfr_match = re.search(r"(?:manufacturer|mfr)\s*[:\-]\s*([\w\s&\.]+)", lower)
    if mfr_match:
        data.manufacturer = AttributeValue(value=mfr_match.group(1).strip(), unit=None, source={})

    # Model
    model_match = re.search(r"(?:model|mdl)\s*[:\-]\s*([\w\-\/]+)", lower)
    if model_match:
        data.model = AttributeValue(value=model_match.group(1).strip(), unit=None, source={})

    # Serial number
    sn_match = re.search(r"(?:serial number|s/n|sn)\s*[:\-]\s*([\w\-\/]+)", lower)
    if sn_match:
        data.serial_number = AttributeValue(value=sn_match.group(1).strip(), unit=None, source={})

    # Voltage e.g. 400V, 400 V AC
    voltage_patterns = (
        r"([0-9]+(?:\.[0-9]+)?)\s*(v|vac|volts)",
    )
    value, unit = parse_numeric_with_unit(lower, voltage_patterns)
    if value is not None:
        data.voltage = AttributeValue(value=value, unit=unit, source={})

    # Current e.g. 10A, 10 A
    current_patterns = (
        r"([0-9]+(?:\.[0-9]+)?)\s*(a|amps|ampere)",
    )
    value, unit = parse_numeric_with_unit(lower, current_patterns)
    if value is not None:
        data.current = AttributeValue(value=value, unit=unit, source={})

    # Power e.g. 5kW, 5 kVA
    power_patterns = (
        r"([0-9]+(?:\.[0-9]+)?)\s*(kw|kva|w)",
    )
    value, unit = parse_numeric_with_unit(lower, power_patterns)
    if value is not None:
        data.power = AttributeValue(value=value, unit=unit, source={})

    # Frequency e.g. 50Hz
    frequency_patterns = (
        r"([0-9]+(?:\.[0-9]+)?)\s*(hz)",
    )
    value, unit = parse_numeric_with_unit(lower, frequency_patterns)
    if value is not None:
        data.frequency = AttributeValue(value=value, unit=unit, source={})

    # IP rating e.g. IP55, IP65
    ip_match = re.search(r"ip\s*([0-9]{2})", lower)
    if ip_match:
        data.ip_rating = AttributeValue(value=f"IP{ip_match.group(1)}", unit=None, source={})

    # Certification (ATEX/CE/UL) – find typical keywords
    certs = []
    for keyword in ("atex", "ce", "ul"):
        if keyword in lower:
            certs.append(keyword.upper())
    if certs:
        data.certification = AttributeValue(value=", ".join(certs), unit=None, source={})

    return data


def parse_submittal_text(text: str) -> EquipmentData:
    """Parse text extracted from a technical submittal.

    The parsing rules mirror those for the nameplate but may be more lenient
    because submittals often use structured tables or sentences to describe
    parameters. In a real implementation, this function could leverage
    NLP/LLM techniques for improved robustness.
    """
    return parse_nameplate_text(text)
