<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "authority": {
      "revision": "2026-09-07T09:12:00Z",
      "source": "user-request"
    },
    "decided_at": "2026-09-07T09:14:00Z",
    "decided_by": "maintainer",
    "fingerprint": "sha256:b2a401c6d185649c9986fb8f920eaf71be1f23fa23a35934c90e235d728123c5",
    "scope": "implement and verify"
  },
  "delivery": {
    "repository": "session-flow",
    "target": "merged pull request"
  },
  "evidence": [
    {
      "criteria": "a verdict recorded at an earlier revision does not cover the candidate",
      "environment": "WSL Ubuntu, ext4 fixture root",
      "fingerprint": "sha256:b2a401c6d185649c9986fb8f920eaf71be1f23fa23a35934c90e235d728123c5",
      "limitations": [
        "synthetic fixture only"
      ],
      "result": "pass",
      "revision": "0c3f1d8e5b7a4c9d2e6f8a1b3c5d7e9f0a2b4c6d"
    }
  ],
  "format": 1,
  "lifecycle": "active",
  "namespace": "2b7c0f16-9d4a-4c31-8f52-6a1e7d3c5b08",
  "order": 10,
  "priority": "P1",
  "provenance": {
    "actor": "maintainer",
    "captured_at": "2026-09-06T18:02:00Z",
    "origin": "user"
  },
  "repositories": [
    {
      "name": "session-flow",
      "path": ".",
      "remote": "git@example.invalid:synthetic/session-flow.git"
    }
  ],
  "revision": 3,
  "scope_fingerprint": "sha256:b2a401c6d185649c9986fb8f920eaf71be1f23fa23a35934c90e235d728123c5",
  "seq": "SEQ-601",
  "title": "Bind release acceptance to a revision"
}
```
<!-- /session-flow:meta -->

## Original request

> release accepted a PASS from three commits ago

## Interpreted intent

Compare the recorded revision with the candidate, and make the
reuse decision explicit.

<!-- session-flow:scope -->
A stored verdict is evidence about the revision it was recorded against: release compares
the recorded revision with the candidate and refuses to infer coverage.
<!-- /session-flow:scope -->
