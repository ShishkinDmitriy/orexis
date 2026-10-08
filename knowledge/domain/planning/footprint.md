---
type: Domain Concept
title: Footprint
description: >-
  The two sets of predicates one text is about — those its patterns read and those its
  template writes — taken from the text and stated nowhere beside it. An action's
  precondition and effect have one, a derivation's INSERT has one, a want's met-test has the
  reading half of one. A side the parser cannot make out is *anything*, which is the safe
  direction, and a variable standing where a predicate should is bounded by a `VALUES` block in
  the same text and by nothing else.
---

# What it is

A text that runs against a store touches some of its vocabulary and none of the rest, and
the footprint says which. It has two halves. The **reads** are the predicates of the patterns
a `SELECT` or a `WHERE` matches, including a pattern under `NOT EXISTS`, since absence is a
thing read - a group under a filter as fully as the group it stands in, a predicate list in it
and a filter nested in it alike (#908; how rdflib hands such a group over, and why both of its
forms are read, is the trap AGENTS.md records). The **writes** are the predicates of a `CONSTRUCT` template, an `INSERT` template
or a retraction. An action has both halves; a want has only the reading half, taken off its
met-test's paths, its `sh:equals` and its SPARQL constraints. The word is the planning
literature's: the state variables an operator may inspect and may change.

# Taken from the text, never declared beside it

A footprint could have been a triple somebody writes next to an action. It is not, because the
construct settles what is written and a second statement of the same thing would drift from
the first with nothing to say so. `agent/planning/footprint.py` parses the texts with
rdflib and answers per call. What it answers feeds the [scopes](/domain/planning/scope.md), which join
predicates that one footprint holds on both halves, and places each want in the scope of what its
met-test reads that some action can change. A type pattern reads its class, not `rdf:type`, so two
domains' `a hanoi:Peg` and `a courier:Van` stay apart.

# Anything, and the one range that bounds it

Where a text will not parse, or a predicate is a variable, the half in question is *anything*.
That over-approximates: a footprint read too wide costs forks and can join two scopes that
should have been apart, but it never lets a plan through that a narrower reading would have
refused. A variable in predicate position is an honest way to write an effect over several
predicates at once, and the range of such a variable is said where SPARQL says it: a `VALUES`
block in the text the engine runs. The reader takes the IRIs a block binds the variable to and
falls back to anything where no block binds it, where a row leaves it `UNDEF`, or where a row
binds it to a literal. A range declared beside the text, an `rdfs:range` on a parameter, is
not read, because it would be a promise about the text that nothing holds the text to.

# Per filling, on a key

The footprint of one TEXT names predicates. The [scopes](/domain/planning/scope.md) need more, since
two levers writing one predicate on two readings are two scopes only if the readings are told apart,
so `atoms_of` reads an action's footprint per FILLING: its precondition is asked over the public
graphs with every pattern optional and no filter, which binds what the world states and leaves
what the state would have bound unbound; each row is one filling as far as the world alone decides
it, and each pattern the filling reads of what some action writes, or writes, is an atom - the
predicate on the subject's key. The key is the subject's own value where the row binds it, and
otherwise the values of whatever shares a pattern with it that the row does bind or the text
states, a reading's feature and property; a subject keyed by nothing keys every atom of its
predicate. The terms a key holds are what a scope later holds as members, so a want naming one is
placed by it.

A pattern asking for the [self](/domain/kernel/self.md) is read as absent, in every half and every
reading: no public graph holds the self and no action writes it, so it can say nothing of what a
step reads or writes. Kept, it bound nothing, stood first in the order rdflib asks optional patterns
in, being the pattern with fewest variables, and changed what the chain after it bound — the
greenhouse's dose came to be filled with the heater, measured.

A row is no filling where it leaves unbound a parameter the WORLD alone decides — one the action
`orexis:takes` that is no subject its effect writes and stands in no pattern reading a predicate
any effect writes or deletes: the valve, the heater, the cell a van drives to. Asked over the
public graphs, such a parameter binds wherever the world holds one, so unbound it is the world
saying there is none, and an action left with no filling is in no scope. The allotment imports
the climate domain and holds no heater, and its heating's rows made two scopes that admitted
nothing ([a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md), #913).

# What it is not

Not a scope: a scope is atoms joined across many fillings of many actions, and one footprint is
one text's, or one filling's. Not a filling's range: which values a parameter may take in the
WORLD is enumerated by the precondition against the state as well; the public half a footprint
reads is the part the world alone decides, and it over-approximates the rest.
