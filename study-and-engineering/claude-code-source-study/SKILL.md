---
name: claude-code-source-study
description: Deep dive into Claude Code source code to learn production-grade AI agent architecture patterns
triggers:
  - study claude code source
  - learn ai agent architecture
  - how does claude code work internally
  - implement agent like claude code
  - understand claude code system prompt
  - build production ai agent
  - claude code tool system design
  - multi agent orchestration patterns
---

# Claude Code Source Study

> Skill by [ara.so](https://ara.so) — Daily 2026 Skills collection.

A 34-article deep-dive into Claude Code's ~1900-file source code, covering System Prompt engineering, multi-agent orchestration, tool systems, permission security, and terminal UI. Learn production-grade AI agent patterns from Anthropic's real CLI product.

NOTE: The repo has grown from the original 25-article v1 to 34 chapters + 6 appendices. Chapter numbering below is the CURRENT one — old doc numbers in any earlier material do NOT map 1:1.

## Local Copy (cloned 2026-09-18)

Cloned at `C:/Users/mnb77/AppData/Local/Temp/Claude-Code-Source-Study` (ephemeral — re-clone from https://github.com/luyao618/Claude-Code-Source-Study if missing).

Verified against upstream `luyao618/Claude-Code-Source-Study@main`.

## What This Project Is

This is a **Chinese-language source code analysis series** that dissects Claude Code (Anthropic's AI CLI coding assistant) module by module — with exact file references, line numbers, and code snippets. Each article extracts reusable design patterns for building your own AI agent applications.

**Tech stack covered:** Bun + TypeScript + Ink (React for terminals) + Anthropic API

## Repository Structure (current, 34 chapters)

```
claude-code-source-study/
├── docs/
│   ├── 00-目录与阅读指引.md        # Index: 8 reading parts, 4 routes
│   ├── 01 项目全景与四种入口形态      # CLI + SDK + MCP server + sandbox
│   ├── 02 启动链路与冷启动优化       # side-effect hoisting, DCE, lazy load
│   ├── 03 配置体系与企业MDM         # 7-dimension settings merge
│   ├── 04 配置迁移即代码            # migrations/ 11 files
│   ├── 05 QueryEngine与对话主循环    # query() AsyncGenerator kernel
│   ├── 06 SystemPrompt与OutputStyle注入 # segmented prompt + cache boundary
│   ├── 07 上下文压缩家族            # 6 compact/cleanup paths
│   ├── 08 PromptCache横切          # CacheSafeParams, fork cache sharing
│   ├── 09 Thinking-Effort-与-Advisor
│   ├── 10 工具协议-注册与-ToolSearch # buildTool, 3-column tool model
│   ├── 11 BashTool-PowerShellTool-双shell
│   ├── 12 文件-代码-与-LSP-协作族
│   ├── 13 通信调度问询与合成工具     # WebFetch/ScheduleCron/SendMessage...
│   ├── 14 Agent系统与SubAgent调用   # runAgent lifecycle, context isolation
│   ├── 15 内置Agent设计模式         # Explore/Plan/Verification prompts
│   ├── 16 任务模型与TaskType谱系
│   ├── 17 Coordinator-Cron-与定时调度
│   ├── 18 MCP协议实现
│   ├── 19 权限系统与远程权限回灌
│   ├── 20 Hooks系统               # 27 HOOK_EVENTS
│   ├── 21 Skill-Plugin-OutputStyle三扩展点
│   ├── 22 FeatureFlag与编译期优化
│   ├── 23 客户端传输与API重试       # withRetry, HybridTransport
│   ├── 24 Bridge-IPC-与远程会话
│   ├── 25 DirectConnect-与上游代理
│   ├── 26 Ink框架深度定制
│   ├── 27 组件与设计系统
│   ├── 28 Keybindings-Vim与Voice输入
│   ├── 29 Buddy宠物
│   ├── 30 Doctor屏与OutputStyle体验
│   ├── 31 Memory子系统全景          # 7-layer memory architecture
│   ├── 32 命令系统全景              # 101 top-level commands
│   ├── 33 状态管理与跨进程桥        # 35-line Store
│   ├── 34 架构模式总结             # 11 transferable patterns
│   ├── appendix/A-F.md            # tool/command/hook/agent/tasktype matrices
│   └── archive/
└── README.md
```

## Reading Routes (from docs/00)

### ⚡ Quick Route (7 chapters)
`01 → 02 → 33 → 05 → 10 → 14 → 34`

### 🤖 AI Engineering Route (9 chapters)
`01 → 33 → 06 → 05 → 07 → 09 → 10 → 14 → 15` (read 08 PromptCache after the trunk)

### 🏢 Remote & Enterprise Route (5 chapters)
`03 → 04 → 23 → 24 → 25`

### 📚 Complete Route
docs/01 through docs/34 in order.

## Key Patterns Extracted from Claude Code

### 1. Tool Builder Pattern (`buildTool()`)

Claude Code registers tools using a builder with three-layer conditional registration:

```typescript
// Pattern extracted from docs/09-工具系统设计.md
const buildTool = <TInput, TOutput>(config: {
  name: string
  description: string
  inputSchema: ZodSchema<TInput>
  handler: (input: TInput, context: ToolContext) => Promise<TOutput>
  isEnabled?: (context: AppContext) => boolean
  requiresPermission?: PermissionLevel
}) => config

// Registration with conditions
const tools = [
  buildTool({ name: 'bash', ... }),
  buildTool({ name: 'read_file', ... }),
  buildTool({ name: 'write_file', ... }),
].filter(tool => tool.isEnabled?.(ctx) ?? true)
```

### 2. AsyncGenerator Conversation Loop (`docs/05`)

```typescript
// Pattern: state-machine conversation loop using AsyncGenerator
async function* conversationLoop(
  messages: Message[],
  tools: Tool[]
): AsyncGenerator<StreamEvent> {
  while (true) {
    const stream = await anthropic.messages.stream({
      model: 'claude-opus-4-5',
      messages,
      tools,
      system: buildSystemPrompt(),
    })

    for await (const event of stream) {
      yield event
    }

    const response = await stream.finalMessage()

    if (response.stop_reason === 'end_turn') break

    if (response.stop_reason === 'tool_use') {
      const toolResults = await executeTools(response.content)
      messages.push({ role: 'assistant', content: response.content })
      messages.push({ role: 'user', content: toolResults })
      // loop continues
    }
  }
}
```

### 3. 35-Line Minimal Store (React ↔ Non-React Bridge) (`docs/03`)

```typescript
// Pattern: tiny reactive store bridging React and imperative code
type Listener<T> = (state: T) => void

function createStore<T>(initialState: T) {
  let state = initialState
  const listeners = new Set<Listener<T>>()

  return {
    getState: () => state,
    setState: (updater: Partial<T> | ((s: T) => T)) => {
      state = typeof updater === 'function'
        ? updater(state)
        : { ...state, ...updater }
      listeners.forEach(l => l(state))
    },
    subscribe: (listener: Listener<T>) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    // React hook integration
    useStore: () => {
      const [s, setS] = React.useState(state)
      React.useEffect(() => subscribe(setS), [])
      return s
    }
  }
}
```

### 4. System Prompt Segmented Construction (`docs/04`)

```typescript
// Pattern: build system prompt in segments with cache boundaries
function buildSystemPrompt(context: AppContext): SystemPrompt {
  return [
    // Static segment — cache this (never changes)
    { type: 'text', text: CORE_INSTRUCTIONS, cache_control: { type: 'ephemeral' } },

    // Semi-static segment — cache per project
    { type: 'text', text: buildProjectContext(context.project), cache_control: { type: 'ephemeral' } },

    // Dynamic segment — never cache (changes each turn)
    { type: 'text', text: buildDynamicContext(context.session) },
  ]
}
```

### 5. Context Auto-Compact with Token Budget (`docs/06`)

```typescript
// Pattern: token budget management with auto-compact
const TOKEN_BUDGET = {
  MAX_CONTEXT: 200_000,
  COMPACT_THRESHOLD: 0.85,  // compact at 85% full
  SUMMARY_RESERVE: 2_000,
}

async function maybeCompact(messages: Message[]): Promise<Message[]> {
  const tokenCount = await countTokens(messages)

  if (tokenCount < TOKEN_BUDGET.MAX_CONTEXT * TOKEN_BUDGET.COMPACT_THRESHOLD) {
    return messages
  }

  // Summarize older messages, keep recent ones verbatim
  const keepRecent = messages.slice(-20)
  const toSummarize = messages.slice(0, -20)

  const summary = await summarize(toSummarize)
  return [
    { role: 'user', content: `Previous conversation summary:\n${summary}` },
    { role: 'assistant', content: 'Understood.' },
    ...keepRecent,
  ]
}
```

### 6. Permission 7-Step Decision Pipeline (`docs/16`)

```typescript
// Pattern: layered permission evaluation
type PermissionMode = 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan' | 'auto' | 'strict' | 'custom'

async function evaluatePermission(
  action: ToolAction,
  context: PermissionContext
): Promise<PermissionResult> {
  // Step 1: Check bypass mode
  if (context.mode === 'bypassPermissions') return { allowed: true }

  // Step 2: Check if action is always-safe
  if (isAlwaysSafe(action)) return { allowed: true }

  // Step 3: Check allowlist
  if (isAllowlisted(action, context.allowlist)) return { allowed: true }

  // Step 4: Check blocklist
  if (isBlocklisted(action, context.blocklist)) return { allowed: false, reason: 'blocklisted' }

  // Step 5: Check auto-approve rules
  if (matchesAutoApprove(action, context.rules)) return { allowed: true }

  // Step 6: Check session memory
  if (context.sessionMemory.has(actionKey(action))) return { allowed: true }

  // Step 7: Ask user
  const decision = await promptUser(action)
  if (decision.remember) context.sessionMemory.add(actionKey(action))
  return { allowed: decision.approved }
}
```

### 7. Multi-Agent Context Isolation (`docs/12`)

```typescript
// Pattern: sub-agent with isolated context
async function spawnSubAgent(task: AgentTask, parentContext: AgentContext) {
  const subContext: AgentContext = {
    // Isolated: sub-agent gets its own conversation
    messages: [],
    sessionId: generateId(),

    // Inherited: shares tools and permissions from parent
    tools: parentContext.tools,
    permissionMode: parentContext.permissionMode,

    // Scoped: limited working directory
    cwd: task.workingDir ?? parentContext.cwd,

    // Budget: prevent runaway sub-agents
    maxTurns: task.maxTurns ?? 10,
    tokenBudget: task.tokenBudget ?? 50_000,
  }

  return conversationLoop(
    [{ role: 'user', content: task.prompt }],
    subContext.tools,
    subContext
  )
}
```

### 8. withRetry for API Overload (`docs/20`)

```typescript
// Pattern: exponential backoff with overload handling
async function withRetry<T>(
  fn: () => Promise<T>,
  options = { maxAttempts: 3, baseDelay: 1000 }
): Promise<T> {
  for (let attempt = 1; attempt <= options.maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (err) {
      if (attempt === options.maxAttempts) throw err

      // Handle Anthropic 529 overloaded
      if (isOverloadError(err)) {
        const delay = options.baseDelay * Math.pow(2, attempt - 1)
        await sleep(delay + Math.random() * 1000) // jitter
        continue
      }

      // Don't retry non-retriable errors
      if (isAuthError(err) || isInvalidRequestError(err)) throw err

      throw err
    }
  }
  throw new Error('unreachable')
}
```

## Patches applied to this skill (2026-09-18, verified against repo main)

The v1 examples below (patterns 1–8) are ILLUSTRATIVE simplifications. Where they conflict with the real source analysis, trust the current chapter docs:

- **System prompt is a `string[]` with `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`**, not a 3-block cache_control array (docs/06 §二): static blocks before the marker get `cacheScope: 'global'`; MCP tools downgrade everything to `'org'`. `DANGEROUS_uncachedSystemPromptSection(name, fn, reason)` is the only per-turn cache breaker — naming forces the cost decision.
- **Conversation loop is `query()` → `queryLoop()` in `query.ts`** (1729 lines): AsyncGenerator; 7 continue-sites each tagged with a `transition` reason; pre-processing pipeline runs lightest→heaviest (tool-result budget → snip → microcompact → context collapse → autocompact) so cheap local trims can dodge the expensive API summary (docs/05 §三).
- **6 compact paths** (docs/07): time-based microcompact (cache cold → replace content), cached microcompact (cache warm → API `cache_edits`), apiMicrocompact (declarative `context_management`), auto-compact (circuit-breaker: 3 consecutive failures stop retrying — real data: one session burned 3272 failures), session-memory-compact (reuse async-extracted notes, zero API call), post-compact cleanup (main-thread-only cache clears; sub-agent compacting must NOT wipe parent caches). Compaction prompt uses `<analysis>`/`<summary>` split: model thinks first, analysis is stripped before injection (CoT-then-strip).
- **Agent context = default-isolated, explicit-shared** (docs/14 `createSubagentContext`): readFileState cloned, UI callbacks undefined, `setAppState` no-op by default, but `setAppStateForTasks` ALWAYS reaches root store (orphan PPID=1 bash zombies otherwise). Explore/Plan agents set `omitClaudeMd: true` — saves 5–15 Gtok/week across 34M+ spawns.
- **Verification Agent = adversarial prompt** (docs/15): prompt names the model's own failure patterns ("verification avoidance", "seduced by the first 80%") and pre-rebuts its rationalizations; `criticalSystemReminder_EXPERIMENTAL` re-injects the hard constraint every user turn; verdict protocol PASS/FAIL/PARTIAL.
- **Memory = 7 layers** (docs/31): CLAUDE.md hierarchy (load order REVERSE of priority — recency bias), auto-memory memdir with closed 4-type taxonomy (user/feedback/project/reference; "what NOT to save" matters — derivable-from-state info is never stored), session-memory (fixed 10-section template, double threshold: token growth AND tool-call count), relevant-memories recall (cheap sideQuery picks ≤5 files, age precomputed to keep cache bytes stable, session-level dedup by scanning messages so compact naturally re-exposes memories), auto-dream consolidation (24h + 5 sessions + file lock; rollback lock mtime on failure).
- **11 architecture patterns summary** (docs/34): DCE via `feature()`+`require()`, 35-line Store (Object.is check; React bridge is one-line `useSyncExternalStore`), tool registry (single `getAllBaseTools()` entry, 3-layer funnel compile/load/runtime, `assembleToolPool` sorts by name for cache stability), 3-tier prompt caching (global / session-memoized / per-turn volatile), 6-layer settings merge with trust boundary (project/local sources can't inject env vars pre-trust — RCE surface), permission pipeline (deny-priority; bypass-immune layer for content-ask rules and sensitive paths; denial circuit breaker 3-consec/20-total), Bridge pointer (file mtime as heartbeat: clean shutdown deletes, crash leaves), Coordinator-Agent (one env var splits same binary; worker tool list = pool MINUS coordinator tools, never two maintained lists), migration-as-code (11 independent idempotent functions, no version chain), markdown-dir-as-extension (filename=key, frontmatter=metadata, memoize+clear instead of watch; skills/commands/CLAUDE.md share the same User→Project priority).

## Applying These Patterns to Your Own Agent

### Minimal Agent Scaffold

```typescript
import Anthropic from '@anthropic-ai/sdk'

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

// 1. Define tools using builder pattern
const tools = [
  buildTool({
    name: 'read_file',
    description: 'Read a file from disk',
    inputSchema: z.object({ path: z.string() }),
    handler: async ({ path }) => fs.readFile(path, 'utf-8'),
  }),
]

// 2. Build system prompt with cache segments
const systemPrompt = buildSystemPrompt({ static: CORE_RULES, dynamic: '' })

// 3. Run conversation loop
for await (const event of conversationLoop(
  [{ role: 'user', content: userInput }],
  tools
)) {
  if (event.type === 'text') process.stdout.write(event.text)
}
```

### Thinking / Extended Reasoning Config (`docs/08`)

```typescript
// Control reasoning effort per request
type ThinkingConfig =
  | { type: 'disabled' }
  | { type: 'enabled'; budget_tokens: number }

// "ultrathink" = maximum budget
const EFFORT_LEVELS = {
  low:        { type: 'enabled', budget_tokens: 1_000 },
  medium:     { type: 'enabled', budget_tokens: 5_000 },
  high:       { type: 'enabled', budget_tokens: 10_000 },
  ultrathink: { type: 'enabled', budget_tokens: 32_000 },
} satisfies Record<string, ThinkingConfig>

const response = await anthropic.messages.create({
  model: 'claude-opus-4-5',
  thinking: EFFORT_LEVELS.ultrathink,
  messages,
})
```

## Troubleshooting

| Problem | Solution |
|---|---|
| Article links 404 | Clone the repo — all articles are in `docs/` locally |
| Code examples reference internal modules | They're illustrative patterns extracted from analysis, not runnable as-is |
| Need the actual Claude Code source | See [Anthropic's published CLI source](https://github.com/anthropics/claude-code) |
| Want to contribute an article | Open a PR to `docs/` following the existing article format |

## Start Here

```bash
# already cloned locally:
#   C:/Users/mnb77/AppData/Local/Temp/Claude-Code-Source-Study (ephemeral; re-clone if gone)
git clone https://github.com/luyao618/Claude-Code-Source-Study
cd Claude-Code-Source-Study

# Quick route: global understanding (7 chapters)
open docs/01-项目全景与四种入口形态.md

# AI engineering deep dive (9 chapters)
open docs/06-SystemPrompt与OutputStyle注入.md

# Architecture patterns summary (read last)
open docs/34-架构模式总结.md
```
