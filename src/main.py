thonimport argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure local imports work when running as "python src/main.py"
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.youtube_parser import extract_video_data  # type: ignore
from extractors.captions_processor import normalize_captions  # type: ignore
from outputs.data_exporter import export_data  # type: ignore

def setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def load_settings() -> Dict[str, Any]:
    """
    Load settings from settings.json if present, otherwise from settings.example.json.
    Returns an empty dict if neither is found.
    """
    config_dir = CURRENT_DIR / "config"
    primary = config_dir / "settings.json"
    example = config_dir / "settings.example.json"

    path = primary if primary.exists() else example if example.exists() else None
    if not path:
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Failed to load settings from %s: %s", path, exc
        )
        return {}

def parse_args(settings: Dict[str, Any]) -> argparse.Namespace:
    default_language = settings.get("default_language", "en")
    default_output_dir = settings.get("output_dir", "data")
    default_formats = ",".join(settings.get("export_formats", ["json"]))

    parser = argparse.ArgumentParser(
        description="YouTube Video Subtitles (captions) Scraper"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to a text file containing YouTube video URLs (one per line).",
    )
    parser.add_argument(
        "--formats",
        "-f",
        default=default_formats,
        help="Comma-separated list of export formats. "
        "Supported: json,csv,excel,xml,html "
        f"(default from settings: {default_formats})",
    )
    parser.add_argument(
        "--language",
        "-l",
        default=default_language,
        help=f"Subtitle language code to extract (default: {default_language}).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=default_output_dir,
        help=f"Directory to write exported files (default: {default_output_dir}).",
    )
    parser.add_argument(
        "--base-name",
        "-b",
        default="output",
        help="Base filename (without extension) for exported files (default: output).",
    )
    parser.add_argument(
        "--skip-empty",
        action="store_true",
        help="Skip URLs that have no captions instead of including empty results.",
    )
    parser.add_argument(
        "--verbosity",
        "-v",
        action="count",
        default=0,
        help="Increase logging verbosity (-v for info, -vv for debug).",
    )

    return parser.parse_args()

def read_input_urls(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    urls: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)

    if not urls:
        raise ValueError(f"No valid URLs found in input file: {path}")

    return urls

def process_videos(
    urls: List[str],
    language: str,
    skip_empty: bool = False,
) -> List[Dict[str, Any]]:
    logger = logging.getLogger("processor")

    all_records: List[Dict[str, Any]] = []
    for idx, url in enumerate(urls, start=1):
        logger.info("Processing %s/%s: %s", idx, len(urls), url)
        try:
            records = extract_video_data(url, language_code=language)
            records = normalize_captions(records)
            if not records and skip_empty:
                logger.warning("No captions found for %s; skipping due to --skip-empty", url)
                continue
            all_records.extend(records)
        except Exception as exc:
            logger.error("Failed to process %s: %s", url, exc, exc_info=logger.isEnabledFor(logging.DEBUG))

    return all_records

def main() -> None:
    settings = load_settings()
    args = parse_args(settings)
    setup_logging(args.verbosity)

    logger = logging.getLogger("main")
    logger.debug("Starting with args: %s", args)

    try:
        urls = read_input_urls(Path(args.input))
    except Exception as exc:
        logger.error("Failed to read input URLs: %s", exc)
        sys.exit(1)

    records = process_videos(urls, args.language, skip_empty=args.skip_empty)
    if not records:
        logger.warning("No records collected from any video.")
    else:
        logger.info("Collected %s caption records.", len(records))

    try:
        export_data(
            records=records,
            output_dir=Path(args.output_dir),
            base_filename=args.base_name,
            formats=[f.strip().lower() for f in args.formats.split(",") if f.strip()],
        )
    except Exception as exc:
        logger.error("Failed to export data: %s", exc)
        sys.exit(1)

    logger.info("Done.")

if __name__ == "__main__":
    main()