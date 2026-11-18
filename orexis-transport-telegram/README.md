# orexis-transport-telegram

The Telegram member of the transport family: a person's words in, the agent's own words out, through the agent's
own bot.

- **Loaded for:** no role of its own. It is loaded where a chat of the agent's has a `telegram:Chat` channel.
- **Words:** `ontology.ttl` (`telegram:`). **Dictionary:** `knowledge/domain/transport/transport.md`,
  `knowledge/domain/speech/chat.md`.
- **Needs:** the bot's token, in the agent's own `secrets/<agent>/`.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| the clock, as often as a role says (`telegram:polledEveryS`), every 3 s where none says | | the bot polled, awaited as a Tokio task |
| a message polled (an arrival) | Telegram | left with speech, listening on the chat, as the chat's words (`orexis_transport::chat::Words`) |

## Activities

None: what it is handed and sent is a row's above, which listens and sends through it.
