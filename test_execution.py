import concurrent.futures
import copy
import json
import sqlite3
import subprocess
import sys
import threading
import unittest
from execution import Executor
from gate import Gate, Denied
from fixtures import ACTION, POLICY, STATE
import test_gate


def response():
    return {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {
        "namespace": "demo", "name": "checkout", "uid": "deployment-1", "resourceVersion": "43"},
        "spec": {"replicas": 3}}


class ExecutionTests(unittest.TestCase):
    setUp = test_gate.GateTests.setUp
    tearDown = test_gate.GateTests.tearDown

    def authorize(self):
        return self.gate.authorize("a", json.dumps(ACTION), POLICY, STATE, "operator",1001)

    def dispatch(self, transport, **changes):
        args = dict(policy=POLICY, state=STATE, requester="operator", now=1002, transport=transport)
        return Executor(self.gate).dispatch("a", **{**args, **changes})

    def test_intent_and_approval_commit_together(self):
        self.gate.db.execute("CREATE TRIGGER fail_intent BEFORE INSERT ON executions BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.gate.db.commit()
        with self.assertRaises(sqlite3.IntegrityError): self.authorize()
        self.assertEqual(self.gate.db.execute("SELECT consumed FROM approvals WHERE id='a'").fetchone()[0], 0)
        self.assertEqual(self.gate.db.execute("SELECT count(*) FROM events").fetchone()[0], 0)

    def test_success_records_state_and_exact_patch(self):
        intent = self.authorize()
        requests = []
        def transport(request):
            requests.append(request)
            return response()
        receipt = self.dispatch(transport)
        self.assertEqual(receipt["status"], "APPLIED_RESPONSE")
        self.assertEqual(requests[0]["patch"], intent["patch"])
        self.assertEqual(requests[0]["target"], intent["target"])
        self.assertEqual([e["status"] for e in receipt["events"]], ["PENDING", "IN_DOUBT", "APPLIED_RESPONSE"])

    def test_applied_then_timeout_is_never_retried(self):
        self.authorize()
        writes = []
        def transport(request):
            writes.append(request)
            raise TimeoutError("secret-must-not-be-recorded")
        self.assertEqual(self.dispatch(transport)["status"], "IN_DOUBT")
        other = Gate(self.path)
        try:
            with self.assertRaises(Denied): Executor(other).dispatch("a", POLICY, STATE,"operator",1003,transport)
            self.assertNotIn("secret-must-not-be-recorded", json.dumps(Executor(other).receipt("a")))
        finally: other.close()
        self.assertEqual(len(writes),1)

    def test_crash_after_claim_survives_reopen(self):
        self.authorize()
        def crash(_): raise SystemExit("injected process interruption")
        with self.assertRaises(SystemExit): self.dispatch(crash)
        other = Gate(self.path)
        try:
            self.assertEqual(Executor(other).receipt("a")["status"], "IN_DOUBT")
            with self.assertRaises(Denied): Executor(other).dispatch("a", POLICY,STATE,"operator",1003,lambda _: self.fail("retry"))
        finally: other.close()

    def test_execution_rechecks_evidence(self):
        self.authorize()
        for changes in ({"policy":{**POLICY,"version":2}}, {"state":{**STATE,"resourceVersion":"43"}}, {"now":1120,"state":{**STATE,"observed_at":1120}}, {"requester":"intruder"}):
            with self.subTest(changes=changes), self.assertRaises(Denied):
                self.dispatch(lambda _: self.fail("must not dispatch"), **changes)

    def test_wrong_response_stays_uncertain(self):
        self.authorize()
        wrong = response()
        wrong["metadata"]["uid"] = "replacement"
        self.assertEqual(self.dispatch(lambda _:wrong)["status"], "IN_DOUBT")

    def test_abrupt_process_exit_keeps_claim(self):
        self.authorize()
        script = """
import os, sys
from gate import Gate
from execution import Executor
from fixtures import POLICY, STATE
gate = Gate(sys.argv[1])
Executor(gate).dispatch('a', POLICY, STATE, 'operator', 1002, lambda _: os._exit(23))
"""
        result = subprocess.run([sys.executable,"-c",script,self.path],capture_output=True,timeout=20)
        self.assertEqual(result.returncode,23, result.stderr.decode(errors="replace"))
        self.assertEqual(Executor(self.gate).receipt("a")["status"],"IN_DOUBT")
        with self.assertRaises(Denied): self.dispatch(lambda _: self.fail("must not retry after process exit"))

    def test_response_validation(self):
        for value in (None, {}, {"apiVersion":"v1"}, {**response(),"spec":{"replicas":True}}):
            with self.subTest(value=value): self.assertFalse(Executor.valid_response(value,ACTION))

    def test_concurrent_dispatch_calls_transport_once(self):
        self.authorize()
        calls = []
        lock = threading.Lock()
        def transport(request):
            with lock: calls.append(copy.deepcopy(request))
            return response()
        def run(_):
            gate = Gate(self.path)
            try:
                Executor(gate).dispatch("a",POLICY,STATE,"operator",1002,transport)
                return True
            except Denied: return False
            finally: gate.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(run,range(8))),1)
        self.assertEqual(len(calls),1)


if __name__ == "__main__": unittest.main()
