# UVTS

UVTS helps manual writers check whether a PDF contains the information that different kinds of users need. This repository contains a React browser application and a FastAPI service.

The current milestone is the application foundation. It includes the five-stage workspace, a generated browser/API contract, anonymous browser sessions, durable service infrastructure, and automated checks. PDF extraction and AI evaluation are intentionally not implemented yet.

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

This foundation does not process uploaded files or call OpenRouter. Those features will be added through the API ports and feature modules already established here. The six grouped topics in `product_spec.md` and `uiux.md` are the canonical first-release taxonomy.
