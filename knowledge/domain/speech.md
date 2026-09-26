---
type: Service
title: Speech
description: >-
  What a peer says to an agent and what the agent says, both DOCUMENTS — TriG naming its graphs
  and saying what each one is, as a world's files do. `heard` believes a peer's document where
  every graph it holds is a state of the world and replaces only what a peer said; `said`
  believes what the agent told a peer. Neither concludes anything; the rules do.
---

# What it is

`agent/speech/` is the translation row for a peer's word, beside [sensing](/domain/sensing.md)'s
for an instrument's. A message from a peer is a speech act and not an observation
([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)), and in
Agent 0.2.0 it is already a document when it arrives: its graphs are named, and its default graph
says what each one is. So there is no pipeline, only a door.

- **`heard(store, me, payload)`** believes a document a transport received on the agent's own
  topic. Every graph in it must be a kind beneath `orexis:StateGraph` — a peer reports what IS,
  never a desire, an action or a rule — and a graph of the same name already held must have
  arrived `orexis:Received`, so a host saying its round again replaces the round its bidders
  hold, and no peer rewrites what the agent said or its world asserts. A document failing either
  is refused whole, in the log.
- **`said(store, me, doc)`** believes what the agent told a peer, `orexis:Recorded` and its own,
  replacing only what it said before. What a host said is its ledger: the round it opened, the
  claims it issued.

# Where documents come from and go

An [action](/domain/action.md) that tells somebody something has an `execution:Saying` among the
operations of its [implementation](/domain/implementation.md), a CONSTRUCT run over the present
when a [step](/domain/step.md) filling it is taken; an IRI its result says is
`execution:to` an agent is a graph, what it says of that IRI is the graph's content, and its kind
and period are the rows. The runtime believes each document as said, revises it, and hands it to
the [transport](/domain/transport.md), which publishes it on the topic the peer listens to.

# What it does not do

It concludes nothing. What a document means — a venue open, a call answered, a claim held — is a
[revision](/domain/revision.md) the rules conclude, and the runtime revises every graph it writes
beside public knowledge alone, so a conclusion lives in the revision of the document it is about
and goes when that document is said again. Which peer spoke is not told apart, since the
transport does not say: two bidders on one venue could each say the other's bid again. That is
the seam signing closes, and nothing signs yet.
