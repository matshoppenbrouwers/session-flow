<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "accepted_at": "2026-09-06T14:20:00Z",
    "actor": "maintainer",
    "authority": {
      "revision": "2026-09-06T14:18:00Z",
      "source": "user-request"
    },
    "fingerprint": "sha256:7b3b92ad7bfe192f14ba105e9abeb626c3ca842c0c8338972022e058eb940d67",
    "scope": [
      "implement",
      "create-pr"
    ]
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "evidence": [
    {
      "criteria": "A reflowed paragraph retains acceptance",
      "environment": "python3.12 on ext4",
      "fingerprint": "sha256:7b3b92ad7bfe192f14ba105e9abeb626c3ca842c0c8338972022e058eb940d67",
      "limitations": [
        "synthetic fixture only"
      ],
      "result": "pass",
      "revision": "0c3f1d8e5b7a4c9d2e6f8a1b3c5d7e9f0a2b4c6d"
    }
  ],
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "6f1d4a02-3c58-4a1e-9b77-0c2f8d5e4411",
  "order": 20,
  "priority": "P1",
  "provenance": {
    "captured_at": "2026-09-05T11:40:00Z",
    "captured_by": "session-research-design",
    "source": "user"
  },
  "references": [
    {
      "commit": "9f2c1ab7d4e6f8091b2c3d4e5f60718293a4b5c6",
      "path": "seq-002/spec.md",
      "role": "behaviour"
    },
    {
      "commit": "9f2c1ab7d4e6f8091b2c3d4e5f60718293a4b5c6",
      "path": "seq-002/plan.md",
      "role": "criteria"
    }
  ],
  "repositories": [
    {
      "name": "session-flow",
      "path": ".",
      "remote": "git@example.invalid:synthetic/session-flow.git"
    }
  ],
  "revision": 5,
  "scope_checks": [
    {
      "actor": "maintainer",
      "at": "2026-09-06T14:20:00Z",
      "authority": {
        "revision": "2026-09-06T14:18:00Z",
        "source": "user-request"
      },
      "fingerprint": "sha256:7b3b92ad7bfe192f14ba105e9abeb626c3ca842c0c8338972022e058eb940d67",
      "kind": "accepted",
      "previous_fingerprint": null,
      "scope": [
        "implement",
        "create-pr"
      ]
    }
  ],
  "seq": "SEQ-002",
  "title": "Bind acceptance to a normalized scope fingerprint"
}
```
<!-- /session-flow:meta -->

# SEQ-002 — Bind acceptance to a normalized scope fingerprint

## Original request

"Status updates should not keep throwing away the acceptance I just gave."

## Approach

A whitespace-only reflow of SEQ-002, still naming the fingerprint accepted at revision 4.

<!-- session-flow:scope -->
Acceptance is a normalized   fingerprint of:

-  the scope text and the
	repository bindings
- the required
  delivery target
- the work-root commits of the referenced behaviour and criteria documents   

Reflowing a paragraph does not invalidate acceptance;
changing what the scope asks for does.
<!-- /session-flow:scope -->
