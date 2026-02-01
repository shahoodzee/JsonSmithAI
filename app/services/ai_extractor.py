from fastapi import UploadFile, HTTPException
import google.generativeai as genai
from app.config import get_settings
from PIL import Image
import io
import json

settings = get_settings()

class AIExtractorService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
             # We rely on the app starting up to catch this configuration error ideally,
             # but here we can just log or pass. The model setup will fail if key is missing.
             pass
        else:
             genai.configure(api_key=settings.GEMINI_API_KEY)
             self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def extract_json_from_image(self, file: UploadFile) -> dict:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="Server misconfiguration: GEMINI_API_KEY missing.")

        try:
            # Read image file
            contents = await file.read()
            image = Image.open(io.BytesIO(contents))

            # Validate image is a supported format (this is implicit by opening it with PIL, but good to keep in mind)
            
            prompt = """
            Analyze this image. It contains a visual representation of a JSON object or data that should be structured as JSON.
            Extract the data and return ONLY a valid JSON object. 
            Do not include Markdown formatting like ```json ... ```. 
            Just return the raw JSON string.
            If the image does not contain recognizable data, return {"error": "No data found"}.
            """

            response = self.model.generate_content([prompt, image])
            
            # Clean up response text just in case
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            return json.loads(response_text)

        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="AI extracted content but it was not valid JSON.")
        except Exception as e:
            # In production, log the actual error `e`
            raise HTTPException(status_code=500, detail=f"AI Processing failed: {str(e)}")

ai_extractor = AIExtractorService()
