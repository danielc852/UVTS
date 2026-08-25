# Current problems and status

## 1. OpenRouter agent connection — solved

The problem was discovered after asking whether UVTS had a test for calling an OpenRouter model, then requesting a live connection test, confirmation of whether the agents were affected, the file scope, and a reviewed solution. The direct API call to `qwen/qwen3.8-27b` returned HTTP 200, while the application smoke test timed out because UVTS passed its 60-second setting directly to `ChatOpenRouter`, which interprets the value as 60 milliseconds and then performs lengthy retries. The solution is to convert seconds to milliseconds in the shared OpenRouter adapter (`timeout_seconds * 1_000`), trim the API key before use, and add unit coverage for both behaviors; this was verified locally when the existing structured-output smoke test passed in 6.95 seconds with a 60,000-millisecond timeout, and independently matches the upstream LangChain issue [ChatOpenRouter: `timeout` parameter violates LangChain seconds convention and forwards as milliseconds](https://github.com/langchain-ai/langchain/issues/39812).

Yes. The shared OpenRouter adapter now converts the public timeout setting from seconds to milliseconds at the `ChatOpenRouter` boundary and trims the API key before passing it to the SDK. Focused regression tests cover the 60-second to 60,000-millisecond conversion, surrounding key whitespace, and blank-key rejection. The full API test suite passes locally; the opt-in live smoke test remains skipped unless explicitly enabled with an API key.

## 2. Agent evaluation latency — open

The application currently takes too long to call the agent and evaluate a question. This makes the evaluation flow feel slow and prevents users from getting timely feedback.

**Goal:** Complete the full evaluation flow within 1 minute, measured from when the user submits a question until the final evaluation result is displayed.

The latency should be measured across the complete flow so the main bottleneck can be identified. This includes request preparation, agent and model calls, retries, tool calls, result processing, and delivery of the result to the UI.

## 3. UI clarity and structure — open

The current UI contains too much unnecessary text, and its information structure can be improved. Important actions and evaluation results are harder to find because they compete with secondary explanations and content.

**Goal:** Simplify the interface by removing or shortening non-essential text, improving the visual hierarchy, grouping related information, and making the main question-and-evaluation flow easy to understand at a glance.
