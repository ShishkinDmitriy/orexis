# orexis-transport

The transport family's contract: what every member — `orexis-transport-mqtt`, `-http`, `-telegram` and `-email` —
does alike, and nothing else reads.

- **Loaded for:** no role. It is no package: it registers nothing, starts nothing and runs no task; each member
  depends on it.
- **Words:** none of its own; a member's are in its own `ontology.ttl`.
- **Dictionary:** `knowledge/domain/transport/transport.md`.

## What it gives a member

| A member | by |
|---|---|
| offers the rows above a channel it reaches, to listen on or send on, a request a send with a reply | `Member`, `Exchange` |
| is found by a row above, which names no member | `Members::add` (`Provided::alter`), `Members::reaching` |
| leaves what it receives for whoever listens or asked, ringing it awake | `Inbox::deliver`, `Inbox::wakes` |
| queues what arrived, a job to handle each | `Pending::arrived`, `Pending::oldest` |
| runs what it queued until nothing is left | `Jobs::queued` |
| decides whether it joins: the world wires the self through it | `wired` |
| carries a chat's words, as Telegram and email do (feature `chat`) | `chat::ChatMember`, `chat::ChatTransport` |
