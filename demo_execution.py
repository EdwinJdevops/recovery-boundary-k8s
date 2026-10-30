"""Synthetic fault injection: applied desired state, lost response, blocked replay."""
import json
import tempfile
from pathlib import Path
from execution import Executor
from gate import Gate, Denied
from fixtures import ACTION, POLICY, STATE


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "journal.db")
        gate = Gate(path)
        gate.approve("review-1", ACTION, POLICY, STATE, "operator", "reviewer",1000)
        gate.authorize("review-1",json.dumps(ACTION),POLICY,STATE,"operator",1001)
        simulated_writes = []
        def lose_response(request):
            simulated_writes.append(request)
            raise TimeoutError("synthetic loss after simulated application")
        receipt = Executor(gate).dispatch("review-1",POLICY,STATE,"operator",1002,lose_response)
        print(json.dumps({"mode":"SYNTHETIC_FAULT_INJECTION", **receipt},sort_keys=True))
        gate.close()
        restarted = Gate(path)
        try:
            try:
                Executor(restarted).dispatch("review-1",POLICY,STATE,"operator",1003,lose_response)
            except Denied as error:
                print(json.dumps({"restart_retry":"DENIED","reason":str(error),"simulated_write_count":len(simulated_writes)},sort_keys=True))
        finally:
            restarted.close()


if __name__ == "__main__": main()
