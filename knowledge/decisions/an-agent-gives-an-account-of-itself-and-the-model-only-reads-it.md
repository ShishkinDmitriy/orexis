---
type: Decision
title: An agent gives an account of itself, and the model only reads it
status: accepted
timestamp: 2026-10-04T12:00:00Z
description: >-
  The sovereign reaches a running society over chat — a Telegram bot, one per world, run by a
  chat gateway that is a process of the world as the simulator is. Each agent gives an ACCOUNT of
  itself, in the dictionary's words, every pass something changed, published retained on its bus;
  the gateway holds the latest of every agent, relays one on a command for nothing, and asks a
  language model only for a free question, handing it the accounts and the question. The model
  phrases and decides nothing, authors no belief, runs no query, picks no act. An account is
  telemetry — watched, never believed; what an agent SAYS to the sovereign is speech, the second
  direction #862 fills through the same gateway. Refused — a model inside the agent, a question
  reaching the agent, the present reconstructed from the series, a model writing SPARQL, a bot per
  agent, a gateway spanning worlds.
---

# The question

The sovereign writes a world's documents and runs the operator's tools, and then the society runs
and the sovereign is gone ([sovereign](/domain/kernel/sovereign.md)). What a person can learn of a
running agent today is what it writes to its [series](/domain/kernel/series.md) — observations and
steps taken, drawn by Grafana — and its log. Nothing says in words what an agent WANTS right now,
what it PLANS to do about it and where its intentions stand; a want is a `planning:WantGraph` with a
period and a state, a plan is rows, an intention a graph of its own, and reading them takes the
store. The sovereign asked for the obvious thing: a chat they can ask *what is going on* and *what
are you going to do*, readable by a person, and cheap.

Two threads already run toward it. Agent 0.1.0 declared a language model as a member of the mind
and never built one; the roadmap says the 0.2.0 tree reserves no seam for it
([llm-heavy-deliberation](/decisions/0.1.0/llm-heavy-deliberation.md),
[the-model-is-consulted-at-the-edge-of-knowledge](/decisions/0.1.0/the-model-is-consulted-at-the-edge-of-knowledge.md)),
and that record left open "a runtime interface, later: the sovereign is absent, not abolished".
And #862 wants a probe recalibrated as a plan the agent walks with its sovereign over Telegram,
the person pressing buttons where only a hand can act. This record decides where a model stands
in relation to the mind — outside it — and what the chat is, so that both threads build one thing.

# What was decided

**The sovereign reaches a running society through a chat gateway, one process of the world.** A
Telegram bot per world, run by `orexis-chat <world>`, a service of the world's compose project as
the simulator is: it reads the world as an agent boots it, connects to the world's broker as a
client the society names, and nothing else of the installation reaches it. The bot's token and the
chat ids it answers live in the world's `secrets/`, mounted into that container alone, so a message
from any other chat is dropped unread. The gateway is reactive and has no desires — the service
0.1.0's [trust-boundary](/decisions/0.1.0/trust-boundary.md) called a gateway, built at last for
the one party outside the society that may ask.

