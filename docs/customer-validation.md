# Customer validation script and record

Status November 1, 2026: **no interviews completed and no customer evidence recorded**. No outreach messages have been sent by the agent.

## Interview guide — 20 minutes

Start with the operator's last real example, before showing the product:

1. What was the last production incident or automation rollout where a recovery action needed approval? What happened, and when?
2. Walk through the actual tools and people between proposal and execution. Where did the process stop or require a manual recheck?
3. Did the proposed arguments, target state or permissions change while waiting? How was that caught? If it was not a problem, record that too.
4. Has a write timed out after it may have succeeded? How did you determine the result, and did a retry create a problem?
5. What existing controls solve this today? Would configuring your existing incident portal, GitOps pipeline or API preconditions be sufficient?
6. How often does this occur? What evidence supports that frequency? Separate direct records from estimates.
7. What operator effort or blocked automation can be attributed specifically to this gap, rather than to the entire incident?
8. Who owns the workflow, security approval and budget? What would prevent installing a small adapter? What is the acceptable integration effort?

Only then show the narrow demonstration. Ask the operator to select a relevant existing workflow and a fair baseline. Request a scheduled evaluation or an introduction to the actual owner; do not treat compliments as demand. Do not request secrets or non-public incident data without appropriate permission. Redacted descriptions are sufficient for initial discovery.

## One record per team

- Interview date and consent to retain notes:
- Role, workflow owner and budget owner (use anonymized labels when appropriate):
- Actual incident/blocker and redacted evidence reference:
- Current tools and what already works:
- Observed gap, frequency and confidence in the estimate:
- Direct operator effort and integration/maintenance cost:
- Strongest disconfirming evidence:
- Proposed fair baseline and pass/fail criteria:
- Concrete next commitment, owner and date:
- Decision: no fit / further discovery / evaluation / conditional paid pilot:

## Pilot acceptance template

Scope one operation in a disposable or approved non-production environment. Specify who can propose, approve, revoke and dispatch; the exact target and parameters; current-state preconditions; expiry; uncertain-outcome handling; and what production credentials remain unavailable. Measure successful actions and rejection cases on the same workload. State the required latency/error budget and integration effort before running the pilot. A paid pilot is not authorization for production access or cloud expenditure.
