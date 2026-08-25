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
