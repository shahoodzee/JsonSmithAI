import httpx
import json
from fastapi import HTTPException, status, UploadFile
from app.config import get_settings

class OCRService:
    BASE_URL = "https://api8.ocr.space/parse/image"
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.OCR_SPACE_API_KEY
        if not self.api_key or self.api_key == "helloworld":
            print("WARNING: OCR_SPACE_API_KEY is not set. Inference will fail.")

    async def extract_text(self, file: UploadFile = None, image_url: str = None) -> dict:
        """
        Sends the image to OCR.Space and returns the parsed result.
        Returns a dict that tries to be the JSON structure if found, otherwise returns text.
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
            "OCREngine": "2",           # Changed from 2 to 1 (Engine 1 is often better for structured JSON-like text)
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
            return {"text": "", "warning": "No text found"}
            
        # Combine text from all pages
        full_text = "\n".join([res.get("ParsedText", "") for res in parsed_results]).strip()
        
        # Return structured JSON response as requested
        return {
            "Success": True,
            "Data": full_text,
            "Message": "Text extracted successfully"
        }

# Singleton
ocr_service_instance = OCRService()

def get_ocr_service():
    return ocr_service_instance
