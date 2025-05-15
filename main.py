from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from PIL import Image
import io
import httpx

app = FastAPI()

app.get("/optimize-image")
async def optimize_image(
    url: str = Query(..., description="The URL of the image to optimize"),
    quality: int = Query(75, ge=1, le=100, description="The quality to optimize the image to"),
    max_width: int = Query(None, ge=1, description="The width to optimize the image to"),
    
):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            image = Image.open(io.BytesIO(response.content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height))
            
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
            
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/jpeg")