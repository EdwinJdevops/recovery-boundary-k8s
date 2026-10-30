# Recovery Boundary

An original, offline Kubernetes recovery authorization prototype for the Meta Global AI Developer Hackathon. A model may propose recovery; a deterministic gate decides whether an exact, reviewed action can become an authorized intent.

## Run locally

Python 3.12; standard library only. No package installation, API keys, cloud account or cluster required.

```sh
python -m unittest -v
python demo.py
```

The demo uses explicitly synthetic proposals. It denies an excessive replica count, authorizes the reviewed proposal once, then denies replay. It is not evidence of a live or recorded Meta model invocation.

## Implemented boundary

- Only `scale_deployment`; exact schema; bounded integer replicas; no shell commands, arbitrary patches or unknown fields.
- Trusted policy scopes requester, cluster, namespaces, replica ceiling and independent approver.
- Approval binds every action field and the entire policy. Policy change requires new approval.
- Target identity includes cluster, namespace, name, UID and opaque resourceVersion. Observations must be no older than 30 seconds and not from the future.
- SQLite conditional update atomically consumes an unexpired approval once, across independent connections; consumption survives reopening.
- Output is a JSON Patch with UID and resourceVersion tests before replacing replicas. A future executor must submit the exact patch to the exact cluster and Deployment using `application/json-patch+json`; never strip preconditions or retry blindly.

The restricted schema contains only ASCII strings and integers. Sorted compact JSON is an internal versioned hash encoding, not a general cross-language canonicalization standard.

## Trust and limits

This is a library and offline demonstration, not a deployed or bypass-resistant enforcement service. Authentication, policy, observation, clock and database access are trusted inputs owned by a future service; the model must not control them or call `approve`. The model must have no cluster write credentials. A compromised service or database is outside this prototype's boundary.

Authorization consumes approval before returning an intent. A crash may therefore lose an intent; do not reset consumed approvals automatically. An intent is not evidence of an attempted or successful Kubernetes mutation. There is no executor, durable execution journal, signed capability, revocation endpoint, API server integration, RBAC deployment, health proof or outcome reconciliation yet. Separate-resource facts can change after observation; the patch only conditions the target Deployment. Resource versions must be compared for equality, not numerically.

## Meta integration status

Not connected or tested. No paid Meta calls, payments or AWS resources were used. Planned integration: a Meta model interprets incident evidence into this constrained proposal schema; the same gate remains independent. Until a genuine permitted Meta model run is integrated and demonstrated, this is not a complete hackathon submission.

## Originality

Code written fresh on October 30, 2026. Existing repositories were inspected for scope; no code was copied from them. AI coding assistance: OpenAI Codex. Python's standard library is used. No third-party runtime dependencies or model weights are bundled. No open-source license grant has been selected for this original code yet.

See [rules verification](docs/rules.md) and [validation](docs/validation.md).
