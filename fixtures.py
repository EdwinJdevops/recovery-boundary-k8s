ACTION = dict(schema=1, cluster="lab", namespace="demo", name="checkout", uid="deployment-1", resourceVersion="42", operation="scale_deployment", replicas=3, requester="operator", incident="incident-1")
POLICY = dict(cluster="lab", namespaces=["demo"], max_replicas=4, requesters=["operator"], approvers=["reviewer"], version=1)
STATE = dict(cluster="lab", namespace="demo", name="checkout", uid="deployment-1", resourceVersion="42", kind="Deployment", apiVersion="apps/v1", observed_at=1000)
