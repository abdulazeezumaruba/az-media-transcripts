from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
import re

app = FastAPI(
    title="AZ Media Transcript API",
    version="1.0.0",
    description="Backend service that returns transcripts for YouTube videos."
)


class TranscriptRequest(BaseModel):
    video_urls: List[str]


class VideoTranscript(BaseModel):
    video_url: str
    transcript: str
    success: bool
    error: Optional[str] = None


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from common URL formats.
    Supports:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
    """
    # Short link: youtu.be/VIDEO_ID
    short_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if short_match:
        return short_match.group(1)

    # Watch link: youtube.com/watch?v=VIDEO_ID
    long_match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    if long_match:
        return long_match.group(1)

    return None


@app.get("/")
async def root():
    return {"status": "AZ Media Transcript API is running"}


@app.post("/transcripts", response_model=List[VideoTranscript])
async def get_transcripts(req: TranscriptRequest) -> List[VideoTranscript]:
    """
    Accepts a list of video_urls and returns transcripts when available.
    Each result includes:
      - video_url
      - transcript (joined text)
      - success (bool)
      - error (string or null)
    """
    results: List[VideoTranscript] = []

    for url in req.video_urls:
        video_id = extract_video_id(url)
        if not video_id:
            results.append(
                VideoTranscript(
                    video_url=url,
                    transcript="",
                    success=False,
                    error="Could not extract video ID from URL.",
                )
            )
            continue

        try:
            # Try to get English transcripts by default.
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en"]
            )
            full_text = " ".join(chunk["text"] for chunk in transcript_data)

            results.append(
                VideoTranscript(
                    video_url=url,
                    transcript=full_text,
                    success=True,
                    error=None,
                )
            )
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            results.append(
                VideoTranscript(
                    video_url=url,
                    transcript="",
                    success=False,
                    error=str(e),
                )
            )
        except Exception as e:
            results.append(
                VideoTranscript(
                    video_url=url,
                    transcript="",
                    success=False,
                    error=f"Unexpected error: {e}",
                )
            )

    return results
