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
thing read. The **writes** are the predicates of a `CONSTRUCT` template, an `INSERT` template
or a retraction. An action has both halves; a want has only the reading half, taken off its
met-test's paths, its `sh:equals` and its SPARQL constraints. The word is the planning
literature's: the state variables an operator may inspect and may change.

# Taken from the text, never declared beside it

A footprint could have been a triple somebody writes next to an action. It is not, because the
construct settles what is written and a second statement of the same thing would drift from
the first with nothing to say so. `agent/planning/footprint.py` parses the texts with
rdflib and answers per call. What it answers feeds two things: the [scopes](/domain/scope.md),
which join predicates that one footprint holds on both halves, and the
[relevance](/domain/relevance.md) closure of the predecessor, which walked footprints backward
from a want.

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

# What it is not

Not a scope: a scope is a set of predicates joined across many footprints, and one footprint
is one text's. Not a filling's range: which values a parameter may take is enumerated by the
precondition against a world, and a footprint names predicates, never values.
