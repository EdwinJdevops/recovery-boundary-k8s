# Production-readiness assessment

Assessment started October 31, 2026. **Release decision: not ready for production.** Passing fixture tests is necessary but insufficient. No claim of customer adoption, commercial validation, production SLOs or reliable model diagnosis has been established.

## Concrete problem and current scope

An approved automation can become unauthorized before dispatch, or lose its response after a write. Recovery Boundary constrains one operation: a conditional Deployment replica change, bound to exact review, policy, evidence and expiry. It preserves ambiguous execution outcomes instead of blindly retrying. This addresses a specific control problem; it is not a general autonomous SRE.

| Gate | Current evidence | Remaining release requirement |
|---|---|---|
| Strict input and policy validation | Duplicate-key rejection, exact action schema, typed policy collections and numeric limits; local tests | Versioned API compatibility and configuration migration policy |
| Exact, independent review | Immutable snapshots; local provisioned identities; HTTP and browser checks | Production identity provider, MFA/session lifecycle and verified operator roles |
| Expiry and revocation | Original expiry preserved; durable revocation serialized with dispatch; concurrency tests | Operational procedures and production identity authorization for cancellation |
| Dispatch crash safety | Durable intent and claim; process-exit/timeout/replay tests | Reconciliation workflow, backup/restore validation, storage failure testing and measured throughput |
| Target permissions | Named-Deployment get/patch Role and API denial tests in disposable kind | Isolated worker credentials; no admin impersonation in production; admission constraints for fields that RBAC cannot restrict |
| Recovery effectiveness | Controlled zero-backend outage harness with separate client, controller and HTTP checks | Verified remote result; broader failure corpus and actual operator feedback |
| Model usefulness | No genuine model-inference evidence yet | Authorized Meta access, real runs, held-out incident evaluation and deterministic baseline comparison |
| Runtime and network isolation | Adapter only permits the dedicated local kind context; UI binds loopback | Supported server/runtime, TLS ingress, network isolation, resource limits and deployment manifests for the real service |
| Observability and incident response | Persisted execution state/reasons and reviewer/revoker attribution | Operational metrics, alerting, protected audit export, retention and on-call runbooks |
| Supply chain | Official tool checksums; Kubernetes/base-image digests and tested action commit pins | Update process, provenance verification and vulnerability review of shipped components |
| Independent review | Focused implementation review and reproducible regression tests | Independent security/design review; no completed external audit is claimed |

## Acceptance boundaries

- SQLite claim/revocation ordering is a single-database guarantee. It is not distributed exactly-once delivery.
- A committed dispatch claim cannot be revoked safely by pretending the write was cancelled. The API refuses that request; outcome investigation is separate.
- RBAC limits object/verb/namespace scope. Permission to patch a Deployment still permits other fields if the worker is compromised. The deterministic adapter restricts fields in trusted code, but production needs additional enforcement and process isolation.
- The review HTTP server remains a loopback prototype based on Python http.server, not a production hosting stack.
- A deliberately injected outage demonstrates a recovery mechanism on known fixtures. It does not demonstrate diagnosis of unknown customer incidents or sustained availability.
- Paid Meta calls and cloud provisioning remain disabled. No inaccessible integration is represented as working.

## Engineering priorities after this change

Obtain evidence of actual user pain from platform operators; evaluate Meta-generated proposals against a small, labeled incident corpus; deploy the trusted boundary with real identity and isolated executor credentials; complete storage recovery and independent review gates before any production release. Keep each claim linked to a reproducible artifact and a stated limit.
