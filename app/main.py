from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.image_router import router as image_router
from app.api.v1.samples_router import router as samples_router

app = FastAPI(
    title="JsonSmithAI API",
    description="Secure API for JsonSmith Web App Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If detail is already the desired structure, return it directly
    if isinstance(exc.detail, dict) and "Success" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    # Default behavior for other HTTP exceptions
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# CORS Configuration
origins = [
    "*", # Allow all for POC. In production, change to specific domains.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(image_router, prefix="/api/v1", tags=["Image Extraction"])
app.include_router(samples_router, prefix="/api/v1", tags=["JSON Builder"])

@app.get("/")
async def root():
    return {"message": "Welcome to JsonSmithAI. Documentation available at /docs"}
