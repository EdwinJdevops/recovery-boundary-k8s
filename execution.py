"""Durable dispatch orchestration. Transport is a trusted injected adapter.

No transport, model, network call or credential discovery is enabled by default.
"""
import json
from gate import Denied, digest, conditional_patch


class Executor:
    def __init__(self, gate):
        self.gate = gate

    def receipt(self, execution_id):
        row = self.gate.db.execute("SELECT status,reason FROM executions WHERE id=?", (execution_id,)).fetchone()
        if row is None:
            raise Denied("unknown_execution")
        events = self.gate.db.execute("SELECT sequence,status,reason,at FROM events WHERE execution_id=? ORDER BY sequence", (execution_id,)).fetchall()
        return {"execution_id": execution_id, "status": row[0], "reason": row[1],
                "events": [dict(zip(("sequence", "status", "reason", "at"), event)) for event in events]}

    def _finish(self, execution_id, status, reason, now):
        with self.gate.db:
            changed = self.gate.db.execute("UPDATE executions SET status=?,reason=? WHERE id=? AND status='IN_DOUBT'", (status, reason, execution_id)).rowcount
            if changed != 1:
                raise Denied("invalid_transition")
            self.gate.db.execute("INSERT INTO events(execution_id,status,reason,at) VALUES (?,?,?,?)", (execution_id, status, reason, now))
        return self.receipt(execution_id)

    @staticmethod
    def valid_response(response, action):
        # Evidence of the returned desired state, not workload health or causality.
        try:
            meta = response["metadata"]
            return (response["apiVersion"] == "apps/v1" and response["kind"] == "Deployment"
                    and all(meta[k] == action[k] for k in ("namespace", "name", "uid"))
                    and type(meta["resourceVersion"]) is str and bool(meta["resourceVersion"])
                    and type(response["spec"]["replicas"]) is int
                    and response["spec"]["replicas"] == action["replicas"])
        except (KeyError, TypeError):
            return False

    def dispatch(self, execution_id, policy, state, requester, now, transport):
        row = self.gate.db.execute("SELECT action,binding,status FROM executions WHERE id=?", (execution_id,)).fetchone()
        if row is None:
            raise Denied("unknown_execution")
        if row[2] != "PENDING":
            raise Denied("execution_already_claimed")
        action = json.loads(row[0])
        self.gate.check(action, policy, state, requester, now)
        self.gate.check_review_evidence(execution_id,state)
        if digest({"action": action, "policy": policy}) != row[1]:
            raise Denied("policy_changed")
        request = {"target": {k: action[k] for k in ("cluster", "namespace", "name")},
                   "content_type": "application/json-patch+json", "patch": conditional_patch(action)}
        # Persist ambiguity BEFORE entering transport. Crash at any later point
        # cannot make a restart retry. Fresh evidence/approval is a separate action.
        with self.gate.db:
            changed = self.gate.db.execute("UPDATE executions SET status='IN_DOUBT',reason='dispatch_claimed' WHERE id=? AND status='PENDING' AND EXISTS (SELECT 1 FROM approvals WHERE approvals.id=executions.id AND consumed=1 AND issued<=? AND expires>?)", (execution_id, now, now)).rowcount
            if changed != 1:
                raise Denied("dispatch_unavailable")
            self.gate.db.execute("INSERT INTO events(execution_id,status,reason,at) VALUES (?,?,?,?)", (execution_id, "IN_DOUBT", "dispatch_claimed", now))
        try:
            response = transport(request)
        except Exception:
            # Never store exception strings: adapters may include credentials.
            return self._finish(execution_id, "IN_DOUBT", "transport_error", now)
        if not self.valid_response(response, action):
            return self._finish(execution_id, "IN_DOUBT", "unverified_response", now)
        return self._finish(execution_id, "APPLIED_RESPONSE", "desired_state_returned", now)
