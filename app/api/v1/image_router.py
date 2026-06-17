from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from typing import Optional

from app.core.security import get_api_key
from app.services.ocr_service import get_ocr_service, OCRService

router = APIRouter()


def _has_uploaded_file(file: Optional[UploadFile]) -> bool:
    """Swagger/curl often send an empty file field; treat that as no file."""
    if file is None:
        return False
    if not file.filename or not file.filename.strip():
        return False
    return True


@router.post("/extract-json", dependencies=[Depends(get_api_key)])
async def extract_json(
    file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """
    Extract JSON from an image using OCR.Space.
    Accepts either a file upload OR an image URL (file wins when both are provided).
    On success, Data is parsed JSON. If OCR yields no text or text that is not valid JSON,
    Success is false and Message explains the failure (see OCR service).
    """

    if image_url and image_url.strip() in ("", "string"):
        image_url = None

    has_file = _has_uploaded_file(file)

    if not has_file and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'file' or 'image_url' must be provided.",
        )

    if not has_file:
        file = None
    elif image_url:
        # Real file upload wins over image_url when both are sent.
        image_url = None

    result = await ocr_service.extract_text(file=file, image_url=image_url)

    return result
