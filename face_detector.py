"""Face detection and encoding using deepface library."""

import numpy as np
from pathlib import Path
from typing import Optional

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None


def load_and_encode_face(image_path: str, model_name: str = "VGG-Face") -> Optional[np.ndarray]:
    """
    Load an image and return the face embedding vector.

    Args:
        image_path: Path to the image file.
        model_name: Face recognition model (VGG-Face, Facenet, OpenFace, etc.).

    Returns:
        Embedding vector (numpy array) or None if no face found.
    """
    if DeepFace is None:
        raise ImportError("deepface not installed. Run: pip install deepface tf-keras")

    try:
        results = DeepFace.represent(
            img_path=image_path,
            model_name=model_name,
            enforce_detection=True,
        )
    except ValueError as e:
        # enforce_detection=True raises ValueError if no face found
        print(f"[FaceDetector] No face found in {image_path}: {e}")
        return None
    except Exception as e:
        print(f"[FaceDetector] Error processing {image_path}: {e}")
        return None

    if not results:
        print(f"[FaceDetector] No face encoding returned for {image_path}")
        return None

    # results is a list of dicts with 'embedding' key
    embedding = np.array(results[0]["embedding"])
    print(f"[FaceDetector] Face encoding: {embedding.shape[0]}-d vector")
    return embedding


def compare_faces(known_encoding: np.ndarray, unknown_encoding: np.ndarray, threshold: float = 0.4) -> bool:
    """
    Compare two face embeddings using cosine similarity.

    Args:
        known_encoding: Reference embedding to compare against.
        unknown_encoding: Embedding to check.
        threshold: Similarity threshold (higher = stricter). Default 0.4.

    Returns:
        True if faces match (cosine similarity >= threshold).
    """
    # Normalize vectors
    known_norm = known_encoding / np.linalg.norm(known_encoding)
    unknown_norm = unknown_encoding / np.linalg.norm(unknown_encoding)

    # Cosine similarity
    similarity = np.dot(known_norm, unknown_norm)
    return similarity >= threshold


def encoding_to_hex(encoding: np.ndarray) -> str:
    """Convert a face encoding to a hex string for storage."""
    return encoding.astype(np.float32).tobytes().hex()


def encoding_from_hex(hex_str: str) -> np.ndarray:
    """Restore a face encoding from its hex string."""
    return np.frombuffer(bytes.fromhex(hex_str), dtype=np.float32)
