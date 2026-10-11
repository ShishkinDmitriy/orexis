---
type: Service
title: Speech
description: >-
  What a peer says to an agent and what the agent says, both DOCUMENTS - TriG naming its graphs
  and saying what each one is, as a world's files do. `heard` keeps a peer's document as statements,
  replacing only what a peer said; `said` keeps what the agent told a peer the same way. What the
  agent believes of either is what an extraction concludes, run by speech over each statement alone.
---

# What it is

`agent/speech/` is the translation row for a peer's word, beside [sensing](/domain/sensing/sensing.md)'s
for an instrument's. A message from a peer is a speech act and not an observation
([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)), and in
Agent 0.2.0 it is already a document when it arrives: its graphs are named, and its default graph
says what each one is. So there is no pipeline, only a door. It is loaded for an agent declared a
[speaker](/domain/speech/speaker.md), and for no other.

- **`heard(store, me, payload)`** keeps a document a transport received on the agent's own topic, as
  [statements](/domain/speech/statement.md): every graph it names, whatever kind it says, arrived
  `orexis:Received` and the agent's own. A graph of the same name already held must have arrived
  received too, so a host saying its round again replaces the round its bidders hold, and no peer
  rewrites what the agent said or its world asserts. A document that is none, or says whose a graph is
  or who the self is, is refused whole, in the log. No kind it says is refused: what is kept is what was
  said.
- **`said(store, me, doc)`** keeps what the agent told a peer the same way, `orexis:Recorded` and its
  own, replacing only what it said before.
- **`extract(store, statement)`** is what the agent comes to believe of either: every
  [extraction](/domain/speech/extraction.md) a domain ships, run over the statement alone, into one
  belief graph derived from it. Speech's part runs it for every statement written, heard or said, so a
  host believes the round it opened by the path its bidders believe the round they heard.

# Where documents come from and go

An [action](/domain/kernel/action.md) that tells somebody something has an `execution:Saying` among the
operations of its [implementation](/domain/execution/implementation.md), a CONSTRUCT run over the present
when a [step](/domain/execution/step.md) filling it is taken; an IRI its result says is
`execution:to` an agent is a graph, what it says of that IRI is the graph's content, and its kind
and period are the rows. Taking the step is the executor's `said` [signal](/domain/kernel/signal.md),
which speech's part, linked to execution's, hears: it keeps the document as said — and extracts from it,
as from what it hears — and hands it, for each agent it is to, to the
[transport](/domain/transport/transport.md) reaching the peer, which publishes it on the topic the peer
listens to.

# What it does not do

It concludes nothing past the extraction. What a document means — a venue open, a call answered, a
claim held — is a [revision](/domain/belief/revision.md) the rules conclude of the belief extracted from
it, beside what the world states and never beside another peer's word, so a conclusion lives with the
statement it is about and goes when that statement is said again. Which peer spoke is not told apart, since the
transport does not say: two bidders on one venue could each say the other's bid again. That is
the seam signing closes, and nothing signs yet.
