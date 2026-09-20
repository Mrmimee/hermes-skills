---
name: jev-decision-engine
description: Use when deciding task routing, tool triage or safety risk.
version: 1.0.0
---

# Jev Autonomous Decision Engine

Proactively invoke Jev (backed by Agnes 3.0 Flash) whenever faced with ambiguous task branching, tool selection, or high-risk actions. Do NOT wait for explicit user requests.

## Autonomous Trigger Scenarios

Proactively invoke Jev when:
1. **Tool Triage / Dispatch**: Multiple tools could solve a problem (e.g. Browser vs Web Search vs Terminal) and a fast decision is needed.
2. **Safety Gate**: Before deleting files, killing processes, or altering network/system configs, score risk with Noul.
3. **Task Complexity Triage**: Score the complexity of a user request to decide whether to handle in-line or fan out to subagents.

## Direct Invocation

Use the preconfigured environment in `C:/Users/mnb77/jev-starter/`:

```python
import os
from system_one_adapter import SystemOneAdapterClient, Choice, Noul, Score
from system_one_adapter.providers.openai import OpenAIProvider

provider = OpenAIProvider(
    "agnes-3.0-flash",
    base_url="https://apihub.agnes-ai.com/v1",
    api_key=os.environ.get("AGNES_API_KEY"),
    api="chat_completions"
)

client = SystemOneAdapterClient(structured_outputs=False, llm_answer_mode="discrete")

# Run decision
response = client.system_one(
    state={"task": "..."},
    questions={
        "action": Choice(instructions="Next step?", criteria={...}),
        "risk": Noul(instructions="Is it destructive?")
    },
    model=provider
)
```
