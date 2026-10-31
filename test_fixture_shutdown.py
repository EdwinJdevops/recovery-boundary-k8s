import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path


class FixtureShutdownTests(unittest.TestCase):
    @unittest.skipUnless(os.name=="posix","POSIX signal regression runs on Linux CI; Windows container test runs remotely")
    def test_sigterm_exits_cleanly(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0))
            port = listener.getsockname()[1]
        path = Path(__file__).parent/"integration"/"app"
        child = subprocess.Popen([sys.executable,"server.py"],cwd=path,env={**os.environ,"PORT":str(port)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+10
            while True:
                try:
                    with urllib.request.urlopen("http://127.0.0.1:"+str(port)+"/index.html",timeout=1) as response:
                        self.assertEqual(response.read().strip(),b"recovery-boundary-ok")
                    break
                except OSError:
                    if child.poll() is not None or time.monotonic()>=deadline:
                        self.fail("fixture failed to start")
                    time.sleep(.1)
            child.terminate()
            self.assertEqual(child.wait(timeout=5),0)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)


if __name__ == "__main__": unittest.main()
