from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from typing import Optional

from app.core.security import get_api_key
from app.services.ocr_service import get_ocr_service, OCRService

router = APIRouter()

@router.post("/extract-json", dependencies=[Depends(get_api_key)])
async def extract_json(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Extract JSON from an image using OCR.Space.
    Accepts either a file upload OR an image URL.
    Returns the visual text found in the image, parsed as JSON if possible.
    """
    
    # Validation: Handle default values from tools like Swagger
    if image_url and image_url.strip() in ("", "string"):
        image_url = None

    if not file and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'file' or 'image_url' must be provided."
        )

    # If file is provided, prioritize it over URL to prevent conflicts
    if file:
        image_url = None

    # All logic including fetching URL is finding handled by the service now or previously by router
    # But since OCR.Space handles URLs directly, we can pass the URL to the service.
    # If it's a file, we pass the file.
    
    result = await ocr_service.extract_text(file=file, image_url=image_url)
    
    return {
        "status": "success",
        "data": result
    }
