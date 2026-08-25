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

The browser uses a small layered, feature-first structure:

- `app` owns bootstrap, providers, routing, theme, and global styles;
- `pages/workspace` composes the workflow route and lazy stage boundaries;
- `entities/workspace` owns the workspace model, response validation, queries, and cache keys;
- `features` is organized by the five user-visible stages, with each feature owning its commands, components, and tests;
- `shared/api` owns the generated HTTP contract, client, and request infrastructure, while `shared/ui` contains the small reusable UVTS presentation layer;
- `mocks` contains development-only workspace examples and is loaded conditionally so demo report data does not enter the normal application entry bundle.

Dependencies flow from the app and page layers toward features, entities, and shared infrastructure. Direct file imports are preferred over barrel files so Vite can analyze and split feature code. Astryx remains the component and interaction source of truth.

Server state and mutations belong in TanStack Query. Form state belongs in React Hook Form and Zod. The active workflow stage is derived from the API resource instead of being duplicated in a browser-only state machine. Workflow stages are lazy-loaded through static import paths, with accessible stages preloaded on intent; the PDF renderer remains a nested, conditional bundle.

### API and worker

`apps/api/src/uvts_api` separates HTTP schemas and handlers, pure domain rules, use-case services, infrastructure ports, and concrete adapters. FastAPI handlers and Celery tasks call services; they do not contain workflow policy.

Document storage, PDF extraction, model access, job publication, and repositories are ports so later features can be tested without network or filesystem dependencies. Queue messages contain record identifiers rather than document text.

### Agent boundaries

The internal model layer is divided by responsibility. Question generation uses trusted system
policy plus explicitly untrusted product context and returns temporary coverage labels that are
discarded before questions are saved. Manual evaluation breaks each question into atomic needs,
validates exact page evidence, and deterministically folds those needs into the public coverage
result. Report synthesis receives only incomplete or missing results and validates that every gap
and recommendation remains traceable. Shared structured-output handling provides strict schemas,
safe provider errors, rate-limit metadata, and one bounded repair attempt.

## Contract ownership

FastAPI generates `contracts/openapi.json`. The web application generates its TypeScript definitions from that committed snapshot under `apps/web/src/shared/api/generated`. Continuous integration regenerates both outputs and fails when a change was not committed.

Public errors use a stable machine code, a plain-language message, a retryable flag, and optional field errors. Raw exceptions, secrets, and internal model details must not cross the contract.

## Anonymous access

The API issues an opaque session token in an HttpOnly, SameSite cookie and stores only its hash. Every test lookup is constrained by the resolved session. A guessed test identifier therefore cannot reveal another session's data.

The current cookie is a browser-session cookie. Longer-lived access and cleanup depend on the future retention decision.

## Development workflow

The web and API applications have separate dependency locks and tests. Root `make` commands provide the common entry points. Docker Compose supplies equivalent PostgreSQL, Redis, API, worker, and web services for local development.

The existing product documents are intentionally retained at the repository root. They are product inputs, not generated implementation documentation.
