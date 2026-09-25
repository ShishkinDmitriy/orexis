---
type: Domain Concept
title: Channel
term: http://example.org/orexis/mqtt#Channel
description: >-
  One named message flow on a bus, as a node — derived from the topics devices already state,
  one per distinct string, so it is discovered rather than authored. It bears the encoding,
  because one topic carries one format however many parties read it; direction lives on the
  relations to it, never in its identity. The transport's own term, and "stream" is the same
  thing's retired name.
---

# What it is

A **channel** is one named message flow on a bus, made a node: `mqtt:Channel`, derived at
genesis from the topics a world's devices already state, one node per distinct string. Nothing
authors one — a world that names a topic twice has one channel and can see that it does, where
two equal literals were only coincidentally alike. The argument for reifying it, and the IRI
scheme that keeps two topics from silently merging, is
[a-stream-is-a-thing](/decisions/a-stream-is-a-thing.md).

# What it bears

**The encoding.** One topic carries one format however many sensors publish into it or agents
read out of it, so `codec:decodedBy` sits on the channel and a shape can refuse two encodings
on one — a claim no sensor-borne fact could make, because a command channel has no sensor at
all. How bytes then become a quantity, and why the scaling stays the sensor's while the codec
is the channel's, is [sensing](/domain/sensing.md)'s and
[bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md)'s.

# Direction is on the relation

A channel is one thing however many parties use it. Who sends and who receives are the
relations `mqtt:publishesOn` and `mqtt:listensOn`, never part of the channel's identity — the
same directed pairs a principal's broker grants have always been, written as a graph instead of
an ACL.

# Scoped by its bus

A channel name means nothing without the `mqtt:MessageBus` it is on, which the world states
too. And the term is deliberately the transport's rather than the kernel's: its premise —
topics — is MQTT's, so a REST binding would derive channels of its own from URLs, and only the
day that exists is the day a transport-neutral class earns its place.

# One word

The concept had two names, and the losing one is worth recording because it is still in old
titles: *stream*. [channel-is-the-word](/decisions/channel-is-the-word.md) ruled — the T-Box
declares `mqtt:Channel`, so discussion says channel, and *stream* survives only as plain
English for flows that are not this node.

# In Agent 0.2.0, a channel is a topic named by its filter

The MQTT transport of `agent/` has no channel node of its own: what this page calls a channel is a
`mqtt4ssn:Topic`, reached through the `mqtt4ssn:TopicFilter` that matches it and carries the one
string the protocol needs, and whether a message on a topic is a sensor's is MQTT's own filter
matching, `+` for one level and `#` for the rest. See [transport](/domain/transport.md).
