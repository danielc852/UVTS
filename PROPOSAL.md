# UVTS — User-View Testing for Product Manuals

## The problem

[Pergamon](https://www.pergamon-labs.com/) helps teams create structured,
regulation-based product manuals. Its focus on approved content, traceability, and
controlled AI solves an important problem: producing consistent manuals at scale
while keeping experts in control.

I chose a related problem: testing a manual from the user's point of view. A manual
can contain all its planned sections but still fail to explain how to set up, use, or
fix a product. Editors usually review the document section by section. Users instead
arrive with goals, limited context, and unexpected problems.

Pergamon's public material led me to this idea. Its website presents manuals as
structured systems rather than one-off documents. A
[LinkedIn post](https://www.linkedin.com/posts/pergamon-labs_pergamonlabs-technicaldocumentation-ai-activity-7457275554526928897-8s4e)
says documentation should stay in sync with changing product data. Another
[post about Pergami](https://www.linkedin.com/posts/pergamon-labs_productupdate-pergamon-pergamiai-activity-7422486444318994432-F-lT)
shows customers asking questions against manuals. Together, these suggest a useful
quality loop: Pergamon helps teams create and maintain manuals; UVTS asks realistic
user questions and checks whether the manual contains the information they need.
UVTS does not check legal compliance, but it can highlight practical gaps before a
manual reaches customers.

## What the app does

UVTS provides one guided workflow:

1. Add a product image, description, and question count.
2. Generate realistic user questions with AI, review them, and confirm the final set.
3. Upload a PDF manual. UVTS checks its type, length, and extractable text.
4. Evaluate the questions in the background with live progress updates.
5. Review a report showing covered, partly covered, and missing information, with
   supporting page references.

The first version is intentionally narrow. It does not generate manuals or certify
legal compliance. It does not support scanned PDFs because reliable OCR and page
evidence would add significant complexity. Report downloads, manual-version
comparison, and team approval tools are also out of scope. Draft questions can be
edited or added before the writer confirms and locks the final set.
The first goal is simply to test whether UVTS can find useful coverage gaps.

## How to run it

You need Docker Desktop (or Docker Engine with Docker Compose), `make`, an OpenRouter
API key, and free local ports `5173` and `8000`. The first build also requires an
internet connection.

From the repository root, create the environment file and add your OpenRouter key:

```sh
cp .env.example .env
```

In `.env`:

```dotenv
OPENROUTER_API_KEY=your-openrouter-api-key
```

Start Docker, then run:

```sh
make dev
```

Wait for the web app, API, worker, PostgreSQL, and Redis to start. Then open
[http://localhost:5173](http://localhost:5173). The API runs at
[http://localhost:8000](http://localhost:8000).

To stop the app, press `Ctrl+C`, then run:

```sh
make down
```

This removes the containers but keeps their data in Docker volumes.

## Architecture and key decisions

The browser app uses React and TypeScript. The API uses FastAPI. Celery handles slow
background work, PostgreSQL stores workflow data, Redis carries jobs and progress
events, local private storage holds uploads, and OpenRouter provides model access.

### 1. Modular monolith and typed API

The backend is one application divided into routes, services, domain rules, and
adapters. FastAPI generates an OpenAPI contract, which generates the browser's
TypeScript types. This is easier to run and change than several small services while
still keeping responsibilities clear. The trade-off is that parts cannot be deployed
or scaled independently.

### 2. Durable state and background jobs

PostgreSQL is the source of truth. Celery performs slow PDF and AI work, while Redis
carries jobs and progress events. The browser refetches current data when an event
arrives. This avoids long-running HTTP requests and makes retries safer, but it adds
the operational cost of running a database, Redis, and a worker.

### 3. Verified AI output

The agents return structured data instead of free-form text. UVTS breaks each question
into information needs, checks cited pages against the extracted manual, and calculates
the final coverage status with normal code. This takes more work and may reject some
useful model responses, but it is safer than presenting unsupported AI output as fact.

## How I worked with AI

I used Codex as my only AI coding tool. I first asked it to inspect the product
documents, code, and tests. I then split the work into small tasks, implemented one
behavior at a time, and reviewed the diff and contracts after each change. Tests acted
as constraints so the model did not invent product behavior from a short prompt.

Representative tasks included:

- change the journey from manual-first to product setup, question confirmation, and
  then manual upload;
- add concurrent evaluation without losing progress, retries, cancellation safety, or
  stable result order;
- simplify the report UI and update its component tests;
- diagnose the OpenRouter smoke-test timeout before changing code.

These are summaries, not verbatim prompts. The approach that worked best was to give
Codex one clear outcome, the important constraints, and a verification step, then
check the resulting code rather than trust its explanation.

One AI-generated integration was wrong. UVTS stored the OpenRouter timeout in seconds,
but `ChatOpenRouter` treated the value as milliseconds. A configured 60-second timeout
therefore became 60 milliseconds and caused slow retries. A direct provider request
worked while the app's live smoke test failed, showing that the integration was the
problem. I inspected the SDK, confirmed the behavior in the upstream
[LangChain issue](https://github.com/langchain-ai/langchain/issues/39812), converted
seconds to milliseconds, and added regression tests. The live structured-output test
then passed with the correct 60,000-millisecond value.

I manually reviewed diffs, schemas, generated contracts, error messages, and workflow
transitions. I also used backend unit and integration tests, frontend component tests,
linting, type checks, builds, and contract checks. The OpenRouter fix received a live
provider test. A fresh Docker test of the complete real-service journey is still
needed before calling the app release-ready.

## Honest limitations

- Results depend on model quality, availability, speed, and cost.
- The concurrency limit applies to each evaluation job, not all users together.
- Scanned PDFs, complex layouts, diagrams, and image-based information may be missed.
- Local file storage needs to be replaced with secure production object storage.
- Anonymous sessions provide no accounts, teams, roles, or cross-device access.
- Coverage does not prove that instructions are correct, safe, current, clear, or
  legally compliant.
- V1 is limited to 20 pages and 15 questions. It has no exports, version comparison,
  or completed real-service Docker verification.

## What's next

With one more month, I would focus on improving the AI workflow. First, I would review
and refine the agent prompts using real examples and human-reviewed results. The goal
would be to make generated questions and evaluations more relevant, consistent, and
easy to verify.

Next, I would expand question generation so users could choose the types of questions
they want, such as basic usage, cross-section, troubleshooting, or edge-case questions.
This would give writers more control over what UVTS tests instead of relying on one
general question-generation approach.

Finally, I would add a retrieval-augmented generation (RAG) system. Rather than sending
the whole manual to the evaluator, UVTS would retrieve the most relevant sections for
each question and evaluate those sections with page references. This would allow UVTS
to support much larger manuals while controlling model context, latency, and cost.

## Time spent

Just under 10 hours.
