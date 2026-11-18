# orexis-transport-email

The email member of the transport family: a person's mail in, the agent's own words out.

- **Loaded for:** no role of its own. It is loaded where a chat of the agent's has a contact point with an email.
- **Words:** `ontology.ttl` (`email:`). **Dictionary:** `knowledge/domain/transport/transport.md`,
  `knowledge/domain/speech/chat.md`.
- **Needs:** the mailbox's credentials, in the agent's own `secrets/<agent>/`.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| the clock, as often as a role says (`email:polledEveryS`), every 30 s where none says | | the mailbox polled, awaited as a Tokio task, one poll at a time |
| a message polled (an arrival) | the mail server | left with speech, listening on the chat, as the chat's words (`orexis_transport::chat::Words`) |

## Activities

None: what it is handed and sent is a row's above, which listens and sends through it.
