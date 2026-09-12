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


def _extract_name_from_results(results: list[dict]) -> str:
    """
    Try to extract a person's name from Google Lens results.
    Scans all results for name patterns, prioritizing social media profiles.
    """
    import re
    from collections import Counter

    # Collect all potential name fragments
    name_candidates = []

    # Words to strip from titles (video/content noise)
    strip_words = {
        "shorts", "reel", "reels", "video", "photo", "picture", "image",
        "fan", "page", "official", "account", "profile", "channel",
        "fc", "sticker", "status", "story", "post", "tweet",
        "solar", "powered", "led", "string", "lights", "garden",
        "delivery", "cannabis", "contact", "jobs", "careers",
        "advice", "golden", "day", "chocolate", "trending",
        "wholesome", "motivation", "inspiration", "money",
        "marvel", "edit", "edits", "thor", "odison",
        "india", "today", "court", "directed", "comedian",
    }

    for result in results:
        title = result.get("title", "")

        # Clean separators
        for sep in [" | ", " - ", " \u2013 ", " \u2014 ", " || ", " \u2022 "]:
            if sep in title:
                title = title.split(sep)[0].strip()

        # Remove common suffixes
        for suffix in [" FC", " Official", " Fan Club", " ID", " page",
                        " - YouTube", " - Instagram", " - Facebook",
                        " \ud83c\udf08"]:
            if title.endswith(suffix):
                title = title[:-len(suffix)].strip()

        # Remove hashtags and @ mentions noise
        title = re.sub(r'#\w+', '', title).strip()
        title = re.sub(r'@\w+', '', title).strip()

        # Remove emoji
        title = re.sub(r'[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff]+', '', title).strip()

        words = title.split()
        if not (2 <= len(words) <= 4):
            continue

        # Skip if mostly noise words
        meaningful = [w for w in words if w.lower() not in strip_words and len(w) > 1]
        if len(meaningful) < 2:
            continue

        # Skip if mostly not alphabetic
        clean = " ".join(meaningful)
        alpha_ratio = sum(c.isalpha() or c == ' ' for c in clean) / max(len(clean), 1)
        if alpha_ratio < 0.8:
            continue

        name_candidates.append(clean)

    if not name_candidates:
        return ""

    # Pick the most common candidate (appears in multiple results = likely the person's name)
    counter = Counter(name_candidates)
    best = counter.most_common(1)[0][0]
    return best


def search_official_account(
    person_name: str,
    api_key: str,
    platform: str = "instagram",
) -> Optional[dict]:
    """
    Search for the official/verified account of a person on a social media platform.

    Args:
        person_name: Name of the person to search for.
        api_key: SerpApi API key.
        platform: Social media platform to search (instagram, twitter, facebook).

    Returns:
        Dict with official account info, or None if not found.
    """
    if serpapi is None:
        raise ImportError("serpapi package not installed. Run: pip install serpapi")

    client = serpapi.Client(api_key=api_key)

    # Search for official account - try multiple queries
    queries = [
        f"{person_name} {platform} official verified",
        f"{person_name} official {platform}",
        f"{person_name} {platform}",
    ]

    for query in queries:
        print(f"[WebSearch] Searching: {query}")

        params = {
            "engine": "google",
            "q": query,
            "num": 5,
        }

        results = client.search(params)
        organic = results.get("organic_results", [])

        for result in organic:
            link = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            # Check if this is a direct link to the platform
            if platform in link.lower():
                # Look for verification indicators
                combined_text = (title + " " + snippet).lower()
                is_official = any(indicator in combined_text for indicator in [
                    "official", "verified", "blue check", "authentic",
                    "real account", "verified account", "follow",
                ])

                # Also check if title is just the person name (strong indicator)
                name_words = person_name.lower().split()
                title_lower = title.lower()
                if all(w in title_lower for w in name_words):
                    is_official = True

                return {
                    "title": title,
                    "link": link,
                    "source": platform.title(),
                    "thumbnail": "",
                    "image": "",
                    "is_official": is_official,
                    "snippet": snippet,
                }

    return None


def find_best_social_media_post(
    results: list[dict],
    api_key: str,
) -> Optional[dict]:
    """
    Find the best social media post from Google Lens results.
    First checks for official accounts, then falls back to any social media match.

    Args:
        results: List of search results from search_google_lens().
        api_key: SerpApi API key.

    Returns:
        Best social media result dict, or None if none found.
    """
    # First, try to find any social media post from lens results
    social_post = find_social_media_post(results)

    if not social_post:
        return None

    # Extract person name from results
    person_name = _extract_name_from_results(results)

    if person_name:
        print(f"[WebSearch] Detected person name: {person_name}")

        # Search for official account across platforms
        for platform in ["instagram", "twitter", "facebook"]:
            official = search_official_account(person_name, api_key, platform)
            if official:
                print(f"[WebSearch] Found official {platform}: {official['link']}")
                if official.get("is_official"):
                    return official

    # Fallback: return the first social media match from lens results
    return social_post


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
