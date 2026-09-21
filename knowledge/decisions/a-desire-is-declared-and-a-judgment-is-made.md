---
type: Decision
title: A desire is declared and a judgment is made, and one word was doing both jobs
description: >-
  The class called `Desire` was never a desire. It carried an urgency, a current reading and an
  expiry, it was built fresh by whichever capability held the stake - seven construction sites,
  four ways of computing urgency - and nothing ever wrote one down or read one back. The DESIRE
  is the row a package's rule writes at genesis, which had no type at all. Naming the second
  thing is what let the first become data, `Want` subclass it as the ontology already
  said, and a repository hand back either without meaning the other.
status: superseded-in-part
superseded-by: a-kind-is-a-type-not-a-binding
timestamp: 2026-09-17T18:00:00Z
---

# The finding, which was found rather than designed

Building `Wants` left an obvious next step — a `Desires` repository, so that asking *which
desire is this want derived under* stopped being a query text inside a deliberator. It could not
be written. The name `Desire` was taken by a dataclass, and that dataclass was not a desire.

What settled it was asking who CONSTRUCTS one. Every site is a capability answering a question:

| built in | what fills `urgency` |
|---|---|
| the ledger | how much of the claim's redeem window is left |
| hosting | a flat `1.0`, because a call is open or it is not |
| sensing | the survival envelope — how much room the subject has left |
| the kernel | binary, for the avoided-pattern and shape wants no module speaks for |

Four ways of judging, none of them reading a stored row. `Agent.pursuing()` does not query for
these at all: it asks the modules, `for wants in self.ask(DESIRES, now)`. **Nothing writes one
and nothing loads one.** Every instance in the tree is built inside the pass that ranks it and
is gone when the pass ends.

Meanwhile the thing a package's `desires.ru` writes at genesis — a node with a binding, a label
and a met-test, read back by everything — had no Python type at all.

# So the word was doing two jobs

| | the **declared** thing | the **made** thing |
|---|---|---|
| where it lives | a row in the roots graph, surviving restarts | one pass, then gone |
| who makes it | a package's rule, once, at genesis | whichever capability holds the stake, every pass |
| what it says | what this agent stands for | how badly it matters right now |
| in the T-Box | `orexis:Desire` | nothing, and there should be nothing |

Told apart only by which file you were in. A collection of desires could not be built without
first deciding which of the two it held, and either choice made the other one's name wrong.

# What was refused

**Giving the STORED thing a different name and leaving `Desire` on the contributed one.** It is
much the cheaper change: nine modules import the dataclass, one subclasses it, and none of them
would have moved. It was refused because it makes the wrong half authoritative. The word
"desire" in every page of this bundle, in `desires.ru`, in `orexis:Desire` and in the sovereign's
own sentences means the declared thing — so the code would have kept a name the vocabulary had
already given away, and a reader meeting `Desires` would have to learn that it does not hold
`Desire`s.

The deciding argument is the subclass axis. `orexis:Want rdfs:subClassOf orexis:Desire` is
already in the T-Box, and a stored want is a stored desire plus what it was derived from plus
the temporals — the same shape, exactly as the ontology says. With the name free, `Want(Desire)`
states that in the type system for nothing. With the name taken, the two stored types can never
be related, and the ontology's own axis stays invisible to the code.

# Amended: the subclass argument did not survive being measured

The deciding argument above was the subclass axis — that `orexis:Want rdfs:subClassOf
orexis:Desire` was already in the T-Box, so freeing the name let `Want(Desire)` state it in the
type system for nothing. The argument was sound and its PREMISE was wrong:
[a-kind-is-a-type-not-a-binding](/decisions/a-kind-is-a-type-not-a-binding.md) found that the
entailment is materialised once at genesis and can never reach a want minted at runtime, so every
writer hand-wrote both types and the axis bought nothing where it was supposed to pay. The
subclass is unlinked and the two stored types are siblings.

**Nothing else here moves.** That a desire is DECLARED and a judgment is MADE, that the seven
construction sites all judge and none read, that the word had to be freed before a collection of
desires could exist — all of it stands, and the rename is what made the measurement above
possible at all.

# Judging is the word, and it names work rather than a thing

**And the type is gone, which the word survives.** For a while `Judgment` named a Python object
made fresh each pass and a `deliberation:Judgment` row written between a desire and a want;
neither exists now (judge-desires-then-derive-wants). What the two carried a WANT carries, and
judging is what running a met-test against the world IS — an act, which is what this section
said it was before either object was built.


Not `Standing` (the keeper's word for an adopted intention), not `Urgency` (which is one field of
it), not `Pursuit` (which is what the agent does with it). A judgment is what you make when you
weigh one thing against what it needs — which is precisely what a capability does with a redeem
window or an envelope — and it does not pretend to be a record. See
[judgment](/domain/judgment.md).

# What it cost, and what came free

The rename touched 18 files, and two guards caught what a regex could not:
`tests/test_store.py` refused the term where a full IRI had been spelled with an
interpolated prefix, and the suite caught a `Want(desire=…)` keyword renamed to `judgment=`.
Both were the same mistake — a substitution that preserves grammar while changing the claim —
and both were found by gates rather than by reading.

What came free is the pair of collections the exercise was for. `Desires.find_first_by_want`
answers where the answer lives, instead of `Wants` being asked for a want in order to read a
field off it. `Desires.find_first_by_uri` replaced the hand-written test for whether a node is a
root. And `pursuit.child_graph`, a second copy of the pursued graph's name, was deleted rather
than migrated, because `Wants.graph_of` already held the formula.

# A file is named for what it holds, singular or plural

The convention the sovereign drew out of this, and it was the same one
[a-repository-is-named-for-what-it-holds](/decisions/a-repository-is-named-for-what-it-holds.md)
stated for classes, applied to files: **`desire.py` holds the model and `desires.py` holds the
collection**, `want.py` and `wants.py` likewise.

**Both halves of that have since been paid for and only one earned it.** There are no
collections ([a-read-is-a-function-over-a-store](/decisions/a-read-is-a-function-over-a-store.md)),
and `Desire` is not a type at all: it was built from a query and discarded, because its two
callers wanted a boolean and a uri. `want.py` keeps its own file for a reason the readability
argument never named — it imports nothing but the standard library, so nineteen modules can
name the type without loading the layer, which is what #455 protects.

# Seams left open

- **`Judgments` is a repository by its name and a service by its work**, and it is the only one.
  It does not read rows — it asks the choir, runs an avoided state's select, compiles a shape into
  the select whose rows are its violations, and ranks the answers. It is kept on the collection
  side for the reason `menu` is: what it hands back is a collection of domain objects derived on
  every ask, and the caller is asking for contents rather than for a decision. Whether that line
  holds is worth revisiting the first time something asks it to decide rather than to assemble.
- **It is handed the whole agent**, where `Wants` was deliberately narrowed to a store. That is
  not an unfinished narrowing: a judgment is CONTRIBUTED, so the collection has to reach the
  contributors, and the contributors are the choir. A collection over stored rows needs a store;
  a collection over contributed answers needs the agent. The asymmetry is the clearest statement
  of what the two kinds are, and collapsing it would hide the distinction this record is about.
- **`keeper._names` and the keeper's promise-writing cannot use either collection.** Progression
  may not import deliberation, and the keeper's own docstring already says why: which want is
  derived under which is deliberation's to say. The duplication there is the layer boundary
  working, not debt.
