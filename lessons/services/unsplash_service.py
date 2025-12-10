"""
Unsplash service for fetching lesson-related images.
"""
import os
import logging
from typing import List
import httpx

logger = logging.getLogger(__name__)

# Get Unsplash access key from environment
# Note: Unsplash uses the Access Key (also called Application ID) as Client-ID in Authorization header
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY') or os.getenv('UNSPLASH_APPLICATION_ID')
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"


def fetch_unsplash_images(topic: str, limit: int = 6) -> List[str]:
    """
    Fetch images from Unsplash based on a topic.
    
    Args:
        topic: The search query/topic (e.g., "photosynthesis")
        limit: Maximum number of images to return (default: 6, will return 3-6)
    
    Returns:
        List of image URLs (regular size). Returns empty list if API fails or key is missing.
    
    Note:
        Uses UNSPLASH_ACCESS_KEY or UNSPLASH_APPLICATION_ID from environment.
        Both refer to the same credential (Access Key/Application ID) used as Client-ID.
    """
    if not UNSPLASH_ACCESS_KEY:
        logger.warning("UNSPLASH_ACCESS_KEY or UNSPLASH_APPLICATION_ID not found in environment variables. Image fetching will not work.")
        return []
    
    if not topic or not topic.strip():
        logger.warning("Empty topic provided to fetch_unsplash_images")
        return []
    
    try:
        # Make API request to Unsplash
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
        }
        params = {
            "query": topic.strip(),
            "per_page": min(limit, 30),  # Unsplash allows up to 30 per page
            "orientation": "landscape"  # Better for educational content
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                UNSPLASH_API_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()  # Raises exception for bad status codes
            
            data = response.json()
            
            # Extract image URLs from response
            images = []
            results = data.get("results", [])
            
            for photo in results[:limit]:
                # Try to get regular size first, fallback to small
                urls = photo.get("urls", {})
                image_url = urls.get("regular") or urls.get("small") or urls.get("thumb")
                
                if image_url:
                    images.append(image_url)
            
            logger.info(f"Successfully fetched {len(images)} images for topic: {topic}")
            return images
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Unsplash API HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"Unsplash API request error: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching Unsplash images: {str(e)}")
        return []

