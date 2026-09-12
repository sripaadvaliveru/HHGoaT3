import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from web_search import search_google_lens, _extract_name_from_results, search_official_account

load_dotenv('F:/HHGoaT3/face-verify/.env')
api_key = os.getenv('SERPAPI_KEY')

print("=== Step 1: Google Lens search ===")
results = search_google_lens('test_faces/Samay.jpg', api_key, num_results=10)
for r in results:
    print(f"  [{r['source']}] {r['title']}")
    print(f"    URL: {r['link']}")

name = _extract_name_from_results(results)
print(f"\nExtracted name: '{name}'")

if name:
    print(f"\n=== Step 2: Searching official accounts for '{name}' ===")
    for platform in ["instagram", "twitter", "facebook"]:
        official = search_official_account(name, api_key, platform)
        if official:
            print(f"\n  [{platform.upper()}]")
            print(f"    Found: {official['link']}")
            print(f"    Title: {official['title']}")
            print(f"    Official: {official.get('is_official')}")
            print(f"    Snippet: {official.get('snippet', '')[:200]}")
            if official.get('is_official'):
                print(f"    >>> THIS IS OFFICIAL - will use this <<<")
                break
        else:
            print(f"  [{platform.upper()}] No result")
else:
    print("Could not extract name from results")
