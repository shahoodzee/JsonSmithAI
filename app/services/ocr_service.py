import httpx
import json
import logging
from typing import Any, Optional, Tuple

from fastapi import HTTPException, status, UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)

OCR_ENGINES = ("3", "2", "1")

# OCR.Space can be slow; use a generous read timeout.
OCR_TIMEOUT = httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=15.0)


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


def _format_ocr_exception(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return type(exc).__name__


class OCRService:
    BASE_URL = "https://api.ocr.space/parse/image"

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

        For image_url, the image is downloaded server-side first because OCR.Space often
        times out fetching signed/private URLs (e.g. Supabase storage).

        If no text is detected or the text is not valid JSON, returns Success false and a
        descriptive Message (character-level OCR mistakes can still make JSON invalid).
        """
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: OCR API Key missing.",
            )

        headers = {"apikey": self.api_key}

        data_base = {
            "language": "eng",
            "isOverlayRequired": "false",
            "scale": "true",
        }

        files = None

        if image_url:
            try:
                async with httpx.AsyncClient(timeout=OCR_TIMEOUT) as client:
                    image_response = await client.get(image_url)
                    image_response.raise_for_status()
                    content = image_response.content
            except httpx.TimeoutException as e:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail={
                        "Success": False,
                        "Data": None,
                        "Message": "Timed out while downloading the image from image_url.",
                        "IsJson": False,
                    },
                ) from e
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "Success": False,
                        "Data": None,
                        "Message": f"Could not download image from image_url: {_format_ocr_exception(e)}",
                        "IsJson": False,
                    },
                ) from e

            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "Success": False,
                        "Data": None,
                        "Message": "image_url returned an empty response.",
                        "IsJson": False,
                    },
                )

            content_type = image_response.headers.get("content-type", "image/png")
            filename = image_url.split("/")[-1].split("?")[0] or "image.png"
            files = {"file": (filename, content, content_type)}
        elif file:
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "Success": False,
                        "Data": None,
                        "Message": "Uploaded file is empty.",
                        "IsJson": False,
                    },
                )
            files = {
                "file": (
                    file.filename or "upload.png",
                    content,
                    file.content_type or "image/png",
                )
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "Success": False,
                    "Data": None,
                    "Message": "Either 'file' or 'image_url' must be provided.",
                    "IsJson": False,
                },
            )

        full_text = ""
        cleaned_text = ""
        parsed = None

        async with httpx.AsyncClient(timeout=OCR_TIMEOUT) as client:
            for engine in OCR_ENGINES:
                data = {**data_base, "OCREngine": engine}
                try:
                    response = await client.post(
                        self.BASE_URL,
                        headers=headers,
                        data=data,
                        files=files,
                    )
                    response.raise_for_status()
                    result = response.json()
                except httpx.TimeoutException as e:
                    logger.exception("OCR.Space request timed out (engine %s)", engine)
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail={
                            "Success": False,
                            "Data": None,
                            "Message": "OCR request timed out. Try again or use a smaller image.",
                            "IsJson": False,
                        },
                    ) from e
                except httpx.HTTPStatusError as e:
                    raise HTTPException(
                        status_code=e.response.status_code,
                        detail=f"OCR API Error: {_format_ocr_exception(e)}",
                    ) from e
                except httpx.HTTPError as e:
                    logger.exception("OCR.Space connection failed (engine %s)", engine)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "Success": False,
                            "Data": None,
                            "Message": f"OCR service connection failed: {_format_ocr_exception(e)}",
                            "IsJson": False,
                        },
                    ) from e
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            "Success": False,
                            "Data": None,
                            "Message": "OCR service returned an invalid response.",
                            "IsJson": False,
                        },
                    ) from e

                if result.get("IsErroredOnProcessing"):
                    continue

                parsed_results = result.get("ParsedResults", [])
                if not parsed_results:
                    continue

                full_text = "\n".join(
                    [res.get("ParsedText", "") for res in parsed_results]
                ).strip()
                if not full_text:
                    continue

                cleaned_text, parsed = _try_parse_json_after_ocr(full_text)
                if parsed is not None:
                    logger.info("JSON parsed successfully with OCR engine %s", engine)
                    break

        if not full_text:
            return {
                "Success": False,
                "Data": None,
                "Message": "No text could be read from the image.",
                "IsJson": False,
            }

        if parsed is None:
            cleaned_text, _ = _try_parse_json_after_ocr(full_text)
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


ocr_service_instance = OCRService()


def get_ocr_service():
    return ocr_service_instance
