# UVTS Basic Implementation Roadmap

**Target release:** Basic end-to-end workflow
**Roadmap updated:** 2026-08-25

## Manual-independent workflow implementation record

The implementation branch uses `schemaVersion: 2` and the canonical stage order
`configuration -> questions -> upload -> evaluation -> report`.

The following decisions are part of the compatibility and recovery contract:

- **Start over is in place.** It keeps the existing test ID and Product setup,
  while removing questions, manuals, evaluation lineage, reports, and agent-operation
  audit data. Manual storage cleanup happens after the database change commits.
- **Question confirmation is a durable boundary.** A generated set is stored as a
  draft with its own ID and Product setup version. Confirmation preserves that exact
  ID and question text. Product setup and regeneration stay locked until Start over.
- **Legacy drafts are preserved.** Old manual-derived questions are marked
  `legacy_manual_unknown` and cannot be confirmed. Users must complete Product setup
  and generate a product-only set. A ready legacy manual remains attached.
- **Legacy completed work remains readable.** The state upgrader infers a stable
  legacy question-set ID and the available manual/question source pair for evaluation
  and report data. The Alembic migration copies that pair onto existing evaluation
  records without deleting stored content.
- **Manual replacement is transactional.** A failed candidate leaves the active
  manual and all existing results untouched. A successful replacement keeps Product
  setup and confirmed questions, then clears only the prior manual's evaluation and
  report lineage.
- **Evidence stays manual-only.** Product image and description may be supplied to
  the evaluator as interpretation context, but report evidence must be a validated,
  exact extract from the evaluated manual.

The API contract now creates tests from multipart Product setup, generates questions
without a request body, adds explicit Confirm and Start over transitions, and attaches
or replaces manuals through `PUT /tests/{test_id}/manual`. The obsolete
manual-created-test and question-configuration operations are not part of OpenAPI.

Verification for this change includes focused state/unit tests, API integration tests,
an Alembic upgrade-and-backfill test, explicit OpenAPI transition assertions, browser
component tests, and deterministic regeneration of the checked-in API/browser
contracts. The release is complete only when the repository-wide check and full
browser journey pass on the final combined worktree.

## Product decision

The manual must not be the first input. A user should define the product and approve
the questions before UVTS asks for the manual.

The target workflow is:

1. **Product setup** — upload a product image, enter a description, and choose a
   question count.
2. **Generate and confirm questions** — UVTS creates questions from the product
   setup only. The user reviews the complete set, generates another set if needed,
   and explicitly confirms the final set.
3. **Upload manual** — after question confirmation, upload and validate one PDF
   manual.
4. **Evaluate** — the agent checks the confirmed questions against the validated
   manual. The product image and description may provide context, but only the
   manual can count as evidence.
5. **Report** — show coverage, evidence, gaps, recommendations, and retry actions.

This ordering prevents the manual from influencing question generation. That is
important because UVTS is meant to discover missing information, including useful
questions the manual does not already answer.

## Original workflow problem

The baseline application modeled the order as `upload -> configuration -> questions
-> evaluation -> report`. The backend also blocked question configuration and
question generation until a manual was ready, and the question-generation service
read manual text.

The implementation changes the state model and those prerequisites before connecting
later UI actions. This avoids producing a question set biased by the manual under
evaluation.

## Milestone summary

| Order | Milestone | User-visible result | Depends on |
| --- | --- | --- | --- |
| 1 | Correct workflow foundations | Product setup is first; question generation no longer requires or reads a manual | Existing saved setup work |
| 2 | Generate questions | Image, description, and count produce a persisted question set with progress and failure states | Milestone 1 |
| 3 | Confirm questions and upload manual | The final question set is locked, then a PDF can be uploaded and validated | Milestone 2 |
| 4 | Evaluate confirmed questions | The agent checks each confirmed question using manual evidence only | Milestone 3 |
| 5 | Complete the report | Results, evidence, gaps, recommendations, and retries are usable in the browser | Milestone 4 |
| 6 | Harden the basic release | The complete journey is tested, accessible, private, and recoverable | Milestones 1–5 |

## Milestone 1 — Correct the workflow foundations

### Goal

Make product setup the first stage and remove every manual prerequisite from setup
and question generation.

### Required work

- Change the canonical stage order to:
  `configuration -> questions -> upload -> evaluation -> report`.
- Create a test before, or as part of, the first product-setup save. Do not create a
  test by uploading a manual.
- Allow the product image, description, and question count to be saved while no
  manual exists.
- Make the question-generation service use the saved product image, description,
  and count. It must not load active manual pages or send manual text to the model.
- Preserve product setup and confirmed questions when a manual is replaced. Clear
  only evaluation and report data connected to the old manual.
- Update API schemas, generated contracts, browser parsing, fixtures, stage labels,
  product documentation, and automated tests together.
- Define migration behavior for existing draft tests. At minimum, old states must
  load without crashing and be mapped to the nearest valid new stage.

### Acceptance criteria

- A clean workspace opens at Product setup.
- A valid product image, non-empty description, and count from 1–15 can be saved
  without a manual.
