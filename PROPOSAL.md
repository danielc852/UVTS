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

### Research and inspiration

Pergamon's public material led me to this idea. I reviewed its website, its AI
Assembly tutorial video, and its public LinkedIn posts. The website and tutorial
present manuals as structured systems that can be assembled with AI rather than as
one-off documents. A
[LinkedIn post](https://www.linkedin.com/posts/pergamon-labs_pergamonlabs-technicaldocumentation-ai-activity-7457275554526928897-8s4e)
says documentation should stay in sync with changing product data. Another
[post about Pergami](https://www.linkedin.com/posts/pergamon-labs_productupdate-pergamon-pergamiai-activity-7422486444318994432-F-lT)
shows customers asking questions against manuals. Together, these suggest a useful
quality loop: Pergamon helps teams create and maintain manuals; UVTS asks realistic
user questions and checks whether the manual contains the information they need.
In that sense, UVTS acts as a pre-publication testing agent: it simulates the
questions Pergami users may ask, identifies answers the manual cannot support, and
gives writers page-level evidence before those gaps reach customers.
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

The first version is intentionally narrow. The following are deliberately out of
scope:

- **Manual generation and legal compliance:** UVTS finds practical coverage gaps; it
  does not write replacement content or certify that a manual meets regulations.
- **Retrieval-augmented generation (RAG):** V1 evaluates the complete extracted text
  of a manual and therefore limits uploads to 20 pages. Building and validating a
  retrieval layer would add complexity before the core idea has been proven useful.
- **Autonomous multi-agent generation:** UVTS has three bounded AI stages—question
  generation, per-question evaluation, and report synthesis—but they follow a fixed
  workflow. The agents do not plan, delegate to one another, or run open-ended tool
  loops. This keeps state transitions, failures, and outputs easier to verify.
- **Scanned and visually complex manuals:** reliable OCR, diagram understanding, and
  page-level visual evidence require a separate evaluation approach.
- **Broader product workflow:** report downloads, manual-version comparison, team
  approvals, and generated authoring tasks are deferred until the coverage test itself
  is validated.

Draft questions can still be edited or added before the writer confirms and locks the
final set. The first goal is simply to test whether UVTS can find useful coverage gaps.

## How to run it

You need Docker Desktop (or Docker Engine with Docker Compose), `make`, an OpenRouter
API key with access or credit for the configured models, and free local ports `5173`
and `8000`. The first build also requires an internet connection.

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
background work, PostgreSQL stores workflow data, Redis carries job messages and
state-change notifications, local private storage holds uploads, and OpenRouter
provides model access.

### 1. Modular monolith and typed API

The backend is one application divided into routes, services, domain rules, and
adapters. FastAPI generates an OpenAPI contract, which generates the browser's
TypeScript types. This is easier to run and change than several small services while
still keeping responsibilities clear. The API and worker can run and scale as separate
processes, but they share one backend codebase and release cycle instead of evolving
as independent services.

### 2. Durable state and background jobs

PostgreSQL is the source of truth. Celery performs slow PDF and AI work, while Redis
carries job messages and state-change notifications. When a notification arrives, the
browser refetches the current state from the API instead of treating the notification
as data. If a notification is missed or the browser reconnects, the durable state is
still available in PostgreSQL. This avoids long-running HTTP requests and makes
recovery and retries safer, but it adds the operational cost of running a database,
Redis, and a worker. This separation also provides a path to larger customer-support
workloads because API and worker capacity can scale independently. Production use
would still require shared object storage, global concurrency controls, and
tenant-level quotas.

### 3. Verified AI output

The agents return structured data instead of free-form text. UVTS breaks each question
into information needs, checks cited pages against the extracted manual, and calculates
the final coverage status with normal code. This takes more work and may reject some
useful model responses, but it is safer than presenting unsupported AI output as fact.

## How I worked with AI

I used ChatGPT as a discussion partner at the start of the project. We explored
different product ideas and approaches, but I did not treat its suggestions as final
decisions. I selected the useful ideas, combined them with my own understanding of the
problem, and decided the product direction and scope.

Once the direction was clear, I asked AI to turn it into two separate text documents:
a product specification and a UI/UX specification. I reviewed and refined both before
asking Codex to build the first version with a multi-agent workflow. The agents worked
on bounded parts of the product using the shared specifications, while I reviewed how
the pieces fitted together.

I broke the build into small tasks based on dependencies and risk. Each task had a
clear outcome, key constraints, and a verification step before it was considered
complete.

After the first draft was complete, I tested the full journey from product setup to
the final report before adding more features. Problems found in that end-to-end test
became the next iteration tasks. I continued the same loop for later work: discuss and
select an idea, update the intended behavior, implement it, test the complete journey,
and refine it. I also reviewed diffs, contracts, and tests after changes instead of
accepting generated code from its explanation alone.

For recent changes, I also used Codex skills such as Code Simplifier and Vercel React
Best Practices to improve code quality and frontend performance. I reviewed each
suggestion before applying it.

Representative tasks included:

- change the journey from manual-first to product setup, question confirmation, and
  then manual upload;
- add concurrent evaluation without losing progress, retries, cancellation safety, or
  stable result order;
- simplify the report UI and update its component tests;
- diagnose the OpenRouter smoke-test timeout before changing code.

For example, one successful task breakdown was: "Evaluate confirmed questions
concurrently, with at most four model calls in flight. Preserve retries, cancellation
safety, progress reporting, and stable result order. Add tests for the concurrency
limit and failure paths, then run the complete evaluation journey."

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

With one more month, I would first build a small benchmark from real manuals, realistic
user questions, and human-reviewed coverage decisions. I would use it to measure false
positives and false negatives, refine the agent prompts, and make the results more
consistent and easy to verify instead of judging improvements by intuition alone.

Next, I would close the loop with authoring. A writer could turn a missing or partly
covered result into a suggested content task, update the manual, and compare the next
version to confirm that the gap was resolved. I would also let writers choose question
types such as basic usage, cross-section, troubleshooting, or edge cases so the test
reflects the product's actual risks.

Finally, once real usage showed that manual size was the limiting factor, I would add
a retrieval-augmented generation (RAG) system. UVTS would retrieve the most relevant
sections for each question and evaluate them with page references, allowing larger
manuals while controlling model context, latency, and cost.

## Time spent

Just under 10 hours.
