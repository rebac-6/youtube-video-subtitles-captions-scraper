thonimport logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

WHITESPACE_RE = re.compile(r"\s+")

def _clean_text(text: str) -> str:
    # Normalize whitespace and strip leading/trailing spaces
    cleaned = WHITESPACE_RE.sub(" ", text).strip()
    return cleaned

def normalize_captions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Post-process caption records:
    - Normalize whitespace in text
    - Drop empty text segments
    """
    normalized: List[Dict[str, Any]] = []
    for record in records:
        text = record.get("text", "")
        cleaned = _clean_text(text)
        if not cleaned:
            logger.debug("Dropping empty caption segment at start=%s", record.get("start"))
            continue

        new_record = dict(record)
        new_record["text"] = cleaned
        normalized.append(new_record)

    logger.info(
        "Normalized captions: %d -> %d records", len(records), len(normalized)
    )
    return normalized