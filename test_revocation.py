import concurrent.futures
import json
import threading
import unittest
import test_gate
import test_review
from gate import Gate, Denied
from execution import Executor
from fixtures import ACTION, POLICY, STATE


class RevocationTests(unittest.TestCase):
    setUp = test_gate.GateTests.setUp
    tearDown = test_gate.GateTests.tearDown

    def authorize(self):
        return self.gate.authorize("a",json.dumps(ACTION),POLICY,STATE,"operator",1001)

    def test_revoke_before_authorization(self):
        self.gate.revoke("a","reviewer",POLICY,1001)
        with self.assertRaises(Denied): self.authorize()
        self.assertEqual(self.gate.db.execute("SELECT count(*) FROM executions").fetchone()[0],0)

    def test_revoke_pending_execution_and_persist_after_reopen(self):
        self.authorize()
        self.gate.revoke("a","reviewer",POLICY,1002)
        other = Gate(self.path)
        try:
            self.assertEqual(Executor(other).receipt("a")["status"],"CANCELLED")
            with self.assertRaises(Denied):
                Executor(other).dispatch("a",POLICY,STATE,"operator",1003,lambda _: self.fail("revoked dispatch"))
        finally: other.close()

    def test_revoke_cannot_promise_cancellation_after_claim(self):
        self.authorize()
        def transport(_):
            other = Gate(self.path)
            try:
                with self.assertRaises(Denied): other.revoke("a","reviewer",POLICY,1002)
            finally: other.close()
            raise TimeoutError()
        result = Executor(self.gate).dispatch("a",POLICY,STATE,"operator",1002,transport)
        self.assertEqual(result["status"],"IN_DOUBT")
        self.assertEqual(self.gate.db.execute("SELECT count(*) FROM revocations").fetchone()[0],0)

    def test_unauthorized_revocation_and_missing_grant_deny(self):
        with self.assertRaises(Denied): self.gate.revoke("a","operator",POLICY,1001)
        with self.assertRaises(Denied): self.gate.revoke("unknown","reviewer",POLICY,1001)

    def test_revoke_dispatch_race_has_consistent_winner(self):
        for n in range(8):
            grant = "race-"+str(n)
            self.gate.approve(grant,ACTION,POLICY,STATE,"operator","reviewer",1000)
            self.gate.authorize(grant,json.dumps(ACTION),POLICY,STATE,"operator",1001)
            barrier = threading.Barrier(2)
            calls = []
            def race(revoke):
                gate = Gate(self.path)
                try:
                    barrier.wait(timeout=5)
                    if revoke:
                        gate.revoke(grant,"reviewer",POLICY,1002)
                    else:
                        Executor(gate).dispatch(grant,POLICY,STATE,"operator",1002,lambda r: calls.append(r))
                    return True
                except Denied: return False
                finally: gate.close()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                winners = list(pool.map(race,[True,False]))
            self.assertEqual(sum(winners),1)
            self.assertEqual(len(calls),0 if winners[0] else 1)
            self.assertEqual(Executor(self.gate).receipt(grant)["status"],"CANCELLED" if winners[0] else "IN_DOUBT")

    def test_malformed_policy_collections_fail_closed(self):
        for field,value in (("requesters","operator"),("approvers","reviewer"),("namespaces","demo"),
                            ("max_replicas",True),("version",True),("version",0),("approvers",[]),
                            ("requesters",["operator","operator"])):
            with self.subTest(field=field),self.assertRaises(Denied):
                Gate.check(ACTION,{**POLICY,field:value},STATE,"operator",1001)


class RevocationHTTPTests(unittest.TestCase):
    setUp = test_review.ReviewHTTPTests.setUp
    tearDown = test_review.ReviewHTTPTests.tearDown
    request = test_review.ReviewHTTPTests.request
    def test_http_revocation_is_attributed_and_blocks_authorization(self):
        self.reviews.approve("review-1",self.hashed,"reviewer",POLICY,STATE,1001)
        self.assertFalse(self.reviews.view("review-1","operator",POLICY)["can_revoke"])
        self.assertEqual(self.request("POST","/reviews/review-1/revoke",self.requester_token,{"snapshot_sha256":self.hashed})[0],403)
        code,body,_ = self.request("POST","/reviews/review-1/revoke",self.reviewer_token,{"snapshot_sha256":self.hashed})
        self.assertEqual(code,200)
        view = json.loads(body)
        self.assertEqual(view["status"],"REVOKED")
        self.assertEqual(view["revocation"]["revoked_by"],"reviewer")
        with self.assertRaises(Denied):
            self.gate.authorize("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1002)

    def test_review_does_not_offer_cancellation_after_dispatch_claim(self):
        self.reviews.approve("review-1",self.hashed,"reviewer",POLICY,STATE,1001)
        self.assertTrue(self.reviews.view("review-1","reviewer",POLICY)["can_revoke"])
        self.gate.authorize("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1002)
        Executor(self.gate).dispatch("review-1",POLICY,STATE,"operator",1003,lambda _:None)
        view = self.reviews.view("review-1","reviewer",POLICY)
        self.assertFalse(view["can_revoke"])
        self.assertEqual(view["execution_status"],"IN_DOUBT")


if __name__ == "__main__": unittest.main()
