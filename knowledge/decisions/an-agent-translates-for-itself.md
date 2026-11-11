---
type: Decision
title: An agent translates for itself, through transports of its own, and its account is selects
status: accepted
timestamp: 2026-10-31T12:00:00Z
description: >-
  The sovereign's ruling of 2026-10-31 on who speaks with a person. A world has no process of its
  own, so translation is a package of the agent, loaded for the role translation:Translator beneath
  the speaker, each agent holding its own model key and its own carriers - a Telegram bot of its own,
  a mailbox, a chat's topic - each a member of the transport family. A transport carries bytes for
  every row alike, an instrument's, a peer's and a person's, and what points at a channel says which
  row reads it. In a group with several agents each answers when named, keeps silent when another
  is, and answers an unnamed question only where its account speaks to it. The account is a SELECT
  each package ships beside its ontology, asked when a person asks and stored nowhere. Refused - the
  translator as a process of the world, a manager agent speaking for the others, and the account as
  a method of every part rendered by templates and published retained.
---

> **Amended 2026-11-01, again:** words that tag an agent's account or reply to it are addressed to that agent
> as its name is, and words that tag or reply to someone else are theirs; the carrier says which, Telegram from
> the message's entities and its reply, and an agent answers to the name it goes by as well as its ids.
>
> **Amended 2026-11-01:** the account is askables — `speech:Askable`, a question a package declares and
> the agent answers from its store — found in the store by kind, and the model is offered sayables and
> askables in one call; `/account` becomes `/status` ([a-question-is-answered-and-every-other-act-is-kept](/decisions/a-question-is-answered-and-every-other-act-is-kept.md)).

# The question

#1043 first shipped the translator as the account record left it: a process of the world beside the
simulator, `python -m translation <world>`, standing in every chat the world states, connected to the
bus as a client of its own, holding the model's key and one Telegram bot for the world; each agent a
*reporter* publishing a templated account of itself, retained, on a topic the translator read. The
sovereign read it and ruled on three things:

- "World has no own processes. Only agents hold processes." A world is documents
  ([where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md)); the simulator stands for
  the physical world, and a translator stands for nobody but the agent whose words it carries.
- There are three kinds of communication, each with transports of its own: agent and device (MQTT,
  HTTP, one day a wire or I2C), agent and agent (TriG over a transport), agent and person (natural
  language through a model, over a chat channel). A transport is independent of all three, so a
  sensor might one day be fed from a Telegram chat or a feed, and a person reached over the bus.
- "If we need a class, we use the triplestore." An account rendered by a Python method per part and
  templates is a class hierarchy written in code; the store already answers what an agent observes and
  does, and a SELECT says it.

# What was decided

**Translation is a package of the agent**, `crates/orexis-translation/`, loaded where the self plays
`translation:Translator`, a role beneath `speech:Speaker`, since what a person states is kept as a
statement through speech's own `heard` and what the agent says to a person reaches translation by
speech's own `told`. Each translating agent holds the model's key, `infra/secrets/model.env`, mounted
into its own container by `orexis-compose`, and its own carriers' secrets: its bot's token, its
mailbox. The model is still called off the pass — the call runs on a thread of its own and what comes
of it is submitted back as a job — so a pass never waits on one, and nothing the model writes is a
belief: the account record's limits on it stand.

**A transport carries bytes for every row, and what points at a channel says which row reads it.** A
member of the family ([transport](/domain/transport/transport.md)) holds a channel — a topic, a
Telegram chat, a mailbox — and knows nothing of what is on it: a channel a sensor observes is
sensing's, one an agent listens on is speech's, and the channel of a [chat](/domain/speech/chat.md)
the agent is in is translation's. A member says a person's words as `prose` and sends words back by
`say_to`; translation hears every member's `prose` and keeps every member that sends, and imports
none of them, as no member imports translation. Telegram and email became members beside MQTT and
HTTP, loaded where a translator speaks through a bot or is in a chat by mail; the MQTT member carries
a chat's topic as well as a board's and a peer's. Since #1119 the words go both ways as a `speech:ProseGraph`
kept and a `speech:ProseKept` said, each side hearing it beneath its own trigger
([policy](/domain/kernel/policy.md)), where translation's `prose` handler and its list of senders were links.

**A bot per agent.** Each agent speaks through a `telegram:Bot` of its own, so a group of several
agents is several bots, each its agent's, and a person writes to the one they mean. The account record
refused this because one token is one consumer of `getUpdates`; that holds, and is why each agent has
its own token rather than sharing the world's.

**In a group, an agent answers what is addressed to it.** Words naming an agent of the chat — by its
local id or its IRI's local name, as a word of its own — are that agent's, and every other agent of
the chat passes over them in silence. Words naming none are offered to each agent's account alone, the
model told to answer `NOTHING` where the account does not speak to the question, so the agent that
knows answers and the rest keep silent. A sayable is filled only from words addressed to the agent, or
in a chat where it is the only agent.

**The account is selects.** A package with something to say of itself ships `account.rq` beside its
ontology: its first comment line the section's title, its `# reads:` line the kinds of graph handed
to it as the default graph. Sensing's says the latest reading of each sensor, execution's each
intention standing. Translation asks each loaded package's select when a person asks — `/account`
answered with the rows for nothing, a question in words answered by the model from them — and stores
nothing (later the askable, retired in turn by
[a-person-states-what-the-chat-allows-in-the-worlds-words](/decisions/a-person-states-what-the-chat-allows-in-the-worlds-words.md)). The account is still telemetry and never a
belief.

# What was refused

- **The translator as a process of the world.** Built in #1043 and refused by the ruling above: a
  process with the model's key standing in every chat of a world speaks for every agent at once, so
  the society has a member no world document says is an agent, with a credential on the bus and every
  agent's inbox granted to it. An agent translating for itself needs no principal but its own.
- **A manager agent speaking for the others** — one agent with one bot, relaying to its peers over
  the bus. It is the fallback if a carrier allowed one bot per chat; Telegram does not limit a group to
  one, so each agent speaks for itself, and the manager stays a seam.
- **The account as a method of every part, rendered by templates, published retained on a topic.**
  Built in #1043 as the account record decided, and refused: a section rendered in Python is a reader
  of the store no text states, and publishing an account every pass a value moves was traffic for a
  question asked a few times a day. A select is a document the package ships, run when asked.

# What it amends

[an-agent-gives-an-account-of-itself-and-the-model-only-reads-it](/decisions/an-agent-gives-an-account-of-itself-and-the-model-only-reads-it.md),
in part: the gateway is no process of the world but each agent's translation part, a model is in the
agent's process though in no pass, a question reaches the agent as a person's words in a chat it is
in, and the account is selects asked when asked. Its limits on the model are kept.
[the-model-compiles-a-routine-and-is-called-back-at-its-edges](/decisions/the-model-compiles-a-routine-and-is-called-back-at-its-edges.md):
the translator at its first edge is the agent's own package, not a process of the world.

# Seams left open

- **Which person spoke** is still the carrier's word — a Telegram user id, a mailbox's sender — and
  unsigned; signing is speech's seam.
- **An unnamed question in a group** is judged by each agent's model apart, so two agents whose
  accounts both speak to it both answer; nothing coordinates them.
- **A sensor fed from a chat.** The transport carries the bytes; nothing yet points a sensor at a
  chat's channel, and sensing would need a pipeline for prose.
- **Planning's account.** No world that chats holds a planner; its select is owed when one does.
