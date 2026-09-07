<!-- session-flow:meta -->
```json
{
  "acceptance": {
    "accepted_at": "2026-09-01T09:00:00Z",
    "actor": "maintainer",
    "authority": {
      "revision": "9d2c1a4",
      "source": "_devdocs/PRD.md"
    },
    "fingerprint": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "scope": [
      "one repository"
    ]
  },
  "format": 1,
  "lifecycle": "accepted",
  "namespace": "8c3a1f6e-2d47-4b19-9a05-7e6b1c4d2f80",
  "order": 3,
  "priority": "P1",
  "provenance": {
    "auto": false,
    "imported_from": "todo/SEQUENCE.md"
  },
  "revision": 1,
  "seq": "SEQ-203",
  "title": "Rewrite the import validator"
}
```
<!-- /session-flow:meta -->

The scope was rewritten after acceptance, so the accepted fingerprint no longer matches.

<!-- session-flow:scope -->
Rewrite the import validator to reject unknown columns instead of ignoring them.
<!-- /session-flow:scope -->
