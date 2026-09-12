"""
Face Identification & Blockchain Verification Pipeline
======================================================
Usage:
    python main.py --image <face_image_path>
    python main.py --image <face_image_path> --search-type visual_matches
    python main.py --deploy   # Deploy the contract to Sepolia
    python main.py --verify <post_hash_hex>  # Verify a hash on-chain
"""

import argparse
import json
import hashlib
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from face_detector import load_and_encode_face, encoding_to_hex
from web_search import (
    search_google_lens,
    find_social_media_post,
    find_best_social_media_post,
    compute_post_fingerprint,
)
from blockchain import (
    store_post_hash,
    verify_post_hash,
    deploy_contract,
    get_stored_count,
)


def banner():
    print(r"""
  _____ ____   __________     _______  __   __
 / ____|  _ \ |__  / __ \ \   / /  _ \ \ \ / /
| (___ | | | | / /|  __ (_) \ / /| |_) | \ V /
 \___ \| | | |/ /_| |__) \ V / |  _ <   | |
 ____) | |_/ / __ \  __/  | |  | |_) |  | |
|_____/|____/ |_| |_|     |_|  |____/   |_|
    Face ID -> Web Search -> Blockchain Verify
    """)


def run_pipeline(image_path: str, search_type: str = "visual_matches"):
    """
    Execute the full pipeline:
    1. Detect and encode face from input image
    2. Search Google Lens for matching social media posts
    3. Upload post fingerprint to Sepolia testnet
    4. Re-verify the hash on-chain
    """
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_image": image_path,
        "steps": {},
    }

    # ── Step 1: Face Detection ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1: Face Detection & Encoding")
    print("=" * 60)

    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    encoding = load_and_encode_face(image_path)
    if encoding is None:
        print("[FATAL] No face detected. Provide a clear, front-facing photo.")
        sys.exit(1)

    enc_hex = encoding_to_hex(encoding)
    enc_hash = hashlib.sha256(encoding.tobytes()).hexdigest()

    print(f"[FaceDetector] Face encoding: 128-d vector")
    print(f"[FaceDetector] Encoding hash (SHA-256): {enc_hash[:32]}...")

    results["steps"]["face_detection"] = {
        "status": "success",
        "encoding_hex": enc_hex[:64] + "...",
        "encoding_hash": enc_hash,
    }

    # ── Step 2: Web Search (Google Lens) ────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Reverse Image Search (Google Lens)")
    print("=" * 60)

    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("[ERROR] SERPAPI_KEY not set in .env")
        sys.exit(1)

    try:
        search_results = search_google_lens(
            image_path=image_path,
            api_key=api_key,
            search_type=search_type,
            num_results=5,
        )
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        sys.exit(1)

    if not search_results:
        print("[WARN] No results found from Google Lens")
        results["steps"]["web_search"] = {"status": "no_results", "matches": []}
    else:
        print(f"[WebSearch] Found {len(search_results)} visual matches:")
        for i, r in enumerate(search_results, 1):
            title_safe = r['title'][:50].encode('ascii', 'replace').decode('ascii')
            link_safe = r['link'].encode('ascii', 'replace').decode('ascii')
            print(f"  {i}. [{r['source']}] {title_safe}")
            print(f"     URL: {link_safe}")

        # Try to find a social media post (prefer official accounts)
        social_post = find_best_social_media_post(search_results, api_key)
        if social_post:
            print(f"\n[WebSearch] Social media match found: {social_post['source']}")
            print(f"  URL: {social_post['link']}")
            discovered_post = social_post
        else:
            print("\n[WebSearch] No social media URL in results. Using first match.")
            discovered_post = search_results[0]

        post_fingerprint = compute_post_fingerprint(discovered_post)

        results["steps"]["web_search"] = {
            "status": "success",
            "total_matches": len(search_results),
            "social_media_found": social_post is not None,
            "discovered_post": discovered_post,
            "post_fingerprint": post_fingerprint,
        }

    # ── Step 3: Blockchain Upload ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Blockchain Verification (Sepolia Testnet)")
    print("=" * 60)

    if "discovered_post" not in results["steps"].get("web_search", {}):
        print("[SKIP] No post to verify — search returned no results.")
        results["steps"]["blockchain"] = {"status": "skipped", "reason": "no_post"}
    else:
        post = results["steps"]["web_search"]["discovered_post"]
        fingerprint = results["steps"]["web_search"]["post_fingerprint"]

        print(f"[Blockchain] Posting fingerprint: {fingerprint[:32]}...")
        print(f"[Blockchain] Post URL: {post['link']}")
        print(f"[Blockchain] Source: {post['source']}")

        try:
            tx_hash = store_post_hash(
                post_hash=fingerprint,
                post_url=post["link"],
                title=post.get("title", "")[:200],
                source=post.get("source", "unknown"),
            )
            print(f"[Blockchain] Transaction sent: {tx_hash}")

            results["steps"]["blockchain"] = {
                "status": "success",
                "tx_hash": tx_hash,
                "post_fingerprint": fingerprint,
            }
        except Exception as e:
            print(f"[ERROR] Blockchain upload failed: {e}")
            results["steps"]["blockchain"] = {"status": "error", "error": str(e)}

    # ── Step 4: Re-verify on-chain ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 4: On-Chain Verification")
    print("=" * 60)

    if results["steps"].get("blockchain", {}).get("status") == "success":
        fingerprint = results["steps"]["blockchain"]["post_fingerprint"]
        print(f"[Verify] Checking hash: {fingerprint[:32]}...")

        try:
            verification = verify_post_hash(fingerprint)
            if verification["verified"]:
                print("[Verify] CONFIRMED — Hash exists on-chain")
                print(f"  Post URL:   {verification['postUrl']}")
                print(f"  Source:     {verification['source']}")
                print(f"  Timestamp:  {verification['timestamp']}")
                print(f"  Uploader:   {verification['uploader']}")
                results["steps"]["on_chain_verification"] = {
                    "status": "verified",
                    "record": verification,
                }
            else:
                print("[Verify] NOT FOUND — Hash not on chain")
                results["steps"]["on_chain_verification"] = {"status": "not_found"}
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            results["steps"]["on_chain_verification"] = {"status": "error", "error": str(e)}
    else:
        print("[SKIP] Blockchain step did not succeed — cannot verify.")
        results["steps"]["on_chain_verification"] = {"status": "skipped"}

    # ── Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))

    # Save results
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"result_{ts}.json"
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n[Output] Results saved to {out_path}")


