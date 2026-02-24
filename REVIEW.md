# NanoClaw Code Review

**Repository**: https://github.com/qwibitai/nanoclaw
**Reviewed at**: ~190 commits, v1.1.2

---

## Summary

NanoClaw is a lightweight AI assistant framework that runs Claude agents inside Linux containers, connecting to messenger platforms (WhatsApp, Telegram, Discord, Slack, Signal). It positions itself as a simpler, more transparent alternative to OpenClaw/Clawdbot.

The project is well-conceived and competently executed for its scope. It has a clear architectural vision — one process, filesystem-based IPC, container isolation — and mostly delivers on it. Below is a frank assessment of strengths and weaknesses.

---

## Architecture: 7/10

**What works well:**

- **Single-process design** is a genuine advantage. No message brokers, no service mesh, no orchestration overhead. For a personal/small-team assistant, this is the right call. The code is graspable in an afternoon.
- **Clean module boundaries.** `container-runner.ts` handles spawning, `container-runtime.ts` abstracts the runtime, `group-queue.ts` manages concurrency, `ipc.ts` handles inter-process communication, `db.ts` handles persistence. Each file has a single responsibility.
- **The "skills over features" contribution model** is genuinely innovative — contributors write Claude Code skill files rather than PRs that grow the codebase. This keeps the core small and pushes customization to the edges.

**What doesn't:**

- **Polling everywhere.** The message loop polls SQLite every 2 seconds (`POLL_INTERVAL`). IPC polls the filesystem every 1 second (`IPC_POLL_INTERVAL`). The scheduler polls every 60 seconds. For a personal assistant this is fine; for anything larger it wastes CPU cycles. `fs.watch`/`inotify` or SQLite's `update_hook` would be more efficient, though admittedly harder to get right cross-platform.
- **The message loop is a single `while(true)` loop** with no backpressure mechanism beyond `MAX_CONCURRENT_CONTAINERS`. If messages flood in faster than containers can process them, the queue will grow unbounded in memory (the `waitingGroups` array in `GroupQueue`). There's no high-water mark or shedding strategy.
- **Two-cursor message tracking** (`lastTimestamp` + `lastAgentTimestamp[chatJid]`) is subtle and fragile. The rollback logic on error (`previousCursor` in `processGroupMessages`) is correct but creates a state machine that's hard to reason about, especially with the parallel "pipe to active container" path in `startMessageLoop`. A dedicated outbox pattern or event-sourcing model would be clearer.

---

## Security: 8/10

This is where NanoClaw is strongest relative to competitors.

**Solid choices:**

- **Container isolation is the primary security boundary.** Each group gets its own container with explicit mount points. The main group gets the project root read-only. Non-main groups can't see other groups' data. This is fundamentally sound — OS-level isolation beats application-level permission checks.
- **Secrets passed via stdin, never written to disk or mounted as files** (`readSecrets()` in `container-runner.ts`). Secrets are deleted from the input object after writing to stdin so they don't appear in logs. Good.
- **Mount allowlist stored outside the project root** (`~/.config/nanoclaw/mount-allowlist.json`). Containers can't modify the security configuration. Symlink resolution via `realpathSync` prevents traversal attacks. Blocked patterns cover the usual suspects (`.ssh`, `.aws`, `.gnupg`, etc.).
- **Per-group IPC namespaces** prevent cross-group privilege escalation. Non-main groups can only send messages to their own chat JID. Task operations are similarly scoped.
- **Group folder validation** (`group-folder.ts`) uses a strict regex (`^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`), blocks reserved names, and checks path traversal with `path.relative`. `ensureWithinBase` is a belt-and-suspenders defense.

**Gaps:**

- **`stopContainer` passes the container name directly into a shell command** (`container-runtime.ts`): `${CONTAINER_RUNTIME_BIN} stop ${name}`. The name is constructed from `group.folder` which is regex-validated, but the pattern itself allows hyphens. The `safeName` construction in `container-runner.ts` replaces non-alphanumeric characters, which helps, but `exec()` with string interpolation is inherently risky. Using `execFile` (no shell) or `spawn` would eliminate shell injection as a class of bug.
- **No network policy on containers.** Agents run with full network access by default. A container could exfiltrate data or make arbitrary HTTP requests. Adding `--network=none` with a controlled proxy for web access would be a significant security improvement.
- **Container runs as host UID** by default (`--user ${hostUid}:${hostGid}`). This means if a container escape occurs, the attacker has the same permissions as the NanoClaw process. Running containers as a dedicated unprivileged user with minimal host filesystem access would limit blast radius.
- **No resource limits on containers.** No `--memory`, `--cpus`, or `--pids-limit` flags. A misbehaving agent can exhaust host resources.

---

## Code Quality: 7/10

**Positive:**

