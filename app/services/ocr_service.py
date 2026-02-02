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
            
        data = {
            "apikey": self.api_key,
            "language": "eng",
            "isOverlayRequired": "false",
            "OCREngine": "2"
        }
        
        files = None
        
        if image_url:
            data["url"] = image_url
        elif file:
            # Read file content for upload
            # OCR.Space expects the file in the 'file' field
            content = await file.read()
            files = {"file": (file.filename, content, file.content_type)}
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.BASE_URL,
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
            error_msg = result.get("ErrorMessage", ["Unknown error"])[0]
            raise HTTPException(status_code=400, detail=f"OCR Processing Failed: {error_msg}")
            
        parsed_results = result.get("ParsedResults", [])
        if not parsed_results:
            return {"text": "", "warning": "No text found"}
            
        # Combine text from all pages
        full_text = "\n".join([res.get("ParsedText", "") for res in parsed_results]).strip()
        
        # Try to parse as JSON if the user expects JSON
        try:
            # naive attempt to find json block if surrounded by ```json ... ``` or just text
            # often OCR adds noise, so this is a best-effort. 
            # If the image IS a picture of a JSON object, the text should be valid JSON.
            # We strip markdown code blocks if present
            cleaned_text = full_text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            return {"raw_text": full_text, "info": "Could not parse text as valid JSON"}

# Singleton
ocr_service_instance = OCRService()

def get_ocr_service():
    return ocr_service_instance
