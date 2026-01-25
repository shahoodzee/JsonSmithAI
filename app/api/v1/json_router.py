from fastapi import APIRouter, Depends
from app.core.security import get_api_key

router = APIRouter()

@router.get("/data", dependencies=[Depends(get_api_key)])
async def get_secure_data():
    return {"message": "You are authorized via API Key!", "status": "success"}

@router.post("/process", dependencies=[Depends(get_api_key)])
async def process_data(payload: dict):
    return {"message": "Data received", "received_payload": payload}
