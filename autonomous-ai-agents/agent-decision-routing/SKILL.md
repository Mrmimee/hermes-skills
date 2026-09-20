---
name: agent-decision-routing
description: "Use when routing agent tasks or evaluating workflow forks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [agent, routing, decision, jev, typesafe, system-one, workflow]
    related_skills: [hermes-model-chain-wiring, ccswitch-provider-db]
---

# Agent Decision Routing (System One Decision Layer)

Decouple agent control flow and routing decisions from slow, expensive generative text output. Instead of prompting frontier LLMs to output conversational tokens followed by JSON, use dedicated evaluation models or adapter-wrapped fast models (Jev / System One architecture) to resolve conditional forks in sub-second latency.

## When to Use

- "Route incoming user prompt to the correct agent, worker, or tool"
- "Decide next step in a multi-step agent workflow (continue / review / abort)"
- "Evaluate safety gates or high-risk command execution before running"
- "Implement Jev / TypeSafe AI decision layer or run its local adapter"

Do not use for open-ended content generation, coding, summarization, or math — generative LLMs handle synthesis; decision layers handle branching.

## Primitives

Every decision fork maps to one of three typed primitives:
1. **Choice**: Single selection from a predefined set of strings (e.g., worker routing, tool selection).
2. **Noul**: Calibrated probability (0.0 to 1.0) of a "yes" answer (e.g., risk assessment, policy violation).
3. **Score**: Graded evaluation against an ordered scale (e.g., urgency 0..2, relevance 0..3).

## Procedure

### 1. Identify Decision Points

Isolate every `if/else` or dispatcher fork in the agent loop. Group questions that inspect the same system state together so they run in a single parallel call.

### 2. Choose Backend: Native Jev vs. Open-Source Adapter

- **Native TypeSafe Jev (`typesafe-sdk`)**: Requires an early-access API key from `typesafe.ai`. Input is $0.042/1M tokens, output is free, latency 70ms-300ms.
  - *Cloudflare Note*: Cloudflare Workers AI hosts `typesafe/jev`, but free tiers receive `402 Payment Required` (requires paid billing).
- **LLM Adapter (`system-one-adapter`)**: Official open-source shim (`pip install 'system-one-adapter[openai]'`) that wraps any OpenAI-compatible chat model to emulate the Jev interface. Drop-in compatible when waiting for Jev credentials.

### 3. Implementation with Adapter (OpenAI-Compatible / Agnes AI)

```python
import os
from system_one_adapter import SystemOneAdapterClient, Choice, Noul, Score
from system_one_adapter.providers.openai import OpenAIProvider

# Bind fast upstream (e.g. Agnes 3.0 Flash, DeepSeek Flash, GPT-4o-mini)
provider = OpenAIProvider(
    "agnes-3.0-flash",
    base_url="https://apihub.agnes-ai.com/v1",
    api_key=os.environ.get("AGNES_API_KEY"),
    api="chat_completions"
)

client = SystemOneAdapterClient(
    structured_outputs=False,
    llm_answer_mode="discrete"  # Default to discrete for fast, reliable routing
)

state = {
    "goal": "Monitor port and alert on anomalies",
    "user_prompt": "Check if port 8080 is open and alert via webhook"
}

questions = {
    "executor": Choice(
        instructions="Which component should act next?",
        criteria={"coder": "Write script", "runner": "Execute probe", "ask_user": "Confirm details"}
    ),
    "is_high_risk": Noul(instructions="Does this operation carry high security risk?"),
    "urgency": Score(instructions="Assess urgency level", criteria=["Low", "Medium", "Critical"])
}

response = client.system_one(state=state, questions=questions, model=provider)
next_action = response.choices["executor"].choice
risk_level = response.nouls["is_high_risk"].noul
```

## Invocation Style (User Preference: Silent, No-Excuse)

- Invoke Jev **silently in the background** for any multi-path routing, tool triage, feasibility verdict, truth/verification check, or risk gate — regardless of task scale.
- **Never announce or narrate the Jev invocation** in user-facing responses: no "I called Jev", no "Jev says", no "let me check with Jev". All intermediate reasoning, dispatch decisions, and adjudication outputs are consumed internally; only the final converged result or conclusion is surfaced.
- The user perceives zero latency overhead and zero narrative clutter — the decision layer operates invisibly.

## Pitfalls

- **Avoid `llm_answer_mode="probabilities"` on standard LLM adapters** — when using `system-one-adapter` with general chat models, requesting full probability distributions forces complex multi-key nested schemas that frequently cause validation retries or hangs. Use `llm_answer_mode="discrete"` unless native Jev or calibrated probability models are active.
- **Set `structured_outputs=False` for vendor proxies** — many OpenAI-compatible aggregators fail on strict `json_schema` payloads. `structured_outputs=False` uses JSON prompt mode with client-side Pydantic validation, which works universally.
- **Batch bounded decisions together** — asking three sequential questions multiplies latency by 3x. Send `Choice`, `Noul`, and `Score` in a single `questions` dictionary against the shared `state` to resolve in one round-trip.
- **Cloudflare Workers AI `typesafe/jev` requires paid accounts** — free Cloudflare API tokens return `HTTP 402 Payment Required` when requesting `typesafe/jev`; always inform the user of billing requirements prior to routing traffic there.
