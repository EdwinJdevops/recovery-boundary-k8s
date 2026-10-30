# Product thesis and evidence bar

Recovery Boundary targets platform engineers reviewing an AI-proposed Kubernetes recovery. The narrow question is: can this exact action still be authorized, and what can we truthfully say if its response disappears?

The differentiator to demonstrate is preservation of the decision and outcome evidence across changed state, concurrent workers, failures and restarts. This is a hypothesis about useful product differentiation, not a claim that nobody else has built these mechanisms.

## What a judge or platform engineer should be able to inspect

1. A concrete incident with an observable user impact and a measured baseline. Do not invent a customer, outage or time-saved number.
2. A real Meta model turning bounded incident evidence into a structured proposal. Show a case where interpretation helps, and compare to a deterministic baseline. A wrapper calling a model is insufficient evidence of useful AI.
3. A review showing exact target, operation, replica count, relevant observations, policy and expiry. Human identity must come from authentication, not the model.
4. An accepted recovery on a local Kubernetes API, followed by separate rollout/health evidence. An HTTP success or desired replica count is not recovered service health.
5. The same proposal rejected after a target UID/resource version or policy change. Include oversized actions, malformed input and replay.
6. A response-loss demonstration where the journal remains uncertain after restart and does not blindly repeat the write. Read-back of matching replicas alone does not prove our action caused them.
7. Reproducible tests, pinned demonstration inputs, and explicit trust boundaries. Publish exact results and distinguish synthetic tests from real integrations.

## Current evidence

The original gate has local and remote CI evidence. The execution journal adds fault-injection tests and an explicitly synthetic restart demonstration. Meta inference, actual Kubernetes transport and rollout verification are still pending.

## Build order while API credits are pending

- Complete the durable gate-to-dispatch lifecycle and its adversarial tests.
- Validate a real conditional PATCH against a disposable local API server when an existing local runtime is available; never use a cloud context implicitly.
- Add a trustworthy review surface and identity boundary before exposing write-capable execution.
- Integrate Meta proposal generation only when permitted credits/access exist; retain the same deterministic boundary and independent tests.
- Measure useful proposal quality and recovery evidence, then record a concise end-to-end demo.

## Article and attribution

Keep a factual evidence ledger: tool, exact role, version/model, verified result, reproducible command, limitation and source. Attribute only products actually used. Do not imply sponsorship, endorsement, production adoption, company featuring or a guaranteed win. No article or tagging campaign is published automatically.
