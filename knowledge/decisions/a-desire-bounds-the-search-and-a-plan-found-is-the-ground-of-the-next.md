---
type: Decision
title: A desire bounds the search, and a plan found is the ground of the searches after it
description: >-
  What keeps two plans of one agent from making a state its standing aversion forbids, which is
  the mechanism #567 still asked for. Measured first on the dispatcher's corridor - no possible
  world either search visits holds two vans on a cell (none of 68), every world and every step
  stands at one instant because the courier declares no landing band, and after the walk the
  beliefs hold no committed step, no prediction and no drift; and on a van parked across the
  other's only shortest path, where the plan drives through it and eleven of the 66 worlds the
  search visits hold two vans on a cell, judged by nobody. Decided - a standing desire is weighed
  in every possible world a search of its scope weighs and a world that NEWLY enters the avoided
  state is refused, the law's pruning of 0.1.0, at 0.56 ms a world; a plan found is the ground of
  the searches after it, laid into the imaginarium as the predictions its steps are within the
  pass and reaching the passes after through the committed step, which a fictive step lays as a
  prediction of its own since no drift speaks for it; and the courier declares a drive's band
  first, since a world whose steps land at once composes no future. Refused - the issue's derived
  temporary want, a universal wearing a want's name and a second owner of the aversion; the
  second want searched in the first plan's cone; the bound alone; execution alone; the aversion
  as the drive's precondition; a repair minted from a foreseen ground two commitments make.
status: accepted
timestamp: 2026-10-04T21:00:00Z
---

# The question

