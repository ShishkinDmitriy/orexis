# orexis-transport-email

The email member of the transport family: a person's mail in, the agent's own words out.

- **Loaded for:** no role of its own. It is loaded where a chat of the agent's has a contact point with an email.
- **Words:** `ontology.ttl` (`email:`). **Dictionary:** `knowledge/domain/transport/transport.md`,
  `knowledge/domain/speech/chat.md`.
- **Needs:** the mailbox's credentials, in the agent's own `secrets/<agent>/`.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| the clock, every `MAIL_POLL_S` | | the mailbox polled on a thread of its own |
| a message polled (an arrival) | the mail server | the words kept as a `speech:ProseGraph`, `speech:ProseKept` said |
| `email:CarryingTrigger`: `speech:ProseKept` | translation | `email:Carrying`, where the words are the agent's own |

## Activities

| Activity | What happens |
|---|---|
| `email:Carrying` | the agent's own words are sent on the chat's channel, as a reply where the words name one |
