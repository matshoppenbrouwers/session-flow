---
name: security-liability-audit
description: >
  Combined technical security and legal liability audit for code changes.
  Covers LLM/AI security, OWASP Top 10, agentic security (Lethal Trifecta),
  secrets detection, desktop app security, dependency supply chain, AND
  legal/liability risk (GDPR, EU AI Act, ToS/EULA coverage, data protection,
  consumer rights, cross-border transfers). Designed for solo developers in
  the EU serving a worldwide userbase. Use when: completing a feature
  implementation, before release, after any change that touches security-sensitive
  areas, AI features, data handling, payment logic, or user-facing terms.
  Triggers on "/security-liability-audit" or as a step in session-post-implementation.
---

# Security & Liability Audit

Perform a combined technical security and legal liability review of recent code changes.

**Announce:** "Running security & liability audit on recent changes."

## Scope Detection

Determine what to audit:

1. **If dispatched by session-post-implementation**: audit uncommitted + recent commit changes
2. **If invoked standalone**: use `git diff` (uncommitted) or `git diff HEAD~1` (last commit)
3. **If argument provided** (e.g., `HEAD~3..HEAD`): use that range

Run `git diff --stat` to get the list of changed files. Read full files for context around changes.

## Part A: Technical Security

Read `references/technical-security.md` for the full pattern library. Apply these checks to changed files:

### A1: Secrets Scan
Grep changed files for known secret prefixes (AWS, OpenAI, GitHub, Slack, Stripe patterns). Check .env handling and frontend env var exposure.

### A2: LLM/AI Security
If changes touch LLM/AI code: check for prompt injection vectors, unsanitized AI output rendering, code execution of AI responses, unvalidated tool calls, and unbounded LLM cost exposure.

### A3: Agentic Security
If changes touch agent/tool/MCP code: run the Lethal Trifecta assessment (private data access + untrusted content + exfiltration vectors). Verify security boundaries are OS-enforced, not prompt-enforced.

### A4: OWASP Checks
Apply focused OWASP Top 10 checks to changed code: injection (SQL, command, path traversal), broken access control, security misconfiguration, authentication issues, data integrity, SSRF.

### A5: Desktop App Security
If changes touch Tauri/IPC/webview code: check IPC argument validation, webview isolation, auto-update signing, filesystem access scoping, deep link parameter validation.

### A6: Dependency Supply Chain
If dependencies changed: run audit tool, check for install scripts in prod deps, verify lockfile tracked.

### A7: Webhook/Integration Security
If changes touch webhook or integration code: verify signature checking, TLS verification, OAuth scope minimization.

## Part B: Liability & Legal

Read `references/legal-liability.md` for the full legal framework reference. Apply these checks to the nature of the changes:

### B1: ToS/EULA Coverage
Does the change introduce behavior not covered by the current Terms of Use?
- New data collection not mentioned in privacy policy
- New AI feature without adequate disclaimer
- New third-party integration without pass-through disclaimer
- New payment/subscription logic without clear terms
- Feature removal that may violate conformity obligations

### B2: Privacy & GDPR
Does the change affect personal data handling?
- New personal data fields collected
- Data sent to a new third party (DPA needed?)
- Changed retention periods or storage locations
- New analytics/tracking added
- Cross-border transfer to non-EU processor

### B3: AI Liability
Does the change affect how AI output is presented or used?
- AI output shown without disclaimer
- AI output made to look more authoritative
- AI used in high-consequence domains (finance, health, legal)
- AI taking autonomous actions without user confirmation
- Transparency notices missing or weakened

### B4: Consumer Protection
Does the change affect the commercial relationship?
- Subscription/payment changes without clear disclosure
- Cancellation flow made harder
- Feature degradation for existing users
- Auto-renewal without notice mechanism

### B5: Data Transfer
Does the change introduce new cross-border data flows?
- New AI provider (check DPF/SCC status)
- New cloud service in non-EU jurisdiction
- User data sent to new endpoint

## Confidence Filtering

Apply confidence-based filtering before reporting. See `references/technical-security.md` Section 8 for the full ruleset.

- **Technical findings**: report every finding and label it high, medium or low confidence; the caller decides what to act on. Hard exclusions apply.
- **Legal findings**: flag as ADVISORY (not bugs but risk gaps). No confidence gate, but label uncertainty clearly.

## Output Format

### Technical Findings

```
TECHNICAL SECURITY FINDINGS
============================
#   Sev    Conf   Status      Category         Finding                    File:Line
--  ----   ----   ------      --------         -------                    ---------
1   CRIT   9/10   VERIFIED    Secrets          API key in source          src/api.ts:42
2   HIGH   8/10   UNVERIFIED  LLM Security     User input in sys prompt   pkb/agent.py:88
```

For each finding include: severity, confidence, status, category, description, exploit scenario (for technical), and recommendation.

### Legal/Liability Findings

```
LIABILITY ADVISORIES
====================
#   Priority   Category         Advisory                              Action Required
--  --------   --------         --------                              ---------------
1   HIGH       GDPR             New data field not in privacy policy  Update privacy policy
2   HIGH       AI Liability     AI feature lacks output disclaimer    Add disclaimer
3   MEDIUM     Consumer         Subscription change needs notice      Add renewal notice
```

For each advisory include: priority, category, what's missing, what to do, and which document to update (ToS, Privacy Policy, in-app notice).

### Summary

```
AUDIT SUMMARY
=============
Technical:  N critical, N high, N medium
Liability:  N high, N medium, N low advisories
Verdict:    PASS / NEEDS FIXES / NEEDS LEGAL REVIEW
```

Verdicts:
- **PASS** — No critical/high technical findings AND no high liability advisories
- **NEEDS FIXES** — Critical or high technical findings exist
- **NEEDS LEGAL REVIEW** — High liability advisories exist (recommend legal counsel review)
- **BLOCKED** — Both technical and legal issues found

## Escalation

If the audit finds issues beyond what code changes can fix (e.g., ToS needs rewriting, DPA needed with a vendor), clearly state:

```
ESCALATION: [Category]
ACTION: [What needs to happen]
WHO: [Developer / Legal counsel / Third-party vendor]
URGENCY: [Before release / Next iteration / When convenient]
```

## Important Rules

- **No code changes.** This audit produces findings and recommendations only.
- **Confidence labels on technical findings.** Report every finding and label it high, medium or low confidence, so the caller decides what to act on.
- **Legal findings are advisories, not bugs.** Label them clearly as risk gaps.
- **Legal disclaimer.** Always end with: "This audit is not legal advice. For binding legal opinions on liability, GDPR compliance, or contract terms, consult a qualified attorney."
- **Framework-aware.** Know your framework's built-in protections.
- **Solo dev perspective.** Prioritize findings by actual risk to a solo developer with limited resources. A theoretical GDPR fine matters less than a real secret leak.

## When to Recommend /cso

If the audit discovers systemic security concerns (not just point findings in the diff), recommend running a full `/cso` audit. Examples:
- Multiple secret pattern matches suggesting systemic secret management issues
- No webhook signature verification anywhere in the codebase
- Complete absence of auth on public endpoints
- Supply chain concerns (many unaudited deps with install scripts)

Chain context: see `references/workflow-overview.md`.
