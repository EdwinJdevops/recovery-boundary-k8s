# Official rules verification — October 30, 2026

Primary sources:

- https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver — rendered browser page titled `Hackathon Terms & Conditions (“Official Rules”) and Event Waiver`, dated October 25, 2026. The text-only web reader returned an empty page; browser rendering exposed the full terms.
- https://dev.meta.ai/events/global-hackathon — event dates and themes. This page still says rules will be published before kickoff; the rendered terms above are more specific.
- https://events.cerebralvalley.ai/e/meta-ai-developer-hackathon — organizer event listing.

## Verified

- Submission deadline: November 4, 2026, 9 PM ET (EST on that date; November 5, 02:00 UTC).
- Every individual must apply and be accepted; participation capped at 20,000. A Meta API account alone is not acceptance.
- Age at least 18 and age of majority where resident. Location, sanctions, employment, government affiliation and family/household restrictions apply. User eligibility and acceptance have not been independently verified.
- Indie: individuals/students and teams up to four. Representative submits and identifies every member. Startup representative must be an active employee authorized to submit. Each participant and submission enters only one track; members must read and agree to rules.
- Participants build with Meta AI products, including Muse Spark, Glimmer, SAM 3 and other products identified on the event page. The terms do not name one universally mandatory model; event page also identifies Meta open weights models. Do not equate this offline deterministic gate or use of Codex with meeting that requirement.
- Submit through https://cerebralvalley.ai/e/meta-ai-developer-hackathon/hackathon/submit .
- Judging: impact 30%, Meta tooling 25%, technical depth/execution 20%, demo 25%. Demo criterion includes working product, live robustness and demo video quality.
- Submission must be original work, owned by entrant/team/organization and respect third-party rights. Technical assistance is allowed subject to ownership. Open source is allowed with applicable license compliance and enhancement/building upon the underlying product.
- Entrant retains ownership; submission grants organizers a broad perpetual license. No purchase is necessary.

## Not explicitly settled by the published terms

- No express pre-existing-code cutoff or rule requiring all code to originate during the event was found. This is not a determination that any existing private project may be reused. This repository instead starts with fresh original code and an explicit provenance statement.
- No public repository requirement, video duration, video hosting format, exact submission fields or live hosting requirement was stated in the terms inspected.
- Participant-only updates and the authenticated submission form have not been verified. These may add requirements and must be checked before submission.

## Remaining submission work

Confirm acceptance, location/age/affiliation eligibility, selected track and team roster; inspect participant updates and form; integrate a real permitted Meta model without unauthorized spending; test against a local Kubernetes API; record a truthful working demo/video; submit before the deadline. No agreement or submission was accepted on the user's behalf during this implementation.

Technical reference for the future conditional executor: https://kubernetes.io/docs/reference/using-api/api-concepts/ .
