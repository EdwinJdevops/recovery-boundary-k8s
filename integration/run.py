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
from review import Reviews
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
    client.run(["wait","--for=condition=Ready","pod/service-probe","-n",NAMESPACE,"--timeout=120s"])
    client.run(["apply","-f",str(Path(__file__).with_name("rbac.yaml"))])
    executor = LocalKubernetes(os.environ["KUBECONFIG"],executor_identity=True)
    policy = dict(cluster=CONTEXT,namespaces=[NAMESPACE],max_replicas=4,
                  requesters=["operator"],approvers=["reviewer"],version=1)
    def action_for(obj, incident):
        return dict(schema=1,cluster=CONTEXT,namespace=NAMESPACE,name=NAME,
                    uid=obj["metadata"]["uid"],resourceVersion=obj["metadata"]["resourceVersion"],
                    operation="scale_deployment",replicas=3,requester="operator",incident=incident)
    checks = []
    require(executor.read()["metadata"]["uid"] == client.read()["metadata"]["uid"],"scoped executor cannot read target")
    forbidden_commands = [
        ["get","secret","boundary-deny","-n",NAMESPACE,"-o","json"],
        ["get","deployment","unapproved","-n",NAMESPACE,"-o","json"],
        ["get","deployment",NAME,"-n","default","-o","json"],
        ["delete","deployment",NAME,"-n",NAMESPACE],
        ["run","unapproved-pod","-n",NAMESPACE,"--image=recovery-boundary-demo:test","--restart=Never"],
    ]
    for command in forbidden_commands:
        try:
            executor.run(command)
        except Denied as error:
            require(str(error)=="kubernetes_forbidden","permission test failed for a non-RBAC reason")
        else:
            raise AssertionError("executor exceeded RBAC scope")
    checks.append("rbac_denies_secrets_other_targets_namespaces_delete_and_pod_creation")
    probe = "import urllib.request; body=urllib.request.urlopen('http://checkout:8080/index.html',timeout=5).read(); assert body.strip()==b'recovery-boundary-ok'; print('HTTP_OK')"
    def service_probe(script):
        return client.run(["exec","pod/service-probe","-n",NAMESPACE,"--","python","-c",script]).strip()
    require(service_probe(probe)=="HTTP_OK","baseline service is unhealthy")
    checks.append("baseline_service_http_passed")
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

            # Harness-only fault injection. The recovery executor cannot scale to zero.
            client.run(["scale","deployment",NAME,"-n",NAMESPACE,"--replicas=0"])
            client.run(["wait","--for=delete","pod","-l","app=recovery-boundary-demo","-n",NAMESPACE,"--timeout=120s"])
            end = time.monotonic()+30
            while True:
                slices = json.loads(client.run(["get","endpointslices.discovery.k8s.io","-n",NAMESPACE,"-l","kubernetes.io/service-name=checkout","-o","json"]))
                if not any(e.get("conditions",{}).get("ready",True) for item in slices["items"] for e in item.get("endpoints",[])):
                    break
                require(time.monotonic()<end,"service endpoints did not become unavailable")
                time.sleep(1)
            failure_probe = """import urllib.request, urllib.error
try:
    urllib.request.urlopen('http://checkout:8080/index.html',timeout=2)
except (urllib.error.URLError,TimeoutError):
    print('SERVICE_UNAVAILABLE')
else:
    raise SystemExit('service unexpectedly reachable')
"""
            require(service_probe(failure_probe)=="SERVICE_UNAVAILABLE","injected outage not observed")
            require(client.read()["spec"]["replicas"]==0,"outage injection did not scale down")
            checks.append("controlled_zero_backend_outage_observed")

            cancelled_obj = client.read()
            cancelled_at = int(time.time())
            cancelled_action = action_for(cancelled_obj,"cancelled-recovery")
            cancelled_state = client.observation(cancelled_obj,cancelled_at)
            cancelled_reviews = Reviews(gate)
            cancelled_hash = cancelled_reviews.create("cancelled",json.dumps(cancelled_action),policy,cancelled_state,"operator",cancelled_at)
            cancelled_reviews.approve("cancelled",cancelled_hash,"reviewer",policy,cancelled_state,cancelled_at)
            cancelled_reviews.revoke("cancelled",cancelled_hash,"reviewer",policy,cancelled_at)
            try:
                gate.authorize("cancelled",json.dumps(cancelled_action),policy,cancelled_state,"operator",cancelled_at)
            except Denied:
                require(client.read()["spec"]["replicas"]==0,"cancelled recovery changed target")
                checks.append("revoked_recovery_authorization_blocked")
            else:
                raise AssertionError("revoked recovery was authorized")

            # Fresh evidence and a different approval are needed for recovery.
            fresh = client.read()
            now = int(time.time())
            action = action_for(fresh,"valid-scale")
            state = client.observation(fresh,now)
            reviews = Reviews(gate)
            reviews.create("valid",json.dumps(action),policy,state,"operator",now)
            viewed = reviews.view("valid","reviewer",policy)
            reviews.approve("valid",viewed["snapshot_sha256"],"reviewer",policy,state,now)
            checks.append("exact_review_snapshot_approved")
            gate.authorize("valid",json.dumps(action),policy,state,"operator",now)
            applied = []
            def transport(request):
                result = executor(request)
                applied.append(result)
                return result
            receipt = Executor(gate).dispatch("valid",policy,state,"operator",int(time.time()),transport)
            require(receipt["status"] == "APPLIED_RESPONSE","valid patch was not confirmed")
            checks.append("approved_conditional_patch_applied")
            wait_ready(client,applied[0],3)
            checks.append("three_replicas_controller_ready")
            # Independent application check through Service DNS, from within the cluster.
            for _ in range(5):
                out = service_probe(probe)
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
                      "scope":"controlled zero-backend fixture outage; not real customer incident diagnosis or sustained availability proof"}
            output = Path("integration-result.json")
            output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
            print(json.dumps(report,sort_keys=True))
        finally:
            gate.close()


if __name__ == "__main__": main()
