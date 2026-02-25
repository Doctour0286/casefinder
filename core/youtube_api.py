"""
CaseFinder v1.0 — YouTube Data API Wrapper
All YouTube API calls go through here.
"""

import requests
import re
from datetime import datetime


def search_videos(api_key: str, query: str, max_results: int = 10,
                  order: str = "viewCount", duration: str = None,
                  published_after: str = None) -> list[dict]:
    """Search YouTube videos."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": order,
        "key": api_key,
        "relevanceLanguage": "en"
    }

    if duration:
        params["videoDuration"] = duration
        # Don't use relevanceLanguage with duration filter
        del params["relevanceLanguage"]

    if published_after:
        params["publishedAfter"] = published_after

    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

    if "error" in data:
        raise Exception(f"YouTube API error: {data['error']['message']}")

    results = []
    for item in data.get("items", []):
        results.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "channel_id": item["snippet"]["channelId"],
            "published": item["snippet"]["publishedAt"],
            "description": item["snippet"].get("description", "")
        })

    return results


def get_video_stats(api_key: str, video_ids: list[str]) -> list[dict]:
    """Get detailed stats for a list of video IDs."""
    if not video_ids:
        return []

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids[:50]),
        "key": api_key
    }

    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

    if "error" in data:
        raise Exception(f"YouTube API error: {data['error']['message']}")

    results = []
    for item in data.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})

        results.append({
            "video_id": item["id"],
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published": snippet.get("publishedAt", ""),
            "description": snippet.get("description", ""),
            "default_language": snippet.get("defaultLanguage", ""),
            "default_audio_language": snippet.get("defaultAudioLanguage", ""),
            "duration": content.get("duration", "PT0S"),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        })

    return results


def get_comments(api_key: str, video_id: str, max_results: int = 100,
                 order: str = "relevance") -> list[dict]:
    """Get comments for a video."""
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_results, 100),
        "order": order,
        "textFormat": "plainText",
        "key": api_key
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()

        if "error" in data:
            return []

        results = []
        for item in data.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]
            results.append({
                "id": item["id"],
                "text": comment.get("textDisplay", ""),
                "likes": comment.get("likeCount", 0),
                "published": comment.get("publishedAt", ""),
            })

        return results
    except Exception:
        return []


def get_channel_stats(api_key: str, channel_id: str) -> dict | None:
    """Get channel subscriber count."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": channel_id,
        "key": api_key
    }

    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()

    if "error" in data:
        return None

    items = data.get("items", [])
    if not items:
        return None

    stats = items[0].get("statistics", {})
    return {
        "channel_id": channel_id,
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
    }


def parse_duration(duration_str: str) -> float:
    """Convert ISO 8601 duration (PT1H2M3S) to minutes."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 60 + minutes + seconds / 60


def months_since(date_str: str) -> int:
    """Calculate months since a date string."""
    try:
        if "T" in date_str:
            pub_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        else:
            pub_date = datetime.fromisoformat(date_str)

        now = datetime.now(pub_date.tzinfo) if pub_date.tzinfo else datetime.now()
        diff = now - pub_date
        return max(0, int(diff.days / 30))
    except Exception:
        return 0
