thonimport csv
import json
import logging
from pathlib import Path
from typing import Iterable, List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"json", "csv", "excel", "xml", "html"}

def _ensure_output_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise IOError(f"Failed to create output directory {path}: {exc}") from exc

def _export_json(records: List[Dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    logger.info("Wrote JSON to %s", path)

def _export_csv(records: List[Dict[str, Any]], path: Path) -> None:
    if not records:
        # Write an empty file with no header
        path.touch()
        logger.warning("No records to write; created empty CSV at %s", path)
        return

    # Get union of all keys to ensure consistent columns
    fieldnames = sorted({key for record in records for key in record.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    logger.info("Wrote CSV to %s", path)

def _export_excel(records: List[Dict[str, Any]], path: Path) -> None:
    df = pd.DataFrame(records)
    df.to_excel(path, index=False)
    logger.info("Wrote Excel to %s", path)

def _export_xml(records: List[Dict[str, Any]], path: Path) -> None:
    from xml.etree.ElementTree import Element, SubElement, ElementTree

    root = Element("videos")
    for record in records:
        rec_el = SubElement(root, "record")
        for key, value in record.items():
            child = SubElement(rec_el, key)
            if isinstance(value, (list, tuple)):
                child.text = json.dumps(value, ensure_ascii=False)
            else:
                child.text = "" if value is None else str(value)

    tree = ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    logger.info("Wrote XML to %s", path)

def _export_html(records: List[Dict[str, Any]], path: Path) -> None:
    if not records:
        html = "<html><body><p>No records.</p></body></html>"
        path.write_text(html, encoding="utf-8")
        logger.info("Wrote empty HTML to %s", path)
        return

    fieldnames = sorted({key for record in records for key in record.keys()})

    rows = []
    header_cells = "".join(f"<th>{key}</th>" for key in fieldnames)
    rows.append(f"<tr>{header_cells}</tr>")

    for record in records:
        cells: List[str] = []
        for key in fieldnames:
            value = record.get(key, "")
            if isinstance(value, (list, tuple)):
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = "" if value is None else str(value)
            cells.append(f"<td>{value_str}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = "<table border='1' cellspacing='0' cellpadding='4'>\n" + "\n".join(rows) + "\n</table>"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>YouTube Subtitles Export</title>
</head>
<body>
  <h1>YouTube Subtitles Export</h1>
  {table_html}
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    logger.info("Wrote HTML to %s", path)

def export_data(
    records: Iterable[Dict[str, Any]],
    output_dir: Path,
    base_filename: str = "output",
    formats: List[str] | None = None,
) -> None:
    """
    Export records to the given formats.
    """
    _ensure_output_dir(output_dir)
    records_list = list(records)

    if not formats:
        formats = ["json"]

    normalized_formats = []
    for fmt in formats:
        fmt_lower = fmt.lower()
        if fmt_lower not in SUPPORTED_FORMATS:
            logger.warning("Ignoring unsupported format: %s", fmt)
            continue
        if fmt_lower not in normalized_formats:
            normalized_formats.append(fmt_lower)

    if not normalized_formats:
        raise ValueError("No valid export formats specified.")

    for fmt in normalized_formats:
        if fmt == "json":
            path = output_dir / f"{base_filename}.json"
            _export_json(records_list, path)
        elif fmt == "csv":
            path = output_dir / f"{base_filename}.csv"
            _export_csv(records_list, path)
        elif fmt == "excel":
            path = output_dir / f"{base_filename}.xlsx"
            _export_excel(records_list, path)
        elif fmt == "xml":
            path = output_dir / f"{base_filename}.xml"
            _export_xml(records_list, path)
        elif fmt == "html":
            path = output_dir / f"{base_filename}.html"
            _export_html(records_list, path)
        else:
            # This shouldn't happen due to SUPPORTED_FORMATS filtering
            logger.error("Unhandled export format: %s", fmt)