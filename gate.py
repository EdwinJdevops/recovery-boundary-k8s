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


class Gate:
    """Trusted service owns DB, policy, identities, clock and observations.

    The model receives only proposal ingress. This library does not authenticate callers.
    """
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute("CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, binding TEXT NOT NULL, issued INTEGER NOT NULL, expires INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0)")
        self.db.commit()

    def close(self):
        self.db.close()

    @staticmethod
    def check(action, policy, state, requester, now):
        validate(action)
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

    def approve(self, approval_id, action, policy, state, requester, approver, now, ttl=120):
        self.check(action, policy, state, requester, now)
        if approver == requester or approver not in policy.get("approvers", []):
            raise Denied("approver_denied")
        if type(ttl) is not int or not 1 <= ttl <= 300:
            raise Denied("invalid_ttl")
        binding = digest({"action": action, "policy": policy})
        with self.db:
            self.db.execute("INSERT INTO approvals(id,binding,issued,expires) VALUES (?,?,?,?)",
                            (approval_id, binding, now, now + ttl))

    def authorize(self, approval_id, raw, policy, state, requester, now):
        action = parse(raw)
        self.check(action, policy, state, requester, now)
        binding = digest({"action": action, "policy": policy})
        # Prepare bytes before claiming; no caller-controlled shell or arbitrary patch.
        patch = [{"op": "test", "path": "/metadata/uid", "value": action["uid"]},
                 {"op": "test", "path": "/metadata/resourceVersion", "value": action["resourceVersion"]},
                 {"op": "replace", "path": "/spec/replicas", "value": action["replicas"]}]
        with self.db:
            changed = self.db.execute("UPDATE approvals SET consumed=1 WHERE id=? AND binding=? AND issued<=? AND expires>? AND consumed=0",
                                      (approval_id, binding, now, now)).rowcount
            if changed != 1:
                raise Denied("approval_unavailable")
        return {"decision": "AUTHORIZED_INTENT", "action_sha256": digest(action),
                "target": {k: action[k] for k in ("cluster", "namespace", "name")},
                "content_type": "application/json-patch+json", "patch": patch}
