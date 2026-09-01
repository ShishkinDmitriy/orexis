---
type: Decision
title: The domain is a plug-in, and Hanoi is the proof
description: >-
  #257 asked for the claim to be tested — a want that is not a number, a retraction that
  really deletes, a second domain touching none of water: — and Tower of Hanoi answers all
  three as an ontology and six ground actions with not one line of Python. The pegs are
  T-Box individuals because the ground actions must name them and code may never name a
  world instance; the disks are the world's, and how many is its whole authorship. The goal
  is a ratified desire — orexis:AtEnd's first writer, met by absence, kernel-judged — and
  the optimal solution is nobody's algorithm: with depth eight admitting eight-move plans,
  the seven-move classic wins because achievers are ranked by cost alone. Measured: 2^n−1
  at n=2 and n=3, seven steps found in 5.8 s on the bench. Building it found a latent
  kernel bug — the world gate's two-road join doubled every asserted string literal, and
  hanoi's pattern node was the first focus a maxCount ever had here. The urgency question
  #257 expected to break was already answered by the deontic sitting: binary is
  sufficiency. What is deliberately not taken: a depth a world could ask for, and #257's
  runtime half — a hanoi device — both seams.
status: accepted
timestamp: 2026-09-01T10:07:41Z
---

# The domain is a plug-in, and Hanoi is the proof

AGENTS.md has claimed since the beginning that plant/water language is the example and not
the architecture, and [#257](https://github.com/ShishkinDmitriy/orexis/issues/257) said the
honest thing: nothing had ever tested it, and every want in every world was a number in a
range. The sovereign chose the probe — a classical planning task, Tower of Hanoi — and the
package that answers is `packages/orexis-tool-hanoi/`: an `ontology.ttl`, an `actions.ttl`,
and **not one line of Python**. No module, no grant, no measure, no derivation. That is the
plug-in claim proven at its strongest form.

## What #257 asked, and what answered it

- **A goal that is not a range** — the goal is a world-ratified desire in the asserted block,
  met by ABSENCE: `orexis:unmetWhen` a pattern binding while any disk's chain bottoms out on
  a peg that is not C. The kernel lifts and judges it with no capability in the room —
  machinery the deontic sitting built for the general avoidance, serving its second customer
  unchanged.
- **A retraction that really deletes** — every effect before this replaced a reading with a
  fresher reading of the same node; a move's `orexis:retracts` removes `?d hanoi:on ?old`
  and its construct adds the new support. The first deletion that is one.
- **A second domain touching none of `water:`** — the diff contains no water term, no sensing
  term, no market term.
- **The urgency #257 expected to break never broke**, because the deontic sitting answered it
  first: a discrete want's urgency is binary — met 0, unmet 1 — which the four-measures
  table calls sufficiency where no intermediate worlds exist. The design work #257 reserved
  was already done under another heading.

## The two placements that make it lawful

**The pegs are T-Box individuals and the disks are the world's**, and that split is rule 1
doing its work rather than taste. The moves are GROUND — one action per (from, to) pair, six
nodes — because a row carries one lever and an effect sees `$about`, never the lever: baking
the pair into the node needs no parameter channel at all. Ground actions must NAME the pegs,
code may never name a world instance, and every Tower of Hanoi ever posed has exactly three
pegs — so the pegs live in the package's vocabulary as `orexis:Below` lives in the kernel's,
and a world authors only its disks: a two-disk world and a three-disk one differ in nothing
else.

**The goal is `orexis:bindsWhen orexis:AtEnd` — the achievement scope's first writer.**
Nothing erodes while a puzzle sits, so nothing makes this want hotter with time; the plan's
end is the whole of what is asked, which is what AtEnd was minted to say and had never been
used for.

## Optimality is the cheapest achiever, and nobody's algorithm

The test that matters gives the search depth EIGHT, so eight-move solutions are reachable —
and the seven-move classic must win, because achievers are ranked by cost alone and every
move declares `orexis:costs` of one. Measured on the bench: two disks solve in exactly 3
moves, three disks in exactly **7 — 2^n − 1 — found in 5.8 s**, and the move list is the
textbook solution (A→C, A→B, C→B, A→C, B→A, B→C, A→C). No Hanoi solver exists anywhere in
the tree; the optimum is the deontic sitting's two-stage ranking doing what it said.

## What building it found

- **A latent kernel bug, caught by the first maxCount that ever had a focus.** The world
  gate joins two data roads — the store's serialisation parse and `effects._triple` — and
  the two disagreed about a plain string's identity: pyoxigraph reports `xsd:string` on
  every simple literal, rdflib holds the plain and the explicitly-typed forms as DISTINCT
  terms, so every asserted string in the join was silently doubled. Nothing ever noticed
  because no shape counted one until hanoi's pattern node arrived with `sh:maxCount 1`.
  Fixed at the constructor: a plain string stays plain.
- **The test builder assumes a wired agent.** `build_agent` reaches for the transport module,
  and the mover holds no bus — so the hanoi tests build a plain `runtime.Agent`, which is
  honest: the world's whole point is the search, and it is the first world with nothing on
  the wire at all.
- **The goal is met by vacuity in an empty state**: before anything poses the puzzle, no
  disk is astray and the want reads met. Noted rather than fixed — "nothing misplaced" is a
  defensible reading of an unposed puzzle, and the state arrives with the pose.

# Seams left open

- **Depth is the engine's, and a world cannot ask for more.** The tests raise `MAX_DEPTH` on
  their own Planner instance; the constant stays 2 for every running agent, per its own
  comment — an agent that could revise it could spend an afternoon planning while its plant
  died. If a deployed world ever needs deep search, that is the mandate pattern's decision —
  a sovereign-bounded pick — and it is deliberately not taken here.
- **#257's runtime half is unbuilt.** A hanoi DEVICE — moves as commands on a bus, state as
  observations, onboarding and compose — would make the mover a running society member
  rather than a planner fixture. The planner-level claim is answered; the running-society
  half of #257's scope is this seam, for a day the puzzle earns a container.

# Issues this closes

[#257](https://github.com/ShishkinDmitriy/orexis/issues/257) — the claim it asked to have
tested is tested, its three bullets each answered, and the design question it reserved was
answered by the deontic sitting before this world existed. The runtime half stands above as
a named seam.
