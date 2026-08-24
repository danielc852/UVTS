# UVTS

UVTS helps manual writers check whether a PDF contains the information that different kinds of users need. This repository contains a React browser application and a FastAPI service.

The current milestone includes the five-stage workspace, private PDF upload and replacement, background page-by-page text extraction, a continuous-scroll PDF viewer, a generated browser/API contract, anonymous browser sessions, and automated checks. The backend now has direct LangChain question-generation and manual-evaluation agents, with durable Celery jobs, progress events, retries, and model-setting audit data. Interactive browser wiring for those agent actions remains a separate feature.

## Repository map

```text
apps/web       Vite, React, TypeScript, and Astryx browser application
apps/api       FastAPI application and Celery worker
contracts      Generated OpenAPI snapshot shared across the app boundary
infra          Docker Compose and service images
docs           Architecture and development documentation
```

Product sources remain at the repository root:

- [Product brief](product_brief.md)
- [Product specification](product_spec.md)
- [UI/UX specification](uiux.md)

## Quick start

1. Copy `.env.example` to `.env` and replace the development-only secrets.
2. Run `make setup` to install locked dependencies.
3. Run `make dev` to start the complete local stack.
4. Open `http://localhost:5173`.

Useful commands:

```text
make setup      Install web and API dependencies
make dev        Start web, API, worker, PostgreSQL, and Redis
make test       Run backend and frontend tests
make contract   Regenerate OpenAPI and browser API types
make check      Run every required repository check
make down       Stop the local stack
```

See [repository architecture](docs/architecture/repository.md) for ownership rules, data flow, and extension points.

## Product boundaries

UVTS accepts unencrypted PDFs with 1–20 pages and document-wide extractable text. Scanned documents remain out of scope because OCR is not included. Agent calls use OpenRouter with the fixed `qwen/qwen3.8-27b` model and do not silently fall back to another model. The six grouped topics in `product_spec.md` and `uiux.md` are the canonical first-release taxonomy.
