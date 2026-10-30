import concurrent.futures
import json
import tempfile
import unittest
from pathlib import Path
from gate import Gate, Denied, parse
from fixtures import ACTION, POLICY, STATE


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "gate.db")
        self.gate = Gate(self.path)
        self.gate.approve("a", ACTION, POLICY, STATE, "operator", "reviewer", 1000)

    def tearDown(self):
        self.gate.close()
        self.tmp.cleanup()

    def run_action(self, action=None, policy=None, state=None, now=1001, requester="operator"):
        return self.gate.authorize("a", json.dumps(ACTION if action is None else action), POLICY if policy is None else policy, STATE if state is None else state, requester, now)

    def test_exact_action_and_preconditions(self):
        result = self.run_action()
        self.assertEqual(result["patch"], [{"op":"test","path":"/metadata/uid","value":"deployment-1"}, {"op":"test","path":"/metadata/resourceVersion","value":"42"}, {"op":"replace","path":"/spec/replicas","value":3}])

    def test_replay(self):
        self.run_action()
        with self.assertRaises(Denied): self.run_action()

    def test_mutations(self):
        for key, value in dict(cluster="other", namespace="prod", name="other", uid="other", resourceVersion="43", replicas=4, requester="other", incident="other", operation="delete", schema=2).items():
            with self.subTest(key=key), self.assertRaises(Denied): self.run_action({**ACTION, key:value})

    def test_policy_change(self):
        with self.assertRaises(Denied): self.run_action(policy={**POLICY,"version":2})

    def test_state_change(self):
        for key, value in dict(uid="recreated", resourceVersion="43", kind="Pod", apiVersion="v1", observed_at=900).items():
            with self.subTest(key=key), self.assertRaises(Denied): self.run_action(state={**STATE,key:value})

    def test_expired_at_boundary(self):
        with self.assertRaises(Denied): self.run_action(now=1120, state={**STATE,"observed_at":1120})

    def test_unknown_and_missing_fields(self):
        with self.assertRaises(Denied): self.run_action({**ACTION,"command":"kubectl delete"})
        with self.assertRaises(Denied): self.run_action({k:v for k,v in ACTION.items() if k != "uid"})

    def test_strict_replicas(self):
        for value in (True, 3.0, "3", 0, -1, 11, None):
            with self.subTest(value=value), self.assertRaises(Denied): self.run_action({**ACTION,"replicas":value})

    def test_bad_json(self):
        for raw in ('{"a":1,"a":2}', 'NaN', '{} trailing', '{'):
            with self.subTest(raw=raw), self.assertRaises(Denied): parse(raw)

    def test_authenticated_requester(self):
        with self.assertRaises(Denied): self.run_action(requester="intruder")

    def test_clock_before_issuance(self):
        with self.assertRaises(Denied): self.run_action(now=999, state={**STATE,"observed_at":999})

    def test_self_approval(self):
        with self.assertRaises(Denied): self.gate.approve("b", ACTION, POLICY, STATE, "operator", "operator",1000)

    def test_durable_consumption(self):
        self.run_action()
        other = Gate(self.path)
        try:
            with self.assertRaises(Denied): other.authorize("a", json.dumps(ACTION), POLICY, STATE,"operator",1001)
        finally: other.close()

    def test_concurrent_claim_has_one_winner(self):
        def claim(_):
            gate = Gate(self.path)
            try:
                gate.authorize("a",json.dumps(ACTION),POLICY,STATE,"operator",1001)
                return True
            except Denied: return False
            finally: gate.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(claim, range(8))),1)


if __name__ == "__main__": unittest.main()
