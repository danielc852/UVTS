# UVTS Development Progress

**Current milestone:** V1 functional workflow implemented  
**Reviewed through:** 25 August 2026

## Current status

V1 of UVTS is working across the intended five-stage journey:

1. Add the product image, description, and question count.
2. Generate, review, and confirm user questions.
3. Upload and validate the PDF manual.
4. Evaluate the confirmed questions against the manual.
5. Review coverage, evidence, gaps, and recommendations in the report.

The application now has a React interface, FastAPI backend, background jobs,
PostgreSQL persistence, Redis events, private file handling, OpenRouter-powered AI
workflows, and automated backend and browser tests.

The feature work is complete enough to call this the **V1 functional milestone**.
The remaining release task is final live-stack verification: the current Playwright
tests cover browser behavior with mocked data, but do not yet prove one complete
Docker-backed journey through the real AI services.

## How I developed it with vibe coding

I worked in short loops:

1. **Describe the product clearly.** I started with the problem, product brief,
   detailed specification, and UI/UX direction.
2. **Build a visible foundation.** I created the app structure and basic five-stage
   interface early so the product could be reviewed as a whole.
3. **Add one capability at a time.** I added document upload, AI agents, question
   generation, evaluation, reporting, and browser integration in separate steps.
4. **Correct the workflow when the product logic changed.** I moved product setup
   and question confirmation before manual upload so the manual cannot influence the
   questions used to test it.
5. **Test and fix real problems.** I added unit, integration, component, contract,
   migration, and browser tests, then fixed configuration and OpenRouter issues as
   they appeared.
6. **Refactor after it worked.** I simplified the frontend and backend boundaries,
   removed repeated workflow code, and improved the database model without changing
   the product behavior.

## Progress timeline

| Date | Progress |
| --- | --- |
| 23 Aug | Defined the product and built the first application foundation. |
| 24 Aug | Added the PDF workflow, AI agents, question generation, evaluation, reporting, and integration. |
| 25 Aug | Reworked the flow to be manual-independent, fixed OpenRouter issues, strengthened tests, and simplified the architecture. |

## What worked well

- Using written specifications gave the AI clear boundaries.
- Small feature and fix commits made the history easy to understand.
- Testing each layer reduced the risk of hidden regressions.
- Revisiting the workflow improved the product instead of locking in the first idea.
- Refactoring after validation kept the code easier to maintain.

## Main lesson

Vibe coding worked best when I treated the AI as an implementation partner, not as
a replacement for product decisions. The strongest results came from giving it a
clear goal, reviewing the output, testing the real behavior, and correcting the
direction in small steps.

## Next step

Run one final Docker-backed end-to-end test with a real product image, OpenRouter
generation, PDF upload, evaluation, page evidence, and report reload. Once that
passes, V1 can be marked release-ready rather than only functionally complete.
