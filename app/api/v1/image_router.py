from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from typing import Optional
import httpx
from io import BytesIO
from PIL import Image

from app.core.security import get_api_key
from app.services.ai_model import get_model_service, JsonExtractorModel

router = APIRouter()

@router.post("/extract-json", dependencies=[Depends(get_api_key)])
async def extract_json(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    model_service: JsonExtractorModel = Depends(get_model_service),
):
    """
    Extract JSON from an image.
    Accepts either a file upload OR an image URL.
    """
    
    if not file and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'file' or 'image_url' must be provided."
        )

    image_data = None
    
    # 1. Handle File Upload
    if file:
        image_data = await file.read()

    # 2. Handle Image URL
    elif image_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch image from URL: {str(e)}"
                )

    # 3. Process Image
    try:
        image = Image.open(BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format."
        )

    # 4. Inference
    result = model_service.predict(image)
    
    return {
        "status": "success",
        "data": result
    }
