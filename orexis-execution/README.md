# orexis-execution

Owns the intentions. It adopts a published plan as an intention, takes each step when it is due, and says whether
the world came to show what the step predicted.

- **Loaded for:** `execution:Executor`.
- **Words:** `ontology.ttl` (`execution:`). **Dictionary:** `knowledge/domain/execution/`.
- **Imports:** the kernel and speech. It names no word of planning.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `execution:AdoptingTrigger`: `planning:PlanPublished` | planning | `execution:Adopting` |
| `execution:SupersedingTrigger`: `planning:PlanSuperseded` | planning | `execution:Superseding` |
| `execution:ResolvingTrigger`: `planning:WantReached` | planning | `execution:Resolving` |
| `execution:WalkingTrigger`: `belief:Revised` | belief | `execution:Walking`, only where the revision changed the present |
| `execution:WalkingTrigger`: `planning:HeadChecked` | planning | the head asked is taken or failed, and `execution:Walking` goes on |
| the clock: a head's `notBefore`, a taken step's `landsAt`, the patience past `notAfter` | | `execution:Walking` |

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `execution:Adopting` | the plan's steps are tagged as the intention's, each written as a committed step | `execution:IntentionAdopted` |
| `execution:Walking` | every head due is asked about (`execution:HeadAsked`) and taken: each order's commands sized from the present and kept as a command graph, each document kept by speech's `said`; every taken step is answered when the present holds its prediction, or failed a patience past its landing | `execution:StepTaken`, `execution:Commanded`, `execution:Told`, `execution:StepAnswered`, `execution:StepFailed`, `execution:IntentionResolved`, `execution:IntentionFailed` |
| `execution:Superseding` | an intention ends after its step in flight, since a plan replaced its untaken steps | `execution:IntentionResolved` |
| `execution:Resolving` | the unbegun intentions pursuing a want end with the outcome named | `execution:IntentionResolved` |

## Who hears what it says

| Event | Heard by |
|---|---|
| `execution:IntentionAdopted`, `execution:StepTaken`, `execution:IntentionResolved` | planning, coordination |
| `execution:HeadAsked` | planning |
| `execution:Commanded` | the MQTT transport (`mqtt:ActuatingTrigger`) |
| `execution:Told` | speech (`speech:SpeakingTrigger`) |
| `execution:StepFailed`, `execution:IntentionFailed` | incidents: the journal keeps the log before each |
