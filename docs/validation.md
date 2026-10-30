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
