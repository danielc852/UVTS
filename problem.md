# OpenRouter agent connection problem

The problem was discovered after asking whether UVTS had a test for calling an OpenRouter model, then requesting a live connection test, confirmation of whether the agents were affected, the file scope, and a reviewed solution. The direct API call to `qwen/qwen3.8-27b` returned HTTP 200, while the application smoke test timed out because UVTS passed its 60-second setting directly to `ChatOpenRouter`, which interprets the value as 60 milliseconds and then performs lengthy retries. The solution is to convert seconds to milliseconds in the shared OpenRouter adapter (`timeout_seconds * 1_000`), trim the API key before use, and add unit coverage for both behaviors; this was verified locally when the existing structured-output smoke test passed in 6.95 seconds with a 60,000-millisecond timeout, and independently matches the upstream LangChain issue [ChatOpenRouter: `timeout` parameter violates LangChain seconds convention and forwards as milliseconds](https://github.com/langchain-ai/langchain/issues/39812).

## Is it solved?

Not yet in the repository code. The root cause and proposed solution are confirmed, and the live smoke test passes with the corrected timeout, but the adapter conversion, API-key normalization, and regression tests still need to be implemented and committed before the problem can be marked solved.
