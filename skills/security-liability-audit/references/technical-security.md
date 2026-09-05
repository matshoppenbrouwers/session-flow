# Technical Security Reference

Deep security patterns for the security-liability-audit skill. Read this file when performing the technical security portion of the audit.

## Table of Contents

1. [LLM/AI Security](#1-llmai-security)
2. [Agentic Security (Lethal Trifecta)](#2-agentic-security-lethal-trifecta)
3. [Secrets Detection](#3-secrets-detection)
4. [OWASP Top 10 (Focused)](#4-owasp-top-10-focused)
5. [Dependency Supply Chain](#5-dependency-supply-chain)
6. [Webhook & Integration Security](#6-webhook--integration-security)
7. [Desktop App Security (Tauri/Electron)](#7-desktop-app-security)
8. [Confidence Filtering & False Positive Rules](#8-confidence-filtering--false-positive-rules)

---

## 1. LLM/AI Security

Source: /cso Phase 7, /security-reviewer Section 7.

### Prompt Injection

Search for user input flowing into system prompts or tool schemas. Flag when user-controlled content enters system message construction via string interpolation, template literals, or f-strings.

**Patterns to grep:**
- String interpolation near `system` prompt construction
- f-string or template literal in prompt templates containing user variables
- User content concatenated with instructions before sending to LLM

**Not prompt injection:** User content in the user-message position of a conversation (that is the intended use).

### Unsanitized LLM Output

LLM responses rendered as HTML without sanitization. Grep for unsafe HTML rendering of AI responses: innerHTML assignments, raw HTML rendering directives, or markdown-to-HTML conversion without output sanitization.

### Code Execution of LLM Output

LLM output passed to code execution mechanisms. Grep for dynamic evaluation functions processing AI responses, shell command execution with LLM-generated arguments, or dynamic imports with LLM-provided paths.

These are CRITICAL because an attacker who controls LLM output (via prompt injection) gains arbitrary code execution.

### Tool/Function Calling Without Validation

- LLM tool calls run without checking an allowed tool list
- Missing parameter validation on tool call arguments
- No rate limiting on tool invocation
- Tool results not validated before returning to LLM

### Unbounded LLM Calls (Cost/Spend Risk)

- No token or request limits per user session
- Recursive agent loops without depth limit
- Missing cost caps or budget enforcement
- User-triggered batch operations that scale LLM calls linearly

**Note:** Unbounded LLM cost is financial risk, not DoS. Never filter it as DoS.

---

## 2. Agentic Security (Lethal Trifecta)

Source: /security-reviewer.

When changed code involves agent/AI functionality, assess the Lethal Trifecta. All three present = maximum risk.

### Private Data Access
- Can the agent read credential files (~/.ssh, ~/.aws, .env)?
- Can it read source code with embedded secrets?
- Can it access databases with PII?
- Can it read other users' data?

### Untrusted Content Exposure
- Does the agent process user-provided URLs or web content?
- Does it read documents from external/shared sources?
- Does it process code from public repos or untrusted deps?
- Does it ingest data from external APIs without validation?

### Exfiltration Vectors
- Can the agent make outbound HTTP requests?
- Can it render images via URL (triggers GET)?
- Can it send messages (Slack, email, webhooks)?
- Can it write to network-accessible locations?

### Key Principle
Security boundaries must be enforced at OS/kernel level (sandbox, container, filesystem permissions), never just via model instructions. Prompt-level restrictions are not security controls.

---

## 3. Secrets Detection

Source: /cso Phase 2.

### Known Secret Prefixes in Diff

Grep changed files for these patterns:
- `AKIA[0-9A-Z]{16}` — AWS access key
- `sk-[a-zA-Z0-9]{20,}` — OpenAI/Anthropic API key
- `sk-ant-[a-zA-Z0-9-]{80,}` — Anthropic API key
- `ghp_[a-zA-Z0-9]{36}` — GitHub personal access token
- `gho_[a-zA-Z0-9]{36}` — GitHub OAuth token
- `github_pat_[a-zA-Z0-9_]{80,}` — GitHub fine-grained PAT
- `xoxb-`, `xoxp-`, `xapp-` — Slack tokens
- `sk_live_`, `sk_test_` — Stripe keys
- `rk_live_`, `rk_test_` — Stripe restricted keys
- `sq0atp-`, `sq0csp-` — Square tokens
- `SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}` — SendGrid
- `key-[a-zA-Z0-9]{32}` — Mailgun
- Passwords/tokens in assignment patterns

### .env Files

- `.env` not in `.gitignore` = CRITICAL
- `.env` tracked by git (not `.example`/`.sample`) = CRITICAL
- Secrets in `.env.example` with real values = HIGH

### Frontend Secret Exposure

Secrets in client-exposed env var prefixes:
- `VITE_` (Vite)
- `NEXT_PUBLIC_` (Next.js)
- `REACT_APP_` (CRA)
- `TAURI_` — check if exposed to webview

If a variable with these prefixes contains a secret (API key, DB URL, service role key), flag as CRITICAL.

---

## 4. OWASP Top 10 (Focused)

Source: /cso Phase 9, project /security skill, ECC security-review.

Focus on the categories most relevant to desktop + web apps with AI:

### A01: Broken Access Control
- Missing auth on routes (skip_before_action, skip_authorization, no_auth, public)
- Direct object reference (user A accessing user B's data by changing IDs)
- Missing authorization checks before sensitive operations

### A03: Injection
- **SQL:** String concatenation/interpolation in queries instead of parameterized
- **Command:** User input passed to shell invocation functions
- **Template:** Dynamic code evaluation with user input
- **Path traversal:** User input in file paths without basename/resolve check

### A05: Security Misconfiguration
- CORS wildcard (`*`) in production
- Debug mode enabled in production
- Verbose error messages with stack traces exposed to users
- Default credentials or admin passwords

### A07: Identification and Authentication
- JWT without expiration or very long expiration
- Passwords stored as plaintext or weak hash (MD5, SHA1)
- No rate limiting on authentication endpoints
- Session tokens not rotated on login

### A08: Software and Data Integrity
- Deserialization of untrusted data
- Unsigned auto-updates (for desktop apps, this is critical)
- Missing integrity checks on downloaded content

### A09: Security Logging Failures
- Authentication events not logged
- Sensitive data (passwords, tokens, PII) in logs
- Error messages expose internal details to users

### A10: SSRF
- URL construction from user input
- User-controlled URLs fetched server-side without allowlist
- Internal service reachable via user-supplied URL

---

## 5. Dependency Supply Chain

Source: /cso Phase 3.

### Vulnerability Scan
Run the appropriate audit tool:
- `npm audit` / `pnpm audit` — Node.js
- `cargo audit` — Rust
- `pip-audit` or `safety check` — Python
- If tool not installed, note as "SKIPPED" (informational, not a finding)

### Install Scripts
For Node.js: check production deps for `preinstall`/`postinstall`/`install` scripts. These run arbitrary code during install.

### Lockfile Integrity
- Lockfile exists AND tracked by git
- Missing lockfile for an app (not library) = finding

### Severity Calibration
- Critical/high CVEs in direct deps = CRITICAL/HIGH
- Install scripts in prod deps = HIGH
- Missing lockfile = HIGH
- devDependency CVEs = MEDIUM max
- No-fix-available advisories without known exploit = skip

---

## 6. Webhook & Integration Security

Source: /cso Phase 6.

### Webhook Signature Verification
For files containing webhook/hook/callback route patterns, check for signature verification (hmac, verify, digest, x-hub-signature, stripe-signature, svix). Webhook routes without signature verification = CRITICAL.

### TLS Verification
Grep for disabled TLS verification patterns (verify=false, VERIFY_NONE, InsecureSkipVerify, etc.). In prod code = HIGH.

### OAuth Scope
Check OAuth configs for overly broad scopes. Request minimum permissions.

---

## 7. Desktop App Security

Patterns specific to Tauri, Electron, and similar desktop frameworks.

### IPC Security
- Tauri `invoke` commands: are arguments validated?
- Are all commands registered explicitly (not wildcard)?
- Can the webview invoke privileged system operations?

### Webview Isolation
- Content Security Policy in webview
- Can the webview navigate to external URLs?
- Are Tauri-specific APIs restricted to necessary scope?

### Auto-Update Security
- Updates signed with a key?
- Update URL uses HTTPS?
- Signature verified before applying update?
- Can an attacker MITM the update check?

### File System Access
- Does the app access files outside its data directory?
- Are file paths from the webview validated before use in backend?
- Path traversal from frontend to backend commands

### Deep Links / Custom Protocol Handlers
- Can a malicious URL trigger app actions?
- Are deep link parameters validated?

---

## 8. Confidence Filtering & False Positive Rules

Source: /cso Phase 12.

### Confidence Labels
Report every finding and label it high, medium or low confidence; the caller decides what to act on.

### Severity Definitions
- **CRITICAL** (9-10/10): Verified exploit path exists. Could write a PoC.
- **HIGH** (8/10): Clear vulnerability pattern with known exploitation methods.
- **MEDIUM** (7/10): Likely issue but less certain. Report with caveat.
- **Below 7**: Do not report.

### Hard Exclusions (auto-discard)
1. DoS / resource exhaustion (EXCEPT LLM cost amplification)
2. Race conditions without concrete exploit path
3. Vulnerabilities only in test fixtures (not imported by non-test code)
4. Log spoofing (unsanitized input to logs)
5. SSRF where attacker controls only the path, not host/protocol
6. Regex complexity on non-untrusted input
7. Missing audit logs (absence of logging alone)
8. Insecure randomness in non-security contexts (UI element IDs)
9. Git history secrets committed AND removed in same initial PR
10. Dependency CVEs with CVSS < 4.0 and no known exploit
11. Docker issues in files named Dockerfile.dev/Dockerfile.local

### Framework-Aware Precedents
- React/Angular are XSS-safe by default. Only flag escape hatches (unsafe HTML rendering directives).
- UUIDs are unguessable. Don't flag missing UUID validation.
- Environment variables and CLI flags are trusted input.
- Client-side JS does not need auth (server's job).
- docker-compose.yml for local dev with localhost = not a finding.

### Finding Status
Mark each finding as:
- **VERIFIED** — Confirmed via code tracing
- **UNVERIFIED** — Pattern match only
- **TENTATIVE** — Below 8/10 confidence but high severity warrants mention

### Variant Analysis
When a finding is VERIFIED, grep the entire codebase for the same pattern. One confirmed SQL injection means there may be more.
