---
type: Decision
title: A role needs something to be a role in, and there is deliberately no auction
description: >-
  Market positions stay predicates rather than becoming first-class roles. Both places this
  project already models a role — a pin's role and a user's role in ratifying a world — hang
  it off a context object, and an auction has none on purpose. A role with nothing to be a
  role in is a second spelling of a predicate. The trigger for revisiting is precise: the day
  an auction becomes an object in the graph.
status: accepted
timestamp: 2026-08-10T00:00:00Z
---

# Context

Three positions exist in a market, and they are expressed three different ways:

| position | how it is expressed |
|---|---|
| host | `market:hosts <market>` — a predicate on the agent |
| bidder | `market:bidsIn <market>` — a predicate on the agent |
| clearing validator | **nothing** — `agent/clearing.py` is a function; no agent holds the position |

That looks like an inconsistency waiting to be tidied into a vocabulary of roles, and the project
already models roles twice, so the machinery would not have to be invented. The question is whether
a role should be a **thing** here — `market:Host`, `market:Bidder`, an agent `fillsRole` in a
context — rather than a predicate plus the capability derived from it.

The question is sharper than it first looks, because
[bid-matching-is-a-capability](bid-matching-is-a-capability.md) left a seam that seems to demand
roles: **owning the venue is structural, convening an auction is per-auction.** If the host rotates
with whichever side is short, then "host" cannot be a standing fact about an agent — it is
something an agent *is*, for the duration of one auction. That is exactly the shape a role has and a
predicate does not.

# Decision — positions stay predicates, and the trigger is written down

No `market:Role`, no `fillsRole`, no role objects. `market:hosts` and `market:bidsIn` stay as they
are, and the capabilities derived from them stay the answer to *what is this agent allowed to do
here*.

**The trigger for revisiting is not "when it feels untidy". It is the day an auction becomes an
object in the graph.** That is a different decision, recorded elsewhere and currently refused, and
this record depends on it rather than restating it.

# Why: both roles we already model hang off a context object

This is the whole argument, and it is not an analogy — it is the same fact twice.

**A pin's role.** `mc:PinRole` is first-class: `mc:pinRole` has `mc:Pin` for its domain, and a pin
is an object with a GPIO number and a rail voltage. [pins-and-wires](pins-and-wires.md) made it
first-class for a stated reason, in `packages/orexis-part-microcontroller/ontology.ttl`:

> `orexis:pin [ mc:pinRole mc:AnalogInPinRole ; mc:gpio 34 ]` used to say in one node, and the length
> is the point: **the old form fused two facts about two different objects.**

The role became a thing because there was a **pin** for it to be a role of. Before `mc:Pin`
existed there was nothing to attach it to, and the fused form was what people wrote.

**A user's role.** `prov:hadRole` is used in `agent_old/provenance.py`, and it hangs off a
`prov:Association` — a node standing for *this agent's involvement in this activity*. PROV-O has
the qualified pattern precisely because a role is meaningless free-floating: you are not a
ratifier, you are a ratifier **of** something.

**And an auction has no object.** [auction](/domain/auction.md) says so deliberately: an auction is
a process, it condenses and dissolves, and *there is no `orexis:Auction` to point at — looking for one
is the usual sign that a market fact and an auction fact have been confused.* So a per-auction role has
nothing to be a role in. Making one first-class today would mean either:

- attaching it to the **market**, which is structural — and then it is `market:hosts` with more
  syntax, saying nothing the predicate did not; or
- inventing `orexis:Auction` to attach it to, which is a decision already taken the other way, and
  taking it as a side effect of a vocabulary tidy-up is the worst way to take it.

**And a W3C Recommendation says the same thing in as many words.** The Organization Ontology
(`org:`, `http://www.w3.org/ns/org#`, Recommendation of 16 January 2014) does not attach a role to
an agent either. It introduces `org:Membership` as an n-ary node carrying `org:member`,
`org:organization` and `org:role`, and explains why:

