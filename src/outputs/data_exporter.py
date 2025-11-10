import json
import logging
import os
from typing import Any, Dict, Iterable, List

import pandas as pd

logger = logging.getLogger(__name__)

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def export_to_json(path: str, comments: List[Dict[str, Any]]) -> None:
    logger.debug("Exporting %d comment(s) to JSON: %s", len(comments), path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)

def export_to_csv(path: str, comments: List[Dict[str, Any]]) -> None:
    logger.debug("Exporting %d comment(s) to CSV: %s", len(comments), path)
    df = _flatten_comments(comments)
    df.to_csv(path, index=False)

def export_to_xlsx(path: str, comments: List[Dict[str, Any]]) -> None:
    logger.debug("Exporting %d comment(s) to XLSX: %s", len(comments), path)
    df = _flatten_comments(comments)
    df.to_excel(path, index=False)

def _flatten_comments(comments: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """
    Flatten nested author fields into top-level columns for CSV/XLSX convenience.
    """
    flattened: List[Dict[str, Any]] = []
    for c in comments:
        author = c.get("author") or {}
        flat = dict(c)  # shallow copy
        flat["author.channelId"] = author.get("channelId")
        flat["author.displayName"] = author.get("displayName")
        flat["author.avatarThumbnailUrl"] = author.get("avatarThumbnailUrl")
        flat["author.isVerified"] = author.get("isVerified")
        # Remove nested author to avoid duplication in tabular formats
        flat.pop("author", None)
        flattened.append(flat)

    return pd.DataFrame(flattened)

def export_all(
    output_dir: str,
    base_filename: str,
    comments: List[Dict[str, Any]],
    formats: List[str],
) -> None:
    """
    Export comments to all requested formats.
    Supported formats: json, csv, xlsx
    """
    _ensure_dir(output_dir)
    formats_normalized = {fmt.lower() for fmt in formats}

    if "json" in formats_normalized:
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        export_to_json(json_path, comments)

    if "csv" in formats_normalized:
        csv_path = os.path.join(output_dir, f"{base_filename}.csv")
        export_to_csv(csv_path, comments)

    if "xlsx" in formats_normalized or "xls" in formats_normalized:
        xlsx_path = os.path.join(output_dir, f"{base_filename}.xlsx")
        export_to_xlsx(xlsx_path, comments)

    logger.info(
        "Exported comments to formats: %s (base filename: %s)",
        ", ".join(sorted(formats_normalized)),
        base_filename,
    )