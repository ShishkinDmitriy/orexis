---
type: Decision
title: The transport is the bottom layer, and the row above it owns the loop
status: accepted
timestamp: 2026-11-17T22:00:00Z
description: >-
  The sovereign's ruling of 2026-11-17. A transport member imported sensing's received, speech's heard and the
  prose functions, scheduled a sensor's polls by sensing's cadence and encoded a step's command, so the bottom of
  the agent stack called up into the row above it and decided what its bytes meant. Decided - the transport is the
  bottom layer and offers three ways to exchange bytes on a channel, listen, request and send, through the
  family's contract; sensing, speech and actuation sit above it and each imports the contract and nothing of a
  member; polling is a request in a loop and the loop is the row's that owns the timing; and every member is
  Tokio-native. A member calling up, an event per message and the executor sending its own commands were refused.
---

# What was true before

[the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md) slices the agent by
representation — network, transport, translation, the belief-revision seam, mind — and puts the transport at the
bottom. The code had the arrows the other way. A [transport](/domain/transport/transport.md) member was handed a
message and decided whose it was: the HTTP member called sensing's `received` with a sensor's bytes and polled each
sensor's url on the cadence sensing declares; the MQTT member called `received` and speech's `heard`, nudged a board
when sensing said a reading had lapsed, and sent the payload a step's command answers; the chat carriers kept a
person's words as speech's prose and carried the agent's. So every member imported the row above it, and a member's
crate pulled sensing or speech into any image it was in. The page said a channel is the transport's and a member
"knows nothing of what they mean" — and then every member knew. It was the Python container's `deliver(channel,
payload)` callback, turned into an import when the agent moved to Rust.

# What was decided

**A CHANNEL IS THE TRANSPORT'S, AND THE TRANSPORT OFFERS THREE WAYS TO EXCHANGE BYTES ON ONE.** A channel is what a
member carries bytes on — a topic, a url, a Telegram chat, a mailbox — named by the world's IRI for it.

- **To listen** is to be handed every message that arrives on a channel, each as it comes: a topic subscribed to, a
  bot's updates, a mailbox's new mail. The listener hands an `Inbox`; the member leaves each message there and rings
  the listener's task awake.
- **To request** is to send bytes on a channel and be handed the one reply: a forecast fetched, a sensor's url read.
  The reply is a message like any other, left in the inbox the requester handed.
- **To send** is to send bytes on a channel and be handed nothing: a command to a board, a document to a peer, the
  agent's words in a chat.

So the contract is two acts, `listen(channel, inbox)` and `send(channel, payload, reply)`, a request being a send
with an inbox for its reply. It lives in the family's crate, `orexis-transport/`, which each member implements and
each row above imports. A member says which channels it reaches by what the world says of them, and publishes
itself to a registry the rows above read (`Provided`), as the series' readers are gathered for a chat; so no row
names a member and the kernel names none.

**THE ROWS ABOVE ARE SENSING, SPEECH AND ACTUATION, AND EACH IMPORTS THE CONTRACT AND NOTHING OF A MEMBER.** What
the bytes mean is the row's: sensing listens on the channels its sensors observe and requests on those it reads by
asking, and concludes observations; speech listens on the topics it hears and the channels of its chats, keeps a
peer's document as a statement and a person's words as prose, and sends the agent's; ACTUATION is the row that turns
a step's command into the bytes a device is told and sends them. No member imports sensing, speech or actuation.

**POLLING IS A REQUEST IN A LOOP, AND THE LOOP IS THE ROW'S THAT OWNS THE TIMING.** Sensing owns a sensor's cadence
and knows when its latest reading lapses, so sensing asks on that cadence, and nudging a board that has gone quiet is
sensing's send. A member's own polling stays the member's only where it is how the member listens: a bot's
`getUpdates` and a mailbox's IMAP fetch have no timing anyone above owns, and their pace stays a member's figure
(`telegram:polledEveryS`, `email:polledEveryS`).

**EVERY MEMBER IS TOKIO-NATIVE.** A request is an `async` exchange a Tokio task awaits, leaving the reply in the
requester's inbox; no member spawns an OS thread per fetch. MQTT already is (`rumqttc`'s `AsyncClient`); HTTP and
Telegram move to `reqwest` over rustls, sharing one client; email moves to `async-imap` on Tokio and `lettre`'s
`AsyncSmtpTransport`, keeping `mail-parser`. A test hands a member that answers at once, so Tokio's paused time
advances only where the agent waits, never past a real socket.

# Amended 2026-11-18: actuation's namespace, payload and nudge

The sovereign ruled three things the record left open, as #1220 began. **The actuation package owns `actuation:`**:
`orexis-actuation/` declares its role, `actuation:Operator`, which depends on the executor, and the words of what an
agent holds and what a device changes (`actuation:hasActuator`, `actuation:actuates`, `actuation:actuatesProperty`),
while the watering domain keeps its valve. **Actuation makes the payload**: the executor says what to actuate and how
much, and actuation turns it into a device's bytes and keeps each act as a `sosa:Actuation`, as sensing turns bytes
into an observation. **Actuation sends the nudge on sensing's word**: sensing says which sensor's reading is due, and
actuation tells the board to sense or to sleep, since telling a device anything is acting on it. A role named
`actuation:Actor` was passed over, the bundle's actor being whoever is asked what will hold.

# What was refused

- **A member calling up into the row its message is for.** It is what the code did: the bottom of the stack
  deciding what its bytes mean, importing every row above it, and a member's crate dragging sensing into an agent
  that only listens for a peer. And the loop sat in the wrong row: the HTTP member polled by sensing's cadence, read
  out of sensing's words.
- **An event per message, heard by whichever row the channel points at.** It inverts the import, as prose already
  reaches translation by `speech:ProseKept`. But a message is not a happening of the agent's: every reading said as an
  event goes to every watcher, the journal and the metrics among them, to be dropped by all but one row; and a reply
  belongs to the one row that asked, which a broadcast cannot address. An inbox handed by the listener reaches the
  one task that asked, in the order the messages came.
- **The executor sending a step's command itself.** The executor decides that a step is taken and says so; the
  bytes a device is told, and the channel it listens on, are a representation of the step, which is the translation
  row's work, as an observation is sensing's of a reading. So actuation is a row of its own.
- **Blocking clients on threads of their own.** `ureq` and the synchronous `imap` work, but a thread per fetch is a
  second way of waiting beside the runtime the agent is, and a request awaited as a task is what the contract's
  `send` with a reply already is. `reqwest` costs a heavier build on the Pi, paid only by an agent whose roles load
  HTTP or Telegram, since each member is a feature of the binary.

# Seams left open

- **Which member reaches a channel when two could.** A world wires a channel through one bus or one bot today, so the
  registry answers one member; a channel two members reach is a seam until a world has one.
- **The contract carries bytes, not what they are.** A content type, a header, a QoS are the member's options for a
  channel, read off the world as each reads them now; nothing in the contract names them until a row needs to choose.
- **A failed request answers nothing.** A reply that never comes is a silence the requesting row already reasons
  about — sensing's [silence](/domain/sensing/silence.md) — so the contract says no error upward until a row would
  plan differently on one.
