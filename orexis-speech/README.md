# orexis-speech

Keeps what is said, by the agent or to it, as statements, and extracts what is believed of each. A statement is
no belief; a domain's `speech:Extraction` makes the belief.

- **Loaded for:** `speech:Speaker`.
- **Words:** `ontology.ttl` (`speech:`). **Dictionary:** `knowledge/domain/speech/`.
- **Imports:** the kernel, and the transport family's contract (`orexis-transport/`), naming no member.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `speech:SpeakingTrigger`: `execution:Told`, `coordination:Told` | execution, coordination | `speech:Speaking` |
| a graph of kind `speech:StatementGraph` written | itself (`said`, `heard`) | the extraction of that statement into a belief graph; no activity |
| a peer's document on the agent's own channel, or a chat's words on its channel (an arrival) | the member that reaches it | `speech:Hearing` |
| `speech:CarryingTrigger`: `speech:ProseKept`, `speech:WritingAnnounced` | translation | `speech:Carrying`, where the words are the agent's own; the agent shown writing, with no activity |

At start it extracts from every statement nothing was extracted from, as on a volume lived in.

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `speech:Speaking` | each statement named is read back from the store as it was said: its graph, its kinds and its period; the document sent to each agent it is to through the member that reaches it, a person passed over | `speech:Said` (`speech:statement`, `speech:to`) |
| `speech:Listening` | for as long as speech runs, one for each channel it listens on, the agent's own and each chat's | nothing: each arrival heard on the channel is part of it |
| `speech:Hearing` | one arrival on a channel is kept: a peer's document as the statements it says, a person's words as prose | `speech:Heard`, once the statements are told written, or `speech:ProseKept` |
| `speech:Carrying` | the agent's own words a prose graph keeps are sent on their channel through the member that reaches it, as a reply where they name one | nothing |

## What it says

| Event | Heard by |
|---|---|
| `speech:Said` | translation (`translation:PhrasingTrigger`) |
| `speech:Heard` | the journal |
| `speech:ProseKept` (said by speech or by translation) | translation, speech (`speech:CarryingTrigger`) |
| `speech:WritingAnnounced` (said by translation) | speech (`speech:CarryingTrigger`) |
