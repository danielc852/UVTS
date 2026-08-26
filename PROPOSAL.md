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

You need Git, Docker Desktop (or Docker Engine with Docker Compose), an OpenRouter API
key with access or credit for the configured models, and free local ports `5173` and
`8000`. Docker must be running, and the first build requires an internet connection.

### 1. Download and open the repository

Cloning is recommended because it preserves the commit history required for this
assessment.

On macOS or Linux, open Terminal and run:

```sh
git clone https://github.com/danielc852/UVTS.git
cd UVTS
cp .env.example .env
```

On Windows, open PowerShell and run:

```powershell
git clone https://github.com/danielc852/UVTS.git
Set-Location UVTS
Copy-Item .env.example .env
```

If you received the repository as a ZIP that includes the `.git` folder, extract it,
open Terminal or PowerShell in the extracted folder containing `PROPOSAL.md`, and run
only the platform-specific copy command above.

### 2. Configure the model connection

Open the new `.env` file in a text editor and replace the empty
`OPENROUTER_API_KEY` value:

```dotenv
OPENROUTER_API_KEY=your-openrouter-api-key
```

### 3. Start the application

From the repository folder, run the same command on macOS, Linux, or Windows:

```sh
docker compose --env-file .env -f infra/compose.yaml up --build
```

Wait for the web app, API, worker, PostgreSQL, and Redis to start. Then open
[http://localhost:5173](http://localhost:5173). The API runs at
[http://localhost:8000](http://localhost:8000).

### 4. Stop the application

In the terminal running UVTS, press `Ctrl+C`, then run:

```sh
docker compose --env-file .env -f infra/compose.yaml down
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

I used ChatGPT to explore product ideas, then chose the direction and scope myself. I
asked AI to help turn the idea into a product specification before using Codex to
implement the application in small tasks.

My usual workflow was simple:

1. Discuss an idea with AI.
2. Choose the approach and describe the expected result.
3. Use a short prompt for a small change, or Plan mode for a larger change.
4. Review the code and test the complete user journey.
5. Use any problems found as the next task.

When an idea was simple and limited to a small change, my prompts were often short.
For example:

> "Instead of sequential evaluation of questions by the agent, would it be better to
> use a concurrent approach to improve efficiency?"

I then asked Codex to check provider rate limits before making the change. From that
discussion, we defined a limit of four concurrent model calls, safe retries, stable
result ordering, and tests for failures and cancellation.

For a refactor or workflow change involving both the frontend and backend, I used Plan
mode before implementation. For example:

> "Use Plan mode to correct the question-generation workflow. After the user uploads
> an image and starts question generation, move to the next section and show a
> progress bar instead of leaving the user on the original page."

Plan mode helped identify the required backend state change, frontend loading and
failure states, and tests before any code was changed. I used the same process to
improve the question flow, simplify the report, and investigate the OpenRouter
timeout. I also used Code Simplifier and Vercel React Best Practices, but reviewed
their suggestions before applying them.

One AI-generated integration was wrong. UVTS stored the OpenRouter timeout in seconds,
but `ChatOpenRouter` treated the value as milliseconds. A configured 60-second timeout
therefore became 60 milliseconds and caused slow retries. A direct provider request
worked while the app's live smoke test failed, showing that the integration was the
problem. I inspected the SDK, confirmed the behavior in the upstream
[LangChain issue](https://github.com/langchain-ai/langchain/issues/39812), converted
seconds to milliseconds, and added regression tests. The live structured-output test
then passed with the correct 60,000-millisecond value.

This experience showed why I did not accept AI output without checking it. I reviewed
code changes, error messages, workflow transitions, and tests. I used backend and
frontend tests, linting, type checks, builds, contract checks, and a live provider test
for the OpenRouter fix. A fresh Docker test of the complete real-service journey is
still needed before calling the app release-ready.

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
