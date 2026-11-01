# Commercial assessment — November 1, 2026

## Decision

**Do not greenlight a standalone commercial product yet. Abandon the generic AI-SRE positioning; retain the code as a technical validation harness while testing one narrow customer problem. Do not rewrite from scratch without better evidence.**

The mechanism is useful in a controlled test: exact review, stale-state vetoes, revocation and conservative handling of uncertain writes. That does not prove a current buyer bottleneck, recurring demand, competitive advantage or willingness to pay. No customer interviews, production deployments, purchase commitments or measured customer ROI have been obtained in this project.

## What the public evidence actually establishes

| Primary source checked November 1 | Established by that source | Consequence for us |
|---|---|---|
| [incident.io, October 28 release](https://incident.io/changelog/plug-your-skills-and-tools-into-the-agent) | Publishes action approval, exact-call execution and proposal/decision/execution audit features, available on Pro/Enterprise | Approval and exact-argument review are not differentiators by themselves |
| [Port tools and approvals](https://docs.port.io/port-ai/tools-and-approvals/) and [workflows](https://docs.port.io/workflows/overview/) | Governed workflows, permissions, review gates and agent-accessible actions | A new approval dashboard competes with functionality in existing platform tooling |
| [PagerDuty Automation Actions](https://docs.pagerduty.com/ai-automation/automation/automation-actions) | Incident-linked diagnostic/remediation execution and action output records | Runbook execution is an established product capability, not a new category we discovered |
| [OpenPort Protocol paper](https://arxiv.org/abs/2602.20196) | Describes an optional State Witness profile for execution-time precondition checks and state-mismatch rejection | State revalidation cannot honestly be claimed as our novel concept |
| [Guarded Commits paper](https://arxiv.org/abs/2610.00037) | Describes approval evidence/ledger checks against artifact, policy and execution path | Transactional approval is prior art; our implementation must earn adoption through useful execution and integration |
| [ARBITER paper](https://arxiv.org/abs/2607.19182) | Describes guarded Kubernetes remediation with typed actions, policy/approval controls and cluster evaluations | A guarded Kubernetes demonstration alone does not establish novelty or superiority |

These are vendor documentation and authors' research reports, not independent validation of every claim or an exhaustive competitor audit. We did not run the competitors' products. Absence of a documented edge-case guarantee is **unknown**, not evidence of a vulnerability or missing feature. Research precedent is not the same as a mature commercial competitor, but it defeats a broad novelty claim.

## The specific problem worth investigating

Hypothesis: a platform team already using agents or automated runbooks has a consequential write that it cannot safely enable because the reviewed action or relevant state can change before execution, and a lost response leaves it unable to decide whether retrying is safe.

Candidate buyer: a platform/SRE lead who owns the affected write path and its operating budget. Candidate user: the incident responder reviewing or executing that runbook. Candidate form: a small adapter/conformance harness within the team's existing workflow, rather than a replacement incident platform. All three are hypotheses, not validated customer facts.

The test is whether the team can show a concrete workflow and explain why existing GitOps, incident-platform approvals, policy checks, provider preconditions or its own small wrapper are insufficient. If it cannot, there is no demonstrated reason to buy another service.

Our current scaling fixture is deliberately simple. It proves a boundary under controlled faults; it is not evidence that customers need an AI system to scale a Deployment. The current local bearer UI, trusted SQLite process and impersonated RBAC test are weaker than a production identity/isolation story. More code cannot substitute for a verified need.

## Commercial proof required before broadening the build

Proposed decision rule, not a market statistic:

1. Interview five qualified operators from at least three independent teams about their most recent relevant incident or blocked automation project. Ask for a redacted incident summary/workflow, not credentials or production access.
2. At least two teams independently identify the same costly gap and schedule a hands-on evaluation against one existing write path, using their current tooling as the comparison.
3. At least one budget owner identifies the purchasing/security path and agrees to a scoped paid pilot if the stated acceptance criteria pass. Praise, GitHub stars and a hypothetical willingness-to-pay answer do not satisfy this gate.
4. Show a measurable net benefit: fewer manual checks or reconciliation steps without unauthorized writes; include review latency, false blocks, integration/maintenance effort and operating cost. Do not attribute the whole cost of an outage to the narrow problem we address.

If those conversations produce no repeated problem, no incremental benefit over existing tools, or no evaluation commitment, stop treating Recovery Boundary as a standalone business. Preserve the code as research/open technical work subject to the owner's licensing decision, or pivot only to a different problem for which we have stronger evidence.

## Evaluation scorecard

Compare the team's existing workflow and a minimal adapter on the same scenarios: changed arguments, changed target UID/version, expired/revoked approval, a cancellation/dispatch race, and a response lost after application. Record what ran, whether it remained authorized, how uncertainty was represented, what an operator had to do next and how long it took. Include unchanged successful actions to detect excessive blocking. Do not compare a hardened prototype against a deliberately unprotected strawman.

No claim that this product is commercially validated, uniquely defensible, production-ready or likely to be adopted by a named company is justified today. The engineering evidence supports a controlled mechanism. Customer evidence must support the business.