- **TypeScript is used idiomatically.** Interfaces for all data structures (`ContainerOutput`, `ContainerInput`, `RegisteredGroup`, etc.). Proper use of `Record<string, T>` and typed database rows. Zod is listed as a dependency for runtime validation.
- **Error handling is generally good.** The container runner catches spawn errors, parse failures, and timeouts. The message loop has a try-catch that doesn't crash on individual message failures. The IPC watcher moves failed files to an error directory rather than silently dropping them.
- **Structured logging with pino** throughout. Log levels are appropriate — `info` for normal operations, `warn` for recoverable problems, `error` for failures.
- **Test files co-located with source** (`container-runner.test.ts`, `db.test.ts`, `group-queue.test.ts`, etc.). Vitest as the test runner is a modern, fast choice.

**Negative:**

- **No runtime input validation at IPC boundaries.** `processTaskIpc` in `ipc.ts` receives arbitrary JSON from the filesystem and accesses properties with optional chaining, but there's no schema validation (despite Zod being a dependency). A malformed IPC file won't crash the process, but it could lead to silent misbehavior (e.g., creating a task with `undefined` fields).
- **Mixed `console.log` and `logger`** in several places (e.g., `findChannel` warnings in `index.ts`). Minor inconsistency but breaks structured logging.
- **The `container-runner.ts` is ~400 lines** doing volume mount construction, secret handling, output parsing, timeout management, and log writing. This file would benefit from being split — `buildVolumeMounts` alone is ~100 lines of non-trivial logic.
- **`hadStreamingOutput` is used before declaration** (referenced in the `stdout` data handler, declared later in the function body). TypeScript/V8 hoists `let` to the block scope but it's in the temporal dead zone — this works because the handler runs asynchronously after declaration, but it's confusing to read.
- **SQLite schema migration uses try-catch on ALTER TABLE** (`db.ts`). This is the SQLite equivalent of "just try it and see if it throws." It works, but a proper migration table with version tracking would be more maintainable as the schema evolves.

---

## Design Decisions Worth Noting

### The "main group" privilege model
One group is designated as `main` and gets elevated privileges: read-only access to the project root, ability to register other groups, ability to schedule tasks for any group, and ability to see all available groups. This is a pragmatic choice for a personal assistant — the admin user's group is trusted, others are sandboxed. It does mean compromise of the main group's container is high-impact.

### Filesystem-based IPC
Containers communicate with the host via JSON files in monitored directories. This is simple, debuggable (you can `ls` and `cat` the IPC directory), and requires no additional dependencies. The tradeoff is latency (1-second polling) and the potential for race conditions, though the atomic-rename pattern (`writeFileSync` to `.tmp`, then `renameSync`) mitigates the latter.

### Session continuity via stdin piping
When a new message arrives for a group with an already-running container, the message is piped to the container via an IPC file rather than spawning a new container. The container watches for `_close` sentinel files to know when to shut down. This avoids the overhead of cold-starting a container for every message but adds complexity to the lifecycle management.

### Container timeout as idle cleanup
The timeout mechanism serves double duty: it's both a safety net (kill runaway agents) and a resource management tool (clean up idle containers). After streaming output, a timeout is treated as "idle cleanup" (success), not failure. This is a reasonable design, but the dual purpose makes the code harder to follow.

---

## Dependency Assessment

| Dependency | Verdict |
|---|---|
| `@whiskeysockets/baileys` | The standard unofficial WhatsApp library. Necessary but carries risk — it reverse-engineers the WhatsApp Web protocol and can break with upstream changes. |
| `better-sqlite3` | Excellent choice. Synchronous API avoids callback complexity for a single-process app. Fast, well-maintained. |
| `pino` | Standard Node.js structured logger. Good choice. |
| `zod` v4.3.6 | Listed but underused. Should be used for IPC input validation, config parsing, and container output parsing. |
| `cron-parser` | Reasonable for cron scheduling. |
| `yaml` | Used for config, though the actual config is currently env-based. |

Notably absent: no HTTP framework (there's no web UI), no ORM (raw SQL is fine for this scale), no state management library. This is good — the project avoids unnecessary abstraction.

---

## Overall Assessment

NanoClaw is a well-scoped project that delivers on its core promise: a lightweight, understandable AI assistant framework with genuine container-based security. The codebase is clean enough that a developer can read and modify it without specialized knowledge, which is exactly its stated goal.

The main risks are:

1. **Container security hardening** — no network isolation, no resource limits, host-UID execution
2. **Input validation gaps** at IPC boundaries
3. **Scaling limitations** from polling architecture (acceptable for the target use case)
4. **WhatsApp dependency fragility** (inherent to the domain, not a code quality issue)

For a personal AI assistant running on a single machine, this is solid work. The security model is better-thought-out than most projects in this space, and the "skills over features" contribution model is a smart way to keep the core maintainable while enabling extensibility. The 13.8k stars are, for once, not undeserved.

**Rating: 7.5/10** — Well-designed for its scope, with room for hardening.
