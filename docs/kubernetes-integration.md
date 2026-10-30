# Disposable Kubernetes integration

The `kubernetes-integration` workflow creates kind inside an ephemeral GitHub Linux runner using its existing Docker runtime. It does not provision AWS resources or use a cloud Kubernetes context. The test adapter refuses remote API endpoints, insecure TLS, proxy URLs and credential plugins. It always passes a dedicated kubeconfig and the exact `kind-recovery-boundary` context; it never falls back to the user's current context.

## Test scope

1. Deploy a repository-owned Python HTTP fixture with one replica and wait for current controller readiness.
2. Approve a scale to three, change the target after observation, and prove the real API rejects the stale resourceVersion without changing replicas.
3. Submit a patch with a wrong UID but current resourceVersion and prove the API rejects it independently.
4. Use fresh evidence and a new approval for the valid conditional scale.
5. Confirm the returned desired state, then independently wait for the same UID/generation to have three updated, ready and available replicas.
6. Make five HTTP requests through the Kubernetes Service from inside the cluster and verify the expected response body.
7. Attempt to replay the execution and confirm it is blocked.

The workflow uploads `integration-result.json` only on success, then removes its own named kind cluster. An `APPLIED_RESPONSE` receipt is still separate from workload readiness and HTTP probe evidence. Five successful requests are a smoke test, not an availability SLO, a load test or proof that every replica served traffic. The fixture starts healthy; this verifies an authorized capacity change, not diagnosis or recovery from a real customer outage.

## Reproduce with an existing local Docker runtime

Use kind v0.33.0, kubectl v1.35.8 and Python 3.12. The workflow downloads the official binaries and verifies their published SHA-256 checksums. The Kubernetes node image is pinned by digest in the workflow. The fixture base image uses the `python:3.12-alpine` tag and is not yet pinned by digest.

In a disposable Linux environment, from the repository root:

```sh
export KUBECONFIG="$PWD/work/recovery-boundary.kubeconfig"
mkdir -p work
kind create cluster --name recovery-boundary --image kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0 --kubeconfig "$KUBECONFIG" --wait 120s
docker build -t recovery-boundary-demo:test integration/app
kind load docker-image recovery-boundary-demo:test --name recovery-boundary
python integration/run.py
kind delete cluster --name recovery-boundary
```

Use the dedicated name only when it is available; do not delete an existing cluster you did not create for this test. The test kubeconfig contains local cluster credentials: do not commit, upload or print it. The adapter uses the generated local administrator credential for integration testing; production authentication, least-privilege deployment and a non-bypassable service boundary remain unimplemented.

## Primary references

- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0
- https://kubernetes.io/docs/reference/kubectl/generated/kubectl_patch/
- https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
