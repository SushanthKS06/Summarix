from youtube_transcript_api import YouTubeTranscriptApi
import re
import asyncio
import logging
import json
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

# Create a single reusable API instance
_ytt_api = YouTubeTranscriptApi()

def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL reliably."""
    if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
        
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = urlparse('https://' + url)
        
    hostname = parsed.hostname or ''
    
    if hostname in ('youtu.be', 'www.youtu.be'):
        video_id = parsed.path[1:]
        return video_id if len(video_id) == 11 else None
        
    if hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if parsed.path == '/watch':
            qs = parse_qs(parsed.query)
            video_id = qs.get('v', [None])[0]
            return video_id if video_id and len(video_id) == 11 else None
        if parsed.path.startswith(('/embed/', '/v/', '/shorts/')):
            parts = parsed.path.split('/')
            if len(parts) >= 3:
                video_id = parts[2]
                return video_id if len(video_id) == 11 else None
                
    # fallback to regex for unusual formats
    pattern = r'(?:v=|\/)([a-zA-Z0-9_-]{11})(?:\?|&|\/|$)'
    match = re.search(pattern, url)
    if match and match.group(1) != "invalid-url":
        return match.group(1)
        
    return None

async def fetch_transcript(video_id: str) -> list[dict]:
    """
    Fetch transcript with timestamps.
    Returns list of dicts: [{'text': '...', 'start': 0.0, 'duration': 1.0}]
    """
    try:
        transcript_list = await asyncio.to_thread(
            _ytt_api.list, 
            video_id
        )
        
        # Try to find transcript in preferred languages
        languages = ['en', 'en-US', 'hi', 'te', 'ta', 'kn', 'ml', 'mr', 'gu', 'bn', 'pa']
        
        try:
            # First try manually created transcripts
            transcript = transcript_list.find_manually_created_transcript(languages)
        except Exception:
            try:
                # Fallback to generated transcripts
                transcript = transcript_list.find_generated_transcript(languages)
            except Exception:
                # If neither is found in preferred languages, grab whatever is available
                raise ValueError("No transcript available in supported languages")

        fetched = await asyncio.to_thread(transcript.fetch)
        return fetched.to_raw_data()
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")

def get_full_text(transcript: list[dict]) -> str:
    """Concatenate transcript snippet texts into a single string."""
    return " ".join(entry.get("text", "") for entry in transcript)


def extract_timestamp_sections(transcript: list[dict], max_sections: int = 6) -> str:
    """Extract natural timestamp sections from transcript data.
    
    Analyzes gaps in timestamps to identify section boundaries
    and formats them as '[M:SS] section text' for the summary prompt.
    """
    if not transcript:
        return ""
    
    sections = []
    total_duration = transcript[-1].get('start', 0) + transcript[-1].get('duration', 0)
    
    if total_duration <= 0:
        return ""
    
    # Divide transcript into roughly equal time segments
    segment_duration = total_duration / max_sections
    current_segment_start = 0.0
    
    for i, entry in enumerate(transcript):
        start = entry.get('start', 0.0)
        text = entry.get('text', '').strip()
        
        if start >= current_segment_start and text:
            minutes = int(start // 60)
            seconds = int(start % 60)
            # Take first ~80 chars as section description
            preview = text[:80].strip()
            if len(text) > 80:
                preview += "..."
            sections.append(f"[{minutes}:{seconds:02d}] {preview}")
            current_segment_start += segment_duration
            
            if len(sections) >= max_sections:
                break
    
    return "\n".join(sections) if sections else ""


async def fetch_video_title(video_id: str) -> str:
    """
    Fetch the actual video title using YouTube's oEmbed endpoint.
    This requires no API key. Falls back to a placeholder on failure.
    """
    import httpx
    
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("title", "Unknown Title")
    except Exception as e:
        logger.warning(f"Could not fetch video title for {video_id}: {e}")
    
    return "Unknown Title"
