thonimport logging
import re
from dataclasses import dataclass
from typing import List, Dict, Any

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from pytube import YouTube
from pytube.exceptions import PytubeError

logger = logging.getLogger(__name__)

YOUTUBE_ID_PATTERN = re.compile(
    r"""(?x)
    (?:v=|\/)([0-9A-Za-z_-]{11})    # standard watch / embed / share URLs
    """
)

@dataclass
class VideoMetadata:
    video_id: str
    video_url: str
    title: str
    length: int
    description: str
    keywords: List[str]
    author: str

def extract_video_id(url: str) -> str:
    """
    Extract the 11-character YouTube video ID from a URL.
    Raises ValueError if not found.
    """
    match = YOUTUBE_ID_PATTERN.search(url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    video_id = match.group(1)
    logger.debug("Extracted video ID %s from %s", video_id, url)
    return video_id

def fetch_video_metadata(video_id: str) -> VideoMetadata:
    """
    Fetch basic video metadata using pytube.
    """
    full_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        yt = YouTube(full_url)
    except PytubeError as exc:
        logger.warning("Failed to fetch metadata via pytube for %s: %s", video_id, exc)
        # Fallback to minimal metadata
        return VideoMetadata(
            video_id=video_id,
            video_url=full_url,
            title="",
            length=0,
            description="",
            keywords=[],
            author="",
        )

    title = yt.title or ""
    length = int(yt.length) if yt.length is not None else 0
    description = yt.description or ""
    keywords = yt.keywords or []
    author = yt.author or ""

    logger.debug("Fetched metadata for %s: %s", video_id, {"title": title, "author": author})
    return VideoMetadata(
        video_id=video_id,
        video_url=full_url,
        title=title,
        length=length,
        description=description,
        keywords=keywords,
        author=author,
    )

def fetch_captions(video_id: str, language_code: str = "en") -> List[Dict[str, Any]]:
    """
    Fetch subtitle tracks using youtube-transcript-api.
    Returns a list of dicts with keys: start, duration, text.
    """
    logger.debug("Fetching captions for %s (lang=%s)", video_id, language_code)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=[language_code, "en"],
        )
    except TranscriptsDisabled:
        logger.warning("Transcripts disabled for video %s", video_id)
        return []
    except NoTranscriptFound:
        logger.warning("No transcript found for video %s", video_id)
        return []
    except Exception as exc:
        logger.error("Error fetching transcript for %s: %s", video_id, exc)
        return []

    # transcript is a list of dicts: {'text': ..., 'start': ..., 'duration': ...}
    logger.debug("Fetched %d caption segments for %s", len(transcript), video_id)
    return transcript

def extract_video_data(video_url: str, language_code: str = "en") -> List[Dict[str, Any]]:
    """
    High-level function:
    - Extract video ID from URL
    - Fetch metadata
    - Fetch captions
    - Combine into a list of records, one per caption segment
    """
    video_id = extract_video_id(video_url)
    metadata = fetch_video_metadata(video_id)
    captions = fetch_captions(video_id, language_code=language_code)

    records: List[Dict[str, Any]] = []

    for segment in captions:
        record = {
            "videoId": metadata.video_id,
            "videoUrl": metadata.video_url,
            "videoTitle": metadata.title,
            "videoLength": str(metadata.length),
            "videoDescription": metadata.description,
            "videoKeywords": metadata.keywords,
            "author": metadata.author,
            "start": str(segment.get("start", "")),
            "duration": str(segment.get("duration", "")),
            "text": segment.get("text", ""),
        }
        records.append(record)

    logger.info(
        "Extracted %d caption records for video %s (%s)",
        len(records),
        metadata.video_id,
        metadata.title,
    )

    return records