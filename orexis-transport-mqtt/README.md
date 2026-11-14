# orexis-transport-mqtt

The MQTT member of the transport family: readings and peers' documents in, commands and the agent's documents out.

- **Loaded for:** no role of its own. It is loaded where a loaded role needs bytes and the society wires a broker.
- **Words:** `ontology.ttl` (`mqtt:`), speaking MQTT4SSN. **Dictionary:** `knowledge/domain/transport/transport.md`.
- **Needs:** `MQTT_BROKERS` and the agent's credentials, from its environment and `secrets/<agent>/`.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| a message on a subscribed topic (an arrival) | the broker | handed to sensing (`received`) for a reading, to speech (`heard`) for a peer's document, or kept as prose for a chat's topic |
| `mqtt:ActuatingTrigger`: `execution:Commanded` | execution | `mqtt:Actuating` |
| `mqtt:TellingTrigger`: `speech:Said` | speech | `mqtt:Telling` |
| `mqtt:CarryingTrigger`: `speech:ProseKept` | translation | `mqtt:Carrying`, where the words are the agent's own |
| the clock: a sensor's next reading falls due | | sensing is asked after its missing readings |

It holds the agent running, since what it senses goes on arriving whatever is wanted.

## Activities

| Activity | What happens |
|---|---|
| `mqtt:Actuating` | each command of the command graph is published on the topic its actuator listens to, not retained; a command whose actuator this member does not reach is passed over |
| `mqtt:Telling` | the document is published to each agent it is to that listens on a topic of the bus; a person is passed over |
| `mqtt:Carrying` | the agent's own words are sent on the chat's channel, where this member carries it |
