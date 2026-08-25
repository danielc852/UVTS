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
- [UI/UX specification](uiux.md)
- [Basic implementation roadmap](implementation_roadmap.md)

## Setup

The recommended way to run the complete application is with:

- Docker Desktop, or Docker Engine with the Docker Compose plugin
- `make`

### Docker requirements

Docker is required for the recommended setup because it runs the web application,
API, background worker, PostgreSQL, and Redis as one local stack. Before starting
UVTS with Docker, confirm that:

- the Docker service is running;
- `docker compose version` works in your terminal;
- ports `5173` and `8000` are available on your computer;
- Docker has permission to download images and create local containers and volumes;
- you have an internet connection for the first run so Docker can download base
  images and application dependencies.

Docker stores the database, Redis data, and uploaded documents in named local
volumes so they remain available when the containers restart. Running `make down`
removes the containers but keeps these volumes and their data.

Make sure Docker is running, then create the local environment file from the repository root:

```sh
cp .env.example .env
```

The values in `.env.example` are intended for local development. Replace
`SESSION_SECRET` with a private value of at least 32 characters before using the
application outside your own development machine.

The Docker workflow installs the application dependencies inside its containers.
You only need to run `make setup` if you also want to run tests, linters, or other
development commands directly on your computer. That requires Python 3.12 or later,
[`uv`](https://docs.astral.sh/uv/), Node.js, and
[`pnpm`](https://pnpm.io/installation).

### Optional setup without Docker

UVTS can run directly on your computer without Docker, but you must install and
manage each service yourself. This setup requires:

- Python 3.12 or later and [`uv`](https://docs.astral.sh/uv/);
- Node.js 22 and [`pnpm`](https://pnpm.io/installation);
- PostgreSQL and Redis running locally;
- `make`.

From the repository root, install the application dependencies and create the API
environment file:

```sh
make setup
cp apps/api/.env.example apps/api/.env
```

Create a local PostgreSQL database and user, then update `DATABASE_URL` in
`apps/api/.env` with their credentials. Confirm that `REDIS_URL` points to your
running Redis service and replace `SESSION_SECRET` with a private value of at least
32 characters.

Apply the database migrations:

```sh
cd apps/api
uv run alembic upgrade head
```

Keep PostgreSQL and Redis running. Then use three separate terminals opened at the
repository root to start the API, background worker, and web application.

Terminal 1 — API:

```sh
cd apps/api
uv run uvicorn uvts_api.main:app --reload --port 8000
```

Terminal 2 — background worker:

```sh
cd apps/api
uv run celery -A uvts_api.workers.celery_app:celery_app worker --loglevel=INFO
```

Terminal 3 — web application:

```sh
cd apps/web
pnpm dev
```

When all three processes are running, open
[http://localhost:5173](http://localhost:5173). Stop each process with `Ctrl+C`.

Do not use the repository-root `.env` for this method without changing it: that
file uses the Docker-only hostnames `postgres` and `redis`. The
`apps/api/.env.example` file uses `localhost` for native services.

## Run with Docker

1. Start Docker Desktop or the Docker Engine.
2. From the repository root, start the complete UVTS stack:

   ```sh
   make dev
   ```

3. Wait for the services to finish starting, then open
   [http://localhost:5173](http://localhost:5173) in a browser.

`make dev` starts the web application, API, background worker, PostgreSQL, and
Redis. Keep that terminal open while using UVTS. Press `Ctrl+C` to stop the running
process, then run `make down` to stop and remove the containers.

Manual questions are evaluated concurrently to reduce waiting time. The worker runs
up to four model calls at once by default; set `EVALUATION_MAX_CONCURRENCY` in `.env`
to an integer from 1 to 15 when provider limits require a different value. Rate-limit
responses are retried with a shared cooldown so one operation does not continue
sending requests during a provider-requested pause.

Useful commands:

```text
make setup      Install web and API dependencies
make dev        Start web, API, worker, PostgreSQL, and Redis
make logs       Follow logs from the local stack
make test       Run backend and frontend tests
make contract   Regenerate OpenAPI and browser API types
make check      Run every required repository check
make down       Stop the local stack
```

See [repository architecture](docs/architecture/repository.md) for ownership rules, data flow, and extension points.

## Product boundaries

UVTS accepts unencrypted PDFs with 1–20 pages and document-wide extractable text.
Question setup accepts one private `image/*` product file up to 10 MB, a non-empty
product description, and 1–15 questions. Scanned documents remain out of scope
because OCR is not included. Agent calls use OpenRouter with the fixed
`qwen/qwen3.8-27b` model and do not silently fall back to another model. Question
types, topic selection, user viewpoints, and per-type question counts are deferred
from the basic V1 workflow.
