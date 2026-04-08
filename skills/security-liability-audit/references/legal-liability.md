# Legal Liability Reference

Legal frameworks and liability protection patterns for solo developers based in the Netherlands serving a worldwide userbase. Read this file when performing the liability portion of the audit.

**Disclaimer:** This reference provides general guidance based on publicly available legal frameworks. It is not legal advice. For binding legal opinions, consult a qualified attorney in the relevant jurisdiction.

## Table of Contents

1. [Applicable Legal Frameworks](#1-applicable-legal-frameworks)
2. [Terms of Use / EULA Checklist](#2-terms-of-use--eula-checklist)
3. [Privacy & Data Protection (GDPR)](#3-privacy--data-protection-gdpr)
4. [EU AI Act Obligations](#4-eu-ai-act-obligations)
5. [Digital Content Directive](#5-digital-content-directive)
6. [Consumer Protection](#6-consumer-protection)
7. [Liability Limitation Patterns](#7-liability-limitation-patterns)
8. [AI Output Liability](#8-ai-output-liability)
9. [Cross-Border Data Transfers](#9-cross-border-data-transfers)
10. [Change Impact Assessment](#10-change-impact-assessment)

---

## 1. Applicable Legal Frameworks

For a Netherlands-based solo dev with worldwide users:

| Framework | Scope | Key Obligation |
|---|---|---|
| **Dutch Civil Code (BW)** | Governs contracts, liability | Basis for ToS enforcement |
| **GDPR (AVG)** | EU + anyone targeting EU users | Data protection, privacy policy, DPAs |
| **EU AI Act** | AI systems in/targeting EU | Transparency, risk classification |
| **Digital Content Directive (2019/770)** | EU digital goods/services | Conformity, updates, right of withdrawal |
| **Consumer Rights Directive (2011/83/EU)** | EU consumer contracts | Information requirements, withdrawal rights |
| **Dutch Telecom Act (Tw)** | Cookie consent, e-privacy | Cookie banners, analytics consent |

**Choice of law:** Dutch law is the natural choice (developer's domicile). Specify Dutch law and Amsterdam/Rotterdam court in ToS. For B2C, consumer's local mandatory consumer protection still applies regardless of choice of law (Rome I Regulation, Art. 6).

---

## 2. Terms of Use / EULA Checklist

Every code change should be checked against whether the ToS/EULA still covers the app's behavior.

### Must-Have Clauses

| Clause | Purpose | Flag if Missing |
|---|---|---|
| **License grant** | What user can/cannot do with the software | CRITICAL |
| **"AS IS" disclaimer** | No warranty of merchantability or fitness for purpose | CRITICAL |
| **Limitation of liability** | Cap damages (typically: amount paid in last 12 months, or fixed cap) | CRITICAL |
| **AI output disclaimer** | AI-generated content is not advice, not guaranteed accurate | CRITICAL if app uses AI |
| **Data loss disclaimer** | User responsible for backups; dev not liable for data loss | HIGH |
| **Third-party service disclaimer** | Not responsible for API outages (OpenAI, Anthropic, etc.) | HIGH if app uses APIs |
| **Indemnification** | User holds dev harmless for misuse of the software | HIGH |
| **Governing law & jurisdiction** | Dutch law, Amsterdam court | HIGH |
| **Termination** | Dev can terminate access for ToS violations | MEDIUM |
| **Modification of terms** | Dev can update ToS with notice | MEDIUM |
| **Force majeure** | Not liable for events beyond control | MEDIUM |
| **Age restriction** | Minimum age (13 COPPA / 16 GDPR) | HIGH if app collects data |
| **Acceptable use** | Prohibited uses (illegal activity, abuse) | MEDIUM |
| **IP ownership** | Dev retains IP; user content remains user's | MEDIUM |

### Change-Triggered ToS Review

When a code change introduces any of the following, verify the ToS covers it:

- **New data collection** — Does the privacy policy cover this data? Is there a legal basis?
- **New AI feature** — Is the AI output disclaimer broad enough?
- **New third-party integration** — Is the third-party disclaimer broad enough?
- **New payment/subscription** — Are pricing terms clear? Refund policy?
- **User-generated content** — Content license, moderation rights, takedown?
- **New communication channel** — Email/notification consent?
- **Sharing/export features** — Who's liable for shared content?
- **Offline/local storage** — Data loss disclaimer covers this?

---

## 3. Privacy & Data Protection (GDPR)

The GDPR applies because the developer is in the Netherlands (Art. 3(1)) AND targets EU users.

### Required Documents

| Document | Required? | Flag if Missing |
|---|---|---|
| **Privacy Policy** | Yes, always | CRITICAL |
| **Cookie Policy** | Yes, if using cookies/analytics | HIGH |
| **Data Processing Agreement (DPA)** | Yes, for each sub-processor | HIGH |

### Privacy Policy Must Cover

- Identity and contact details of the controller (you)
- What personal data is collected and why
- Legal basis for each processing activity (Art. 6 GDPR):
  - Consent (opt-in, freely given, withdrawable)
  - Contract performance (needed to deliver the service)
  - Legitimate interest (with balancing test documented)
- Categories of recipients / sub-processors
- Cross-border transfers and safeguards (Section 9)
- Retention periods (how long data is kept)
- User rights: access, rectification, erasure, portability, restriction, objection
- Right to lodge complaint with Dutch DPA (Autoriteit Persoonsgegevens)
- Automated decision-making / profiling (if applicable)

### Sub-Processors (DPAs Required)

For each third-party that processes user data on your behalf, you need a DPA:

| Service | Processes User Data? | DPA Available? |
|---|---|---|
| OpenAI API | Yes (prompts may contain user content) | Yes, in their Terms |
| Anthropic API | Yes (same) | Yes, in their Terms |
| Cloud hosting (Vercel, etc.) | Yes (serves requests) | Yes, typically in Terms |
| Analytics (Plausible, etc.) | Depends on setup | Check |
| Payment (Stripe) | Yes (billing data) | Yes, in Stripe DPA |

### Change-Triggered GDPR Review

Flag when a code change:
- Collects new personal data fields
- Sends personal data to a new third party
- Changes data retention (stores longer, new storage location)
- Adds analytics/tracking
- Processes special category data (health, biometrics, political)
- Adds automated decision-making affecting users
- Changes from EU to non-EU data processing

---

## 4. EU AI Act Obligations

The EU AI Act entered into force August 2024, with phased implementation through 2026.

### Risk Classification

Desktop AI tools typically fall under **limited risk** or **minimal risk**:

| Risk Level | Examples | Obligations |
|---|---|---|
| **Unacceptable** | Social scoring, real-time biometric identification | Prohibited |
| **High** | Employment, education, credit scoring, law enforcement | Heavy regulation |
| **Limited** | Chatbots, AI content generation, emotion recognition | Transparency obligations |
| **Minimal** | AI-enabled games, spam filters | No specific obligations |

A desktop productivity tool with AI features is typically **limited risk** unless it's used for high-risk purposes.

### Transparency Obligations (Limited Risk)

- Inform users they are interacting with an AI system
- Label AI-generated content as such (text, images, audio)
- If the app generates deepfakes or synthetic media: must be labeled

### Change-Triggered AI Act Review

Flag when a code change:
- Adds new AI-powered features (classify the risk level)
- Changes AI from assistant to decision-maker (could elevate risk level)
- Adds emotion recognition or biometric processing (elevated risk)
- Generates synthetic content (labeling requirement)
- Removes or weakens AI transparency notices

---

## 5. Digital Content Directive

EU Directive 2019/770, implemented in Dutch law (BW Book 7, Title 1, Section 10a).

### Key Obligations for Digital Content

| Obligation | What It Means | Duration |
|---|---|---|
| **Conformity** | Software must match description, be fit for normal purpose | Duration of contract |
| **Updates** | Must provide security and functionality updates | Reasonable period (at least 2 years for one-time purchase) |
| **No degradation** | Updates must not reduce functionality below what was advertised | Ongoing |
| **Remedy** | If non-conforming: repair, replace, or refund | Hierarchy: repair first |

### Implications for Solo Dev

- You must provide security updates for a reasonable period after purchase
- You cannot push updates that remove features the user paid for
- If the app breaks after an update, user has right to remedy
- For subscriptions: conformity required for the entire subscription period

### Change-Triggered Review

Flag when a code change:
- Removes a feature that users rely on (potential conformity issue)
- Changes subscription terms or pricing model
- Deprecates functionality without replacement
- Breaks backward compatibility with user data

---

## 6. Consumer Protection

### Dutch/EU Consumer Rights

| Right | Requirement |
|---|---|
| **Right of withdrawal** | 14 days for digital content. Can be waived ONLY with explicit consent before delivery + acknowledgment that withdrawal right is lost. |
| **Pre-contractual information** | Total price, payment terms, functionality, compatibility, interoperability — must be clear before purchase. |
| **No hidden costs** | All costs disclosed upfront. |
| **Clear complaint procedure** | Must provide way to report issues. |

### Subscription-Specific

- Clear pricing per period
- Easy cancellation (no dark patterns)
- Renewal notices before auto-renewal
- Pro-rata refund where applicable

### Change-Triggered Review

Flag when a code change:
- Adds or changes payment/subscription logic
- Makes cancellation harder
- Adds auto-renewal without notice mechanism
- Changes what's included in a tier/plan

---

## 7. Liability Limitation Patterns

These are the standard clauses that protect a solo developer. The ToS/EULA should contain ALL of them.

### "AS IS" Disclaimer (Essential)

```
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

**Note:** Under EU consumer law, this disclaimer has limits. You cannot disclaim liability for:
- Intentional harm or gross negligence
- Death or personal injury caused by negligence
- Fraud or fraudulent misrepresentation
- Product liability (defective product causing physical harm)

But you CAN disclaim:
- Indirect/consequential damages
- Loss of data, profits, business
- AI output accuracy
- Third-party service availability
- Fitness for a particular purpose beyond what's advertised

### Liability Cap

Standard pattern: limit total liability to the greater of (a) amount paid by user in last 12 months, or (b) a fixed small amount (e.g., EUR 50). Under Dutch law, liability caps in B2C contracts are enforceable if reasonable and clearly communicated.

### Indemnification

User agrees to indemnify and hold harmless the developer for:
- User's violation of the ToS
- User's misuse of the software
- Claims arising from user's content
- User's violation of applicable laws

### Force Majeure

Not liable for failure caused by: natural disasters, war, pandemic, government action, power outage, internet disruption, third-party service failure, or any event beyond reasonable control.

---

## 8. AI Output Liability

This is the most critical liability area for AI-powered software.

### Required Disclaimers

The app and ToS must clearly state:

1. **Not professional advice**: AI output is not legal, financial, medical, or professional advice
2. **No accuracy guarantee**: AI can produce incorrect, incomplete, or misleading output
3. **User verification required**: User must independently verify AI output before relying on it
4. **No liability for AI actions**: Developer not liable for decisions made based on AI output
5. **AI limitations acknowledged**: AI may hallucinate, produce biased output, or miss context

### In-App Notice

Best practice: show a visible notice near AI-generated content. Example:
"AI-generated. May be inaccurate. Verify before use."

### Change-Triggered Review

Flag when a code change:
- Adds AI features that users might rely on for important decisions
- Removes or weakens AI output disclaimers
- Makes AI output look more authoritative (e.g., removing "AI-generated" labels)
- Adds AI to domains where errors have high consequences (finance, health, legal)
- Allows AI to take autonomous actions without user confirmation

---

## 9. Cross-Border Data Transfers

When user data leaves the EU/EEA (e.g., sent to US-based AI APIs).

### Legal Mechanisms

| Mechanism | Status | Use When |
|---|---|---|
| **EU-US Data Privacy Framework** | Active (since July 2023) | US company is DPF-certified (check list) |
| **Standard Contractual Clauses (SCCs)** | Always available | Non-DPF US companies, other countries |
| **Adequacy decision** | Country-specific | UK, Canada, Japan, etc. have adequacy |
| **Explicit consent** | Last resort | Only if informed, specific, occasional |

### Practical Checklist

For each cross-border transfer:
1. Identify which user data is transferred
2. Identify the destination country
3. Check for adequacy decision or DPF certification
4. If neither: SCCs must be in place (usually in the vendor's DPA)
5. Document the transfer in your privacy policy
6. Assess whether a Transfer Impact Assessment (TIA) is needed

### Change-Triggered Review

Flag when a code change:
- Sends user data to a new third-party service
- Changes data processing from EU to non-EU infrastructure
- Adds a new AI provider (check their DPF/SCC status)
- Stores user data in a new region

---

## 10. Change Impact Assessment

Use this decision tree for every significant code change:

```
Does this change...
  |
  ├─ Collect new personal data?
  |    └─ YES → Check: privacy policy covers it, legal basis exists,
  |              retention defined, user informed
  |
  ├─ Send data to a new third party?
  |    └─ YES → Check: DPA exists, privacy policy updated,
  |              transfer mechanism valid (DPF/SCCs/adequacy)
  |
  ├─ Add/modify AI features?
  |    └─ YES → Check: AI disclaimers in place, risk level classified,
  |              transparency notices shown, output not rendered as authoritative
  |
  ├─ Change payment/subscription logic?
  |    └─ YES → Check: pricing clear, cancellation easy, renewal notices,
  |              withdrawal right handled, ToS covers it
  |
  ├─ Remove or degrade features?
  |    └─ YES → Check: conformity obligation (users paid for this?),
  |              migration path, reasonable notice period
  |
  ├─ Handle credentials or authentication?
  |    └─ YES → Check: secrets not logged, tokens short-lived,
  |              auth failures rate-limited
  |
  ├─ Expose new endpoints or APIs?
  |    └─ YES → Check: auth required, input validated,
  |              rate limited, CORS configured
  |
  └─ Touch agent/LLM/tool-calling code?
       └─ YES → Check: Lethal Trifecta assessment,
                tool permissions scoped, output sanitized
```

### Severity for Legal/Liability Findings

| Severity | Meaning |
|---|---|
| **CRITICAL** | Missing ToS/privacy policy, active GDPR violation, secret exposure |
| **HIGH** | Missing required clause in ToS, missing DPA, AI disclaimer gap |
| **MEDIUM** | ToS doesn't cover new feature, privacy policy outdated, minor gap |
| **LOW** | Best practice not followed, improvement opportunity |
