# Architecture Decision Records

## ADR-001: Docker for Command Sandboxing

**Status**: Accepted
**Date**: 2026-02

### Context
MiniClaw needs to execute arbitrary user commands safely. Options considered:
1. chroot jails
2. Linux namespaces directly
3. Docker containers
4. Firecracker microVMs

### Decision
Use Docker containers with strict security flags.

### Rationale
- **docker-py**: Mature Python SDK, well-documented
- **Familiar**: Most developers understand Docker
- **Sufficient isolation**: For educational use case, Docker isolation is adequate
- **Easy cleanup**: Containers can be removed instantly
- **Resource limits**: Built-in support for memory/CPU/PIDs limits

### Consequences
- Requires Docker daemon on host
- ~100ms overhead for container creation
- Must maintain custom runner image

---

## ADR-002: Command Allowlist over Blocklist

**Status**: Accepted
**Date**: 2026-02

### Context
Need to restrict which commands can be executed in the sandbox.

### Decision
Use explicit allowlist (`ALLOWED_COMMANDS`) instead of blocklist.

### Rationale
- **Fail-closed**: Unknown commands are blocked by default
- **Auditable**: Easy to review what's permitted
- **Defense in depth**: Even if container escapes, command restrictions apply

### Consequences
- Must explicitly add each new command
- Users may request commands not on the list
- `sh -c` requires special handling

---

## ADR-003: No Shell Interpretation (shell=False)

**Status**: Accepted
**Date**: 2026-02

### Context
Commands could be executed via `shell=True` (interpret shell syntax) or `shell=False` (direct exec).

### Decision
Always use `shell=False` with `shlex.split()` to parse commands into argv.

### Rationale
- **Prevents injection**: No shell metacharacter interpretation
- **Explicit parsing**: We control exactly what runs
- **Consistent behavior**: Same parsing rules everywhere

### Consequences
- Pipes, redirections, `&&` chains don't work
- Users must use `sh -c "..."` for shell features (validated separately)
- Some convenience lost for power users

---

## ADR-004: web_fetch Runs on Host

**Status**: Accepted
**Date**: 2026-02

### Context
The web_fetch tool needs network access. Options:
1. Run inside container with selective network
2. Run on host with SSRF protection

### Decision
Run web_fetch on the host Python process with SSRF protection.

### Rationale
- **Container stays air-gapped**: No network exceptions needed
- **SSRF protection**: Validate DNS resolution before connecting
- **Simpler networking**: No Docker network configuration

### Consequences
- Must implement thorough SSRF protection
- Host IP stack is exposed to responses
- Redirect following requires validation

---

## ADR-005: SSRF Protection via DNS Pre-Resolution

**Status**: Accepted
**Date**: 2026-02

### Context
web_fetch must not connect to internal/private IPs.

### Decision
Resolve DNS first, validate IP against blocklist, then connect.

### Rationale
- **Catches DNS rebinding**: URL host is validated at fetch time
- **Catches redirects**: Event hook validates redirect URLs
- **Comprehensive blocklist**: All RFC 1918/5735 ranges covered

### Blocked Networks
- 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- 169.254.0.0/16 (link-local)
- 0.0.0.0/8, 100.64.0.0/10 (special)
- IPv6 equivalents (::1, fc00::/7, fe80::/10)

### Consequences
- Cannot fetch from legitimate internal services
- DNS resolution adds latency
- httpx event hooks required for redirect validation

---

## ADR-006: One Container Per Session

**Status**: Accepted
**Date**: 2026-02

### Context
How to manage container lifecycle across user sessions.

### Decision
Create one container per `chat_id`, keep alive during session, destroy on `/reset`.

### Rationale
- **Isolation**: Each user gets separate filesystem
- **Performance**: Container reuse avoids startup latency
- **Clean slate**: `/reset` gives fresh environment

### Naming Convention
`miniclaw-runner-{chat_id}`

### Consequences
- Must track container state per session
- Orphan containers possible if process crashes
- `cleanup_all()` needed for maintenance

---

## ADR-007: Circuit Breakers in Agent Loop

**Status**: Accepted
**Date**: 2026-02

### Context
LLM might loop infinitely calling tools.

### Decision
Implement three circuit breakers:
1. **max_turns** (10): Hard limit on iterations
2. **repeated_call** (2): Same tool call twice = stop
3. **consecutive_errors** (3): Three failures in a row = stop

### Rationale
- **Cost control**: Prevents runaway API usage
- **UX**: Better to stop than spin forever
- **Debuggable**: Stop reason is reported

### Consequences
- May stop prematurely on legitimate long tasks
- Users need to understand circuit breaker messages

---

## ADR-008: Groq + Llama 3.1 70B as LLM Backend

**Status**: Accepted
**Date**: 2026-02

### Context
Need an LLM with tool calling support.

### Decision
Use Groq API with `llama-3.1-70b-versatile` model.

### Rationale
- **Free tier**: Good for educational project
- **Fast inference**: Groq's LPU gives low latency
- **Tool calling**: Native function calling support
- **Open weights**: Llama is open source

### Consequences
- Dependent on Groq service availability
- May need to adjust prompts for model quirks
- Rate limits on free tier

---

## ADR-009: Alpine as Runner Base Image

**Status**: Accepted
**Date**: 2026-02

### Context
Need a minimal base image for the sandbox.

### Decision
Use Alpine Linux 3.19 with explicit package list.

### Rationale
- **Small size**: ~5MB base
- **Security**: Minimal attack surface
- **Explicit tools**: We install only what's needed

### Removed Tools
- wget (default in Alpine)
- curl
- nc (netcat from busybox)

### Consequences
- Must explicitly remove network tools
- Some GNU coreutils behaviors differ
- apk for package management

---

## ADR-010: JSONL Structured Logging

**Status**: Accepted
**Date**: 2026-02

### Context
Need observability for debugging and auditing.

### Decision
Use JSONL format for all logs with structured fields.

### Fields
- `container_id`, `chat_id`
- `argv`, `command`
- `exit_code`, `duration_ms`
- `truncated`, `stopped_reason`

### Rationale
- **Parseable**: Easy to grep, jq, analyze
- **Structured**: Fields are consistent
- **Auditable**: Full command history

### Consequences
- Logs are not human-readable without tooling
- Must ensure no sensitive data in logs
