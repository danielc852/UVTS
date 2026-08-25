# UVTS — User-View Testing for Product Manuals

## The problem

[Pergamon](https://www.pergamon-labs.com/) helps product and compliance teams turn
product information into structured, regulation-grounded manuals. Its emphasis on
approved content blocks, traceability, controlled AI, and repeatable publishing
addresses a difficult production problem: creating consistent documentation at
scale without losing expert control.

I chose the adjacent problem of testing a manual from the user's point of view.
A document can have the expected sections and still leave a customer unable to set
up, use, or troubleshoot the product. Traditional editorial review tends to follow
the document's structure; users arrive with goals, incomplete context, and unusual
failure cases. Finding those coverage gaps before publication can reduce support
work, returns, and avoidable product risk.

This direction came from several signals in Pergamon's public material. The website
describes manuals as structured, auditable systems rather than one-off text. A
[Pergamon LinkedIn post about documentation systems](https://www.linkedin.com/posts/pergamon-labs_pergamonlabs-technicaldocumentation-ai-activity-7457275554526928897-8s4e)
argues that documentation must stay synchronized with changing product data. Another
[post introducing Pergami](https://www.linkedin.com/posts/pergamon-labs_productupdate-pergamon-pergamiai-activity-7422486444318994432-F-lT)
shows customers asking questions against product manuals and positions those
questions as useful support signals. Together, these suggested a complementary
quality loop: Pergamon helps teams build and maintain manuals; UVTS asks realistic
user questions and checks whether the manual contains the information needed to
answer them. UVTS is not a compliance checker, but it could help Pergamon users find
practical coverage gaps before a manual reaches customers.

## What the app does

UVTS provides one guided browser workflow:

1. The writer adds a product image, a short description, and a target question count.
2. AI generates realistic user questions from that product context. The writer can
   regenerate the set and must explicitly confirm it.
3. The writer uploads a PDF manual. The API validates the file, page limit, and
   extractable text before making it active.
4. A background worker evaluates the confirmed questions concurrently. The browser
   receives live progress updates while durable state remains in PostgreSQL.
5. The report summarizes covered, partly covered, and missing information. Each
   supported finding includes page-level evidence, while filters, gaps, and follow-up
   suggestions make the result easier to review.

The first version is deliberately narrow. It does not generate manuals or certify
legal or regulatory compliance. OCR and scanned/image-only PDFs are excluded because
reliable OCR, layout interpretation, and evidence mapping would substantially expand
the validation problem. It also omits editing individual generated questions,
downloadable reports, comparisons between manual versions, and team comments or
approval workflows. Those are useful features, but the first goal was to validate
the core question: can a writer quickly discover information that real users may
need but the manual does not cover?

## How to run it

The recommended setup uses Docker so the browser app, API, worker, PostgreSQL, and
Redis start as one stack.

### Requirements

- Docker Desktop, or Docker Engine with the Docker Compose plugin
- `make`
- An OpenRouter API key
- Ports `5173` and `8000` available locally
- Internet access on the first run so Docker can download images and dependencies

### Start the application

From the repository root:

```sh
cp .env.example .env
```

Open `.env` and set:

```dotenv
OPENROUTER_API_KEY=your-openrouter-api-key
```

Start Docker Desktop or Docker Engine, confirm that `docker compose version` works,
then run:

```sh
make dev
```

The first build may take several minutes. Wait until the web, API, worker, PostgreSQL,
and Redis services have started, then open
[http://localhost:5173](http://localhost:5173). The API listens on
[http://localhost:8000](http://localhost:8000).

`make dev` stays attached to the service logs. Press `Ctrl+C` to leave that process,
then stop and remove the containers with:

```sh
make down
```

The named Docker volumes keep database, Redis, and uploaded-document data between
runs. `make down` does not delete those volumes.

### Optional repository checks

Running checks directly on the host additionally requires Python 3.12 or later,
[`uv`](https://docs.astral.sh/uv/), Node.js 22, and
[`pnpm`](https://pnpm.io/installation). Then run:

```sh
make setup
make check
```

`make check` runs backend and frontend linting, type checks, tests, the production
web build, generated-theme verification, and the OpenAPI contract check.

## Architecture and key decisions

UVTS uses a React and TypeScript browser application with a FastAPI backend. Celery
runs document and model work in the background. PostgreSQL stores authoritative
workflow state, Redis carries jobs and progress notifications, local private storage
holds uploaded files, and the API accesses language models through OpenRouter.

### 1. Modular monolith with a typed application boundary

The backend is one deployable application organized into HTTP routes, services,
domain rules, ports, and adapters. FastAPI generates an OpenAPI contract from which
the browser's TypeScript types are generated. This is simpler to run and change than
several independently deployed services, while still making ownership boundaries
explicit. The trade-off is that services cannot be scaled or released independently;
if usage justified that complexity later, the existing service and port boundaries
provide sensible extraction points.

### 2. Durable state plus asynchronous work

PostgreSQL is the source of truth. Slow PDF and model operations run in Celery, and
Redis carries queue messages and server-sent progress notifications. When an event
arrives, the browser fetches the current resource rather than treating the event as
authoritative state. This avoids holding HTTP requests open during variable model
latency and makes retries safer. It costs more operationally than an in-process task
queue because local and production environments need a worker, Redis, and PostgreSQL.

### 3. Constrain and verify model output

The agents return structured schemas rather than free-form prose. Evaluation breaks
each question into information requirements, validates cited pages against extracted
manual pages, and deterministically folds those results into the public coverage
status. Report findings must remain traceable to question results. This adds code and
can reject an otherwise useful model response, but it is safer than presenting fluent,
unverifiable output as evidence—especially in a documentation product where trust and
traceability matter.

## How I worked with AI

I used Codex as the only AI coding tool. My workflow was to first ask it to inspect
the product documents, current implementation, and tests; split work into bounded
changes; implement one behavior at a time; and then review the diff and repository
contracts before moving on. I kept product intent in the root specifications and used
tests as executable constraints rather than asking the model to invent behavior from
a short prompt.

Representative task breakdowns included:

- inspect the workflow state and propose the smallest change needed to move from a
  manual-first journey to product setup, question confirmation, and then upload;
- add concurrent evaluation while preserving per-question progress, bounded retries,
  cancellation behavior, and deterministic result ordering;
- compare the report UI with the product and accessibility requirements, simplify the
  hierarchy, and update focused component tests;
- diagnose the live OpenRouter smoke-test timeout before changing implementation code.

These are representative descriptions, not a verbatim prompt transcript. The useful
pattern was giving Codex a narrow outcome, named constraints, and a verification step,
then checking its work against the actual code rather than accepting the explanation
alone.

One important failure was the OpenRouter timeout. The generated integration passed a
setting documented by UVTS in seconds directly to `ChatOpenRouter`, but that boundary
interpreted the value as milliseconds. A nominal 60-second timeout therefore became
60 milliseconds and triggered slow retry behavior. A direct provider request worked,
while the application's live structured-output smoke test failed, which showed that
the problem was in the integration rather than the model. I inspected the SDK boundary,
confirmed the mismatch against the upstream
[LangChain timeout issue](https://github.com/langchain-ai/langchain/issues/39812),
converted seconds to milliseconds in the shared adapter, and added regression tests
for the conversion and API-key normalization. The smoke test then passed with a
60,000-millisecond timeout.

Before considering individual changes done, I manually reviewed diffs, public schemas,
generated contracts, failure messages, and workflow transitions. I also used backend
unit and integration tests, browser component tests, linting, type checking, production
builds, and contract-generation checks. For the provider bug I ran the opt-in live
OpenRouter structured-output smoke test. I have not treated automated browser tests as
proof of the final real-service journey: a fresh Docker-backed end-to-end pass with a
real product image, manual, and all AI stages remains a release-readiness check.

## Honest limitations

- Results depend on model quality, availability, latency, and cost. Concurrency reduces
  waiting time but does not guarantee the one-minute target under provider throttling.
- The concurrency limit applies per evaluation job, not across every user or worker.
  A busier deployment needs a shared provider-wide limit and better rate-limit metrics.
- Evidence depends on extractable PDF text. Scans, complex layouts, diagrams, tables,
  and meaning carried mainly by images can be missed or mapped poorly.
- Uploaded files use local private storage. Production needs durable object storage,
  encryption and retention controls, malware scanning, and operational backup policy.
- Access is based on anonymous browser sessions. There are no accounts, organizations,
  roles, durable cross-device access, or collaborative review controls.
- A coverage result says whether information appears to exist; it does not prove that
  the instructions are correct, safe, clearly written, current, or legally compliant.
- The V1 limits manuals to 20 pages and questions to 15, and it lacks exports, version
  comparison, question editing, and a final real-service Docker journey in the release
  verification record.

## What's next

With one more month, I would first test UVTS with Pergamon's real manual structures and
writer workflows, agree on useful coverage metrics, and build a small human-reviewed
evaluation set. That would show where the model helps and where its labels or evidence
are unreliable before expanding the feature surface.

I would then productionize storage and identity, including object storage, retention,
authenticated organizations, and role-based access. In parallel I would add OCR and
layout-aware extraction, a Redis-backed provider-wide concurrency limit, structured
latency/cost/quality observability, and repeatable end-to-end tests against real model
calls. The product layer would add manual-version comparison, editable question sets,
review comments and approvals, and exportable reports. The longer-term opportunity is
to feed confirmed gaps back into Pergamon's structured content workflow so writers can
move directly from a failed user need to the relevant approved content block, while
keeping a human responsible for every change.

## Time spent

Just under 10 hours.
