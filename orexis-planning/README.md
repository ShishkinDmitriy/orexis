# orexis-planning

Derives wants from desires, searches for a plan for each, and publishes it. It also checks each head as execution
takes it.

- **Loaded for:** `planning:Planner`.
- **Words:** `ontology.ttl` (`planning:`), `wait.ttl` (`planning:Wait`). **Dictionary:** `knowledge/domain/planning/`.
- **Imports:** the kernel and belief. Outside this crate the one name imported is `Planner`.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `planning:PlanningTrigger`: `belief:Revised` | belief | `planning:Planning`, where the policy judges a state changed or a belief that came to the agent was revised |
| `planning:PlanningTrigger`: `execution:IntentionAdopted`, `execution:StepTaken`, `execution:IntentionResolved` | execution | `planning:Planning` |
| `planning:PlanningTrigger`: `coordination:DrawWon` | coordination | `planning:Planning`, reopening the wants it names (`planning:reopens`) |
| `execution:HeadAsked` | execution | the head checked against the present; no activity |
| the clock: the present reaches the next ground the last planning laid | | `planning:Planning` |
| the clock: a search the budget cut short, `planning:budgetEveryS` later (10 s) | | `planning:Planning` |

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `planning:Planning` | lay the grounds (the present, then each foreseen instant); derive the wants; search each want's scope within the budget of worlds; publish what was found; hold the agent or let it go | `planning:PlanPublished`, `planning:WantReached`, `planning:PlanSuperseded`, `planning:WantUnreachable` |

## What it says

| Event | Beneath | For |
|---|---|---|
| `planning:PlanPublished` | `execution:AdoptingTrigger` | execution adopts the plan |
| `planning:WantReached` | `execution:ResolvingTrigger` | execution ends the want's unbegun intentions |
| `planning:PlanSuperseded` | `execution:SupersedingTrigger` | execution ends an intention after its step in flight |
| `planning:HeadChecked` | `execution:WalkingTrigger` | the answer to `execution:HeadAsked` |
| `planning:WantUnreachable` | `orexis:Incident` | the journal keeps the log before it |
