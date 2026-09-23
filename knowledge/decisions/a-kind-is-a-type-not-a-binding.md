---
type: Decision
title: A kind is a type, not a binding, and a want is not a kind of desire
description: >-
  `orexis:Always` was a binding whose documented reader - the planner - never read it; all six
  readers asked it to tell WHICH KIND a node was, which is a type's job. And `orexis:Want` was a
  subclass of `orexis:Desire` whose entailment could never reach a runtime want, so every writer
  hand-wrote both types and `?d a orexis:Desire` matched both kinds. Between them, a node could
  be a desire by type and a want by binding at once - three shipped worlds were exactly that,
  and neither collection could see them. The binding is gone, the subclass is unlinked, and the
  type is the kind.
status: accepted
timestamp: 2026-09-17T21:00:00Z
---

# What was measured

Four shipped worlds, built through genesis, asked what each collection holds:

```
--- tower/mover ---        every_disk_home          AtEnd  Desire  >> NEITHER
--- courier/courier ---    every_parcel_delivered   AtEnd  Desire  >> NEITHER
--- hanoi/hanoi ---        every_disk_home          AtEnd  Desire  >> NEITHER
--- loner/gardener ---     6 of 6 found
```

**Three of the four had their single desire — the entire point of the world — in neither
collection.** The keeper's promise fell in the same hole. Nothing failed, because falling out of
a collection is an empty result and [an empty result is not an
error](/decisions/a-test-that-asserted-nothing.md).

The proximate cause is that `Wants.find_all` asked `?w a orexis:Want` and `Desires.find_all`
asked `?d orexis:bindsWhen orexis:Always` — two different partitions assumed to be one. Neither
repository could use the other's test, and that is the symptom worth chasing rather than the
defect.

# The binding had no reader for what it claims to be

`orexis:bindsWhen`'s own comment says: *"WHEN a want binds along a plan. **The planner is the
reader**: Always is judged at every state of a candidate plan, AtEnd at the end-world alone,
Within against the simulated clock."*

The planner never branched on it. The one site that looks like it does reads something else —
`judgment.expires`, falling back to `judgment.holds_at`. Every actual reader, all six, asked the
binding to tell it **which kind a node was**: is this a root, is this a child, is this a debt.

| reader | what it was really asking |
|---|---|
| `Desires.find_all` | is this the standing kind |
| `pursuit._is_root` | is this a root |
| `judgments._CHILDREN_Q` | which is root and which is child |
| `Wants.find_first_by_desire` | is this not a debt |
| `keeper._names` | child or root |
| sensing's `module.py` | find the root |

A property that six readers use to ask what something IS is a type wearing a property's clothes.
`orexis:Always` is gone: a desire holds at every instant, which its type says, and saying it
again in a triple is what let the two axes come apart.

# The subclass was already fake at runtime

`orexis:Want rdfs:subClassOf orexis:Desire` looked like it was earning its place — every query
asking `?d a orexis:Desire` found wants too. It was not. The RDFS closure is **materialised once,
at genesis**, over what the store held then; a want is minted long afterwards and nothing ever
entails the supertype for it. So `Wants.save` and `ower.owe` hand-wrote `a orexis:Want ,
orexis:Desire` on every mint, and a paragraph in `pursuit.py` existed to explain why.

So the axis cost a doubled type on every write, bought nothing at runtime, and did one thing
that was actively harmful: it made `?d a orexis:Desire` match both kinds, which is why a
collection of desires had to filter on a binding to find its own contents.

# What this makes true

**Declared versus derived was never the axis.** `desire.md` said a desire is *declared* and a
want is *derived*, and three worlds ratify a want directly in a `desire.ttl` — authored,
standing, and handed to a search. They were not violations; the page had named the wrong
distinction. The axis is **standing versus occasioned**, the type carries it, and how a node came
to be — authored by a world, derived by the derivation, minted by the ledger — is provenance
rather than kind.

Everything follows from that. `Desires.find_all` asks `?d a orexis:Desire`. `Wants.find_all`
asks `?w a orexis:Want`. `pursuit._is_root` asks whether the desires hold it. No reader filters
on a binding to work out a kind, and `orexis:bindsWhen` is a want's property saying when along a
plan — which is what it always claimed to be, and can now become if a reader is ever written.

# What was refused

**Widening a query instead.** `Wants.find_all` could have asked `bindsWhen != Always`, which
catches all three worlds and the promise today. It was refused because it would be a fifth
independent definition of what a want is — four writers already disagreed — and the sixth writer
still would not know it. The duplication was the disease; another query is another symptom.

**Keeping `orexis:Always` as a binding for PDDL3's sake.** PDDL3's `always` is a real modality
and a want that must hold *throughout* a plan is a real thing to want. Nothing here forecloses
it: what was removed is a word that identified a kind, and if a throughout-the-plan binding is
ever needed it returns as a binding with an actual reader. A term nobody reads is annotation,
however well it reads.

# Also fixed on the way, because the change forced it

`orexis:BindingWantShape` exists to stop a want defaulting its binding, and it did neither job it
was written for. Its enumeration `sh:in ( Always AtEnd Within )` **omitted `orexis:At`**, which a
want derived from a foreseen crossing (#619) binds and `Wants.save` writes — so the shape would
have refused one, silently, because such a want is minted at runtime and swept long before the
next boot validates anything. And it targeted `sh:targetSubjectsOf orexis:metWhen`, which after
this change would demand a binding of every DESIRE. It targets `orexis:Want` now, which is the
thing it is about.

# Amended: what the type MEANS, and where the binding goes next

This record said *the type is the kind* and stopped there — true, and thin enough that it could
only argue from the bug it was fixing.
[a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md)
says what the two kinds mean — a desire holds at EVERY instant of its period, a want at SOME
instant of it — which is a better reason for their disjointness than this record gave, and which
finds that `orexis:bindsWhen` states a third time what the type and the graph's period already say
between them. Nothing here is reversed; the binding this record left standing as "a want's, saying
when along a plan" is on its way out for the same reason `orexis:Always` was.

# Seams left open

- **The shape now reaches an obligation's record**, which it deliberately did not before, against
  a volume written before the binding existed. The ledger has stated `orexis:Within` on every
  debt it mints since #472 and a volume older than that fails a good deal else — but a live
  volume is a live volume, and if one is ever met the answer is a migration like the ledger's
  own, not a shape that cannot see half its subject.
- **`afforder.wants_of` names both kinds, out loud.** It keyed off the subclass before and nobody
  said so. The planner is usually standing on a want and sometimes on a root — where a root reads
  unmet and nothing can be minted for it — so the map holds both. Whether the planner should ever
  be handed a root is a separate question, and #675 is where it would be settled.
- **`agent_old/inference.py` materialises one axiom fewer.** Nothing depended on that one; the
  closure is generic and the guard that refuses a seventh hand-rolled subclass walk is untouched.