def main():
    banner()

    parser = argparse.ArgumentParser(description="Face ID → Web Search → Blockchain Verify")
    parser.add_argument("--image", "-i", help="Path to face image for identification")
    parser.add_argument(
        "--search-type", "-s",
        default="visual_matches",
        choices=["visual_matches", "exact_matches", "all"],
        help="Google Lens search type (default: visual_matches)",
    )
    parser.add_argument("--deploy", action="store_true", help="Deploy FaceVerify contract to Sepolia")
    parser.add_argument("--verify", metavar="HASH", help="Verify a post hash on-chain")
    parser.add_argument("--count", action="store_true", help="Show number of stored hashes")

    args = parser.parse_args()

    if args.deploy:
        print("Deploying FaceVerify contract to Sepolia testnet...")
        addr = deploy_contract()
        print(f"\nUpdate .env with: CONTRACT_ADDRESS={addr}")
        return

    if args.verify:
        result = verify_post_hash(args.verify)
        print(json.dumps(result, indent=2, default=str))
        return

    if args.count:
        n = get_stored_count()
        print(f"Hashes stored on-chain: {n}")
        return

    if not args.image:
        parser.print_help()
        sys.exit(1)

    run_pipeline(args.image, search_type=args.search_type)


if __name__ == "__main__":
    main()
