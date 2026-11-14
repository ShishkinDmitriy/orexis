# orexis-speech

Keeps what is said, by the agent or to it, as statements, and extracts what is believed of each. A statement is
no belief; a domain's `speech:Extraction` makes the belief.

- **Loaded for:** `speech:Speaker`.
- **Words:** `ontology.ttl` (`speech:`). **Dictionary:** `knowledge/domain/speech/`.
- **Imports:** the kernel alone.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `speech:SpeakingTrigger`: `execution:Told`, `coordination:Told` | execution, coordination | `speech:Speaking` |
| a graph of kind `speech:StatementGraph` written | itself (`said`, `heard`) | the extraction of that statement into a belief graph; no activity |
| a peer's document (`heard`, a call, not an event) | a transport member | the statement kept, `speech:Heard` said |

At start it extracts from every statement nothing was extracted from, as on a volume lived in.

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `speech:Speaking` | each statement named is read back from the store as it was said: its graph, its kinds and its period | `speech:Said` (`speech:statement`, `speech:to`) |

## What it says

| Event | Heard by |
|---|---|
| `speech:Said` | the MQTT transport (`mqtt:TellingTrigger`), translation (`translation:PhrasingTrigger`) |
| `speech:Heard` | the journal |
| `speech:ProseKept` (said by a transport or by translation, in speech's words) | translation, each transport's carrying trigger |
| `speech:WritingAnnounced` (said by translation) | the Telegram transport |
