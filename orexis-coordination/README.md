# orexis-coordination

Two agents that want one resource ask each other and draw lots for it. The coordinator asks the peers in range
what its constraints read, answers them, concludes each conflict itself and lays what it yields to.

- **Loaded for:** `coordination:Coordinator`, beneath the speaker, the planner and the executor.
- **Words:** `ontology.ttl` (`coordination:`). **Dictionary:** `knowledge/domain/coordination/`.
- **Imports:** the kernel and speech; it speaks belief's, planning's and execution's words.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `coordination:CoordinatingTrigger`: `belief:Revised` | belief | `coordination:Coordinating` (a peer comes in range by what the agent senses) |
| `coordination:CoordinatingTrigger`: `execution:IntentionAdopted`, `execution:StepTaken`, `execution:IntentionResolved` | execution | `coordination:Coordinating` (the holdings are read off the intentions) |
| a graph of kind `coordination:QuestionGraph` written | speech's extraction | the question answered, the conflicts concluded |
| a graph of kind `coordination:AnswerGraph` written | speech's extraction | the conflicts concluded, what it yields to laid |
| the clock: a patience, while it is asking or in conflict | | `coordination:Coordinating` |

At start it mints the agent's secret for the draws where it holds none.

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `coordination:Coordinating` | ask the peers in range with the agent's holdings; conclude each conflict; lay each peer's holdings as said, or as foreseen where the peer is silent | `coordination:Told`, `coordination:Asked`, `coordination:Said`, `coordination:Foreseen`, `coordination:Concluded`, `coordination:DrawWon` |

## What it says

| Event | Beneath | For |
|---|---|---|
| `coordination:Told` | `speech:SpeakingTrigger` | speech tells the question or the answer |
| `coordination:DrawWon` | `planning:PlanningTrigger` | planning reopens the wants named |
| `coordination:Asked`, `coordination:Said`, `coordination:Foreseen`, `coordination:Concluded` | `coordination:Held` or `orexis:Event` | the journal and the history view |
