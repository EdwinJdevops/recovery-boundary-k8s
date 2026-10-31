# Exact-action review boundary

The local review prototype exposes the significant transaction data before approval: target cluster, namespace, Deployment name, UID, resourceVersion, replica count, requester, incident, full policy, observation, generated patch and expiry. The display and approval use the same immutable snapshot stored by trusted code. Approval submits only that snapshot's digest; the HTTP client cannot select an approver identity, replace the action or extend expiry.

## What is enforced

- Provisioned bearer credentials map to server-owned principal identities. Only current approvers or the original requester can read a review; only a distinct authorized approver can approve it.
- The current policy must match the reviewed policy. Current evidence must match the reviewed observation except for its refreshed observation timestamp, and freshness must still pass.
- Creating the approval, recording the reviewer/time and claiming the pending review happen in one SQLite transaction. Concurrent approvals have one winner; a failed insert rolls the decision back.
- Approval expiration remains the original review expiry; waiting to approve never extends it.
- Reviewed evidence remains bound at authorization and dispatch. An unreviewed change invalidates the action even if its target identity fields are unchanged.
- The review interface does not expose a dispatch endpoint or cluster credentials. Reviewing/approving alone does not produce a Kubernetes write.
- Current authorized approvers can revoke an approved, unused grant through `POST /reviews/{id}/revoke` with the viewed snapshot digest. Revocation is durable and attributed. It is serialized with the dispatch claim; a pending execution becomes CANCELLED. Once dispatch has been claimed, cancellation is refused rather than falsely reported as successful. The UI offers revocation only to a current approver while the execution is still revocable.

The generated review hash is an internal binding, not proof of human attention, a signature or a tamper-proof audit log. The database and policy/evidence providers remain trusted. The original library API remains available to trusted integration code; this prototype does not establish process isolation against callers with direct database or cluster access.

## Local demo

Set `RECOVERY_REVIEW_TOKEN` through your local secret mechanism to an independently generated high-entropy token of at least 32 characters. Do not paste credentials into the chat, commit them or put them in a URL. Then run `python demo_review.py` and open `http://127.0.0.1:8765/`. Enter the token in the password field, load `demo-review`, inspect it, acknowledge its scope and approve. The synthetic review expires after five minutes; restarting creates a fresh temporary review/database.

The service binds only 127.0.0.1. Tokens are not stored in browser storage, cookies, logs or the database. Authentication uses an Authorization header; cross-origin requests and unexpected Host values are rejected. Responses use no-store and a restrictive content security policy. The server does not provide CORS or public binding.

## Production gaps

This is local prototype authentication, not SSO, MFA, enterprise identity verification or a remotely deployed approval service. It uses Python's standard-library HTTP server, which Python explicitly does not recommend for production. No public TLS ingress, rate limiting, identity-token lifecycle/revocation, signed audit storage or privileged executor isolation is implemented. Approval revocation is separate from identity-token revocation. Do not expose this server through a tunnel or public interface. Loopback does not protect against a compromised local OS or malicious local process.

Meta model inference is not implemented by this review flow. The browser demonstration uses synthetic fixture evidence, while the separate kind integration exercises the review kernel before a real conditional API write. HTTP authentication tests use generated, temporary identities and actual loopback requests.

Primary design references: [OWASP transaction authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html), [Python 3.12 HTTP server limits](https://docs.python.org/3.12/library/http.server.html).
