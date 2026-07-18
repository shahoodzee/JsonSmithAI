import json
import re
from typing import Any, List, Literal

from fastapi import HTTPException, status
from google import genai

from app.config import get_settings

SampleType = Literal["string", "int"]

ANTIGRAVITY_AGENT = "antigravity-preview-05-2026"


class SampleService:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        settings = get_settings()
        if not settings.GEMINI_API_KEY or not settings.GEMINI_API_KEY.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GEMINI_API_KEY is not configured on JsonSmithAI.",
            )

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
        return self._client

    async def generate_samples(
        self,
        key: str,
        sample_type: SampleType,
        seed: Any,
        frequency: int,
    ) -> List[Any]:
        key = (key or "").strip()
        if not key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="key is required.",
            )

        if sample_type not in ("string", "int"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="type must be 'string' or 'int'.",
            )

        if frequency < 1 or frequency > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="frequency must be between 1 and 50.",
            )

        seed_value = self._normalize_seed(seed, sample_type)

        if frequency == 1:
            return [seed_value]

        prompt = (
            f'Generate exactly {frequency} unique plausible sample values for a JSON property.\n'
            f'Property name (semantic meaning): "{key}"\n'
            f'Type: {sample_type}\n'
            f'Example / seed value (use as style reference; include it as the first value when sensible): {json.dumps(seed_value)}\n'
            f'Return ONLY a valid JSON array of length {frequency}. No markdown, no explanation, no tools.\n'
            f'All values must be unique and match the type ({sample_type}).'
        )

        client = self._get_client()
        try:
            # Antigravity free-tier agent via Interactions API (no sandbox/tools needed).
            interaction = client.interactions.create(
                agent=ANTIGRAVITY_AGENT,
                input=prompt,
                environment="remote",
                tools=[],
                agent_config={
                    "type": "antigravity",
                    "max_total_tokens": 8000,
                },
            )
            text = (getattr(interaction, "output_text", None) or "").strip()
            if not text:
                raise ValueError("Antigravity returned an empty response.")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Antigravity request failed: {exc}",
            ) from exc

        values = self._parse_array(text)
        values = self._coerce_and_validate(values, sample_type, frequency, seed_value)
        return values

    def _normalize_seed(self, seed: Any, sample_type: SampleType) -> Any:
        if sample_type == "int":
            try:
                if isinstance(seed, bool):
                    raise ValueError("bool is not a valid int seed")
                return int(seed)
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="seed must be a valid integer when type is 'int'.",
                ) from exc
        return "" if seed is None else str(seed)

    def _parse_array(self, text: str) -> List[Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", cleaned)
            if not match:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Antigravity did not return a valid JSON array.",
                )
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Antigravity did not return a valid JSON array.",
                ) from exc

        if not isinstance(parsed, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Antigravity response must be a JSON array.",
            )
        return parsed

    def _coerce_and_validate(
        self,
        values: List[Any],
        sample_type: SampleType,
        frequency: int,
        seed_value: Any,
    ) -> List[Any]:
        coerced: List[Any] = []
        for item in values:
            if sample_type == "int":
                try:
                    if isinstance(item, bool):
                        raise ValueError("bool is not int")
                    coerced.append(int(item))
                except (TypeError, ValueError) as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Antigravity returned a non-integer value for type 'int'.",
                    ) from exc
            else:
                coerced.append(str(item))

        if seed_value not in coerced:
            coerced = [seed_value] + coerced

        unique: List[Any] = []
        seen = set()
        for item in coerced:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)

        if len(unique) < frequency:
            i = 1
            while len(unique) < frequency:
                if sample_type == "int":
                    candidate = int(seed_value) + i
                else:
                    candidate = f"{seed_value}_{i}" if seed_value != "" else f"value_{i}"
                if candidate not in seen:
                    seen.add(candidate)
                    unique.append(candidate)
                i += 1

        return unique[:frequency]


sample_service = SampleService()
