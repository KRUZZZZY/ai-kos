"""AI-KOS blob storage — manage binary files as article backends.

Store images, PDFs, audio, video in datasets/blobs/ with optional
OCR (pytesseract) and PDF text extraction (pymupdf) for search indexing.
"""

import shutil
import os
import mimetypes
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("ai-kos.blobs")


def _validate_slug(slug: str) -> str:
    """Validate a blob slug, refusing anything that could escape the store.

    Rejects empty slugs and slugs containing path separators or `..`
    (e.g. `../../escape`) before any path join happens.
    """
    if not slug or not slug.strip():
        raise ValueError("slug must not be empty")
    if "/" in slug or "\\" in slug or ".." in slug:
        raise ValueError(
            f"invalid slug {slug!r}: path separators and '..' are not allowed"
        )
    return slug.strip()


def store_blob(source_path: str, dest_dir: str = "datasets/blobs",
               slug: Optional[str] = None) -> dict:
    """Copy a binary file to the blob store. Returns BlobRef-compatible dict."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {source_path}")
    if slug is not None:
        slug = _validate_slug(slug)

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    stem = slug or src.stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ext = src.suffix or ".bin"
    dest_name = f"{stem}-{ts}{ext}"
    dest_path = dest / dest_name

    shutil.copy2(src, dest_path)

    mime_type, _ = mimetypes.guess_type(str(src))
    size = dest_path.stat().st_size

    logger.info(f"Stored blob: {dest_path} ({size} bytes, {mime_type})")

    return {
        "path": str(dest_path),
        "mime_type": mime_type or "application/octet-stream",
        "size_bytes": size,
        "extracted_text": "",
    }


def delete_blob(blob_path: str) -> bool:
    """Delete a blob file. Returns True if deleted."""
    p = Path(blob_path)
    if p.exists():
        p.unlink()
        logger.info(f"Deleted blob: {blob_path}")
        return True
    return False


def list_blobs(blob_dir: str = "datasets/blobs") -> list:
    """List all blobs with size and MIME type."""
    d = Path(blob_dir)
    if not d.exists():
        return []
    results = []
    for f in sorted(d.iterdir()):
        if f.is_file():
            mime, _ = mimetypes.guess_type(str(f))
            results.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "mime_type": mime or "unknown",
            })
    return results


def extract_text(blob_path: str, mime_type: str = "") -> str:
    """Try to extract text from a binary file for search indexing.

    - Images: pytesseract OCR (requires pytesseract + Pillow)
    - PDFs: pymupdf/fitz (already used in AI-KOS ingestion)
    Returns empty string on failure or if deps missing.
    """
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(blob_path)

    if mime_type and mime_type.startswith("image/"):
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(blob_path)
            text = pytesseract.image_to_string(img)
            logger.info(f"OCR extracted {len(text)} chars from {blob_path}")
            return text.strip()
        except ImportError:
            logger.debug("pytesseract not installed — skipping OCR")
        except Exception as e:
            logger.warning(f"OCR failed for {blob_path}: {e}")

    if mime_type == "application/pdf":
        try:
            import fitz
            doc = fitz.open(blob_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            logger.info(f"PDF extracted {len(text)} chars from {blob_path}")
            return text.strip()[:5000]
        except ImportError:
            logger.debug("pymupdf not installed — skipping PDF text extraction")
        except Exception as e:
            logger.warning(f"PDF extraction failed for {blob_path}: {e}")

    return ""


def parse_3d_model(filepath: str) -> dict:
    """Extract metadata from 3D model files (.obj, .stl, .glb, .gltf).

    Returns {vertex_count, face_count, format, bounding_box} or empty dict.
    """
    ext = Path(filepath).suffix.lower()
    result = {"format": ext}

    if ext == ".obj":
        return _parse_obj(filepath, result)
    elif ext == ".stl":
        return _parse_stl(filepath, result)
    elif ext in (".glb", ".gltf"):
        return _parse_gltf(filepath, result)

    return {}


def _parse_obj(filepath: str, result: dict) -> dict:
    """Parse Wavefront OBJ — count vertices and faces."""
    vertices = 0
    faces = 0
    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line.startswith("v "):
                    vertices += 1
                elif line.startswith("f "):
                    faces += 1
        result["vertex_count"] = vertices
        result["face_count"] = faces
        logger.info(f"OBJ parsed: {vertices} vertices, {faces} faces")
    except Exception as e:
        logger.warning(f"OBJ parse error: {e}")
    return result


def _parse_stl(filepath: str, result: dict) -> dict:
    """Parse STL (ASCII or binary) — count facets."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(5)
        if header == b"solid":
            # ASCII STL
            with open(filepath) as f:
                faces = sum(1 for line in f if "facet normal" in line)
            result["face_count"] = faces
        else:
            # Binary STL — 80-byte header + 4-byte count
            with open(filepath, "rb") as f:
                f.seek(80)
                count = int.from_bytes(f.read(4), "little")
            result["face_count"] = count
        logger.info(f"STL parsed: {result.get('face_count', 0)} faces")
    except Exception as e:
        logger.warning(f"STL parse error: {e}")
    return result


def _parse_gltf(filepath: str, result: dict) -> dict:
    """Parse glTF/GLB — count meshes and vertices from JSON header."""
    try:
        import json as _json
        if filepath.endswith(".glb"):
            import struct
            with open(filepath, "rb") as f:
                # GLB header: 12 bytes magic + version + length
                f.read(12)
                # First chunk: JSON
                chunk_len = struct.unpack("<I", f.read(4))[0]
                json_data = _json.loads(f.read(chunk_len))
        else:
            with open(filepath) as f:
                json_data = _json.load(f)

        meshes = json_data.get("meshes", [])
        total_verts = 0
        accessors = json_data.get("accessors", [])
        for mesh in meshes:
            for prim in mesh.get("primitives", []):
                pos_idx = prim.get("attributes", {}).get("POSITION")
                if pos_idx is not None and pos_idx < len(accessors):
                    total_verts += accessors[pos_idx].get("count", 0)
        result["mesh_count"] = len(meshes)
        result["vertex_count"] = total_verts
        result["face_count"] = sum(len(m.get("primitives", [])) for m in meshes)
        logger.info(f"glTF parsed: {len(meshes)} meshes, {total_verts} vertices")
    except Exception as e:
        logger.warning(f"glTF parse error: {e}")
    return result