> The situation of an Agent fulfilling that role within an organization is then expressed through
> instances of the `org:Membership` n-ary relationship. This also makes it possible to annotate the
> relationship with qualifying information such as duration, salary, reference to the employment
> contract and so forth.

*Duration* is the word that matters here. A membership is annotatable precisely because it is a
node, and "for the length of this auction" is exactly the annotation a rotating host would need —
on a node we do not have.

Three precedents, one rule: **a role is a fact about a relationship, so it needs the relationship
to exist as a node.** Where the node exists, roles earn their place. Where it does not, they are a
second spelling.

**So when the trigger fires, the shape is off the shelf.** `org:` is small — `Role`, `Membership`,
`member`, `organization` — and importing four terms is nothing like importing an accounting
ontology (see [settlement-speaks-rea](settlement-speaks-rea.md) for why that distinction is about
the hand-materialised RDFS closure). Nothing is imported today, because there is no membership to
represent while positions are standing facts.

# The predicate already does the work a role is wanted for

The intuition behind roles is that a position is *contextual* — an agent is a host **here** and a
bidder **there**, and a flag on the agent cannot say that. That is true of a flag. It is not true
of what is written, because the predicate's object carries the context.

An agent stating `market:hosts A ; market:bidsIn B` is handled correctly today, and by construction
rather than by luck. `agent_old/world.py` loads the two into separate fields, and each module reads its
own:

- `hosting.py` iterates `me.hosted_markets`
- `bidding.py` iterates `me.markets`

So it hosts in A only and bids in B only. **The position is already per-market**; what it is not is
per-auction, and per-auction is precisely the thing with no object to hang on.

This also settles what a role would add that a capability does not. A capability says *what an
agent can do*; a position says *where it stands*. They coincide here only because every capability
in a market is derived from a position — and while they coincide, a role object would be a third
name for one fact. [AGENTS.md](../../AGENTS.md) rule 2 makes the same test of capabilities: where
nothing could differ, you have a function rather than a capability. A role nothing could vary
independently of the predicate is a synonym rather than a term.

# Clearing having no position is not the inconsistency it looks like

The table above invites the reading that clearing is missing something the other two have. It is
not. [clearing-as-validator](clearing-as-validator.md) makes it a **thin, region-want-free notary**: it
holds no resource, wants nothing, and takes no side. Giving it a role would say it occupies a
position in the market, which is the one thing it is designed not to do — a role implies a region want in
a way a function does not.

So the three-way inconsistency is really two positions and one non-participant, and the encoding is
telling the truth about which is which. That it *looks* untidy is the cost of it being accurate.

# Consequences

- **The seam about who hosts stays where it is.** This record does not move it, and deliberately
  removes one wrong way to close it: a per-auction host is not reachable by promoting `market:hosts`
  to a role, because the promotion needs an auction object first.
- **Two questions are now known to be one.** *Should positions be roles?* and *should an auction be
  an object?* have the same answer, and the second is the one to argue. Anyone reaching for roles
  again should be sent to [auction](/domain/auction.md) rather than to this record's conclusion.
- **The rule generalises past markets.** A package adding a role should be asked what
  node it hangs off. If the answer is "the agent", it is a predicate.

# Seams left open

- **An auction is not an object, and this record does not argue that it should become one.** It
  says only that roles depend on the answer. The argument for an auction object — that it would give
  bids, the offer, the trade and the host a single thing to be about — is real and is not made
  here.
- **Nothing reads a peer's position.** `market:bidsIn` is public and no agent asks who else bids in
  its market except through `participants()`, which the host uses for addressing rather than for
  judgement. Whether a bidder should be able to see the field it is bidding against is a strategy
  question with no design.
- **`orexis:actsFor` is a fourth position and was not examined.** It says whose interest an agent
  advances — a plant, for a plant agent — and it is neither a market position nor a capability
  premise. Whether it is the same kind of fact as the two above is untested; it is left alone
  because nothing currently depends on the answer.
