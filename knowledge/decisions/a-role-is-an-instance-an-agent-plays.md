---
type: Decision
title: A role is an instance an agent plays, in a context and over a period, and never its type
description: >-
  The sovereign, 2026-10-11 - a type is what a thing is for its whole life; a student, an employee, a
  patient is something it plays, bound in time, and nothing stops it playing several at once, a
  student of two schools. Roles were stated as rdf:type of the agent. Decided - a role is an instance
  the agent declares it plays (orexis:plays), anonymous unless something must refer to it, carrying its own context and what
  belongs to it - the venue it hosts and the valve it serves through, the venue it bids in and the
  price it bids, the sensors it observes - and holding
  over the period of the graph it is stated in. The role classes stay, as the classes of role
  instances, so the boot loads packages by the same closure one hop further. The relation a role was
  founded on becomes the role's own property, so market:hosts and market:bidsIn fold into it. Whether
  a peer sees a role is where it is stated, a document every agent of the world is given or the
  agent's own self graph. Refused - roles as types of the agent, package roles kept as types beside
  role instances, a link from the role to its player, and a role's period stated on the instance with
  machinery of its own. Amended 2026-10-12 - an observer's silent and stuck limits are its role's,
  the observer shape's default where none is stated, where they were stances with a constant in code.
status: accepted
timestamp: 2026-10-11T12:00:00Z
---

# Context

[a-package-is-loaded-only-for-a-role-the-agent-is-declared-in](/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md)
made roles declared, never derived, and grounded them in OntoClean: a role is anti-rigid, since its
holder can stop holding it. But it modelled a role as a TYPE of the agent, `:supplier a orexis:Self ,
market:Host`, with `orexis:Role` beneath `orexis:Agent`. A type is what a thing is for its whole
life, as a person is a person from birth to death; a role is what it plays: a student, an employee,
a patient. Three things a role has, a type cannot:

- **A context.** A student is a student OF a school. The host role was "founded on" `market:hosts`,
  a second fact beside the type, and onboarding had to hold the two in agreement.
- **More than one at once.** A student of two schools, a patient of two doctors. As a type, an agent
  is a host once, however many venues it holds, and what differs per venue had nowhere to live. Read
  off the market's actions on 2026-10-11: Serving picks its valve as whatever device reaches the
  holder's subject, so a host of two venues would dose through the wrong one; and a bid reads one
  `market:valuePerL` off the agent, so a bidder in two venues bids one price in both.
- **A period.** A role begins and ends. A type holds as long as the thing does.

# The decision

**A role is an instance the agent plays.**

```turtle
:supplier orexis:plays
    [ a market:Host ;   market:onVenue :water ; actuation:through :water_valve ] ,
    [ a market:Bidder ; market:onVenue :feed ;  market:valuePerL 0.8 ] .
```

- **`orexis:plays`**, the kernel's, from the agent to a role it plays: the agent declares its roles,
  as it declares what it is (`orexis:Self`) in the same document. The boot reads it before any
  package is loaded, so it is a word packages meet at.
- **A role is anonymous unless something must refer to it.** A blank node is enough for a role that
  is only played; it is named where another statement points at it, as a claim might name the host
  role that served it. A blank node is copied as itself wherever quads are copied (the imaginarium is
  filled by quads, not text), and a graph's hash is canonical over blank nodes.
- **What belongs to the role is the role's.** Its context (`market:onVenue`) and what it plays with
  there: the device a host serves through, the price a bidder bids. Two venues are two roles, each
  with its own.
- **The relation a role was founded on becomes the role's own property.** `market:hosts` and
  `market:bidsIn` fold into the role's `market:onVenue`: a bidder finds a venue's host by the host
  role on it, and there is one fact where there were two to keep in agreement.
- **A package role is an instance too, and carries its context where it has one.** An observer's
  is the sensors it reads: `:fern_agent orexis:plays [ a sensing:Observer ; sensing:sensor :probe ]`.
  Which sensors report to an agent is then declared, where today it is derived: a sensor hosted by
  what the agent acts for, by a sample of it, or by a place containing it (the observer's shape in
  `agent/sensing/ontology.ttl`). Derived, a probe moved into a pot the agent acts for became its
  sensor without anyone saying so, which is the premise-derived loading the role record refused, one
  level down. A role with nothing to point at, a predictor or a planner, carries none, and a role's
  shape says what it needs: the host's asks for its venue, the observer's for a sensor.

**The role classes stay, as the classes of role instances.** `market:Host rdfs:subClassOf
planning:Planner , execution:Executor , speech:Speaker , belief:Deliberator` now reads as a statement
about roles: a host role is a planner role and the rest. `orexis:Role` is the class every role class
is beneath, and no longer beneath `orexis:Agent`: a role is not an agent, it is played by one. The
boot finds every role the self plays, takes their classes, closes them and loads the packages whose
ontologies declare one, which is today's closure one hop further. `orexis:Self` stays a type, since
being itself is the one thing the agent is for its whole life
([the-self-is-a-class-held-to-one-instance](/decisions/the-self-is-a-class-held-to-one-instance.md)).

