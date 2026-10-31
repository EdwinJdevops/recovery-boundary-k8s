import concurrent.futures
import copy
import http.client
import json
import secrets
import sqlite3
import threading
import unittest
import test_gate
from gate import Gate, Denied
from fixtures import ACTION, POLICY, STATE
from review import Reviews
from review_server import ReviewApp, make_server
from execution import Executor


class ReviewTests(unittest.TestCase):
    setUp = test_gate.GateTests.setUp
    tearDown = test_gate.GateTests.tearDown

    def create(self):
        self.reviews = Reviews(self.gate)
        return self.reviews.create("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1000)

    def approve(self, hashed, **changes):
        args = dict(principal="reviewer",policy=POLICY,state=STATE,now=1001)
        return self.reviews.approve("review-1",hashed,**{**args,**changes})

    def test_view_is_exact_and_approval_records_identity(self):
        hashed = self.create()
        view = self.reviews.view("review-1","reviewer",POLICY)
        self.assertEqual(view["snapshot"]["action"],ACTION)
        self.assertEqual(view["snapshot"]["policy"],POLICY)
        self.assertEqual(view["snapshot"]["observation"],STATE)
        self.assertEqual(view["snapshot_sha256"],hashed)
        approved = self.approve(hashed,now=1010)
        self.assertEqual((approved["approver"],approved["decided_at"]),("reviewer",1010))
        expires = self.gate.db.execute("SELECT expires FROM approvals WHERE id='review-1'").fetchone()[0]
        self.assertEqual(expires,1120)
        intent = self.gate.authorize("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1011)
        self.assertEqual(intent["patch"],view["snapshot"]["patch"])

    def test_mismatch_self_approval_expiry_and_policy_change_deny(self):
        hashed = self.create()
        for digest_value,changes in (("0"*64,{}),(hashed,{"principal":"operator"}),
                (hashed,{"now":1120}),(hashed,{"policy":{**POLICY,"version":2}}),
                (hashed,{"principal":"intruder"})):
            with self.subTest(changes=changes),self.assertRaises(Denied): self.approve(digest_value,**changes)

    def test_changed_evidence_denies_even_if_action_identity_matches(self):
        hashed = self.create()
        with self.assertRaises(Denied): self.approve(hashed,state={**STATE,"extra_condition":"changed"})
        # A fresh observation of unchanged evidence is permitted.
        self.approve(hashed,state={**STATE,"observed_at":1001})

    def test_review_cannot_be_reapproved(self):
        hashed = self.create()
        self.approve(hashed)
        with self.assertRaises(Denied): self.approve(hashed)

    def test_review_evidence_remains_bound_at_authorization_and_dispatch(self):
        hashed = self.create()
        self.approve(hashed)
        changed = {**STATE,"extra_condition":"changed"}
        with self.assertRaises(Denied):
            self.gate.authorize("review-1",json.dumps(ACTION),POLICY,changed,"operator",1002)
        self.gate.authorize("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1002)
        with self.assertRaises(Denied):
            Executor(self.gate).dispatch("review-1",POLICY,changed,"operator",1003,lambda _:self.fail("must not dispatch"))

    def test_review_view_access(self):
        self.create()
        with self.assertRaises(Denied): self.reviews.view("review-1","intruder",POLICY)

    def test_approval_insert_failure_rolls_back_review_decision(self):
        hashed = self.create()
        self.gate.db.execute("CREATE TRIGGER fail_review BEFORE INSERT ON approvals BEGIN SELECT RAISE(ABORT,'injected'); END")
        self.gate.db.commit()
        with self.assertRaises(Denied): self.approve(hashed)
        self.assertEqual(self.reviews.view("review-1","reviewer",POLICY)["status"],"PENDING")

    def test_concurrent_review_has_one_winner(self):
        hashed = self.create()
        def attempt(_):
            gate = Gate(self.path)
            try:
                Reviews(gate).approve("review-1",hashed,"reviewer",POLICY,STATE,1001)
                return True
            except Denied: return False
            finally: gate.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt,range(8))),1)


