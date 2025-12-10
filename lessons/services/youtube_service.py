"""
YouTube service for fetching lesson-related videos.
"""
import os
import logging
from typing import List, Dict
import httpx

logger = logging.getLogger(__name__)

# Get YouTube API key from environment
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"


def fetch_youtube_videos(topic: str, subject: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Fetch educational videos from YouTube based on topic and subject.
    
    Args:
        topic: The lesson topic (e.g., "photosynthesis")
        subject: The subject area (e.g., "biology")
        limit: Maximum number of videos to return (default: 5, max 50)
    
    Returns:
        List of dictionaries with 'title' and 'url' keys. Returns empty list if API fails or key is missing.
        Example: [{"title": "Video Title", "url": "https://www.youtube.com/watch?v=VIDEO_ID"}, ...]
    """
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY not found in environment variables. Video fetching will not work.")
        return []
    
    if not topic or not topic.strip():
        logger.warning("Empty topic provided to fetch_youtube_videos")
        return []
    
    # Build search query: combine topic, subject, and "lesson" keyword for educational content
    query_parts = [topic.strip()]
    if subject and subject.strip():
        query_parts.append(subject.strip())
    query_parts.append("lesson")
    search_query = " ".join(query_parts)
    
    try:
        # Make API request to YouTube Data API v3
        params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "maxResults": min(limit, 50),  # YouTube allows up to 50 per request
            "key": YOUTUBE_API_KEY,
            "videoEmbeddable": "true",  # Only return embeddable videos
            "order": "relevance"  # Order by relevance
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                YOUTUBE_API_URL,
                params=params
            )
            response.raise_for_status()  # Raises exception for bad status codes
            
            data = response.json()
            
            # Extract video data from response
            videos = []
            items = data.get("items", [])
            
            for item in items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                
                if video_id and snippet.get("title"):
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    videos.append({
                        "title": snippet.get("title", "Untitled Video"),
                        "url": video_url
                    })
            
            logger.info(f"Successfully fetched {len(videos)} videos for topic: {topic}, subject: {subject}")
            return videos
            
    except httpx.HTTPStatusError as e:
        logger.error(f"YouTube API HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"YouTube API request error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching YouTube videos: {str(e)}")
        return []

