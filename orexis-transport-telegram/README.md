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
| the clock, every `TELEGRAM_POLL_S` | | the bot polled on a thread of its own |
| a message polled (an arrival) | Telegram | the words kept as a `speech:ProseGraph`, `speech:ProseKept` said |
| `telegram:CarryingTrigger`: `speech:ProseKept` | translation | `telegram:Carrying`, where the words are the agent's own |
| `telegram:CarryingTrigger`: `speech:WritingAnnounced` | translation | `telegram:Carrying`, showing the agent writing |

## Activities

| Activity | What happens |
|---|---|
| `telegram:Carrying` | the agent's own words are sent on the chat's channel, as a reply where the words name one; or the chat is shown the agent writing |
