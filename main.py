import hashlib
import os
import io
from urllib.parse import urlparse

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image
import httpx

app = FastAPI()

CACHE_DIR = "image_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Optional: restrict which domains are allowed
# ALLOWED_DOMAINS = {"image.tmdb.org"}

def get_cache_key(url: str, max_width: int, quality: int, fmt: str) -> str:
    key_string = f"{url}|{max_width}|{quality}|{fmt}"
    return hashlib.sha256(key_string.encode()).hexdigest()

@app.get("/optimize-image")
async def optimize_image(
    url: str = Query(..., description="URL of the image to optimize"),
    max_width: int = Query(800, description="Max width of optimized image"),
    quality: int = Query(75, description="Compression quality (1-95)"),
    fmt: str = Query("webp", pattern="^(jpeg|jpg|webp)$", description="Output format")
):
    # Optional: security check
    parsed = urlparse(url)
    # if parsed.netloc not in ALLOWED_DOMAINS:
        # raise HTTPException(status_code=403, detail="Domain not allowed")

    cache_key = get_cache_key(url, max_width, quality, fmt)
    cached_path = os.path.join(CACHE_DIR, f"{cache_key}.{fmt}")

    if os.path.exists(cached_path):
        media_type = "image/webp" if fmt == "webp" else "image/jpeg"
        return StreamingResponse(open(cached_path, "rb"), media_type=media_type)

    # Download image
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not fetch image: {e}")

    try:
        img = Image.open(io.BytesIO(resp.content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not open image: {e}")

    # Resize
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # Color mode adjustments
    if fmt in ("jpeg", "jpg") and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    elif fmt == "webp" and img.mode == "P":
        img = img.convert("RGBA")

    # Save to cache
    try:
        img.save(cached_path, format=fmt.upper(), quality=quality, optimize=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save image: {e}")

    media_type = "image/webp" if fmt == "webp" else "image/jpeg"
    return StreamingResponse(open(cached_path, "rb"), media_type=media_type)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)