- Attempting to generate questions does not query or read an active manual.
- The question agent receives exactly the product image, description, and count.
- Existing API, browser, and contract tests pass after regeneration.
- New tests prove that no manual is required for setup or generation.

### Assignment prompt

```text
Implement Milestone 1 from implementation_roadmap.md: correct the UVTS workflow
foundation.

Target order: configuration -> questions -> upload -> evaluation -> report.
Product setup must be the first screen. Save product image, product description,
and question count without requiring a PDF. Question generation must use only those
three inputs and must not read or send manual text.

Inspect the current FastAPI state model, test creation endpoints, question
configuration route, question services, React workflow ordering, fixtures, and
tests before editing. Reuse the provider-neutral question-generation input builder
where appropriate. Add a safe compatibility path for existing stored draft states.
Regenerate the OpenAPI contract and browser types through the repository command;
do not hand-edit generated files. Preserve unrelated worktree changes.

Add focused backend and frontend tests proving:
1. clean workspaces start at Product setup;
2. setup saves without a manual;
3. generation never requires or reads a manual;
4. the new stage ordering and navigation work;
5. invalid image, description, and count errors remain clear.

Run the relevant tests and repository checks. Summarize the behavior change and any
migration decision in plain language.
```

## Milestone 2 — Connect question generation and review

### Goal

Turn a saved product setup into a durable question set that the user can review.

### Required work

- Wire the browser action to the existing background question-generation endpoint.
- Use the fixed OpenRouter model settings already defined by the backend.
- Persist generation status and expose progress through the existing test events
  mechanism.
- Validate structured agent output: exact requested count, non-empty text, unique
  IDs, and no duplicate normalized question text.
- Keep the previous successful set visible until Generate again succeeds.
- Show clear pending, success, retryable failure, and non-retryable failure states.
- Render the full numbered question list without manual-derived labels or answers.

### Acceptance criteria

- Generate questions creates exactly the requested number of unique questions.
- Reloading the page restores the latest successful set and current operation state.
- A failed Generate again attempt does not delete the previous set.
- A duplicate click cannot start a second concurrent operation.
- No generated question refers to the manual, page numbers, or a proposed answer.

### Assignment prompt

```text
Implement Milestone 2 from implementation_roadmap.md: connect saved product setup
to background question generation and the Review questions UI.

Use only the saved product image, product description, and requested count. Wire the
React action to the FastAPI endpoint and existing event/refetch mechanism. Persist
operation state, validate exact count and uniqueness, and keep the previous question
set until regeneration succeeds. Show full question text and clear working/error
states. Prevent concurrent generation.

Do not add manual input to question generation. Do not implement evaluation in this
task. Add unit, integration, component, and event-state tests in proportion to the
changed behavior. Regenerate contracts if the API changes, run relevant checks, and
summarize the feature in plain language.
```

## Milestone 3 — Confirm questions, then upload the manual

### Goal

Add an explicit approval boundary so the tested questions cannot change after the
manual is introduced.

### Required work

- Add a persisted question-set state such as `draft` and `confirmed`, with a
  confirmation timestamp or immutable version identifier.
- Add a Confirm questions action. Make the consequence clear: regeneration and
  setup editing are unavailable after confirmation unless the user deliberately
  starts over.
- Unlock Upload manual only after confirmation.
- Upload the PDF to the existing test; remove the first-upload endpoint that creates
  a new test, or retain it only as a documented compatibility path.
- Keep current PDF validation rules: PDF, 1–20 pages, not password protected, and
  document-wide readable text.
- Replacing a ready manual keeps product setup and confirmed questions, but clears
  the evaluation and report after a successful replacement.
- Removing a manual returns to the Upload manual stage without deleting the product
  setup or confirmed questions.

### Acceptance criteria

- The manual upload is locked until the question set is confirmed.
- Confirmation survives reload and prevents silent question changes.
- A failed manual replacement preserves the current ready manual and all current
  results.
- A successful replacement preserves confirmed questions and clears only evaluation
  and report data.
- Destructive confirmations name exactly what will be removed.

### Assignment prompt

```text
Implement Milestone 3 from implementation_roadmap.md: persist explicit question
confirmation and unlock manual upload only afterward.

Add a durable draft/confirmed question-set boundary. After confirmation, prevent
silent setup edits or regeneration. Change PDF upload so it attaches to the existing
test created during Product setup. Keep the current PDF validation and background
processing behavior.

On successful manual replacement, preserve product setup and confirmed questions and
clear only evaluation/report data. On failed replacement, preserve everything. On
manual removal, return to Upload manual and retain the confirmed questions.

Update the UI copy, API state transitions, contracts, and tests. Include tests for
confirmation immutability, upload locking, replacement failure, replacement success,
removal, reload restoration, and ownership. Run relevant checks and summarize the
new approval boundary in plain language.
```

## Milestone 4 — Evaluate the confirmed questions

### Goal

Run the evaluator only when both the immutable question set and a validated manual
are ready.

### Required work

