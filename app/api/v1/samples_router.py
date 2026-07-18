from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.security import get_api_key
from app.services.sample_service import sample_service

router = APIRouter()


class GenerateSamplesRequest(BaseModel):
    key: str = Field(..., min_length=1)
    type: Literal["string", "int"]
    seed: Any
    frequency: int = Field(..., ge=1, le=50)


class GenerateSamplesResponse(BaseModel):
    values: list[Any]


@router.post(
    "/generate-samples",
    response_model=GenerateSamplesResponse,
    dependencies=[Depends(get_api_key)],
)
async def generate_samples(body: GenerateSamplesRequest):
    """
    Generate unique sample values for a JSON Builder column.
    Uses the property key as semantic context and seed as a style example.
    """
    values = await sample_service.generate_samples(
        key=body.key,
        sample_type=body.type,
        seed=body.seed,
        frequency=body.frequency,
    )
    return GenerateSamplesResponse(values=values)
