---
type: Decision
title: A level is a vocabulary, and a bridge is what connects two
status: accepted
timestamp: 2026-09-03
description: >-
  Hierarchical planning here is not hand-written decomposition. A level is the vocabulary
  some actions write their effects in; a search runs inside one vocabulary and never leaves
  it; an action nobody takes is a promise the level beneath will keep, and when the keeper
  reaches such a step it translates the promised fact through the bridge and asks the search
  for it there, from the world as it then is, splicing what comes back under the step.
  Refused: hand-written methods for physics (a protocol is declared, physics is planned);
  the outer search seeing the lower actions (seven moves would be thirty drives); a fixed
  number of levels (a domain defines its level by what it writes, whether it is taken, and
  its bridge).
---

# A level is a vocabulary, and a bridge is what connects two

The sovereign's questions over one afternoon (2026-09-03) drew this out, and the record is
written so the picture can be checked without the code. It fixes what a level is, so the
courier-and-hanoi world — planning inside another — is an instance rather than a design.

**There is one search and one keeper.** A level is a vocabulary that some actions write
their effects in: hanoi's, where a disk is on a peg; the courier's, where a van and a parcel
are at cells; a motor domain's, where a heading and a speed are numbers. A search runs inside
one vocabulary and never leaves it, because [relevance](/domain/relevance.md) keeps the
actions whose effects write what the want reads, and a want is written in one vocabulary.
That is the whole of "abstraction": Move's effect asserts the disk arrives and says nothing
about how, the way a coarse operator always does, so the outer search plans seven Moves and
never sees a cell — not because a cell was forgotten, but because no template at that level
mentions one. The want is whole at the top.

**An action nobody takes is a promise the level beneath will keep.** Move has no taker; drive,
pick and drop are taken. When the keeper reaches a step of a taker-less action it cannot hand
it to anyone, so it translates the step's promised fact — the one triple its
`progression:predicts` carries — through the bridge into the lower vocabulary, and puts that to
deliberation as a want, from the world as it then is. The plan that comes back is spliced
in under the step, its steps [`progression:partOf`](/domain/step.md) the abstract step's filling,
and walked as any plan is. When the last of them is answered the abstract step's own verdict
is judged through the same bridge, and the next abstract step becomes current and is planned
in turn, from wherever the van now stands. The parts of the desire appear one level down as
the steps' predictions, one fact each, and the tree of facts ends where the world confirms
a leaf. A declared [method](/domain/method.md) is the same splice with the search skipped, for
a protocol that has no choice in it.

**A domain defines its level by three things, and none of them is a number.** The facts its
actions write, which is what its search plans over. Whether its actions are taken, which says
whether it is the bottom. And its bridge to the level beneath — a peg is at a cell, a cell is
at a coordinate — without which the level below cannot be asked anything. Add a motor domain
and Drive becomes the abstract action of its level; the same disk is on a peg, at a cell and
at a coordinate, and the bridge at each boundary is the identity between those descriptions
of one thing. Nothing in the kernel counts levels.

**Nobody picks the first level; the want does.** Written in hanoi's words, the goal is planned
over Moves; written as parcels at cells, over drives, and hanoi never appears. Going down is
the bridge's decision, not a choice either: if two lower domains could both bring a translated
fact about, they are one inner search over the union, ranked by cost, exactly as the plant
world chooses between the butt and the venue at a single level.

# What was refused

- **Hand-written methods for physics.** A method for Move — travel, lift, travel, place — was
  built with parameter templates and dropped the same day: the sovereign wants no
  hand-written method where a search would do. Physics is planned; a protocol (tender,
  present) is declared, since its steps have no effects a want reads and no search could
  find them.
- **The outer search seeing the lower actions.** With the bridge applied inside the search,
  relevance would pull drives into the hanoi search and seven moves would be thirty drives in
  one budget. The bridge is applied to FACTS at the boundary — a step's promise going down, a
  verdict coming back — never to the world a search plans over.
- **A fixed number of levels, or a level as a setting.** "Taker-less means abstract" is a fact
  in the graph, and the bridge is a package's declaration; two levels, three or one are all
  the same mechanism.

# What was built, the day after

The promise path, exactly as above, with one simplification the code found: a promise is an
ordinary want. The keeper writes the translated fact as an `orexis:Desire` the agent holds
(its promises graph, projected into the desire modality), the ordinary path lifts and plans
it, and the abstract step waits on the same fact; the verdict withdraws the want and writes
the coarse fact. Nothing is spliced — the sub-plan is an intention of its own for the promise
want, and `progression:promisedBy` links the two. The tower world runs seven Moves planned once
above and seven drives-plans below (`tests/test_tower.py`). Found on the way: relevance read
nothing from a select whose only pattern sits under `FILTER NOT EXISTS`, since rdflib leaves
that pattern untranslated; it reads it now.

# Seams left open

- **The outer level's costs abstract the level below.** Move costs one whether the van is next
  to the peg or across the grid; a level's cost may one day read the level below's estimate
  the way a want reads a package's select. Left until the tower shows a wrong choice for it.
- **A promise refused below teaches the outer level** — settled (#533): when the search
  below answers a promise with no plan, or a plan that does not reach it, deliberation says so
  to the keeper, which writes `progression:refusedBelow` on the promising step and lapses it at
  once rather than waiting out its patience. The level above then passes over a candidate of
  the same action, lever and subject while the refusal is younger than the patience — recorded
  in the trace as passed over, not weighed — and tries it again after, since the world may
  have changed. Each distinct move is refused once per patience, so two levels cannot loop,
  and a tower with peg C cut off plans around the cut until nothing helps.
- **A promise nobody could ever keep is a misconfigured world** — settled (#532): a bridge into
  facts no declared action writes is refused at onboarding and at boot. Narrower than first
  filed, and rightly: a taker-less action with no bridge at all is knowledge-only and admitted,
  since a wire-less world's whole point is the search, and the actions a bridge lands on need
  not be taken here — a level nobody executes is still a level somebody could plan.
