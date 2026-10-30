# Validation — October 30, 2026

Environment: Windows, bundled Python 3.12.14; no third-party dependencies installed.

- Initial sandbox run: 13 errors because SQLite could not open temporary database files; not a passing run.
- Rerun outside sandbox: 13 tests passed in 4.798 seconds.
- Final suite after adding approval issuance-time binding: `python -m unittest -v`: 14 tests passed in 3.433 seconds, OK.
- `python demo.py`: exit 0; unsafe proposal DENIED (replica_limit), exact approved proposal AUTHORIZED_INTENT, replay DENIED (approval_unavailable).
- `python -m compileall -q gate.py fixtures.py demo.py test_gate.py`: completed without errors; combined verification command exited 0.

Tests cover exact generated conditional patch, approval replay, mutation of each action field, policy change, changed UID/resource version/kind/API version, stale observations, expiration boundary, clock before issuance, unknown/missing fields, strict integer replica types, duplicate keys/malformed JSON, caller identity, self-approval, durable consumption and eight independent concurrent connections with exactly one winner.

CI workflow runs tests, synthetic demo and compilation on Ubuntu with Python 3.12. Remote CI result must be checked independently; local success is not evidence of a successful remote run.

Not tested: live Kubernetes API server or admission behavior, actual cluster recovery, Meta model inference, authenticated review service, deployment or browser UI. No paid API requests, cloud provisioning or AWS spending occurred.
