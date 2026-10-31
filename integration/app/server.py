"""Test HTTP fixture with explicit PID-1 termination handling."""
import os
import signal
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def main():
    server = ThreadingHTTPServer(("0.0.0.0",int(os.environ.get("PORT","8080"))),SimpleHTTPRequestHandler)
    def stop(_signum, _frame):
        # shutdown() must run outside the thread executing serve_forever().
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()


if __name__ == "__main__": main()