class ReviewHTTPTests(unittest.TestCase):
    def setUp(self):
        test_gate.GateTests.setUp(self)
        self.reviews = Reviews(self.gate)
        self.hashed = self.reviews.create("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1000)
        self.reviewer_token = secrets.token_urlsafe(32)
        self.requester_token = secrets.token_urlsafe(32)
        app = ReviewApp(self.path,{self.reviewer_token:"reviewer",self.requester_token:"operator"},
                        lambda:copy.deepcopy(POLICY),lambda now:{**STATE,"observed_at":now},lambda:1001)
        self.server = make_server(app)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        test_gate.GateTests.tearDown(self)

    def request(self,method="GET",path="/reviews/review-1",token=None,body=None,headers=None):
        headers = {} if headers is None else dict(headers)
        if token is not None: headers["Authorization"] = "Bearer "+token
        if body is not None:
            headers.setdefault("Content-Type","application/json")
            body = json.dumps(body)
        connection = http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body,headers)
            response = connection.getresponse()
            return response.status,response.read(),dict(response.getheaders())
        finally: connection.close()

    def test_authentication_and_exact_approval_over_http(self):
        self.assertEqual(self.request()[0],401)
        self.assertEqual(self.request(token="invalid")[0],401)
        code,body,headers = self.request(token=self.reviewer_token)
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["snapshot_sha256"],self.hashed)
        self.assertEqual(headers["Cache-Control"],"no-store")
        code,body,_ = self.request("POST","/reviews/review-1/approve",self.reviewer_token,{"snapshot_sha256":self.hashed})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["approver"],"reviewer")
        self.assertEqual(self.gate.db.execute("SELECT count(*) FROM executions").fetchone()[0],0)

    def test_requester_cannot_approve_and_identity_cannot_be_supplied(self):
        self.assertEqual(self.request("POST","/reviews/review-1/approve",self.requester_token,{"snapshot_sha256":self.hashed})[0],403)
        self.assertEqual(self.request("POST","/reviews/review-1/approve",self.reviewer_token,{"snapshot_sha256":self.hashed,"approver":"reviewer"})[0],400)

    def test_cross_origin_and_host_rebinding_deny(self):
        self.assertEqual(self.request(token=self.reviewer_token,headers={"Origin":"https://evil.example"})[0],403)
        self.assertEqual(self.request(token=self.reviewer_token,headers={"Host":"evil.example"})[0],403)

    def test_wrong_digest_and_oversize_deny(self):
        self.assertEqual(self.request("POST","/reviews/review-1/approve",self.reviewer_token,{"snapshot_sha256":"wrong"})[0],403)
        self.assertEqual(self.request("POST","/reviews/review-1/approve",self.reviewer_token,{"snapshot_sha256":"x"*2000})[0],413)

    def test_duplicate_json_member_is_rejected_over_http(self):
        connection = http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)
        try:
            connection.request("POST","/reviews/review-1/approve",
                '{"snapshot_sha256":"first","snapshot_sha256":"second"}',
                {"Authorization":"Bearer "+self.reviewer_token,"Content-Type":"application/json"})
            response = connection.getresponse()
            self.assertEqual(response.status,403)
            self.assertEqual(json.loads(response.read())["error"],"invalid_json")
        finally:
            connection.close()

    def test_ui_has_no_inline_script_or_token_storage(self):
        code,body,headers = self.request(path="/")
        self.assertEqual(code,200)
        self.assertIn(b"Review the exact recovery action",body)
        self.assertIn("frame-ancestors 'none'",headers["Content-Security-Policy"])
        _,script,_ = self.request(path="/review.js")
        self.assertNotIn(b"innerHTML",script)
        self.assertNotIn(b"localStorage",script)


if __name__ == "__main__": unittest.main()
