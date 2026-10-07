---
type: Decision
title: Two minds meet by saying their routes and drawing lots on a conflict, because nobody owns a cell
description: >-
  The sovereign's decision of 2026-10-07 for #568, recorded before its code. Two agents on two hosts,
  one van each, start from the same world documents; nothing oversees them, the world does not act,
  and no cell has an owner who could issue a right to it. Decided - a van senses the vans within a
  radius and plans alone beyond it (#922); in range each SAYS ITS ROUTE, the cells its van will hold
  over the coming periods, and says it again when it changes; each checks the constraint it already
  holds, no cell holds two vans, over both routes, and both reach one verdict; on a conflict they DRAW
  LOTS by commit and reveal, neither entering the contested cell meanwhile and a lost message
  restarting the draw; the loser lays the winner's route as a prediction, its walking plan reopens
  (#921) and it waits (#920) or goes round, and a step predicts its own effect alone (#919), which keeps
  the laid route out of the loser's own acts (#923). Random because a symmetric conflict has no fair
  deterministic answer, committed because a self-interested agent that hears first would otherwise
  always win, and unenforced because a collision hurts both. The line it draws - where defecting pays
  the resource has an owner and the market, where colliding hurts both a convention suffices. Refused -
  right-of-way as a lot or an owner per cell, a reservation table or intersection manager, cost
  negotiation in two rounds, a rank the world states, a seen van believed anywhere it can reach, and
  the world refusing a drive. A world with peers owes well-formed infrastructure.
status: accepted
timestamp: 2026-10-07T20:00:00Z
---

# The question

[#567](https://github.com/ShishkinDmitriy/orexis/issues/567) asked how ONE mind keeps two of its
plans off one cell, and
[one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md)
answered it: the wants a constraint can make collide are one want, searched once, and a world that
violates the constraint is impossible. [#568](https://github.com/ShishkinDmitriy/orexis/issues/568)
asks the same of TWO minds, and the setting is the one this project was built for:

- Two agents on two hosts start from the same world documents and drive one van each. Each holds the
  constraint *no cell holds two vans* ([constraint](/domain/planning/constraint.md)); neither sees the
  other's plan.
- **Nothing oversees them.** There is no third agent, no shared store and no service in `infra/`
  that could hold a schedule ([where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md)).
- **The world does not act; only agents act.** What a world is, is documents and the physics a
  simulator plays from them; it refuses nothing at runtime.
- **Agents sense, and speech is acting and sensing.** Saying is an act, an
  `execution:Saying` taken as a step; hearing is a document arriving through
  [speech](/domain/speech/speech.md), beside what an instrument says through sensing
  ([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)).
- **No cell has an owner**, so nobody can issue a right to enter it. That is what separates this
  from water, which a [host](/domain/market/host.md) holds and sells as signed claims.

Earlier versions of #568 asked for right-of-way sold by a market, for a cost negotiation in two
rounds, and for a rank the world states. The discussion of 2026-10-07 refused all three; this record
is what it decided instead, written first, as #568 asks.

# What the tree holds today, verified

Read on the branch tip that carries #919 (`bb4b4a12`, 2026-10-07); nothing of the two-minds protocol
is built, and nothing here was run on a bench.

- **A peer cannot say a prediction.** `heard` refuses a document any of whose graphs is not a kind
  beneath `orexis:StateGraph` (`agent/speech/heard.py`): a peer reports what IS. A route said as
  state would be copied into the present ground, which is false — the van is not yet where its route
  goes — so a route the agent lost to becomes an `orexis:PredictionGraph` only by this decision, and
  #923 argues the refusal it relaxes.
- **There was no wait.** A courier-only `courier:Wait` was built and taken back out the same day,
  both within PR #924 (the revert is `bb4b4a12`), because waiting is every world's and is #920's,
  rewritten. *Amended 2026-10-07: built by #920 — `planning:Wait`, the planning package's own
  [wait](/domain/planning/wait.md), in every scope, landing where the next ground the search can tell
  apart begins; with a peer's route laid as predictions, the crossing is waited out and the corridor
  with the peer standing ahead is found (`world/dispatcher/tests/test_dispatcher.py`).*
- **Soft commitment has one trigger** — a want a constraint couples to the walking one arriving
  (`derive_wants`, `planning:reopens`; [commitment](/domain/execution/commitment.md)). A route laid as
  a prediction that makes a walking plan's next worlds impossible reopens nothing; that is #921.
- **A step predicts its own effect** since #919 (built on this branch, PR #924 open): before it, a
  plan taken across a laid route carried the other van's next cell in every drive, and a fictive drive
  wrote where the other van went into this agent's beliefs. Measured in the #568 prototype and pinned
  by `a_step_lands_across_a_prediction_it_does_not_touch` and
  `a_wait_across_a_prediction_predicts_nothing` under `agent/planning/tests/plans/`.
- **The constraint is the dispatcher's, in the avoided state's form** — a `planning:unmetWhen` select
  over `courier:at` whose rows are two vans on one cell (`world/dispatcher/constraints.ttl`). Both
  agents of a two-van world would hold that same text.

# The decision

Six pieces, each an issue under #568.

1. **Attention ([#922](https://github.com/ShishkinDmitriy/orexis/issues/922)).** A van carries a
   sensor that observes the other vans within a radius the world states, each by identity and cell —
   an ordinary observation whose result is a cell. Beyond the radius nothing is observed and the agent
   plans alone, exactly as today. A peer seen on a cell is a present fact, and the constraint keeps
   this agent's search out of that cell whatever was or was not said: sightings are the safety net,
   never the plan.
2. **Say the route ([#923](https://github.com/ShishkinDmitriy/orexis/issues/923)).** In range, each
   agent says its ROUTE — the cells its van will hold over the coming periods, read off its
   intention's untaken steps, a drive in flight holding both its cells — and says it again whenever
   it changes. One document per agent.
3. **Check (#923).** Each lays the peer's route beside its own and asks the constraint it already
   holds. Same rule, same documents, same verdict, so the two agree on WHETHER there is a conflict
   without telling each other. No conflict, and nothing more is said.
4. **Draw (#923).** On a conflict the two DRAW LOTS by commit and reveal — each says a hash of a
   random number and a nonce, then, both commitments heard, its number and nonce; each checks the
   other's reveal against its commitment, and both compute the winner from the same facts. While the
   draw is unfinished neither enters the contested cell. A commitment or a reveal that never arrives
   restarts the draw after a patience: a lost message delays the decision and never causes a
   collision.
5. **Plan around the winner ([#921](https://github.com/ShishkinDmitriy/orexis/issues/921),
   [#920](https://github.com/ShishkinDmitriy/orexis/issues/920)).** The loser lays the winner's
   route as a prediction over its periods, which speech writes; a world the walking plan's untaken
   steps reach now violates the constraint, so the walking want is reopened from where its step in
   flight lands; and the search finds a `planning:Wait`, landing at the next ground, or a way round,
   whichever is cheaper. The winner keeps its route.
6. **A step predicts only its own effect
   ([#919](https://github.com/ShishkinDmitriy/orexis/issues/919)).** The winner's laid moves are the
   ground's, never the loser's acts, so a fictive drive writes only its own van and the landing check
   holds the loser to nothing the winner does.

**The words.** What a van says about the cells it will hold is a **route** — an intention said,
never a "claim": `market:Claim` is the market's signed entitlement from a host
([claim](/domain/market/claim.md)), owed and presented and served, and one word must not mean two
things. The exchange that settles a conflict is a **draw**, its two halves a commitment and a
reveal. Both words are speech's, since speech owns the conversation — the route, the commitment, the
reveal and the comparison — and both get their pages in the dictionary, under speech, in the change
that declares them (#923), before anything reads them. **Attention** is sensing's, with #922. This
record coins no term.

# Why

**Something must be asymmetric, and the only fair asymmetry is chance.** The two agents run the same
code on the same documents and want the same cell at the same time. Lehmann and Rabin (about 1981,
the dining philosophers) showed that processes identical in program and state have no deterministic
protocol that breaks such a tie — every deterministic rule run by both does the same thing in both.
These agents are not quite identical: each has its own IRI, and an order on IRIs would break every
tie. But an order on identities is a RANK, and the same agent would win every meeting for ever; the
sovereign refused it as static, unfair and an order imposed from outside (below). Of what is left,
fair randomness is the one asymmetry that needs neither a rank nor an owner, and each meeting is a
fresh one.

**Commitment is what makes chance fair between self-interested agents.** Each agent wants to win.
If each simply said a random number, whichever heard the other's first could choose its own to win,
every time. Blum's coin flipping by telephone (about 1981) is the textbook answer: commit to the
choice by its hash, reveal only once both commitments are in, and check the reveal against the
commitment. Neither can choose after seeing the other's choice, and both compute one winner from one
set of facts.

**Nobody enforces the result, because nobody needs to.** A collision hurts both vans. Given that the
other follows the convention, following it is each agent's best move — a coordination game in Lewis's
sense (Convention, about 1969), not a prisoner's dilemma — so the outcome holds without a referee.
That is THE LINE this decision draws between the courier and the water market:

- **Where defecting pays, the resource has an owner.** Water taken unpaid is water gained, so the
  host who holds it issues signed claims and checks each one presented; the [market](/domain/market/market.md)
  exists because cheating would otherwise pay.
- **Where defecting harms both, a shared convention suffices.** A van that enters a cell its peer won
  hits its peer; nothing is gained by the breach, so nothing has to be checked before it.

**The convention is deontic; the constraint stays alethic.** *No cell holds two vans* is physics, a
`planning:Constraint`, and a world violating it is impossible — that does not change. *The loser
yields to the winner's route* is an obligation, which can be broken, and a breach is a computable
fact from what was seen and heard: the said route, the draw, and a sighting of the loser on a cell
the winner's route held ([modality](/domain/kernel/modality.md) — a breach is not a stronger gap).
Nothing here acts on one yet; that is a seam.

**A step predicting its own effect is what lets the rest compose.** Laying a peer's route as a
prediction is the tool the one-mind record kept for strangers, and without #919 the loser's own
plan carried the winner's moves as though it had made them.

**One mind stays coupled.** None of this replaces #567 for one agent: a mind that sees both plans
searches them as one, which is the independence-detection and M* family's answer below, and the two
records validate each other — coupled search where one mind sees both plans, prioritised planning
with a drawn priority where two minds see only what they say.

# Where it sits in the literature

From memory, as the discussion was told it; years are approximate.

- **Coupled search for one mind** — multi-agent pathfinding: independence detection (Standley,
  ~2010) plans each agent alone and merges the ones whose plans conflict into one joint search; M*
  (Wagner and Choset, ~2011) couples only where a collision is; conflict-based search (Sharon et al.,
  ~2012, journal ~2015) branches on who yields. #567's footprint coupling is independence detection
  done ahead of the search, over the reach, and the one-mind record refused CBS as the default for the
  reason it gives. That this is where the field's optimal methods live is the confirmation #567 had
  not cited.
- **An overseer that reserves** — cooperative A* and windowed hierarchical cooperative A* (Silver,
  ~2005) plan agents in order against a shared space-time reservation table; autonomous intersection
  management (Dresner and Stone, ~2008) has a manager grant time slots. Both are refused below.
- **Two minds, prioritised and decentralised** — asynchronous decentralised prioritised planning,
  ADPP, and its completeness in well-formed infrastructures (Čáp et al., ~2015): each robot plans
  around the trajectories of those above it, said to it, and the method is complete where no start
  or goal blocks another's only route. This decision is that, with the priority drawn per conflict
  instead of fixed — and it takes over the condition as the world's duty.
- **Reactive avoidance** — velocity obstacles and ORCA (van den Berg et al., ~2008–2011): reciprocal,
  continuous, no plans exchanged. It is the layer below a plan, and a grid world has no velocities.
- **Conventions designed in** — social laws (Shoham and Tennenholtz, ~1995): restrict what agents may
  do offline so conflicts cannot arise. The well-formed world is the social law here; the draw is for
  what a law cannot foresee.
- **Exchanging partial plans** — partial global planning (Durfee and Lesser, ~1987–1991) and its
  generalisation GPGP (Decker and Lesser, ~1992–1995): agents exchange the parts of their plans that
  interact. A said route is a partial global plan of one van.
- **Symmetry and fairness** — Lehmann and Rabin (~1981) and Blum (~1981), above.

# What was refused

- **Right-of-way as a market lot, or an owner per cell** — #568's first version, and the paragraph of
  the one-mind record that said "what the market allocates (right-of-way as a lot, #568)". A lot is
  sold by a host who holds the good; no agent holds a cell, so a host would have to be invented — an
  owner the world does not have, and on the bench a third agent and a third container where the pair
  need only agree. The market exists because defection pays; here it does not. The sovereign refused it.
- **A shared reservation table or an intersection manager** (Silver; Dresner and Stone). A table both
  write is shared state, which this project refuses structurally — there is no shared store — and a
  manager granting slots is an overseer in disguise, a single point of failure on a bus that has none.
- **Cost negotiation in two rounds, the cheaper detour yielding** — #923's first version. A detour's
  cost is known only once the other's route is known, so one round says routes and a second says costs,
  every conflict; and it buys nothing a draw does not: the two agents' costs are each agent's own word,
  unverifiable and inflatable by whoever wants the cell, so "the cheaper yields" rewards the better
  liar. Over many meetings the draw is fair in expectation, and the extra round is not paid.
- **A rank the world states** — an order of the agents, or an order on their IRIs. The sovereign
  refused it: static, so the same agent yields every time; unfair, for that reason; and an order
  imposed from outside on agents who are each other's equals.
- **Believing a seen van "possibly anywhere it can reach"** — #922's first version: a reach-closure
  laid as a prediction from each sighting. It guesses from sightings what a said route states exactly,
  and the guess grows with every period ahead until it blocks the whole grid. Superseded by peers
  saying their routes; the sighting stays as the present-tense safety net.
- **The world refusing a drive into an occupied cell.** The world does not act. A refusal at the
  simulator would be an overseer living in the physics, and on real vans there is no one to say it.
- **For one mind, anything but coupled search.** #567 stands as decided: one mind that holds both
  plans searches them as one; this protocol is for minds that do not.

# The world's duty

**A world with peers must be well-formed infrastructure**: no van's start or goal cell may block
another van's only route — a corridor needs a passing place, a bay, a siding. Decentralised
prioritised planning is complete there and deadlocks where it is not (Čáp et al., ~2015): two vans
nose to nose in a one-cell corridor with no passing place have no plan between them however the draw
falls, because the loser has nowhere to go and the winner cannot pass. That is the badly formed case,
and it is fixed by the author, not by the agents — the same rule as a constraint the world states,
that the world says what is possible and an agent does not argue with it. #568's done-when says the
two shapes it is held to: a crossing, where the loser waits, and a corridor with one passing place,
where the loser pulls aside. Whether `orexis-onboard` should refuse a badly formed world, as it refuses
a contradicted present, is a seam below.

# It is generic

Nothing in the protocol is the courier's. It applies to any resource that nobody owns, that physics
admits one user of at a time, and whose collision hurts both users:

- a shared water line with no supplier — two growers' valves on one main;
- **two heaters on one circuit** — the second world it applies to, named here so the first slice is
  not mistaken for the mechanism: the "cell" is the circuit over a period, a route is the heater's
  committed stretches, and a collision is a tripped breaker that leaves both cold;
- a radio channel — CSMA's random backoff (Ethernet, 802.11) is the same randomness without
  commitment, because stations are not adversaries and a station that cheats the backoff only jams
  itself;
- one charger, and a single-track section of line.

What a world names is the constraint; what speech carries is a route over whatever that constraint
reads. The courier is the first slice because its constraint is already stated.

# Seams left open

- **The shared circuit, the second world.** Named above and not built; it is the trigger for checking
  that a route is a stretch over any constraint's key and not a list of cells.
- **A peer that never speaks.** A van that says no route — an older agent, a broken bus, a human
  driver — is still seen, and the sighting keeps the cell it stands on out of the search. Nothing
  predicts where it will be next; that is the price of refusing the reach-closure, and the trigger
  for revisiting it is a world where silent peers are expected rather than faults.
- **A withheld reveal is a free re-draw.** The agent that reveals second sees the outcome first and can
  stay silent; the restart after a patience then gives it another draw, and a patient defector wins
  every meeting at the cost of delay. Two-party coin flipping that is fair against an aborting party
  is not possible in general (Cleve, ~1986). The convention survives it — nobody collides — but its
  fairness does not; the trigger is a world where one agent is seen to win much more than half its
  draws, and the remedy is the breach this record already makes computable: a withheld reveal counted
  against the withholder.
- **Fairness over many meetings.** Each draw is fair; a sequence of them is fair in expectation and
  says nothing about a short run, and nothing weighs a loser's accumulated delay. Whether a run of
  losses should change anything is not decided.
- **More than two vans at once.** The draw is between two; three vans contesting one cell, or three
  pairwise draws whose winners cycle — A over B, B over C, C over A — give no total order, and the
  completeness result above assumes one. The first world with three vans in one radius is the trigger.
- **A breach is computable and nothing acts on it.** No agent says one, believes one or plans around a
  peer that commits one; that is reputation, which the roadmap parks with an open society.
- **A badly formed world is refused by nobody.** Well-formedness is the author's duty here; whether
  onboarding should check it, as it checks a contradicted present, waits for the first world authored
  without a passing place.
- **What the radius must cover.** #922 states it as one drive plus a message's flight; the draw adds a
  commitment and a reveal each way. The figure is the implementation's to measure and the world's to
  state.

# What it amends

- [one-mind-couples-the-wants-a-constraint-can-make-collide](/decisions/one-mind-couples-the-wants-a-constraint-can-make-collide.md),
  superseded in part: its paragraph *two minds optimize alone and meet through prediction, the market
  and execution* named right-of-way as a lot, which is refused here; and its seams on a step that
  waits and on two minds' announced routes now point at #920 and at this record.
- #568, #922 and #923's first versions, rewritten to this on 2026-10-07; and #920, rewritten from a
  courier action to the planning package's own wait.
