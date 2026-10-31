import copy
import unittest
from unittest.mock import patch
from gate import Denied, conditional_patch
from fixtures import ACTION
from kubernetes_local import LocalKubernetes, workload_ready, ready_backend_count, CONTEXT, NAMESPACE, NAME


def healthy():
    return {"apiVersion":"apps/v1","kind":"Deployment", "metadata":{
        "uid":"u1","name":NAME,"namespace":NAMESPACE,"generation":2},
        "spec":{"replicas":3},"status":{"observedGeneration":2,"replicas":3,
        "updatedReplicas":3,"readyReplicas":3,"availableReplicas":3,
        "conditions":[{"type":"Available","status":"True"}]}}


class KubernetesTests(unittest.TestCase):
    def test_empty_endpoint_slices_and_unknown_readiness(self):
        for item in ({"endpoints":None},{"endpoints":[]},{}):
            self.assertEqual(ready_backend_count({"items":[item]}),0)
        self.assertEqual(ready_backend_count({"items":[{"endpoints":[{"conditions":{"ready":False}},
            {"conditions":{"ready":True}},{"conditions":{"ready":None}},{}]}]}),3)

    def test_malformed_endpoint_evidence_cannot_prove_outage(self):
        for obj in ({},{"items":None},{"items":[None]},{"items":[{"endpoints":"bad"}]},
                    {"items":[{"endpoints":[{"conditions":"bad"}]}]}):
            with self.subTest(obj=obj),self.assertRaises(Denied): ready_backend_count(obj)

    def test_health_requires_current_controller_evidence(self):
        self.assertTrue(workload_ready(healthy(),"u1",2,3))
        for key, value in (("observedGeneration",1),("availableReplicas",2),("updatedReplicas",2),
                           ("readyReplicas",True),("replicas",4),("unavailableReplicas",1)):
            obj = healthy()
            obj["status"][key] = value
            with self.subTest(key=key): self.assertFalse(workload_ready(obj,"u1",2,3))

    def test_recreated_or_superseded_workload_is_not_healthy(self):
        for key,value in (("uid","u2"),("generation",3),("deletionTimestamp","now")):
            obj = healthy()
            obj["metadata"][key] = value
            self.assertFalse(workload_ready(obj,"u1",2,3))
        self.assertFalse(workload_ready({},"u1",2,3))

    def test_local_configuration_rejects_remote_or_plugin(self):
        base = {"clusters":[{"cluster":{"server":"https://127.0.0.1:6443"}}],"users":[{"user":{}}]}
        with patch.object(LocalKubernetes,"_json",return_value=base):
            client = LocalKubernetes(__file__)
            self.assertIn("--context",client.prefix)
        for server in ("https://example.com:6443","http://127.0.0.1:6443","https://127.0.0.1:6443/api"):
            bad = copy.deepcopy(base)
            bad["clusters"][0]["cluster"]["server"] = server
            with patch.object(LocalKubernetes,"_json",return_value=bad),self.assertRaises(Denied):
                LocalKubernetes(__file__)
        bad = copy.deepcopy(base)
        bad["users"][0]["user"]["exec"] = {"command":"external-login"}
        with patch.object(LocalKubernetes,"_json",return_value=bad),self.assertRaises(Denied): LocalKubernetes(__file__)

    def test_patch_preserves_tests_and_never_uses_shell(self):
        client = object.__new__(LocalKubernetes)
        request = {"target":{"cluster":CONTEXT,"namespace":NAMESPACE,"name":NAME},
                   "content_type":"application/json-patch+json","patch":conditional_patch(ACTION)}
        with patch.object(client,"_json",return_value={}) as call:
            client(request)
            args = call.call_args.args[0]
            self.assertIn("--type=json",args)
            self.assertIn('/metadata/uid',args[args.index("--patch")+1])
        request["patch"][0]["op"] = "remove"
        with self.assertRaises(Denied): client(request)


if __name__ == "__main__": unittest.main()
