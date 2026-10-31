---
type: Domain Concept
title: Requirement
term: http://example.org/orexis/onboarding#RequirementGraph
description: >-
  What a world must state of a package's or a domain's words, as SHACL shapes the owner of the
  words ships beside its ontology, in a graph of onboarding's kind. Onboarding holds a world to
  every one before anything is granted; no agent loads one.
---

# What it is

A requirement is a package's word about what a document using its terms must say: a sensor
observes a property and is mounted on something, an observer role reads a sensor, a desire carries
one of its two tests. It is a SHACL shape, and the package or domain owning the words ships it in a
`requirements.ttl` beside its `ontology.ttl`, as `agent/sensing/requirements.ttl` and
`domains/market/requirements.ttl` do. A domain imports it from its ontology, as it imports its
actions and rules. A world whose words are its own ships its requirements the same way, a
`requirements.ttl` beside its `world.ttl`, and they are held exactly as a package's are: a word is
held to what its owner says of it, and a world owns its own. Onboarding ships its own too: limits that
are its own, what tells a world's brokers apart and gives each client the address it is told — a
broker asserting a url asserts a plain one, since a board is flashed and the simulator started with
the plain port, and a client that is no agent is connected to one broker the society names as one —
and what is stated in two packages' words neither may speak of the other — an observer reading a sensor
over MQTT is connected to a broker the sensor's client is.

A refusal a renderer wrote by hand is a requirement's to make, and the renderer only formats. Each
of `orexis-mqtt`, `orexis-compose` and `orexis-firmware` once refused what it read as it read it — a
client connected to no broker, a world's simulated systems hosted by two clients, a sentinel's probe
with no cadence — and each such refusal is a shape now, shipped by whoever owns the words: the
simulation domain's, that every simulated system is hosted by one client, the simulator's own; sensing's,
that a sensor states one `ssn-system:Frequency`, and that its [scaling](/domain/sensing/scaling.md) is
two points apart, which the generator read to size a wake window and sensing's rule reads to conclude a
quantity. What a renderer passed over in silence became a
requirement the same way — a simulated system hosted by no client, which a simulator was started for
and never played; and a person who speaks to an agent is held the same way by the transport's, before
`orexis-compose` picks the client the translator connects as: hosted by one client, with an address of
some kind and one of each, listening on an inbox, speaking to an agent that listens on one, and a client
they speak through saying on one topic and hearing on one. The installation's reader refused its document by hand in the same way, a check per
reading — two stores, a store with no organisation, a view over no TLS — and each is a shape now,
judged once as the document is read. What stays in a renderer is what no document can answer: a
credential not yet minted, a port the installation has not allocated, a monitored world where the
installation serves metrics from no store or a person named where it names no model, which is two
documents' word — and what is said in a word
no vocabulary declares: which board is a sentinel is its hardware graph's `mc:firmware`, so that a
sentinel's subject states a range is the firmware generator's to refuse, there being no owner to ship
the shape.

A requirement is not a [shape](/domain/planning/shape.md) in planning's sense. A met-test says what
an agent wants of the world it believes, and the agent judges it every pass. A requirement says
what a sovereign must have written for the world to be read at all, and it is judged once, before
the world is believed.

# Who reads it

[Onboarding](/domain/onboarding/onboarding.md) alone, which is why the graph's kind is onboarding's,
declared in `onboarding/ontology.ttl` beside the [deployment](/domain/onboarding/deployment.md)
graph's. An agent's boot passes over a kind its vocabulary does not declare, so its store holds no
requirement: what an agent holds is accepted and revised once it runs, and only a sovereign's
document, before it is believed, may be refused. Every one of onboarding's tools asks for the
judgment before it renders anything, called alone or in turn, so none of them judges a world itself.

What is judged is what each agent will believe: its boot, the world's common beliefs with its own
documents beside them. So a world's document may leave a fact about a shared thing to the agents'
own, and an agent whose own documents complete it is not refused. The common beliefs are judged
alone only to say a fault once: one they break and every agent's boot breaks too is the world's,
and the rest is each agent's that reports it. The world's deployment graph is judged beside either,
being no belief and the world's alone.

Onboarding reads the requirements off the world, which knows every package's vocabulary, and never
off an agent's boot, which loads only what the agent's roles do: an agent playing an executor alone
loads no planning, and the requirement refusing it is planning's.

The [installation](/domain/onboarding/deployment.md) ships its own, `infra/requirements.ttl` beside
its document, as a world ships its own beside `world.ttl`, and is held to them as the document is
read, so every tool reading it refuses one that does not hold and none judges it: one series store
and one view, each with one url of the scheme the template serves it over and one image, the store
with one organisation; history served by a store; one retention and one window per purpose; and one
pool, each url of it with a host and a port. Two of onboarding's own are judged of it beside them:
that no url carries a credential — the deployment page says why — judged of a world's deployment
too; and that one port on one host is held by one listener: of a world it refuses two of its brokers on one
port; of the installation, before a port is allocated, a broker on another world's port or on a
service's, judged over every url the installation holds. The shape targets the listener and asks only
a url of what it clashes with, so it is one requirement at both grains.

# What a rule fills

A requirement may carry a `sh:rule` beside its constraints, and the rule fills what the constraint
would otherwise refuse: `orexis-onboard` runs the rules over a world's asserted documents, writes what
they made as a derived document, and judges the world with it in — so what remains unmet is garbage,
and what a rule could complete is completed, by the same shape. The first is a topic's name. A society
states that a sensor publishes on a topic, a device takes commands on one, an agent listens on one —
the MQTT4SSN topic node both ends name — and no filter, since which name a topic goes by matters to
nobody and that both ends agree matters to everyone. Onboarding's rule names each by its principal and
its purpose: `sensors/<client>/reading` for what a board publishes, one topic however many sensors it
carries, each reading its own value of the one document by pointer; `sensors/<client>/command` for
what the board listens to; `actuators/<device>/command` for a device a client hosts;
`agents/<id>/inbox`; `people/<person>/inbox` for a person the
[translator](/domain/speech/translator.md) speaks for, with `people/<person>/says` and
`people/<person>/hears` for a client of their own they speak through. It writes them to `society.derived.ttl` beside the society, a society graph every
reader reads as the society — the [transport](/domain/transport/transport.md), the simulator, the
ACL, a board's `config.h` — and nothing computes a name. A filter a world asserts is kept and the rule
writes none for it; what the derived document leaves unnamed, a topic nothing publishes on or listens
to, and what it names twice or names alike, is refused. The committed document is held to a fresh
derivation, as the installation's allocation is.

# What stays in the ontology

What an agent reads as it runs stays in the vocabulary it loads. The observer's limits are the one
case: what holds of `sensing:silentAfter` and `sensing:stuckAfter` where a role states none is a
`sh:defaultValue` on a shape in sensing's ontology, which the stuck rule reads there. That shape
refuses nothing; the observer's refusals are its requirement's.
