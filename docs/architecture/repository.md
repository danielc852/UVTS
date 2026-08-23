# Repository architecture

## Purpose

UVTS is a modular monolith with a separate browser application. The browser presents the workflow; the API owns documents, workflow state, authorization, background work, evidence validation, and all external AI access.

```text
Browser -> typed HTTP API -> service layer -> domain rules
                              |             |
                              v             v
                        adapters/ports   PostgreSQL
                              |
                         Celery + Redis
```

PostgreSQL is the source of truth. Redis carries job and progress notifications but is not the authoritative record of test state. A server-sent event tells the browser that state changed; the browser then fetches the current test resource.

## Application boundaries

### Browser

`apps/web/src/features` is organized by the five user-visible stages. A feature owns its components, state adapters, and tests. Routes compose features but do not contain business rules. `shared` contains only small UVTS utilities and accessibility helpers; Astryx remains the component and interaction source of truth.

Server state belongs in TanStack Query. Form state belongs in React Hook Form and Zod. The active workflow stage is derived from the API resource instead of being duplicated in a browser-only state machine.

### API and worker

`apps/api/src/uvts_api` separates HTTP schemas and handlers, pure domain rules, use-case services, infrastructure ports, and concrete adapters. FastAPI handlers and Celery tasks call services; they do not contain workflow policy.

Document storage, PDF extraction, model access, job publication, and repositories are ports so later features can be tested without network or filesystem dependencies. Queue messages contain record identifiers rather than document text.

## Contract ownership

FastAPI generates `contracts/openapi.json`. The web application generates its TypeScript definitions from that committed snapshot. Continuous integration regenerates both outputs and fails when a change was not committed.

Public errors use a stable machine code, a plain-language message, a retryable flag, and optional field errors. Raw exceptions, secrets, and internal model details must not cross the contract.

## Anonymous access

The API issues an opaque session token in an HttpOnly, SameSite cookie and stores only its hash. Every test lookup is constrained by the resolved session. A guessed test identifier therefore cannot reveal another session's data.

The current cookie is a browser-session cookie. Longer-lived access and cleanup depend on the future retention decision.

## Development workflow

The web and API applications have separate dependency locks and tests. Root `make` commands provide the common entry points. Docker Compose supplies equivalent PostgreSQL, Redis, API, worker, and web services for local development.

The existing product documents are intentionally retained at the repository root. They are product inputs, not generated implementation documentation.
