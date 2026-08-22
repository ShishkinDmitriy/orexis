---
type: Decision
title: Channel is the word, and stream was the same thing's second name
status: accepted
timestamp: 2026-08-22T00:00:00Z
description: >-
  The derived per-topic node was called channel and stream interchangeably — inside one
  decision record, inside one rdfs:comment, inside one page of sensing. The T-Box declares
  mqtt:Channel, so channel is the word; stream is demoted to plain English for flows that are
  not the node. Found by the ubiquitous-language audit, beside mandate/Commitment; the two
  rulings differ in direction — there the prose word won and the ontology moved, here the
  ontology word won and the prose moved — because in both cases the winner is wherever one
  meaning already lived.
---

# Context

The ubiquitous-language audit cross-referenced the dictionary, the ontologies and the code,
looking for one concept under two names. The derived per-topic node failed hardest: the record
that introduced it is titled *"a stream is a thing"* and derives an `mqtt:Channel` in its first
paragraph; the class's own `rdfs:comment` opened *"One named stream on a bus"*; and
`sensing.md` used both words in one sentence. Nobody chose the split — the decision's title
used the English word for the idea and the ontology used the word the code wanted, and neither
noticed the other.

# Decision

**Channel.** The T-Box declares `mqtt:Channel`, `mqtt:channelTopic`, `mqtt:publishesOn` and
`mqtt:listensOn`, and rule 1 means every query and every rule already says channel — so the
prose moves to the code's word, the cheap direction. The dictionary gains
[channel](../domain/channel.md), the interleaved passages in `sensing.md` and the two
`rdfs:comment`s now say channel, and *stream* survives only as plain English for a flow that is
not this node (an agent's annotation stream in Grafana is not an `mqtt:Channel`).

Note the direction is the opposite of
[a-mandate-is-not-a-commitment](a-mandate-is-not-a-commitment.md), decided the same day: there
the ontology moved to the prose word. The rule is not "the ontology wins" or "the prose wins" —
it is that the winner is wherever ONE meaning already lives. *Channel* meant one thing
everywhere it appeared; *Commitment* meant three.

# What does not change

The record `a-stream-is-a-thing` keeps its title — a decision is history, and its argument is
untouched by what the thing is called. Its body already said channel wherever it touched the
term.
