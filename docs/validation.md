# Validation — October 30, 2026

Environment: Windows, bundled Python 3.12.14; no third-party dependencies installed.

- Initial sandbox run: 13 errors because SQLite could not open temporary database files; not a passing run.
- Rerun outside sandbox: 13 tests passed in 4.798 seconds.
- Final suite after adding approval issuance-time binding: `python -m unittest -v`: 14 tests passed in 3.433 seconds, OK.
- `python demo.py`: exit 0; unsafe proposal DENIED (replica_limit), exact approved proposal AUTHORIZED_INTENT, replay DENIED (approval_unavailable).
- `python -m compileall -q gate.py fixtures.py demo.py test_gate.py`: completed without errors; combined verification command exited 0.

Tests cover exact generated conditional patch, approval replay, mutation of each action field, policy change, changed UID/resource version/kind/API version, stale observations, expiration boundary, clock before issuance, unknown/missing fields, strict integer replica types, duplicate keys/malformed JSON, caller identity, self-approval, durable consumption and eight independent concurrent connections with exactly one winner.

CI workflow runs tests, synthetic demo and compilation on Ubuntu with Python 3.12. Remote CI result must be checked independently; local success is not evidence of a successful remote run.

## Durable execution follow-up — October 30, 2026

- Final `python -m unittest -v`: **23 tests passed in 30.388 seconds**, OK, on Windows Python 3.12.14 outside the sandbox.
- Includes a real child process exiting abruptly with code 23 after the durable dispatch claim; parent confirms IN_DOUBT and blocks another dispatch.
- Adds transaction rollback fault injection, execution-time policy/expiry/state/requester checks, eight concurrent dispatcher connections with one transport call, response validation, simulated application followed by timeout, and restart replay blocking.
- `python demo_execution.py`: exit 0; IN_DOUBT persisted; restart retry DENIED; simulated write count 1.
- Compilation check for gate.py, execution.py, test_execution.py and demo_execution.py passed; combined verification command exited 0.
- The journal is additive to the existing SQLite schema. No production data migration was run.
- No kubectl, Docker, kind or k3d executable was found on the current command path. No runtime was installed.

The statements above describe the durable-journal milestone. Real API evidence added below supersedes its previously pending API-integration status; callback tests alone remain distinct from that evidence.

## Real Kubernetes integration — October 30, 2026

- Local offline suite: **27 tests passed in 7.707 seconds**, OK, Windows Python 3.12.14. Added local-context/credential-plugin checks, precondition preservation and controller-readiness validation. Compilation passed; combined verification command exited 0.
- Host inspection: Ubuntu WSL has Docker and kubectl installed, but the Docker socket was unavailable and WSL reported a user-session startup failure. No host service was modified or runtime installed.
- First integration workflow [41051654753](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41051654753) failed validation before testing because `runner.temp` was unavailable in job-level env. Fixed by initializing the dedicated kubeconfig through GITHUB_ENV inside a runner step.
- Corrected commit: [480c210](https://github.com/EdwinJdevops/recovery-boundary-k8s/commit/480c210b3a5a4f7a870f8d1f959133d502cc562e).
- Real kind workflow [41051862622](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41051862622): **success**, 1m 17s reported by GitHub. Ubuntu runner, CPython 3.12.15, kind v0.33.0, Kubernetes v1.35.8. Official binary checksum checks passed.
- Actual integration output: stale_resource_version_rejected_by_api; wrong_uid_rejected_by_api; approved_conditional_patch_applied; three_replicas_controller_ready; five_service_http_probes_passed; execution_replay_blocked.
- [Evidence artifact](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41051862622/artifacts/12974768191) uploaded successfully. Disposable cluster cleanup succeeded. No kubeconfig or credentials were uploaded.
- [Offline CI 41051862582](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41051862582): success on the same code commit.

Remaining unverified: Meta model inference, real outage diagnosis/recovery, authenticated review UI/service, production RBAC/isolation, sustained availability/load, and external customer deployment. The CI cluster tests a healthy fixture's authorized capacity change. No paid Meta API requests, cloud provisioning or AWS spending occurred; the test cluster ran inside a GitHub-hosted runner.

## Local authenticated review — October 31, 2026

- Final local suite: **41 tests passed in 19.995 seconds**, OK, Windows Python 3.12.14. Compilation passed; combined verification command exited 0.
- Added actual loopback HTTP tests for missing/invalid credentials, authenticated review/approval, no-store responses, identity-field injection, self-approval denial, Host/Origin rejection, duplicate JSON members and bounded request bodies.
- Added exact snapshot, current policy/evidence, original expiry, atomic decision/approval rollback, concurrent approval and execution-time evidence binding tests.
- Chrome smoke check loaded a synthetic review with a generated temporary test identity, displayed the target/action/policy/evidence/expiry/digest, checked the acknowledgment and returned `APPROVED by reviewer. No write was dispatched.` Credential field was cleared before capturing proof. The temporary preview process was stopped afterward.
- In-app browser was unavailable; the existing connected Chrome integration was used. This was a browser capability failure, not a review-service failure.
- Published implementation: [65a1721](https://github.com/EdwinJdevops/recovery-boundary-k8s/commit/65a1721672452b6851efae6c53a1ea263c93a31e).
- [Remote offline CI](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41203371239): success; actual job log reports **41 tests in 3.545 seconds, OK**. Both synthetic demos and compilation succeeded.
- [Reviewed kind integration](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41203371227): success on Kubernetes v1.35.8; actual log lists stale_resource_version_rejected_by_api, wrong_uid_rejected_by_api, exact_review_snapshot_approved, approved_conditional_patch_applied, three_replicas_controller_ready, five_service_http_probes_passed and execution_replay_blocked.
- [Reviewed API evidence artifact](https://github.com/EdwinJdevops/recovery-boundary-k8s/actions/runs/41203371227/artifacts/13042803652) uploaded; disposable cluster cleanup succeeded. This combines the review kernel with real API execution. The separate HTTP tests validate authentication; this is not an enterprise identity or human-attention test.

This supersedes only the earlier pending local-review status. Production SSO/MFA, revocation, public TLS hosting and privileged executor isolation remain unimplemented. The review HTTP server is explicitly a loopback prototype. No Meta inference or paid API calls were made.

## Revocation and production gates — October 31, 2026

- Full local suite: 49 tests passed in 33.000 seconds, OK. After tightening the UI eligibility flag, the focused revocation suite passed all 8 tests in 11.807 seconds. Compilation passed; combined verification commands exited 0.
- Covers revocation before authorization, durable cancellation of pending execution, refusal after dispatch claim, eight rounds of revocation/dispatch concurrency, HTTP reviewer attribution, requester denial, and malformed policy collection/number rejection.
- Added a controlled zero-backend outage plus API-enforced RBAC denial tests to the kind harness. Remote results for these additions are pending until independently checked after publication.
- Pinned the fixture base-image digest and action commits to values already resolved in prior successful CI logs. No production readiness or independent security audit is claimed.
