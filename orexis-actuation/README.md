# orexis-actuation

The translation row's acting side, the mirror of sensing: what a step commands is made into the device's document,
sent through the transport member that reaches it, and kept as `sosa:Actuation`s.

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
| `actuation:Actuating` | each actuator the step's command graph sets is sent one document, each value at its property's `actuation:commandPointer`, through the member that reaches it as a channel it is sent on, and what was sent is kept as an `actuation:ActuationGraph`; a setting with no pointer and an actuator no member reaches are passed over, in the log | nothing |
