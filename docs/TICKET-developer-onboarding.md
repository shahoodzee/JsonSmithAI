# Ticket: Developer onboarding — README & local run guide

## Summary

Add project documentation so new developers can clone JsonSmithAI, configure secrets, install dependencies, and run the API locally without tribal knowledge.

---

## Type

`Documentation` / `Developer Experience`

---

## Priority

Medium

---

## Description

JsonSmithAI is a FastAPI service that exposes `POST /api/v1/extract-json` to extract structured JSON from images via OCR.Space. The repository previously lacked a root `README.md`, which forced developers to infer setup steps from code (`app/config.py`, `Dockerfile`, `requirements.txt`).

This ticket delivers:

1. A **README.md** with prerequisites, virtualenv setup, `.env` configuration, local run commands, API examples, Docker instructions, and troubleshooting.
2. Clear documentation that secrets are loaded from **environment variables** and **`.env`** (not `appsettings.json`).

---

## Background / Problem

- No single source of truth for local development.
- Confusion between .NET `appsettings.json` and Python `.env` configuration.
- Onboarding required reading multiple files to understand auth (`X-API-Key`), OCR flow, and response envelopes.

---

## Scope

### In scope

- [x] Create `README.md` at repository root
- [x] Document required environment variables
- [x] Document venv creation, activation, and `pip install -r requirements.txt`
- [x] Document `uvicorn` run command from project root
- [x] Document `POST /api/v1/extract-json` with curl examples
- [x] Document success / failure response shapes
- [x] Document Docker build and run
- [x] Add troubleshooting section

### Out of scope

- CI/CD pipeline documentation
- Production deployment runbooks (Azure, AWS, etc.)
- Client SDK or frontend integration guides
- Changes to application code or API behavior

---

## Acceptance criteria

- [ ] A developer with Python 3.9+ can follow README from a clean clone and start the API on `http://127.0.0.1:8000`
- [ ] README lists all required `.env` variables with descriptions
- [ ] README explains that `X-API-Key` must match `API_KEY`
- [ ] README includes at least one curl example for file upload
- [ ] README documents JSON parse failure response (`Success: false`, `Message: "Could not parse the image as JSON."`)
- [ ] README states that `appsettings.json` is not used by this Python service
- [ ] No secrets or real API keys are committed to the repository

---

## Technical notes

| Item | Detail |
|------|--------|
| Config loader | `pydantic-settings` via `app/config.py` |
| Env file | `.env` in project root (gitignored) |
| Env var names | `API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `OCR_SPACE_API_KEY` |
| Default venv name | `JsonSmithAIVenv` (gitignored) |
| Run command | `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` |
| Primary endpoint | `POST /api/v1/extract-json` |

---

## Test plan

1. Clone repo on a machine without prior setup.
2. Create venv and `pip install -r requirements.txt`.
3. Add `.env` with valid keys.
4. Run uvicorn from repo root — confirm `/docs` loads.
5. Call `/api/v1/extract-json` with valid `X-API-Key` and a test image.
6. Confirm unauthorized request returns `Not authorized` envelope.

---

## Definition of done

- [ ] `README.md` merged to default branch
- [ ] Ticket markdown file included in PR for traceability
- [ ] PR reviewed and approved
- [ ] No application behavior changes in this PR

---

## Related files

- `README.md`
- `docs/TICKET-developer-onboarding.md`
- `app/config.py`
- `app/api/v1/image_router.py`
- `app/services/ocr_service.py`
- `requirements.txt`
- `Dockerfile`