**An agent gives an account of itself.** An *account* is what an agent says of itself for a person:
what it observes, what it wants, what it plans and what it is doing, in the dictionary's words
([ubiquitous language](/decisions/the-knowledge-is-filed-like-the-code.md)) — a want named for its
desire, its state and the instant it is minted for; a plan as its steps with their actions, values
and landings; an intention at the step it stands at; each observation with its reading, side and
when the next is due. Each [part](/domain/kernel/part.md) answers its own, duck-typed as `link`,
`start` and `stop` are and as an event answers its `point`: sensing accounts for its observations,
planning for its wants and plans, execution for its intentions, and a part with nothing to say has
no such method. The account part — an `account` package of `agent/`, beside `history/` and `metrics/`, created
where the world names a chat — hears the runtime's pass, asks every part, and publishes the text
retained on the agent's own account topic when it differs from the last. Retained, so a gateway
that restarts finds every agent's latest without asking anybody; on change, so a quiet agent costs
the bus nothing. The account is **telemetry and never a belief**: no plan branches on what the agent
said of itself, so by [model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)
it is written nowhere in the store, and the part that writes it imports no package's words, as
history and metrics import none ([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).
It is prose by templates, not a document: the gateway knows no package's words at all, and a
person reads it as it is.

**A command costs nothing, and a free question costs one call.** The gateway holds the latest
account of every agent of the world. `/agents` lists them; `/account grower` relays the grower's
as it was published; `/wants`, `/plans`, `/doing` relay one section of every account. None of that
touches a model. A message that is not a command is a free question, and the gateway answers it by
one call: a system prompt that explains the account's form in the dictionary's words, stable so the
cache holds it; the accounts of the agents the question names, or all where it names none; and the
question. The model is told what it is reading and asked to answer from it and say when the account
does not say. **Where the gateway is given no model, a free question is answered with the commands
it understands** — the chat works, and the model is a convenience bought by a key.

**The model phrases and decides nothing.** It is handed text and returns text. It runs no query
against any store, it authors no belief, it names no step, it reaches no agent; nothing it writes
enters the society. That is the constraint every 0.1.0 record on the model fixed — "a move from
the menu and never free text-to-action" — met here by giving the model no menu at all. And the
sovereign's words never reach an agent's mind either: a question stops at the gateway, which asks
nobody. The one way a person's word reaches an agent is the second direction below, as a document
`heard` believes, and `heard` refuses everything that is not a state of the world.

**Two directions, two paths, one gateway.** What an agent *accounts* of itself is telemetry, out
through the account topic. What an agent *says* to its sovereign — "the terrace probe needs
recalibrating, ready?" — is speech: an `execution:Saying` of a step, to the chat as a peer the
society names, believed as said and told through the transport as any document is
([speech](/domain/speech/speech.md)); the gateway renders it with its buttons, and a press is a
document the person said, heard as a peer's word. That is #862's protocol, and this record makes
room for it and designs none of it: the chat is a client of the society, so `orexis-mqtt` grants it
what the wiring implies — today `_TOLD_Q` grants writes on an agent's listen topic to agents alone,
and the chat's read of every account topic and its write for a press are two rows for the grant to
add. The gateway is the one process both directions share; neither is the other.

**The model is a shared service of the installation, and its key is the installation's secret.**
`infra/installation.ttl` says where the shared services are — the series store, the images —
and the model joins them: which model, as a deployment fact the gateway is told through its
environment, never named in code. The key lives in `infra/secrets/` beside the admin token, is
mounted into the gateway alone, and no agent ever holds it: an agent image carries no model client,
exactly as it carries no onboarding. Telegram's token is the world's — one bot, one world — and
lives in the world's `secrets/`, as its location does.

# What it costs

An account is a handful of lines per want, intention and observation — one to two kilobytes for an
agent of the greenhouse's size, some five hundred tokens. A free question over a three-agent world
is therefore about two thousand input tokens, most of them the accounts, and a short answer; at the
first-party rates cached 2026-09-25:

| model | input $/M | output $/M | a question, ~2k in, ~150 out |
|---|---|---|---|
| `claude-opus-5-5` | 4.00 | 20.00 | about one cent |
| `claude-haiku-4-5` | 1.00 | 5.00 | about a quarter of a cent |

The commands cost nothing, the account is published only on change, and the system prompt is
cached. The cheapness is the architecture's — no model in the loop, no model for a readout — and
which model is a dial the installation turns; the default is the current Opus, and a sovereign who
asks often sets Haiku.

# What was refused

- **A model inside the agent.** 0.1.0's `deliberation:Consulting`, a member of the mind consulted
  at the edge of knowledge. Nothing here needs it: a readout is the person's side, not the agent's,
  and a model in the agent is a key per agent, a client in every image and a cost per pass for a
  question asked a few times a day. The seam stays where 0.1.0 left it — a model proposing a
  belief the shapes refuse — and is not opened by this.
- **A question reaching the agent.** Request and response over the bus: the gateway asks, the agent
  answers from its store. It needs a protocol, a door into the agent for a person's text and an
  answer that is lost when the gateway is down. The account is published whether anyone asks, and
  retained, so the gateway asks nobody and a restart loses nothing.
- **The present reconstructed from the series.** The gateway could read InfluxDB — Grafana does —
  and the history already carries observations and steps. But a want, a plan and an intention are
  not history, and "a series read back is no longer a series": the store holds what stands, and a
  second reader deriving the present from what happened is a second present.
- **The model writing SPARQL.** A question translated to a query over the store would be the one
  free-text-to-action this project refuses everywhere, with the `GRAPH` trap and an unbounded cost
  for company. The model reads words an agent wrote; it writes none the agent reads.
- **A bot per agent.** Telegram's `getUpdates` is one consumer per token, so two agents polling one
  bot conflict and the sovereign would otherwise hold a bot per agent. One bot is the world's, and
  the gateway is why.
- **A gateway spanning worlds.** It would hold a credential on every world's broker — Grafana's
  position, a read-token across every bucket — and a world's secrets would meet in one container.
  One process per world, as the simulator is; the trigger for revisiting is a sovereign of several
  worlds who wants one chat, and the answer then is a bot per world in one Telegram, not one
  process.

# Seams left open

- **The gateway says nothing of its own accord.** It answers; it does not announce a plan
  published or an intention failed. Pushing a changed section of an account to the chat on
  `/watch` is a line in the gateway, once a sovereign wants it.
- **The past is not in the account.** "What did you see yesterday" is the history's, and a tool the
  model may call to read an agent's history bucket — a read token, as Grafana's — is buildable;
  not here, since the account is the present. The season is reflection's, decided the same day:
  [reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)
  reads the series for what a season says of the agent and offers a proposal, and never asks it
  for the present, which is this record's refusal kept.
- **The account's form is each package's, and nothing holds the prose to the store.** The same debt
  the bundle carries (the-knowledge-is-filed-like-the-code): a template that says `Searching` for a
  want the planner now calls otherwise rots in the present tense. A case per part that renders a
  fixture store and compares the text is what keeps it.
- **Which peer spoke** is still untold apart in speech, and a press from the chat is believed as
  any peer's word; signing is the seam that closes it, as speech says.

# What this emits

Three issues, to be filed in this order, each with its definition of done; #862 is the fourth and
already stands:

1. *Let an agent give an account of itself* — the kernel word, an `account` package of `agent/`, each part's
   `account()` in its package's words, published retained on change. Done when the greenhouse's
   grower publishes an account a person can read, tested against a fixture store per part.
2. *A chat gateway per world* — the `chat/` tree and `orexis-chat <world>`, Telegram over its Bot
   API with no library beyond the standard one, the commands, and the one model call where a key is
   given. Done when `/account grower` relays the account and a free question is answered from it.
3. *Onboarding grants the chat* — the society names the chat as a client, `orexis-mqtt` mints its
   credential and derives its grants, `orexis-compose` adds its service where the society names one,
   `infra/installation.ttl` names the model. Done when `orexis-onboard greenhouse` deploys the
   gateway and nothing by hand.
