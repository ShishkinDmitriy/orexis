# orexis-actuation

The translation row's acting side, the mirror of sensing: what a step commands is sent to the device through the
transport member that reaches it.

- **Loaded for:** `actuation:Operator`, which depends on `execution:Executor`.
- **Words:** `ontology.ttl` (`actuation:`), speaking SOSA's words for acting; a domain's devices are in
  `domains/actuation/`. **Dictionary:** `knowledge/domain/actuation/`, first `operator.md`.
- **Imports:** the kernel, and the transport family's contract (`orexis-transport/`), naming no member.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `actuation:ActuatingTrigger`: `execution:Commanded` | execution | `actuation:Actuating` |

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `actuation:Actuating` | each command of the step's command graph is sent to its actuator through the member that reaches it as a channel it is sent on; one no member reaches is passed over, in the log | nothing |
