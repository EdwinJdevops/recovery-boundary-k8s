"""Explicit, local-kind-only kubectl adapter; never selects a default context."""
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from gate import Denied

CONTEXT = "kind-recovery-boundary"
NAMESPACE = "recovery-boundary-demo"
NAME = "checkout"


class LocalKubernetes:
    def __init__(self, kubeconfig, kubectl="kubectl", executor_identity=False):
        path = Path(kubeconfig).resolve(strict=True)
        self.prefix = [kubectl, "--kubeconfig", str(path), "--context", CONTEXT,
                       "--request-timeout=10s"]
        # This reads configuration only. Never print the output or invoke auth plugins.
        config = self._json(["config", "view", "--minify", "-o", "json"])
        try:
            cluster = config["clusters"][0]["cluster"]
            user = config["users"][0]["user"]
            url = urlsplit(cluster["server"])
            if (url.scheme != "https" or url.hostname not in ("127.0.0.1", "localhost", "::1")
                    or url.username or url.password or url.path not in ("", "/")
                    or url.query or url.fragment or not url.port
                    or cluster.get("insecure-skip-tls-verify") or cluster.get("proxy-url")
                    or user.get("exec") or user.get("auth-provider")):
                raise Denied("local_cluster_required")
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise Denied("invalid_local_config") from exc
        if executor_identity:
            # CI tests API-enforced RBAC using admin-authorized impersonation.
            # This is not an isolated worker credential or a production auth flow.
            self.prefix += ["--as","system:serviceaccount:"+NAMESPACE+":recovery-executor"]

    def run(self, args, input_text=None):
        # args come from trusted code, never model-generated command text.
        result = subprocess.run(self.prefix + args, input=input_text, capture_output=True,
                                text=True, timeout=20, shell=False)
        if result.returncode:
            if "Error from server (Forbidden)" in result.stderr:
                raise Denied("kubernetes_forbidden")
            raise Denied("kubectl_failed")  # stderr can contain credentials; do not log it.
        return result.stdout

    def _json(self, args):
        return json.loads(self.run(args))

    def read(self):
        return self._json(["get", "deployment", NAME, "-n", NAMESPACE, "-o", "json"])

    @staticmethod
    def observation(obj, now):
        return {"cluster": CONTEXT, "namespace": obj["metadata"]["namespace"],
                "name": obj["metadata"]["name"], "uid": obj["metadata"]["uid"],
                "resourceVersion": obj["metadata"]["resourceVersion"],
                "kind": obj["kind"], "apiVersion": obj["apiVersion"], "observed_at": now}

    def __call__(self, request):
        if request["target"] != {"cluster":CONTEXT,"namespace":NAMESPACE,"name":NAME}:
            raise Denied("adapter_scope_denied")
        patch = request["patch"]
        if (request["content_type"] != "application/json-patch+json" or type(patch) is not list
                or len(patch) != 3):
            raise Denied("invalid_patch")
        for op, path in zip(patch[:2], ("/metadata/uid", "/metadata/resourceVersion")):
            if (set(op) != {"op","path","value"} or op["op"] != "test" or op["path"] != path
                    or type(op["value"]) is not str or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}",op["value"])):
                raise Denied("invalid_precondition")
        last = patch[2]
        if (set(last) != {"op","path","value"} or last["op"] != "replace"
                or last["path"] != "/spec/replicas" or type(last["value"]) is not int
                or not 1 <= last["value"] <= 10):
            raise Denied("invalid_mutation")
        return self._json(["patch", "deployment", NAME, "-n", NAMESPACE, "--type=json",
                           "--patch", json.dumps(patch), "-o", "json"])


def workload_ready(obj, uid, generation, replicas):
    """Controller evidence only; separate HTTP probes are needed for service health."""
    try:
        meta, status = obj["metadata"], obj["status"]
        if (obj["apiVersion"] != "apps/v1" or obj["kind"] != "Deployment"
                or meta["name"] != NAME or meta["namespace"] != NAMESPACE
                or meta["uid"] != uid or meta.get("deletionTimestamp")
                or type(meta["generation"]) is not int or meta["generation"] != generation
                or type(status["observedGeneration"]) is not int
                or status["observedGeneration"] < generation
                or type(obj["spec"]["replicas"]) is not int or obj["spec"]["replicas"] != replicas):
            return False
        for field in ("replicas", "updatedReplicas", "readyReplicas", "availableReplicas"):
            if type(status.get(field)) is not int or status[field] != replicas:
                return False
        return (status.get("unavailableReplicas", 0) == 0
                and any(c.get("type") == "Available" and c.get("status") == "True"
                        for c in status.get("conditions", [])))
    except (KeyError, TypeError, AttributeError):
        return False
