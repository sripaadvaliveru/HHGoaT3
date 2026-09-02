"""Web search using SerpApi Google Lens for reverse face image search."""

import os
import hashlib
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    import serpapi
except ImportError:
    serpapi = None


SOCIAL_MEDIA_DOMAINS = [
    "instagram.com", "twitter.com", "x.com", "facebook.com",
    "linkedin.com", "tiktok.com", "reddit.com", "pinterest.com",
    "snapchat.com", "youtube.com", "threads.net", "mastodon.social",
]


def _is_social_media_url(url: str) -> bool:
    """Check if a URL belongs to a known social media platform."""
    if not url:
        return False
    domain = urlparse(url).netloc.lower()
    return any(sm in domain for sm in SOCIAL_MEDIA_DOMAINS)


def search_google_lens(
    image_path: str,
    api_key: str,
    search_type: str = "visual_matches",
    num_results: int = 5,
) -> list[dict]:
    """
    Search Google Lens for visually similar images using a local face image.

    Args:
        image_path: Path to the local face image.
        api_key: SerpApi API key.
        search_type: "visual_matches", "exact_matches", or "all".
        num_results: Max results to return.

    Returns:
        List of result dicts with keys: title, link, source, thumbnail, image.
    """
    if serpapi is None:
        raise ImportError("serpapi package not installed. Run: pip install serpapi")

    client = serpapi.Client(api_key=api_key)

    # Upload the local image to get a temporary image_id
    print(f"[WebSearch] Uploading {image_path} to SerpApi...")
    upload = client.upload_image(image_path)
    image_id = upload["image_id"]
    print(f"[WebSearch] Image uploaded. image_id={image_id}")

    # Search Google Lens
    params = {
        "engine": "google_lens",
        "image_id": image_id,
        "type": search_type,
    }

    print(f"[WebSearch] Searching Google Lens (type={search_type})...")
    results = client.search(params)

    # Extract visual matches
    matches = results.get("visual_matches", [])
    print(f"[WebSearch] Found {len(matches)} visual matches")

    # Format results
    formatted = []
    for match in matches[:num_results]:
        formatted.append({
            "title": match.get("title", ""),
            "link": match.get("link", ""),
            "source": match.get("source", ""),
            "thumbnail": match.get("thumbnail", ""),
            "image": match.get("image", ""),
        })

    return formatted


def find_social_media_post(results: list[dict]) -> Optional[dict]:
    """
    From Google Lens results, find the first result that links to a social media post.

    Args:
        results: List of search results from search_google_lens().

    Returns:
        First social media result dict, or None if none found.
    """
    for result in results:
        if _is_social_media_url(result.get("link", "")):
            return result
    return None


def compute_post_fingerprint(post: dict) -> str:
    """
    Compute a SHA-256 fingerprint of a discovered post for blockchain storage.

    Combines URL, title, source, and image URL into a single hash.
    """
    data = f"{post.get('link', '')}|{post.get('title', '')}|{post.get('source', '')}|{post.get('image', '')}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def download_image(url: str, save_path: str) -> Optional[str]:
    """Download an image from a URL and save it locally. Returns the local path."""
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return save_path
    except Exception as e:
        print(f"[WebSearch] Failed to download {url}: {e}")
        return None