[#567](https://github.com/ShishkinDmitriy/orexis/issues/567) posed one agent, two vans, two parcels
and an aversion — no cell holds two vans — and asked for a search that derives a want from a conflict
between two plans, re-searching one van under it while the other's plan stands. The world is built
and measured (`world/dispatcher/`, [measure-the-search](/runbooks/measure-the-search.md)); the
aversion is a standing desire in its honest form, `planning:unmetWhen`, judged in every ground
since #892, so two vans posed on one cell mint a want and a drive parts them. What nobody judges is
the state two plans make BETWEEN acts: on the corridor each plan drives its van through `c2_1` at
its third step, the two are walked in lockstep, and the present holds two vans on that cell for one
act. The two-vans seam of
[a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md) carries the
finding; this record decides what the architecture does about it, and refuses the alternatives,
the issue's own among them.

# What the code does today, measured

Three measurements, on the development container, one pass of the Planner at a budget of 128 over
the booted world as `world/dispatcher/tests/test_dispatcher.py` builds it (not committed to the
suite; the figures are what the decision below stands on).

- **The corridor.** Two wants, two plans of five steps, 33 and 33 weighings over 68 possible
  worlds. Every one of the 68 worlds has the pass's instant for both ends of its period, and every
  one of the ten steps carries that instant as its `execution:notBefore`, `execution:landsAt` and
  `execution:notAfter`: the courier's three actions declare no `planning:landsAfter`
  (`domains/courier/actions.ttl`), so a step lands the instant it is taken and the two plans have
  no instants to be composed at. **None of the 68 worlds holds two vans on one cell.** Weighing the
  aversion in every one of them — `weigh(store, desire, world)`, the function as it stands, which
  judges a desire about a world exactly as it judges a want and writes the same rows — costs
  38.4 ms for the 68 (median of five, min 37.7), 0.56 ms a world, against a pass of about 290 ms;
  it reads unmet in none. Through the runtime the walk is ten acts and both vans stand on `c2_1`
  for one of them; afterwards the beliefs hold two `orexis:PlanGraph`s and **no**
  `execution:CommittedStepGraph` (every window closed and swept within the pass), **no**
  `orexis:PredictionGraph`, no drift graph and no sensor.
- **A van parked across the other's only shortest path** — van B at `c2_1` with nothing to do,
  parcel A owed at `c3_1` from `c1_1`, the two-step route running through B. One want, 58
  weighings, a five-step plan whose drives are `c1_1`, `c2_1`, `c3_1`: the search drives through
  the parked van. **Eleven of the 66 worlds it visits hold two vans on one cell**, and weighing the
  aversion in all 66 reads unmet in exactly those eleven. Walked, both vans stand on `c2_1` for one
  act; the present before and after holds them apart, so the aversion weighed in grounds minted
  nothing.
- **What the executor holds a step to.** `Executor.tick` hands a due head to the queue with no
  question asked of it; `Planner._blocked` asks, once per pass, whether the present admits each due
  head's precondition, and the drive's precondition reads adjacency alone. Nothing in execution
  reads the aversion, so execution alone has nothing to hold a van to.

The three say the same thing from three sides. The aversion is read only in grounds and the grounds
are the agent's beliefs with its predictions applied; a plan is possible worlds, stated and never
believed, and two plans found in one pass are two chains of stated worlds that nothing composes.
The committed step (#849) is the one row of an intention written as a belief, and it reaches the
future through a drift alone; the courier has no sensed property and no drift, and the step's own
prediction — the two graphs it names — is not what the committed step carries
([committed-step](/domain/execution/committed-step.md)). And without a landing band there is no
future at all: a step at the present's instant is composed with nothing.

# The claim

Three parts, and each is a mechanism the architecture already has, read one grain further.

**A standing desire bounds the search.** Every possible world a want's search weighs is weighed as
well for every desire the holder holds whose met-test reads a predicate of the scope — the same
`weigh`, the same `planning:Weighing` with its `planning:violation` rows, the judgment
[one-function-mints-every-want](/decisions/one-function-mints-every-want.md) already calls one at
two grains. A world is REFUSED — neither opened nor an achiever — where a desire reads unmet in it
by a row that has no equal in the world it was forked from: it newly enters the avoided state. That
is never-newly-enter, which the 0.1.0 law's violation shapes did at expansion and which #565 left as
the coordination half to build; the parked van is its first instance, eleven worlds refused and a
seven-step route around found instead of the five-step route through. A desire already unmet in
the ground is no bound on the plan that repairs it, since repair removes a row and enters nothing:
two vans posed on one cell still mint their want and a drive still parts them. What this does NOT
do is touch the corridor — none of the 68 worlds either search visits holds two vans, because each
plan moves its own van and the conflict is between two plans — and that is the measurement that
shows the bound is half of the answer.

**A plan found is the ground of the searches after it.** This is the IRMA order the committed step
was built for — a commitment is background a new option is filtered against, earliest committed
first ([a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md))
— and the medium is the store, as [planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)
says of every meeting between the two. Two grains of it:

- *Within a pass*, a plan found for one want is laid into the imaginarium, before the next want of
  the scope is searched, as the predictions its steps are: one `orexis:PredictionGraph` per step,
  holding from the step's `execution:landsAt`, carrying the facts of the step's `execution:adds`
  graph and retracting those of its `execution:retracts` graph against `$state` — the exact shape
  `lay_ground` lays a ground from ("a prediction is an action nobody takes"; this is the one
  somebody will). The grounds are re-laid, the next want is searched from the present as before,
  and each of its worlds is forked from the ground holding at its landing with its path replayed
  there — `take._replayed`, built for #596 — so a world of van B's search at the third drive holds
  van A where A's plan puts it, and the bound refuses the one that joins it on `c2_1`. B's plan
  routes around, or waits where its domain has a step that waits. Every plan a pass finds is
  published, so a plan found is already what the pass will commit to, and the pass's own
  `walking()` already reads a plan published and adopted by nobody as walked; laying it as the
  next search's premise says the same thing a search earlier. The desires are weighed once, in the
  grounds the pass laid from the beliefs, and are not weighed again in the re-laid ones: a plan
  the bound let through enters no avoided state, so there is nothing new for the derivation to
  read.
- *Across passes*, through the committed step. A step a drift reads reaches the grounds as it does
  today, a flow the drift accumulates. A step whose action is FICTIVE — a drive, a move — is read by
  no drift and never will be, since nothing moves a van but a drive and the executor itself writes
  the step's prediction into the state when it takes it; so the executor lays it ahead as well,
  at adoption beside the committed step, as the same prediction graph the pass laid, derived from
  the committed step and forgotten with it. A want minted while A's plan walks — a third parcel —
  is then searched in grounds that hold A where A will be, by the ordinary pass.

The order is the store's. Within a pass it is the order the pass searches the wants of a scope in,
which is the order they stand in the store; across passes it is adoption, which the intentions
carry. The elder plan stands and the younger is found around it, which is what the issue asked —
"one van's plan is re-searched while the other's stands" — without anything being re-searched: the
younger is searched once, against the elder.

**A world whose steps land at once composes no future, so the courier declares a drive's band
first.** Every world and every step of the dispatcher stands at one instant today, and a plan with
no instants cannot be the ground of anything: the ground at a landing is the present, and the
present holds the vans apart. An action's landing is a band the domain declares as the band it is
([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md));
the courier's nought is the courier saying it is a puzzle, and the dispatcher is a world about two
plans meeting in TIME. Declared, each drive's world moves a stretch on, the five steps stand at
five instants, and the composed grounds have a third instant for two vans to meet at. The courier
alone — one van, hanoi's tower on it — is unmoved by the band but for its instants, since nothing
there is composed.

What each part keeps and what it breaks, against the principles:

- *A desire is weighed in grounds alone* — AMENDED: a desire is weighed in grounds to mint and in
  possible worlds to bound. `weigh` already does both; the Planner did not ask it to. The line in
  AGENTS.md is rewritten by this record.
- *A search is never handed a DESIRE* — KEPT: what the search PURSUES is still the want, and a desire
  bounds the worlds as a precondition admits the candidates. The desire is read, never pursued, as
  the law was read.
- *A want is judged by its met-test and nothing else* — KEPT: the want is; a WORLD is refused by the
  desires, which is admission, not score. The search still sees no partial progress and the
  frontier is still cost.
- *Nothing stands between a desire and a want* — KEPT, and this is what refuses the issue's
  mechanism below: the desire itself is the bound.
- *A want an intention is walking is neither searched nor handed down again* — KEPT: the elder plan
  is never touched; the younger is searched once, against it.
- *A pass begins in one place, and judging happens once in it* — KEPT: the desires are judged in the
  grounds the pass laid; a plan laid afterwards is the search's premise, as a possible world is.
- *A committed step is a belief over its landing window, and a drift reads it there* — WIDENED: a
  fictive step's prediction is laid by the executor, since no drift will read it. The committed
  step still carries no prediction and still crosses into the present as nothing; the prediction
  graph is applied by `lay_ground` at its landing and handed to no reader of the present, which is
  what [a-steps-prediction-is-two-graphs-it-names](/decisions/a-steps-prediction-is-two-graphs-it-names.md)
  refused putting the two graphs in a BELIEF for.
- *Control the derivative, not the value* — KEPT: nothing here picks a route or a cell; the bound
  says what is not available and the elder's ground says what will be true, and the search picks.

# What was refused

- **The issue's derived, temporary want** — "van B is not at cell X while van A crosses it", hung
  on the conflict, dying with it. Three things are wrong with it in Agent 0.2.0's terms. It is
  UNIVERSAL — hold at every instant of an interval, `hold-during` in
  [a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md)'s
  table — and a want is existential, achieve once; the kind is the type, and a want that must hold
  throughout is a desire wearing a want's name. It RESTATES the standing aversion for one cell and
  one interval, a second owner of a claim the desire already states for every cell at every
  instant. And it STANDS BETWEEN the desire and the search — a search that derives wants is a
  second minter beside `derive_wants`, which
  [one-function-mints-every-want](/decisions/one-function-mints-every-want.md) refused in every
  other package. What the issue wanted of it, the standing desire gives directly: weighed in B's
  worlds forked from A's grounds, it refuses the shared cell without a word being minted. The
  trigger for revisiting is a conflict the standing desire cannot say — one relating two
  conditions, the four PDDL3 forms the quantifier model does not reach.
- **The second want searched in the first plan's cone.** Candidate worlds are STATED, grounds are
  BELIEVED with predictions applied, and the planner's two readers are built on that line
  (`world_at` leaves out every possible world but the one meant). Forking B's worlds from A's
  possible worlds would make A's plan a premise before anything was committed to it and under a
  name nothing carries forward, where laying it as a prediction into the grounds makes it a
  premise the way every prediction is one — applied at its instant, superseded by the next, and
  read by the one reader. The cone's worlds also have no instants of their own to compose at
  without the band, which is the same objection as the next.
- **The bound alone.** Measured: none of the corridor's 68 worlds holds two vans, so a bound on
  worlds refuses nothing there. It is the right half for a plan that breaks the aversion by itself
  — the parked van — and no half at all for two plans that break it together.
- **Execution alone** — the readiness hold and the patience of #568's text. There is no readiness
  hold in Agent 0.2.0 (`Executor.tick` hands a due head over unasked), `Planner._blocked` asks the
  present once a pass and the drive's precondition reads adjacency alone, so nothing holds a van to
  anything. Built, a hold at take time would catch a van already standing on the cell and never two
  arriving in one drain, which is the corridor; and it would decide in the executor, where
  [planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)
  put every judgment of a step in planning and only the ending in execution. "The world verifies
  the plan, not a search" is about a METHOD that worked once and is walked again; it does not say
  the agent may make a state it holds an aversion to and find out by making it. The hold's two
  limits, deadlock and fairness, are the market's answer for two agents (#568); for one agent
  neither arises, since one mind sees both plans and the elder's ground is where the younger is
  found.
- **The aversion as the drive's precondition** — `FILTER NOT EXISTS { ?other courier:at ?to }` on
  the Drive. It would catch the parked van and nothing of the corridor, since each search's present
  has the cell empty; it would put the WORLD's word into the DOMAIN, where `world/dispatcher/desires.ttl`
  says in its own comment that no domain says two vans may not share a cell; and it would state the
  aversion twice, once as a desire the derivation reads and once as a precondition the search
  reads, with nothing holding the two to each other.
- **A repair minted from a foreseen ground two commitments make.** With the committed steps laid as
  predictions and nothing else changed, the pass after an adoption would read the aversion unmet at
  the third drive's instant and `derive_wants` would mint `no_cell_holds_two_vans.pursued` there,
  searched from that ground, a one-step drive placed at that instant and adopted as a third
  intention — two intentions moving one van at one instant, the repair of a universal by an
  existential, after the fact. The ordering within the pass is what makes this never happen for
  two plans found together: the younger is found around the elder. Where it CAN still happen is the
  seam below.

# Measured

| case | wants | weighings | worlds visited | holding two vans | aversion weighed in every world | walked |
|---|---|---|---|---|---|---|
| the corridor | 2 | 33 and 33 | 68 | 0 | 38.4 ms (min 37.7), 0.56 ms each, unmet in 0 | both on `c2_1` for one act |
| a van parked across the only shortest path | 1 | 58 | 66 | 11 | unmet in 11 | both on `c2_1` for one act |

And of the corridor's pass: one distinct instant across the 68 worlds' periods and the ten steps'
three instants each; after the runtime's pass, two plan graphs, no committed step, no prediction,
no drift, no sensor.

# Seams left open

- **A surprise that shifts a lockstep.** Two plans found around each other meet nowhere in the
  grounds; a step landing late moves one plan's instants and not the other's, and the pass after
  may read the aversion unmet at an instant both commitments make. Today the derivation would mint
  the repair refused above. What it should do is end the younger intention whose step the composed
  ground now refuses, as a blocked step ends one — planning's judgment, execution's ending, the
  second early-ending case of planning-and-execution-meet-at-the-store read at the step's landing
  instead of the present — and search its want again against the elder's grounds. That needs the
  untaken steps of a standing intention judged in the grounds at their landings and not only the
  head in the present, since a head becomes due the instant its predecessor lands and is taken in
  the same walk. Its trigger is the first world where a landing's band is wide enough to shift
  one of two plans; the dispatcher's drives land exactly.
- **A step that waits.** The courier has no action that does nothing for a stretch, so a van found
  around an elder plan takes a detour where one act's wait would do. A `Wait` is the domain's to
  add, costed and banded like a drive; whether an agent's wait is an action or the absence of one
  is the first question it poses.
- **A fictive step's world moves when the step is taken, and its prediction from when it lands.**
  The executor writes a fictive step's adds into the state at take time and the intention advances
  at `landsAt`; laid as a prediction from `landsAt`, the step's effect is in the present a band
  before it is in the ground. Harmless while the present is laid over the ground at the same
  instant; the first world where a reader compares the two decides which instant a fictive step
  moves the world at.
- **A committed step and a drift about one key.** A sensed step reaches the grounds through its
  drift; a fictive one through its own prediction; nothing shipped is both. A step whose action a
  drift reads AND whose two graphs name a key the drift moves would be laid twice, and the two
  predictions at one boundary supersede in parallel.
- **A plan that must pass through a forbidden state.** Never-newly-enter refuses every world that
  does, so a want whose every plan breaks a standing desire on the way — a bid that creates a debt
  under a desire to owe nothing, if a world wrote one — is unreachable, as PDDL3's `always` makes
  such a problem unsolvable. No shipped desire reads any shipped plan's intermediate state unmet;
  the first that does is the trigger, and the answer is the desire's to narrow, not the bound's to
  soften.
- **The bound's cost is desires times worlds.** 0.56 ms a world for one aversion over a store of
  seventy worlds; only the desires whose met-test reads a predicate the scope's actions write are
  weighed, so a desire about soil costs the courier's search nothing. A world with many desires in
  one scope has not been measured.
- **Ties, and the order within a pass.** Which of two wants found in one pass is the elder is the
  order the pass searches them in, which is the store's order and not a ranking; nothing ranks
  wants, as [a-want-is-judged-by-its-met-test-and-nothing-else](/decisions/a-want-is-judged-by-its-met-test-and-nothing-else.md)
  left it. The day a world needs the nearer van to go first, that is the ranking seam and not this
  record's.

# What it amends

- The AGENTS.md line *a desire is weighed in grounds alone, in the planner's pass, and the walk
  comes after it*, which described the code and the corridor's finding; it now carries the rule and
  names this record.
- The two-vans seam of [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md),
  which named "the mechanism #567 names — a search that derives a want" as what would separate the
  vans; the vans stay one scope, and what holds their plans apart is this record's.
- The seam of [a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md)
  asking whether a maintenance constraint should be judged at every state of a candidate plan: yes,
  as a bound, never-newly-enter, and the dispatcher's aversion is the first.
- The IRMA seam of [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md),
  which said two plans interfere only where a drift reads the committed steps: a fictive step is
  laid as its own prediction, since no drift will read it.
- #565's closing word that the coordination half — a candidate world scored for every want of the
  component — was untouched: it is decided here as a bound by the desires, not a score, and
  [#567](https://github.com/ShishkinDmitriy/orexis/issues/567)'s mechanism is refused in favour of
  it. Nothing of this is built; the issues that carry it are named from the roadmap.
