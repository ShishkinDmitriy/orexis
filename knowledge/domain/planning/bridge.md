---
type: Domain Concept
title: Bridge
description: >-
  A rule of a world that combines two domains, concluding a fact in one vocabulary from facts in
  the other — a disk is on the peg standing on its cell. Authored by whoever combines the
  domains, run forwards over the beliefs like any rule, and run backwards by refinement to keep
  a step one level down. Neither domain knows it.
---

# What it is

A [level](/decisions/the-hierarchy-is-found-in-the-rules.md) is a vocabulary: hanoi's, where a
disk is on a peg; the courier's, where a parcel is at a cell. Neither domain mentions the
other, and each plans on its own. A world that wants the puzzle solved by a van combines them,
and says in a `sh:RulesGraph` of its own how the two describe one thing:

```sparql
CONSTRUCT { ?disk hanoi:on ?peg } WHERE {
  ?disk a hanoi:Disk ; courier:at ?cell .
  ?peg a hanoi:Peg ; courier:at ?cell .
  FILTER NOT EXISTS { ?larger a hanoi:Disk ; courier:at ?cell ; hanoi:size ?l .
                      ?disk hanoi:size ?s . FILTER(?l > ?s) } }
```

That is the bridge, and it is an ordinary SHACL rule: a [revision](/domain/belief/revision.md) the
deliberator concludes of the state whenever the state moves, so the puzzle's words are believed
beside the grid's with no file stating them. `domains/tower/` holds two — a disk on the next
larger disk sharing its cell, and the largest on the peg — and one axiom, that a disk is a
parcel.

# Which way it runs

**Forwards, over the beliefs**, as every rule does: where the disks stand says what each is on.

**Backwards, at a step's boundary**, by [refinement](/domain/planning/refinement.md): a step that
predicts `disk_1 hanoi:on hanoi:PegC` binds the rule's head to that fact, and the rule's
WHERE, bound, is what the level beneath must make true. A bridge is therefore held to a shape a
rule elsewhere is not — ONE head triple, whose variables its WHERE binds plainly — and a rule
outside that shape is left out and said in the log, never guessed at.

**Never inside a search.** The search runs no rules, so a bridge couples no actions and joins
no [scope](/domain/planning/scope.md): the puzzle's search forks Moves and the courier's forks drives,
each in its own imaginarium.

# What it is not

**Not declared per action.** 0.1.0's bridge was a node refining one action, translating its
promised facts down with a CONSTRUCT of its own; the rule here refines no action and translates
nothing — whichever step predicts a fact some bridge concludes is kept below, and the met-test
below is the rule's own text.

**Not a method.** A method declares how an action is taken; a bridge says
only what one level's fact means in the other's words, and the steps are found by a search.
