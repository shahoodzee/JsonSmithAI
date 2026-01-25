from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.json_router import router as json_router

app = FastAPI(
    title="JsonSmithAI API",
    description="Secure API for JsonSmith Web App Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
origins = [
    "*", # Allow all for POC. In production, change to specific domains.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(json_router, prefix="/api/v1", tags=["Json Core"])

@app.get("/")
async def root():
    return {"message": "Welcome to JsonSmithAI. Documentation available at /docs"}
