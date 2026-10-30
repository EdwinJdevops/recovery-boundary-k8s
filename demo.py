"""Synthetic proposals, NOT a recorded or live Meta model response."""
import json
import tempfile
from pathlib import Path
from gate import Gate, Denied
from fixtures import ACTION, POLICY, STATE

with tempfile.TemporaryDirectory() as directory:
    gate = Gate(str(Path(directory) / "approval.db"))
    gate.approve("review-1", ACTION, POLICY, STATE, "operator", "reviewer", 1000)
    for label, action in [("unsafe synthetic proposal", {**ACTION, "replicas": 10}),
                          ("approved exact proposal", ACTION), ("replayed proposal", ACTION)]:
        try:
            result = gate.authorize("review-1", json.dumps(action), POLICY, STATE, "operator", 1001)
        except Denied as error:
            result = {"decision": "DENIED", "reason": str(error)}
        print(json.dumps({"scenario": label, **result}, sort_keys=True))
    gate.close()
