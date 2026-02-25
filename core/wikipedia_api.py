"""
CaseFinder v1.0 — Wikipedia API Wrapper
For getting case information and checking image availability.
"""

import requests


def search_wikipedia(query: str) -> dict | None:
    """Search Wikipedia for a case."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "opensearch",
        "search": query,
        "limit": 5,
        "namespace": 0,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if len(data) > 1 and data[1]:
            return {
                "title": data[1][0],
                "url": data[3][0] if len(data) > 3 else None
            }
    except Exception:
        pass

    return None


def get_page_extract(api_key: str, title: str) -> str | None:
    """Get a Wikipedia page extract (summary)."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id != "-1":
                return page_data.get("extract", "")
    except Exception:
        pass

    return None


def get_page_images(title: str) -> list[str]:
    """Get all images from a Wikipedia page."""
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "images",
        "format": "json"
    }

    images = []
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id != "-1":
                for img in page_data.get("images", []):
                    images.append(img["title"])
    except Exception:
        pass

    return images


def get_thumbnail_image(title: str) -> str | None:
    """Get a thumbnail image from Wikipedia page."""
    # Try pageimages API first (free license images)
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "pithumbsize": 300,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id != "-1" and "thumbnail" in page_data:
                return page_data["thumbnail"]["source"]
    except Exception:
        pass

    # Fallback: get first real image from images list
    images = get_page_images(title)
    skip_words = ["icon", "logo", "flag", "map", "edit", "lock", "question",
                  "wiki", "commons", "stub", "symbol", "pictogram", "padlock"]

    for img in images:
        img_lower = img.lower()
        if not any(skip in img_lower for skip in skip_words):
            # Return the image info (we'd need another API call to get URL)
            return img

    return None
