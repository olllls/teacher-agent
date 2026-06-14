from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from backend.config import settings

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/storage")
async def get_storage():
    """Return upload directory usage stats."""
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return {"upload_files": 0, "upload_size_mb": 0.0}

    files = [f for f in upload_dir.iterdir() if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    return {
        "upload_files": len(files),
        "upload_size_mb": round(total_size / (1024 * 1024), 2),
    }


async def cleanup_expired_files():
    """Layer 2: delete files in uploads dir older than 24 hours."""
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.exists():
        return

    import time

    now = time.time()
    cutoff = now - 24 * 3600
    deleted = 0
    for f in upload_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            deleted += 1
            print(f"[INFO] Cleanup: deleted upload file {f.name}")

    if deleted:
        print(f"[INFO] Cleanup: removed {deleted} expired file(s)")
