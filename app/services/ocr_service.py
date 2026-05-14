import httpx
import json
from typing import Any, Optional, Tuple

from fastapi import HTTPException, status, UploadFile

from app.config import get_settings


def _strip_markdown_code_fence(text: str) -> str:
    """Remove leading ``` / ```json and trailing ``` from model/OCR-wrapped JSON."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    first_nl = t.find("\n")
    if first_nl == -1:
        return t
    body = t[first_nl + 1 :]
    end = body.rfind("```")
    if end != -1:
        body = body[:end]
    return body.strip()


def _try_parse_json_after_ocr(text: str) -> Tuple[str, Optional[Any]]:
    """
    Strip common markdown wrappers, then attempt json.loads.
    Returns (cleaned_text, parsed_or_none).
    """
    cleaned = _strip_markdown_code_fence(text)
    candidates = (cleaned, cleaned.replace("\\n", "\n"))
    for candidate in candidates:
        try:
            return cleaned, json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return cleaned, None


class OCRService:
    BASE_URL = "https://api8.ocr.space/parse/image"
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.OCR_SPACE_API_KEY
        if not self.api_key or self.api_key == "helloworld":
            print("WARNING: OCR_SPACE_API_KEY is not set. Inference will fail.")

    async def extract_text(
        self,
        file: Optional[UploadFile] = None,
        image_url: Optional[str] = None,
    ) -> dict:
        """
        Sends the image to OCR.Space and returns the parsed result.

        OCR may return JSON wrapped in markdown fences (```json ... ```); that wrapper
        is stripped and valid JSON is returned as a parsed object in Data.

        If no text is detected or the text is not valid JSON, returns Success false and a
        descriptive Message (character-level OCR mistakes can still make JSON invalid).

        Character-level OCR mistakes (e.g. _ vs space in identifiers) are not corrected.
        """
        if not self.api_key:
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: OCR API Key missing."
            )
        
        # Match user's working curl: apikey in header
        headers = {
            "apikey": self.api_key
        }

        data = {
            "language": "eng",
            "isOverlayRequired": "true", # Changed from false to true to match Postman response provided
            "OCREngine": "3",           # Changed from 2 to 1 (Engine 1 is often better for structured JSON-like text)
            "scale": "true",
        }
        
        files = None
        
        if image_url:
            data["url"] = image_url
        elif file:
            content = await file.read()
            # httpx format: "field_name": (filename, content, content_type)
            files = {"file": (file.filename, content, file.content_type)}
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.BASE_URL,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"OCR API Error: {str(e)}")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OCR Service connection failed: {str(e)}")
                
        # Parse Response
        if result.get("IsErroredOnProcessing"):
            error_msg = result.get("ErrorMessage")
            if isinstance(error_msg, list):
                error_msg = error_msg[0]
            raise HTTPException(status_code=400, detail=f"OCR Processing Failed: {error_msg}")
            
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            return {
                "Success": False,
                "Data": None,
                "Message": "No text could be read from the image.",
                "IsJson": False,
            }

        # Combine text from all pages
        full_text = "\n".join([res.get("ParsedText", "") for res in parsed_results]).strip()
        if not full_text:
            return {
                "Success": False,
                "Data": None,
                "Message": "No text could be read from the image.",
                "IsJson": False,
            }

        cleaned_text, parsed = _try_parse_json_after_ocr(full_text)
        if parsed is None:
            return {
                "Success": False,
                "Data": None,
                "Message": "Could not parse the image as JSON.",
                "IsJson": False,
                "ExtractedText": cleaned_text,
            }

        return {
            "Success": True,
            "Message": "Text extracted successfully",
            "Data": parsed,
            "IsJson": True,
        }

# Singleton
ocr_service_instance = OCRService()

def get_ocr_service():
    return ocr_service_instance
