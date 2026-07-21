# JsonSmithAI

> **Secure FastAPI service** that extracts structured JSON from images using OCR — built for the JsonSmith web app.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](#)

---

## Table of contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
  - [1. Clone and enter the repo](#1-clone-and-enter-the-repo)
  - [2. Create and activate the virtual environment](#2-create-and-activate-the-virtual-environment)
  - [3. Install dependencies](#3-install-dependencies)
  - [4. Configure secrets](#4-configure-secrets)
  - [5. Run the API](#5-run-the-api)
- [API reference](#api-reference)
  - [Endpoints](#endpoints)
  - [Authentication](#authentication)
  - [POST /api/v1/extract-json](#post-apiv1extract-json)
  - [Response shapes](#response-shapes)
- [Docker](#docker)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development notes](#development-notes)
- [License](#license)

---

## Overview

JsonSmithAI accepts an image (file upload or URL), runs OCR via [OCR.Space](https://ocr.space/), strips common markdown wrappers, and returns parsed JSON when the extracted text is valid.

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/` | GET | None | Health / welcome |
| `/docs` | GET | None | Swagger UI |
| `/api/v1/extract-json` | POST | `X-API-Key` | Extract JSON from an image |

---

## Prerequisites

- **Python 3.9+** (3.11+ recommended for local dev)
- **pip**
- An [OCR.Space API key](https://ocr.space/ocrapi)
- Supabase credentials (required by config; reserved for future integration)

---

## Quick start

### 1. Clone and enter the repo

```powershell
git clone <repository-url>
cd JsonSmithAI
```

### 2. Create and activate the virtual environment

**Windows (PowerShell)**

```powershell
python -m venv JsonSmithAIVenv
.\JsonSmithAIVenv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv JsonSmithAIVenv
source JsonSmithAIVenv/bin/activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure secrets

Create a `.env` file in the **project root** (same folder as `requirements.txt`):

```env
API_KEY=your-secret-api-key-for-clients
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-key
OCR_SPACE_API_KEY=your-ocr-space-api-key
```

> **Where do secrets come from?**  
> This app uses **Pydantic Settings** (`app/config.py`). Values are loaded from:
>
> 1. **Environment variables** (highest priority)
> 2. **`.env` file** in the working directory
>
> There is **no** `appsettings.json` — that is a .NET pattern and is not used here.

### 5. Run the API

From the project root (so `app` imports correctly):

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API root: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## API reference

### Endpoints

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 1 | `GET` | [`/`](#get-root) | None | Welcome / health check |
| 2 | `GET` | `/docs` | None | Swagger UI (interactive API docs) |
| 3 | `GET` | `/redoc` | None | ReDoc (alternative API docs) |
| 4 | `POST` | [`/api/v1/extract-json`](#post-apiv1extract-json) | `X-API-Key` | Extract and parse JSON from an image |

### Authentication

Every protected route requires the `X-API-Key` header. The value must **exactly match** `API_KEY` in your `.env` or environment.

### GET /

Returns a welcome message. No authentication required.

```json
{
  "message": "Welcome to JsonSmithAI. Documentation available at /docs"
}
```

### POST /api/v1/extract-json

Extract structured JSON from an image via OCR. Accepts **either** a file upload **or** an image URL (file takes priority if both are sent).

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `file` | form | `UploadFile` | One of `file` or `image_url` | Image file containing JSON (PNG, JPG, etc.) |
| `image_url` | form | `string` | One of `file` or `image_url` | Public URL to an image |

**File upload**

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract-json" `
  -H "accept: application/json" `
  -H "X-API-Key: your-secret-api-key-for-clients" `
  -F "file=@path/to/image.png;type=image/png"
```

**Image URL**

```powershell
curl -X POST "http://127.0.0.1:8000/api/v1/extract-json" `
  -H "accept: application/json" `
  -H "X-API-Key: your-secret-api-key-for-clients" `
  -F "image_url=https://example.com/screenshot.png"
```

### Response shapes

**Success** — OCR text parsed as valid JSON:

```json
{
  "Success": true,
  "Message": "Text extracted successfully",
  "Data": { "your": "parsed-json" },
  "IsJson": true
}
```

**Failure** — text found but not valid JSON:

```json
{
  "Success": false,
  "Data": null,
  "Message": "Could not parse the image as JSON.",
  "IsJson": false,
  "ExtractedText": "raw ocr output for debugging"
}
```

**Unauthorized** — wrong or missing API key:

```json
{
  "Success": false,
  "Data": null,
  "Message": "Not authorized"
}
```

---

## Docker

Build and run with environment variables passed at runtime:

```powershell
docker build -t jsonsmithai .
docker run -p 8000:8000 `
  -e API_KEY=your-secret-api-key-for-clients `
  -e SUPABASE_URL=https://your-project.supabase.co `
  -e SUPABASE_KEY=your-supabase-key `
  -e OCR_SPACE_API_KEY=your-ocr-space-api-key `
  jsonsmithai
```

The container listens on **port 8000**.

---

## Project structure

```
JsonSmithAI/
├── app/
│   ├── main.py              # FastAPI app, CORS, routers
│   ├── config.py            # Settings (.env + env vars)
│   ├── api/v1/
│   │   └── image_router.py  # POST /extract-json
│   ├── core/
│   │   └── security.py      # X-API-Key validation
│   └── services/
│       └── ocr_service.py   # OCR.Space integration + JSON parsing
├── requirements.txt
├── Dockerfile
├── .env                     # Local secrets (gitignored)
└── README.md
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Not authorized` | `X-API-Key` ≠ `API_KEY` | Match header to `.env` exactly |
| `ModuleNotFoundError: app` | Wrong working directory | Run `uvicorn` from repo root |
| Settings validation error on startup | Missing `.env` vars | Set all four required keys |
| `Could not parse the image as JSON` | OCR output is not valid JSON | Check `ExtractedText`; improve image quality |
| OCR API errors | Invalid OCR.Space key or quota | Verify `OCR_SPACE_API_KEY` |

---

## Development notes

- **Hot reload:** use `--reload` with uvicorn during local development.
- **CORS:** currently allows all origins (`*`) for POC; tighten before production.
- **OCR accuracy:** character-level mistakes (e.g. `_` vs space) are not auto-corrected.

---

## License

Copyright © 2026 shahoodzee. All rights reserved.

This repository is a personal/portfolio project. No license is granted.
You may view the code on GitHub, but you may not copy, modify, distribute,
or use it for any purpose without prior written permission.