- Enforce both prerequisites on the server: confirmed question-set version and ready
  manual ID/version.
- Snapshot those IDs on the evaluation operation so late replacements cannot change
  an in-progress result.
- Wire Evaluate questions in the browser and show per-question progress from events.
- Keep evaluation grounded in the manual. The model may use the product context to
  understand the question, but it must never treat that context or outside knowledge
  as evidence.
- Validate that found and partly-found results contain real page references and that
  not-found results contain no invented evidence.
- Continue after one question fails and support retrying only failed questions.

### Acceptance criteria

- Evaluation cannot start before confirmation and a ready manual.
- Every completed result uses the exact confirmed question and manual snapshot.
- Evidence page numbers exist in the uploaded manual.
- One failed question does not remove successful results.
- Reload restores progress and completed results.

### Assignment prompt

```text
Implement Milestone 4 from implementation_roadmap.md: connect evaluation of the
confirmed questions against the ready PDF manual.

Require a confirmed question-set version and ready manual version on the server, and
snapshot both when evaluation begins. Wire the browser action and live progress.
Ensure the manual is the only evidence source: found/partly-found results need real
page references, and not-found results must have no invented evidence. Preserve
completed results when one question fails and support retrying failed questions only.

Do not redesign report presentation in this task. Add service, agent-validation,
integration, component, and event restoration tests. Run relevant checks and
summarize the evaluation safeguards in plain language.
```

## Milestone 5 — Finish the report and recovery actions

### Goal

Make the persisted evaluation useful to a writer without requiring technical or AI
knowledge.

### Required work

- Show the exact summary: “X questions are covered out of Y total questions.”
- Show found, partly found, not found, and failed counts that add up to the total.
- Display every question result with information needed, found, missing, and page
  evidence.
- Group gaps, connect recommendations to results, and suggest follow-up questions.
- Mark partial reports clearly and connect Retry failed questions to the backend.
- Support starting another evaluation with the same confirmed questions after a
  manual replacement.

### Acceptance criteria

- Summary counts match detailed results.
- Every recommendation traces to a gap or question.
- Partial reports are never presented as complete.
- Report content survives reload and remains understandable at keyboard-only and
  200% zoom usage.

### Assignment prompt

```text
Implement Milestone 5 from implementation_roadmap.md: complete the UVTS report and
recovery actions.

Use persisted evaluation results. Show the required coverage sentence and consistent
counts, detailed question evidence, grouped gaps, linked recommendations, follow-up
questions, and a clear incomplete-report warning. Wire retry of failed questions and
support reevaluation after a manual replacement without changing the confirmed
question set.

Keep language suitable for non-technical writers and do not generate answers to the
questions. Add data-consistency, component, integration, accessibility, and reload
tests. Run relevant checks and summarize the report behavior in plain language.
```

## Milestone 6 — End-to-end hardening

### Goal

Make the basic release safe and dependable for a small user group.

### Required work

- Add a Playwright happy path covering setup through report.
- Add recovery paths for invalid image, generation failure, invalid PDF, evaluation
  failure, reconnect/reload, and manual replacement.
- Verify session ownership for all product images, manuals, questions, events, and
  reports.
- Verify private, no-store delivery and deletion of uploaded files.
- Audit keyboard operation, focus movement, labels, live regions, error messages,
  contrast, and 200% zoom.
- Document local setup, required services, environment variables, model behavior,
  and known limits.

### Acceptance criteria

- `make check` passes in a clean environment.
- The happy path works with background workers and survives reloads.
- One browser session cannot access another session's test or files.
- Deletion removes stored product images, manuals, and connected test data.
- Known basic-release limits are documented in one place.

### Assignment prompt

```text
Implement Milestone 6 from implementation_roadmap.md: harden the complete UVTS basic
workflow for release.

Add end-to-end happy-path and recovery tests from Product setup through Report.
Verify session ownership, private file delivery, deletion, background-operation
recovery, accessibility, and reload behavior. Fix issues found within this workflow
without expanding the product scope. Update setup and limitation documentation.

Run make check and the Docker-backed happy path when available. Report any check that
could not run, explain why, and summarize release readiness in plain language.
```

## Rules shared by every milestone

- The product image, description, and question count create questions; the manual
  does not.
- The confirmed question set is immutable for one evaluation lineage.
- Only the uploaded manual can support an Information found or Information partly
  found result.
- Do not create answers to user questions.
- Persist state before notifying the browser; events should tell clients to refetch
  durable state.
- The server owns workflow transition rules. The browser mirrors them but is not the
  security boundary.
- Preserve the user's unrelated worktree changes.
- Keep API schemas, OpenAPI, generated browser types, runtime parsing, fixtures, and
  tests synchronized.
- Explain errors and final behavior in plain language.

## Recommended implementation order

Complete milestones sequentially. Milestones 2–5 all depend on the corrected state
model from Milestone 1, so they should not be developed in parallel against the old
workflow. Within a milestone, backend state transitions and frontend presentation can
be assigned separately only after the API contract and acceptance criteria are agreed.
