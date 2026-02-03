"""
reporting.py
This module generates human-readable and machine-friendly outputs from
comparison results. It produces a pandas DataFrame for display in the UI,
exports the data to an Excel file and assembles plain-English commentary
explaining each comparison outcome.
"""
from __future__ import annotations

from typing import List
import pandas as pd

from .comparison import ComparisonResult


def results_to_dataframe(results: List[ComparisonResult]) -> pd.DataFrame:
    """Convert a list of `ComparisonResult` objects into a pandas DataFrame.

    Columns:
        - Field
        - Nameplate Value
        - Submittal Value
        - Status
        - Comment

    Returns:
        A pandas DataFrame.
    """
    data = [
        {
            "Field": r.field.title().replace("_", " "),
            "Nameplate Value": r.nameplate_value,
            "Submittal Value": r.submittal_value,
            "Status": r.status,
            "Comment": r.comment,
        }
        for r in results
    ]
    df = pd.DataFrame(data)
    return df


def write_results_to_excel(df: pd.DataFrame, path: str) -> None:
    """Write comparison results DataFrame to an Excel file.

    Args:
        df: The DataFrame to write.
        path: Destination file path.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Compliance")


def generate_plain_english_summary(results: List[ComparisonResult]) -> str:
    """Generate a plain-English explanation of the comparison results.

    The summary lists each field with its compliance status and explanation.
    """
    lines = []
    for r in results:
        lines.append(f"{r.field.title().replace('_', ' ')}: {r.status} – {r.comment}")
    return "\n".join(lines)
