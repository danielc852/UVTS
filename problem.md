# Current problems and status

## 1. OpenRouter agent connection — solved

The problem was discovered after asking whether UVTS had a test for calling an OpenRouter model, then requesting a live connection test, confirmation of whether the agents were affected, the file scope, and a reviewed solution. The direct API call to `qwen/qwen3.8-27b` returned HTTP 200, while the application smoke test timed out because UVTS passed its 60-second setting directly to `ChatOpenRouter`, which interprets the value as 60 milliseconds and then performs lengthy retries. The solution is to convert seconds to milliseconds in the shared OpenRouter adapter (`timeout_seconds * 1_000`), trim the API key before use, and add unit coverage for both behaviors; this was verified locally when the existing structured-output smoke test passed in 6.95 seconds with a 60,000-millisecond timeout, and independently matches the upstream LangChain issue [ChatOpenRouter: `timeout` parameter violates LangChain seconds convention and forwards as milliseconds](https://github.com/langchain-ai/langchain/issues/39812).

Yes. The shared OpenRouter adapter now converts the public timeout setting from seconds to milliseconds at the `ChatOpenRouter` boundary and trims the API key before passing it to the SDK. Focused regression tests cover the 60-second to 60,000-millisecond conversion, surrounding key whitespace, and blank-key rejection. The full API test suite passes locally; the opt-in live smoke test remains skipped unless explicitly enabled with an API key.

## 2. Agent evaluation latency — improved; timing verification open

The application previously evaluated questions one at a time, so total waiting time
grew roughly with the number of questions. It now evaluates a bounded number of
questions concurrently. The default maximum is four and can be configured from 1 to
15 with `EVALUATION_MAX_CONCURRENCY`. Each question still reports its own progress
and failure, completed results are preserved, and HTTP 429 responses use limited
retries plus a shared provider cooldown.

**Goal:** Complete the full evaluation flow within 1 minute, measured from when the user submits a question until the final evaluation result is displayed.

Automated integration tests confirm that model calls overlap only up to the configured
limit, rate-limit retries respect their cooldown, and cancellation and failure paths
remain safe. The one-minute goal is not yet marked solved because it still needs a
real Docker-backed measurement across request preparation, model calls, retries,
result processing, and delivery to the browser.

**Low-priority follow-up:** `EVALUATION_MAX_CONCURRENCY` currently limits each
evaluation job rather than all evaluation jobs combined. If several users start
evaluations at the same time, each job can run up to its own configured limit, so the
total number of OpenRouter requests can be higher. This is not urgent for the current
small-scale use case. Before UVTS is used by many simultaneous users or runs several
worker instances, add a shared provider-wide concurrency limit, such as a Redis-backed
semaphore or a dedicated evaluation worker queue with controlled capacity.

**Model fallback follow-up:** The OpenRouter client and the evaluation service can
both retry a request when the selected model is unavailable or rate limited. Repeatedly
waiting for the same model can make an evaluation take much longer than expected. The
preferred solution is to use an OpenRouter fallback model instead of adding more
application-level retry coordination. For example, if the primary model cannot serve
the request, OpenRouter could route it to `deepseek-v4-flash`. Keep any remaining
retries small and bounded, and verify the exact OpenRouter model identifier and
fallback routing configuration before implementation.

## 3. UI clarity and structure — solved

The interface had repeated step numbers and secondary explanations that competed
with the current task, while the report presented important findings as a long,
mostly static sequence.

The workflow now uses plain stage titles, quieter completion markers, a simpler app
header, and concise back/continue navigation. The report groups information into a
clear dashboard: exact status counts and a labeled coverage bar provide the overview;
filters isolate covered, review-needed, or failed questions; expandable results keep
page evidence available without overwhelming the page; and gaps link back to the
questions they affect. Responsive styles and accessible labels preserve the same
structure on narrow screens and for assistive technology.

Component and workspace tests were updated for the simplified headings and navigation,
and report tests cover filtering, linked results, retry behavior, and the visible
coverage breakdown.

## 4. AI over-engineering in early generations — review safeguard needed

Early AI-generated implementations often add more layers, files, abstractions, and
configuration than the first release needs. Even when the code works, this can make
the repository harder to understand, review, test, and change. It can also hide
duplicate code or leave unused parts behind after the design changes.

For each early implementation generation, request a clean, structured repository for
review before accepting the result. The review should show:

- the repository tree, with each main folder and important file explained in plain
  words;
- what was added, moved, merged, simplified, or removed during cleanup, and why;
- where each product responsibility belongs, so the same job is not implemented in
  several places;
- which abstractions and dependencies are necessary now, rather than only useful for
  an imagined future;
- the tests or checks that prove cleanup did not change the intended behavior; and
- any remaining complexity that could not safely be removed.

The final explanation must avoid technical shorthand and state what the cleaned
structure means for the product. This gives the reviewer a practical way to verify
that the outcome matches the expected first-release scope: every major part has one
clear purpose, unnecessary machinery is removed, and a new contributor can find
where a change belongs without tracing many layers.