**A role holds over the period of the graph it is stated in**, as everything that ends by the clock
does here. A role with no end is stated in a document with no period; a role that begins or ends is
stated in a graph of its own, with the period it holds over. A reader standing at an instant is handed
the graphs holding then, so an action's precondition or a desire that asks for the role the agent
plays reads only the roles holding at that instant.

**The period bounds what the agent does, never what it runs.** The boot loads the packages for every
role the self plays, whenever it holds. A host whose role has ended stops offering rounds, because no
host role holds and its actions admit nothing; nothing is unloaded.

**Whether a peer sees a role is where it is stated.** Some roles a peer must address: a bidder must
find a venue's host to call it, which is why `market:hosts` was public. Others no peer reads: what an
agent observes or predicts. The first are stated in a document every agent of the world is given, the
society; the second in the agent's own self graph. There is no kind for "visible": since
[the-state-is-what-a-scope-can-change-and-everything-known-is-belief](/decisions/the-state-is-what-a-scope-can-change-and-everything-known-is-belief.md)
what a graph says is belief, and who holds it is which documents each agent is given. The test for
where a role goes is the one the role record already set: a peer is given a role only where a plan of
the peer's would branch on it
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).

**A role is read only as asserted**, as #952 decided for what defines what the agent can do: a peer's
document saying a role is believed as what the peer said and loads nothing, and no precondition takes
a role from it.

# Why

**One concept, one shape.** The role and the relation it was founded on were one thing stated twice,
and the second statement was where everything per-context was forced to live or had no home at all.
As an instance the role carries its context and what belongs to it.

**It is what the ontologies that model roles do.** A role played in a context and over a time is the
pattern of the W3C ORG ontology's `org:Membership` (a member, an organization, a role, `org:memberDuring`),
of PROV's qualified association with `prov:hadRole`, and of UFO's qua individuals and relators
(Guizzardi, 2005), in which an anti-rigid role type is instantiated by the role and not by its player.
The role record's OntoClean grounding stands; it is applied one level up.

# What was refused

- **A role as a type of the agent**, today's. It cannot carry a context, cannot be played twice, and
  has no period short of the agent's whole life.
- **Package roles kept as types beside role instances.** They begin and end as a host does, the
  observer has a context of its own, its sensors, and two mechanisms for one concept is the synonym
  the dictionary refuses.
- **A link from the role to its player** (`orexis:playedBy`), as first drafted. The agent declares
  what it plays beside what it is, so the link runs from the agent; and a role pointing at its player
  must be named to be found from the agent's side, where an anonymous role is enough.
- **A role's period stated on the role with machinery of its own**, `orexis:during` read by every
  reader that asks for a role. The project already has one way something holds for a stretch, a
  graph's period handed out by `graphs_of`, and a second would be read by some readers and not others.
- **A visibility flag on a role.** Who is given a document is deployment, and a flag would be a kind
  saying how a graph is shared, which #952 removed.

# Seams left open

- **A role stated after birth.** The self graph is the agent's own, so a role added for a running
  agent still reaches it only on a fresh volume; the role record's seam stands, and the trigger with
  it. A role whose period begins later is no such case, since its packages are loaded at birth.
- **A role given by another agent.** An employer appointing an employee is a role one agent states
  of another. A peer's role is read only as asserted here, so nothing can be appointed at runtime.
  **The trigger: the first world where one agent's act gives another a role.**

# An observer's limits are its role's (amended 2026-10-12)

How long a sensor may be silent or stuck, `sensing:silentAfter` and `sensing:stuckAfter`, were
[stances](/domain/kernel/stance.md), one figure for every sensor the agent heard, and where the self
graph stated none a constant in `missed` and `received` held — and a literal six in the stuck rule,
which reads the figure too and could not import a constant, so the one figure lived in two places held
equal by a test. Decided: **a limit is a figure about what a role is over, so the observer role states
it** beside the sensors it reads, and where a role states none **the observer shape's `sh:defaultValue`
holds**, in sensing's ontology, which Python and the rule both read. A sensor judged by another figure
is read by another observer role, as two venues are two host roles.

Refused: the limits kept as stances, since a figure the agent holds about one of its sensors is not its
word about itself, and one figure for all its sensors is the per-context value this record exists to
give a home; and the default kept in code, since a rule cannot read it, and a default in two places is
the drift a test was holding back. The other stances keep their constants in code: nothing but Python
reads them.

# How it is built

The first step is built: `orexis:plays` and the role classes no longer beneath `orexis:Agent`, the boot
reading the classes of the roles played, every world's self graph rewritten, and the observer's role
carrying its sensors (`sensing:sensor`) and its limits. Which sensors are an agent's is declared: the
transports ask sensing for them (`cadence.sensors`), the broker's ACL is derived from them, and
onboarding holds them to where they are mounted, both ways.

Left: the market's roles carrying their venue, their valve and their price, with `market:hosts` and
`market:bidsIn` retired and Serving and Bidding reading the role. A world in which one agent hosts one
venue and bids in another is the test that it holds.

Once that is built, this supersedes in part the [role](/domain/kernel/role.md),
[host](/domain/market/host.md) and [bidder](/domain/market/bidder.md) pages' remaining account of the
relations a role was founded on; the role record (the role as a type of the agent, `orexis:Role`
beneath `orexis:Agent`) and the stance record (a sensor's limits as stances) are superseded in part
already.
