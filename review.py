"""Trusted review snapshots. Principal identities must come from authentication."""
import json
import re
import sqlite3
from gate import Gate, Denied, digest, conditional_patch, parse, validate_policy


class Reviews:
    def __init__(self, gate):
        self.gate = gate
        gate.db.execute("CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL, approver TEXT, decided_at INTEGER)")
        gate.db.commit()

    def create(self, review_id, raw, policy, state, requester, now, ttl=120):
        if type(review_id) is not str or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}",review_id):
            raise Denied("invalid_review_id")
        action = parse(raw)
        Gate.check(action,policy,state,requester,now)
        if type(ttl) is not int or not 1 <= ttl <= 300:
            raise Denied("invalid_ttl")
        snapshot = {"schema":1,"review_id":review_id,"action":action,"policy":policy,
                    "observation":state,"patch":conditional_patch(action),
                    "created_at":now,"expires_at":now+ttl}
        encoded = json.dumps(snapshot,sort_keys=True,allow_nan=False)
        with self.gate.db:
            self.gate.db.execute("INSERT INTO reviews(id,snapshot,digest,status) VALUES (?,?,?,'PENDING')",
                                 (review_id,encoded,digest(snapshot)))
        return digest(snapshot)

    def _row(self, review_id):
        row = self.gate.db.execute("SELECT snapshot,digest,status,approver,decided_at FROM reviews WHERE id=?",(review_id,)).fetchone()
        if row is None:
            raise Denied("review_unavailable")
        snapshot = json.loads(row[0])
        if digest(snapshot) != row[1]:
            raise Denied("snapshot_integrity_error")
        return snapshot, row

    def view(self, review_id, principal, current_policy):
        validate_policy(current_policy)
        snapshot, row = self._row(review_id)
        if principal != snapshot["action"]["requester"] and principal not in current_policy.get("approvers",[]):
            raise Denied("review_access_denied")
        revoked = self.gate.db.execute("SELECT revoked_by,reason,at FROM revocations WHERE id=?",(review_id,)).fetchone()
        execution = self.gate.db.execute("SELECT status FROM executions WHERE id=?",(review_id,)).fetchone()
        return {"snapshot":snapshot,"snapshot_sha256":row[1],"status":"REVOKED" if revoked else row[2],
                "approver":row[3],"decided_at":row[4],
                "execution_status":execution[0] if execution else None,
                "can_revoke":principal in current_policy["approvers"] and row[2]=="APPROVED" and not revoked and (execution is None or execution[0]=="PENDING"),
                "revocation":dict(zip(("revoked_by","reason","at"),revoked)) if revoked else None}

    def revoke(self, review_id, viewed_digest, principal, policy, now):
        snapshot, row = self._row(review_id)
        if row[2] != "APPROVED" or type(viewed_digest) is not str or viewed_digest != row[1]:
            raise Denied("review_changed_or_decided")
        self.gate.revoke(review_id,principal,policy,now)
        return self.view(review_id,principal,policy)

    def approve(self, review_id, viewed_digest, principal, policy, state, now):
        snapshot, row = self._row(review_id)
        if row[2] != "PENDING" or type(viewed_digest) is not str or viewed_digest != row[1]:
            raise Denied("review_changed_or_decided")
        if not snapshot["created_at"] <= now < snapshot["expires_at"]:
            raise Denied("review_expired")
        if digest(policy) != digest(snapshot["policy"]):
            raise Denied("policy_changed")
        # A fresh read may have a newer timestamp; all other reviewed evidence must match.
        relevant = lambda s: {k:v for k,v in s.items() if k != "observed_at"}
        if digest(relevant(state)) != digest(relevant(snapshot["observation"])):
            raise Denied("reviewed_evidence_changed")
        action = snapshot["action"]
        values = Gate.approval_values(review_id,action,policy,state,action["requester"],principal,
                                      now,snapshot["expires_at"]-now)
        # Claim the review and create its approval in one transaction. A second
        # connection cannot approve it again, and failure rolls both changes back.
        try:
            with self.gate.db:
                changed = self.gate.db.execute("UPDATE reviews SET status='APPROVED',approver=?,decided_at=? WHERE id=? AND digest=? AND status='PENDING'",
                                               (principal,now,review_id,viewed_digest)).rowcount
                if changed != 1:
                    raise Denied("review_changed_or_decided")
                self.gate.db.execute("INSERT INTO approvals(id,binding,issued,expires) VALUES (?,?,?,?)",values)
                self.gate.db.execute("INSERT INTO approval_evidence(id,digest) VALUES (?,?)",
                                     (review_id,digest(relevant(snapshot["observation"]))))
        except sqlite3.IntegrityError as exc:
            raise Denied("approval_conflict") from exc
        return self.view(review_id,principal,policy)
