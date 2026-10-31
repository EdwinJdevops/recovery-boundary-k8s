"""Synthetic review UI, deliberately disconnected from any cluster executor."""
import json
import os
import tempfile
import time
from pathlib import Path
from fixtures import ACTION, POLICY, STATE
from gate import Gate
from review import Reviews
from review_server import ReviewApp, make_server


def main():
    token = os.environ.get("RECOVERY_REVIEW_TOKEN","")
    if len(token) < 32:
        raise SystemExit("Set RECOVERY_REVIEW_TOKEN to a strong, provisioned local token of at least 32 characters. Do not share or commit it.")
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory)/"review.db")
        now = int(time.time())
        gate = Gate(path)
        Reviews(gate).create("demo-review",json.dumps(ACTION),POLICY,{**STATE,"observed_at":now},"operator",now,300)
        gate.close()
        app = ReviewApp(path,{token:"reviewer"},lambda:POLICY,lambda at:{**STATE,"observed_at":at},lambda:int(time.time()))
        server = make_server(app,8765)
        print("Synthetic review prototype: http://127.0.0.1:8765 ; no cluster writes. Review expires after five minutes.",flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__": main()
