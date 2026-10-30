"""Real API integration against the dedicated disposable kind cluster only."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gate import Gate, Denied, conditional_patch
from execution import Executor
from kubernetes_local import LocalKubernetes, workload_ready, CONTEXT, NAMESPACE, NAME


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def wait_ready(client, applied, replicas):
    end = time.monotonic() + 120
    while time.monotonic() < end:
        obj = client.read()
        if workload_ready(obj,applied["metadata"]["uid"],applied["metadata"]["generation"],replicas):
            return obj
        time.sleep(1)
    raise AssertionError("workload readiness timed out")


def main():
    client = LocalKubernetes(os.environ["KUBECONFIG"])
    # Applies only the fixed repository fixture to the explicitly guarded cluster.
    client.run(["apply","-f",str(Path(__file__).with_name("workload.yaml"))])
    initial = client.read()
    wait_ready(client,initial,1)
    policy = dict(cluster=CONTEXT,namespaces=[NAMESPACE],max_replicas=4,
                  requesters=["operator"],approvers=["reviewer"],version=1)
    def action_for(obj, incident):
        return dict(schema=1,cluster=CONTEXT,namespace=NAMESPACE,name=NAME,
                    uid=obj["metadata"]["uid"],resourceVersion=obj["metadata"]["resourceVersion"],
                    operation="scale_deployment",replicas=3,requester="operator",incident=incident)
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        gate = Gate(str(Path(directory)/"journal.db"))
        try:
            # Mutate after observation: the API, not a mock, must veto the stale PATCH.
            before = client.read()
            now = int(time.time())
            stale = action_for(before,"stale-rv")
            state = client.observation(before,now)
            gate.approve("stale",stale,policy,state,"operator","reviewer",now)
            gate.authorize("stale",json.dumps(stale),policy,state,"operator",now)
            client.run(["annotate","deployment",NAME,"-n",NAMESPACE,"boundary-test=changed","--overwrite"])
            receipt = Executor(gate).dispatch("stale",policy,state,"operator",int(time.time()),client)
            require(receipt["status"] == "IN_DOUBT","stale patch must not report applied")
            require(client.read()["spec"]["replicas"] == 1,"stale patch changed replicas")
            checks.append("stale_resource_version_rejected_by_api")

            # Test UID independently of resourceVersion, using a deliberately wrong UID.
            fresh = client.read()
            wrong = action_for(fresh,"uid-veto")
            wrong["uid"] = "00000000-0000-0000-0000-000000000000"
            try:
                client({"target":{"cluster":CONTEXT,"namespace":NAMESPACE,"name":NAME},
                        "content_type":"application/json-patch+json","patch":conditional_patch(wrong)})
            except Denied:
                pass
            else:
                raise AssertionError("API accepted wrong UID")
            require(client.read()["spec"]["replicas"] == 1,"UID veto changed replicas")
            checks.append("wrong_uid_rejected_by_api")

            # Fresh evidence and a different approval are needed for the valid action.
            fresh = client.read()
            now = int(time.time())
            action = action_for(fresh,"valid-scale")
            state = client.observation(fresh,now)
            gate.approve("valid",action,policy,state,"operator","reviewer",now)
            gate.authorize("valid",json.dumps(action),policy,state,"operator",now)
            applied = []
            def transport(request):
                result = client(request)
                applied.append(result)
                return result
            receipt = Executor(gate).dispatch("valid",policy,state,"operator",int(time.time()),transport)
            require(receipt["status"] == "APPLIED_RESPONSE","valid patch was not confirmed")
            checks.append("approved_conditional_patch_applied")
            wait_ready(client,applied[0],3)
            checks.append("three_replicas_controller_ready")
            # Independent application check through Service DNS, from within the cluster.
            probe = "import urllib.request; body=urllib.request.urlopen('http://checkout:8080/index.html',timeout=5).read(); assert body.strip()==b'recovery-boundary-ok'; print('HTTP_OK')"
            for _ in range(5):
                out = client.run(["exec","deployment/"+NAME,"-n",NAMESPACE,"--","python","-c",probe])
                require(out.strip() == "HTTP_OK","service HTTP probe failed")
            checks.append("five_service_http_probes_passed")
            try:
                Executor(gate).dispatch("valid",policy,state,"operator",int(time.time()),lambda _: require(False,"replayed write"))
            except Denied:
                checks.append("execution_replay_blocked")
            else:
                raise AssertionError("execution replay accepted")
            report = {"mode":"REAL_KIND_API", "checks":checks,"replicas":3,
                      "kubernetes":json.loads(client.run(["version","-o","json"]))["serverVersion"]["gitVersion"],
                      "scope":"local fixture; not production recovery or sustained availability proof"}
            output = Path("integration-result.json")
            output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
            print(json.dumps(report,sort_keys=True))
        finally:
            gate.close()


if __name__ == "__main__": main()
