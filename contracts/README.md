# UVTS API contract

`openapi.json` is generated from the FastAPI application and is the source of truth for browser API types.

Regenerate it from `apps/api`:

```sh
uv run python -m uvts_api.generate_openapi
```

The browser must send credentials on API requests so the private, opaque `uvts_session` cookie is included. Start or recover an anonymous session with `POST /api/v1/session` before accessing a test. A `404 test_not_found` response deliberately does not distinguish a missing test from a test owned by another session.

The SSE endpoint emits `test.updated` events. Redis messages carry no test data; they only wake the API so it can refetch the latest persisted state from PostgreSQL. Event IDs are monotonically increasing `state_version` values, and comment-only heartbeat frames keep idle connections alive.

Do not hand-edit `openapi.json`. Regenerate it and commit the result whenever a route or schema changes.
