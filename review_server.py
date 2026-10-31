"""Loopback prototype only. Pre-provisioned bearer identities; no cluster dispatch."""
import hashlib
import hmac
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from gate import Gate, Denied, parse
from review import Reviews


class ReviewApp:
    def __init__(self, database, credentials, policy_provider, state_provider, clock):
        if not credentials or any(type(t) is not str or len(t) < 32 for t in credentials):
            raise ValueError("strong provisioned credentials required")
        self.database = database
        self.identities = {hashlib.sha256(t.encode()).digest():p for t,p in credentials.items()}
        self.policy = policy_provider
        self.state = state_provider
        self.clock = clock

    def authenticate(self, header):
        if not header or not header.startswith("Bearer "):
            raise Denied("authentication_required")
        hashed = hashlib.sha256(header[7:].encode()).digest()
        for expected, principal in self.identities.items():
            if hmac.compare_digest(hashed,expected):
                return principal
        raise Denied("authentication_required")


def make_server(app, port=0):
    class Handler(BaseHTTPRequestHandler):
        server_version = "RecoveryBoundaryLocal"
        sys_version = ""

        def log_message(self, *_):
            pass  # Request targets and authorization headers must never be logged.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def respond(self, code, value, content_type="application/json"):
            data = json.dumps(value).encode() if content_type == "application/json" else value
            self.send_response(code)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self):
            expected_host = "127.0.0.1:"+str(self.server.server_port)
            origin = self.headers.get("Origin")
            if (self.headers.get_all("Host",[]) != [expected_host]
                    or (origin is not None and origin != "http://"+expected_host)):
                return self.respond(403,{"error":"origin_denied"})
            assets = {"/":"review.html","/review.js":"review.js","/review.css":"review.css"}
            if self.command == "GET" and self.path in assets:
                types = {"/":"text/html; charset=utf-8","/review.js":"text/javascript; charset=utf-8","/review.css":"text/css; charset=utf-8"}
                return self.respond(200,(Path(__file__).with_name("review_ui")/assets[self.path]).read_bytes(),types[self.path])
            match = re.fullmatch(r"/reviews/([a-zA-Z0-9_-]{1,64})(/approve|/revoke)?",self.path)
            if not match:
                return self.respond(404,{"error":"not_found"})
            gate = None
            try:
                headers = self.headers.get_all("Authorization",[])
                principal = app.authenticate(headers[0] if len(headers)==1 else None)
                gate = Gate(app.database)
                reviews = Reviews(gate)
                policy = app.policy()
                if self.command == "GET" and not match[2]:
                    result = reviews.view(match[1],principal,policy)
                elif self.command == "POST" and match[2]:
                    if (self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length",[])) != 1
                            or self.headers.get("Content-Type") != "application/json"):
                        return self.respond(400,{"error":"invalid_body"})
                    try:
                        size = int(self.headers["Content-Length"])
                    except ValueError:
                        return self.respond(400,{"error":"invalid_body"})
                    if not 1 <= size <= 1024:
                        return self.respond(413,{"error":"invalid_body"})
                    body = parse(self.rfile.read(size))
                    if type(body) is not dict or set(body) != {"snapshot_sha256"}:
                        return self.respond(400,{"error":"invalid_body"})
                    now = app.clock()
                    if match[2] == "/revoke":
                        result = reviews.revoke(match[1],body["snapshot_sha256"],principal,policy,now)
                    else:
                        result = reviews.approve(match[1],body["snapshot_sha256"],principal,policy,app.state(now),now)
                else:
                    return self.respond(405,{"error":"method_denied"})
                return self.respond(200,result)
            except Denied as error:
                return self.respond(401 if str(error)=="authentication_required" else 403,{"error":str(error)})
            except Exception:
                return self.respond(500,{"error":"review_unavailable"})
            finally:
                if gate is not None:
                    gate.close()

        do_GET = handle_request
        do_POST = handle_request

    # No option to bind a public interface in this prototype.
    return ThreadingHTTPServer(("127.0.0.1",port),Handler)
