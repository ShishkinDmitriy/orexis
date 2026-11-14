# orexis-belief

Revises what the agent believes. An inference concludes of one graph and never deletes; a transition changes the
agent's own state, triggered once by each arrival of testimony.

- **Loaded for:** `belief:Deliberator` (and any role beneath it, such as `sensing:Observer`).
- **Words:** `ontology.ttl` (`belief:`). **Dictionary:** `knowledge/domain/belief/`.
- **Imports:** the kernel alone.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| a graph of kind `orexis:BeliefGraph` written | any package | `belief:Revising` |
| `belief:RevisingTrigger`: `sensing:Perceived` | sensing | `belief:Revising` |

At start it revises once what the world authored as the agent's state.

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `belief:Revising` | the rules conclude of each graph written since the last pass, into its revision graph; then the transitions each arrival triggers are applied to the agent's own state; all within a budget of rule executions, continued next pass if cut short | `belief:Revised` (`belief:revised` the sources, `belief:changed` the states that changed) |

## Who hears `belief:Revised`

Planning, execution, coordination and sensing each put it beneath a trigger of their own.
