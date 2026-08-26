# UVTS — User-View Testing System

UVTS (User-View Testing System) helps manual writers check whether a PDF
contains the information that different kinds of users need. This repository
contains a React browser application and a FastAPI service.

The current V1 milestone implements the complete five-stage browser workflow: product
setup, AI question generation and confirmation, private PDF upload, concurrent manual
evaluation, and an interactive coverage report. The React application and FastAPI
service also include background jobs, live progress events, page evidence, retryable
failures, anonymous sessions, durable PostgreSQL state, private file storage, and
automated backend and browser checks.

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
- [Basic implementation roadmap](implementation_roadmap.md)

## Run with Docker

You need Docker Desktop (or Docker Engine with Docker Compose), `make`, an OpenRouter
API key, and free local ports `5173` and `8000`. The first build also requires an
internet connection.

From the repository root, create the environment file:

```sh
cp .env.example .env
```

Add your OpenRouter key to `.env`:

```dotenv
OPENROUTER_API_KEY=your-openrouter-api-key
```

Start Docker, then run:

```sh
make dev
```

Docker starts the web app, API, worker, PostgreSQL, and Redis. When they are ready,
open [http://localhost:5173](http://localhost:5173). The API runs at
[http://localhost:8000](http://localhost:8000).

To stop the app, press `Ctrl+C`, then run:

```sh
make down
```

This removes the containers but keeps their data in Docker volumes. Use `make logs`
to follow the service logs.

`make dev` deliberately reads the OpenRouter key from the root `.env` file, even
if the current shell has an empty variable with the same name. Startup stops with
a clear error when the key is missing instead of launching question generation in
an unusable state.

Workspace history, uploaded documents, and queued state persist across restarts in
Docker volumes. To erase all local UVTS data and start from a blank workspace, stop
the app and run `docker compose --env-file .env -f infra/compose.yaml down --volumes`.
This reset cannot be undone.

Manual questions are evaluated concurrently to reduce waiting time. The worker runs
up to four model calls at once by default; set `EVALUATION_MAX_CONCURRENCY` in `.env`
to an integer from 1 to 15 when provider limits require a different value. Rate-limit
responses are retried with a shared cooldown so one operation does not continue
sending requests during a provider-requested pause.

See [repository architecture](docs/architecture/repository.md) for ownership rules, data flow, and extension points.

## Product boundaries

UVTS accepts unencrypted PDFs with 1–20 pages and document-wide extractable text.
Question setup accepts one private `image/*` product file up to 10 MB, a non-empty
product description, and 1–15 questions. Scanned documents remain out of scope
because OCR is not included. Agent calls use `qwen/qwen3.8-27b` through OpenRouter,
which automatically tries `minimax/minimax-m3` when the primary model fails. Set
`OPENROUTER_FALLBACK_MODEL` to change the fallback or leave it blank to disable
model fallback. Both models use medium reasoning effort by default; set
`OPENROUTER_REASONING_EFFORT` to choose another OpenRouter-supported level for the
whole primary-and-fallback request. Question
types, topic selection, user viewpoints, and per-type question counts are deferred
from the basic V1 workflow.
