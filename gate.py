"""Offline authorization kernel. No cluster credentials, shell or network calls."""
import hashlib
import json
import re
import sqlite3


class Denied(ValueError):
    pass


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Denied("duplicate_key")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Denied("nonfinite")))
    except (ValueError, TypeError) as exc:
        raise Denied("invalid_json") from exc


FIELDS = {"schema", "cluster", "namespace", "name", "uid", "resourceVersion",
          "operation", "replicas", "requester", "incident"}


def validate_policy(policy):
    required = {"cluster","namespaces","max_replicas","requesters","approvers","version"}
    if type(policy) is not dict or set(policy) != required:
        raise Denied("invalid_policy")
    if (type(policy["cluster"]) is not str or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}",policy["cluster"])
            or type(policy["max_replicas"]) is not int or not 1 <= policy["max_replicas"] <= 10
            or type(policy["version"]) is not int or policy["version"] < 1):
        raise Denied("invalid_policy")
    for field in ("namespaces","requesters","approvers"):
        values = policy[field]
        if (type(values) is not list or not values
                or any(type(v) is not str or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}",v) for v in values)
                or len(set(values)) != len(values)):
            raise Denied("invalid_policy")


def validate(action):
    if type(action) is not dict or set(action) != FIELDS:
        raise Denied("invalid_fields")
    if type(action["schema"]) is not int or action["schema"] != 1:
        raise Denied("invalid_schema")
    for key in FIELDS - {"schema", "replicas"}:
        if type(action[key]) is not str or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", action[key]):
            raise Denied("invalid_identity")
    if action["operation"] != "scale_deployment":
        raise Denied("unsupported_operation")
    if type(action["replicas"]) is not int or not 1 <= action["replicas"] <= 10:
        raise Denied("invalid_replicas")


def digest(value):
    # Internal versioned ASCII schema; not a general RFC 8785 implementation.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("ascii")).hexdigest()


def conditional_patch(action):
    return [{"op": "test", "path": "/metadata/uid", "value": action["uid"]},
            {"op": "test", "path": "/metadata/resourceVersion", "value": action["resourceVersion"]},
            {"op": "replace", "path": "/spec/replicas", "value": action["replicas"]}]


class Gate:
    """Trusted service owns DB, policy, identities, clock and observations.

    The model receives only proposal ingress. This library does not authenticate callers.
    """
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute("CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, binding TEXT NOT NULL, issued INTEGER NOT NULL, expires INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)")
        self.db.execute("CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, action TEXT NOT NULL, binding TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, execution_id TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL, at INTEGER NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS approval_evidence (id TEXT PRIMARY KEY, digest TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS revocations (id TEXT PRIMARY KEY, revoked_by TEXT NOT NULL, reason TEXT NOT NULL, at INTEGER NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def check_review_evidence(self, approval_id, state):
        row = self.db.execute("SELECT digest FROM approval_evidence WHERE id=?",(approval_id,)).fetchone()
        if row is not None and row[0] != digest({k:v for k,v in state.items() if k != "observed_at"}):
            raise Denied("reviewed_evidence_changed")

    @staticmethod
    def check(action, policy, state, requester, now):
        validate(action)
        validate_policy(policy)
        if type(now) is not int:
            raise Denied("invalid_clock")
        try:
            if action["requester"] != requester or requester not in policy["requesters"]:
                raise Denied("requester_denied")
            if action["cluster"] != policy["cluster"] or action["namespace"] not in policy["namespaces"]:
                raise Denied("scope_denied")
            if type(policy["max_replicas"]) is not int or action["replicas"] > policy["max_replicas"]:
                raise Denied("replica_limit")
            if type(state["observed_at"]) is not int or not 0 <= now - state["observed_at"] <= 30:
                raise Denied("stale_observation")
            for field in ("cluster", "namespace", "name", "uid", "resourceVersion"):
                if action[field] != state[field]:
                    raise Denied("state_changed")
            if state["kind"] != "Deployment" or state["apiVersion"] != "apps/v1":
                raise Denied("wrong_resource")
        except (KeyError, TypeError) as exc:
            raise Denied("missing_evidence") from exc

    @staticmethod
    def approval_values(approval_id, action, policy, state, requester, approver, now, ttl=120):
        Gate.check(action, policy, state, requester, now)
        if approver == requester or approver not in policy.get("approvers", []):
            raise Denied("approver_denied")
        if type(ttl) is not int or not 1 <= ttl <= 300:
            raise Denied("invalid_ttl")
        binding = digest({"action": action, "policy": policy})
        return (approval_id, binding, now, now + ttl)

    def revoke(self, approval_id, principal, policy, now):
        validate_policy(policy)
        if principal not in policy["approvers"] or type(now) is not int:
            raise Denied("revocation_denied")
        with self.db:
            # Linearize with dispatch: a committed claim cannot be called cancelled.
            self.db.execute("BEGIN IMMEDIATE")
            grant = self.db.execute("SELECT issued FROM approvals WHERE id=?",(approval_id,)).fetchone()
            if grant is None or now < grant[0]:
                raise Denied("approval_unavailable")
            execution = self.db.execute("SELECT status FROM executions WHERE id=?",(approval_id,)).fetchone()
            if execution is not None and execution[0] not in ("PENDING","CANCELLED"):
                raise Denied("dispatch_already_claimed")
            self.db.execute("INSERT OR IGNORE INTO revocations VALUES (?,?,?,?)",
                            (approval_id,principal,"operator_cancelled",now))
            if execution is not None and execution[0] == "PENDING":
                self.db.execute("UPDATE executions SET status='CANCELLED',reason='approval_revoked' WHERE id=?",(approval_id,))
                self.db.execute("INSERT INTO events(execution_id,status,reason,at) VALUES (?,?,?,?)",
                                (approval_id,"CANCELLED","approval_revoked",now))
        return "REVOKED"

    def approve(self, approval_id, action, policy, state, requester, approver, now, ttl=120):
        values = self.approval_values(approval_id, action, policy, state, requester, approver, now, ttl)
        with self.db:
            self.db.execute("INSERT INTO approvals(id,binding,issued,expires) VALUES (?,?,?,?)",
                            values)

    def authorize(self, approval_id, raw, policy, state, requester, now):
        action = parse(raw)
        self.check(action, policy, state, requester, now)
        self.check_review_evidence(approval_id,state)
        binding = digest({"action": action, "policy": policy})
        # Prepare bytes before claiming; no caller-controlled shell or arbitrary patch.
        patch = conditional_patch(action)
        with self.db:
            changed = self.db.execute("UPDATE approvals SET consumed=1 WHERE id=? AND binding=? AND issued<=? AND expires>? AND consumed=0 AND NOT EXISTS (SELECT 1 FROM revocations WHERE revocations.id=approvals.id)",
                                      (approval_id, binding, now, now)).rowcount
            if changed != 1:
                raise Denied("approval_unavailable")
            # Same transaction as consumption: no consumed approval without intent.
            self.db.execute("INSERT INTO executions VALUES (?,?,?,?,?)",
                            (approval_id, json.dumps(action, sort_keys=True), binding, "PENDING", "authorized"))
            self.db.execute("INSERT INTO events(execution_id,status,reason,at) VALUES (?,?,?,?)",
                            (approval_id, "PENDING", "authorized", now))
        return {"decision": "AUTHORIZED_INTENT", "action_sha256": digest(action),
                "execution_id": approval_id,
                "target": {k: action[k] for k in ("cluster", "namespace", "name")},
                "content_type": "application/json-patch+json", "patch": patch}
