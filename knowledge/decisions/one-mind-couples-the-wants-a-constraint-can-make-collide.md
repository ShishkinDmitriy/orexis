---
type: Decision
title: One mind couples the wants a constraint can make collide, and two minds meet through prediction, the market and execution
description: >-
  What keeps two plans of one agent from making a state its standing aversion forbids, which is
  the mechanism #567 still asked for, decided twice in two days. Measured on the dispatcher - no
  possible world either search visits on the corridor holds two vans (none of 68), every world and
  step stands at one instant since the courier declares no landing band, and after the walk the
  beliefs hold no committed step or prediction; a van parked across the other's shortest path is
  driven through, eleven of 66 worlds holding two vans, judged by nobody; and one want about both
  parcels, searched coupled, found the joint plan at 674 candidates against 90 for two. Decided -
  the wants of one mind are COUPLED where a constraint's footprint says their plans may interfere,
  one cluster, one want, one search, which finds the joint optimum by construction; a constraint
  is its own KIND, planning:Constraint, what the world says is possible stated in a desire's words
  and of another modality, weighed in every possible world, and a world that violates one is
  impossible - never repaired, the present validated and refused rather than mended (built as a
  desire's bound, #902, and reworked 2026-10-06 - the corridor's colliding worlds impossible and
  the parked van served or moved rather than driven through); a walking want is reconsidered when
  a want the footprint couples to it arrives (built, #905 - the step in flight kept, the joint want
  searched from where it lands); a limit on acts in flight is world state - one driver aboard one
  van, whose own constraint couples the plans that move it (built, #903); two minds optimize alone and meet through what they
  observe, what they are told and what the market allocates. Refused - the derived temporary want;
  the elder plan laid as the younger's ground, this record's own first version; independent plans
  reconciled afterwards as the default for one mind; the bound alone; execution alone; the aversion
  as a precondition; the constraint as a reading of a desire bounding worlds it newly enters; and
  a resource over committed steps' windows the executor holds (built, #903, and refused).
status: accepted
timestamp: 2026-10-05T09:00:00Z
---

# The question

[#567](https://github.com/ShishkinDmitriy/orexis/issues/567) posed one agent, two vans, two parcels
and an aversion — no cell holds two vans — and asked for a search that derives a want from a conflict
between two plans. The world is built and measured (`world/dispatcher/`,
[measure-the-search](/runbooks/measure-the-search.md)); the aversion is a standing desire in its
honest form, `planning:unmetWhen`, judged in every ground since #892, so two vans posed on one cell
mint a want and a drive parts them. What nobody judges is the state two plans make BETWEEN acts: on
the corridor each plan drives its van through `c2_1` at its third step, the two are walked in
lockstep, and the present holds two vans on that cell for one act. The question is how the plans of
one mind are combined, and this record answers it twice: a first version on 2026-10-04 sequenced
them, the elder plan laid as the younger's ground, and the sovereign refused it the same day, before
it merged, for the reason given under *What was refused*. This is the version that stands.

# What the code does today, measured

On the development container, one pass of the Planner at a budget of 128 over the booted world as
`world/dispatcher/tests/test_dispatcher.py` builds it; not committed to the suite.

- **The corridor.** Two wants, two plans of five steps, 33 and 33 weighings over 68 possible
  worlds. **None of the 68 holds two vans on one cell**, because each plan moves its own van and the
  collision is between the plans, not inside either. Every world and every step stands at the pass's
  instant: the courier's actions declare no `planning:landsAfter`, so the plans have no time axis to
  be compared on. Walked, both vans stand on `c2_1` for one act. Afterwards the beliefs hold two plan
  graphs and no committed step, no prediction, no drift: the committed step reaches the future
  through a drift alone ([committed-step](/domain/execution/committed-step.md)) and the courier has
  none. *Since #901 (2026-10-05) the courier declares its band — a drive half a minute to a minute,
  a pick and a drop at once — so the steps land at distinct instants, the worlds hold over periods
  and a committed drive's window is two minutes and more; the counts above did not move.*
- **A van parked across the other's only shortest path** — van B at `c2_1` with nothing to do,
  parcel A owed at `c3_1` from `c1_1`. One want, 58 weighings, a five-step plan that drives through
  the parked van; **eleven of the 66 worlds visited hold two vans**, and weighing the aversion in all
  66 — `weigh(store, desire, world)`, the function as it stands — reads unmet in exactly those
  eleven, at 0.56 ms a world.
- **One want about both parcels, searched coupled** — the derivation as it stood before
  [a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md): the
  joint ten-step plan, 674 candidates and 85 seconds at a budget of 1024, against 90 candidates for
  the two wants apart. That is the product's price at two vans, and it grows exponentially with
  them.
- **What execution holds a step to.** `Executor.tick` hands a due head over unasked; `Planner._blocked`
  asks the present once a pass whether a head's precondition holds, and a drive's reads adjacency
  alone. Two intentions are walked in parallel, and nothing asks whether one actor can take two
  steps in one drain.

# The claim

**One mind couples the wants a constraint can make collide.** An agent holding one desire over every
parcel ranks the parcels together, and the plans for them are not strangers: they share the vans,
the grid and the aversion. Where two wants' plans may interfere, the mind that sees both searches
them as ONE — one cluster, one want about both instances, one search over one imaginarium — and the
plan it finds is optimal for both by construction, under the cost the search already uses, the sum
of its steps' costs. Nothing new is minted to say it: the derivation already mints a want per
cluster, and what changes is the clustering rule. Today a cluster is the instances a shape's block is
about, which made every parcel its own want; now instances whose plans may interfere under a
constraint are one cluster, and instances no constraint can join stay apart, as they were. The
joint want's estimate is the desire's select summed over its instances — exactly the sum #893
narrowed away for a want about one — so the frontier is still A\* and still admissible, and the
invariant is weighed in every world the coupled search opens, so the colliding worlds are pruned
from the product rather than found in it afterwards.

**What couples is the constraint, read the way a scope is.** A scope is a predicate on a key
([a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md)); a constraint is a
select, so it has a footprint: the predicates it reads and the key it joins them on. The two-vans
aversion reads `courier:at` on vans and joins on the cell, so two wants may collide under it only
where both have an action writing `at` on a key the aversion can join. Two vans on disjoint grids
never meet; a parcel want and a want about soil never meet; those stay separate wants and pay no
product. The analysis is the scopes' meet, one level up, and it is what makes coupling affordable:
the product is paid only by the groups a constraint can actually make collide.

*Built 2026-10-05 (#900), and one word of the above was wrong: read as a scope's atoms are, off the
public graphs with every pattern optional, the aversion is grid-blind — it joins `van_a` to `van_b`
with the cell unbound on the shipped pose and on two grids a continent apart alike, since the drive's
adjacency is a `FILTER` over coordinates and the public half of a text is its patterns. The footprint
is read instead over the REACH, the delete-free closure of the effects' constructs over their
preconditions from the present ground, where the aversion's rows are the collisions the plans could
make: 32 on the shared grid, none on disjoint grids. An instance meets a row's terms through a filling
the reach admits that binds both, the pick of the parcel into the van. Per pass, in the derivation,
since the reach begins at the present; 17 ms a pass on the dispatcher and one query on a holder with
no aversion ([constraint](/domain/planning/constraint.md), `agent/planning/couplings.py`).*

**A constraint is its own kind, and the difference from a desire is modality.** The bundle had the
desire and the precondition and nothing between: a desire is what the agent wants of the world, a
precondition what one action needs. A constraint is what the world says is POSSIBLE — a met-test
asks whether a world is desired, a constraint whether it can be — and that is a difference of
logic and not of strength, the bouletic against the alethic (AGENTS.md: desire is bouletic,
availability alethic). So it is a kind of its own, `planning:Constraint`, stated by the world in a
desire's words — a holder `planning:holds` it, it carries a shape under `planning:metWhen` or an
avoided state under `planning:unmetWhen`, the same compiler yields the same rows — and no subclass
of `planning:Desire`, since the one thing that differs is what a row means.

- *A world that violates a constraint is impossible.* `Planner.expand` weighs each constraint of
  the holder whose footprint the scope's actions write in every world it weighs the want in, and a
  world where any yields a row is marked `planning:impossible` on its own row and the want's
  weighing of it made bare — `planning:open` and `planning:met` taken back — so the frontier's and
  the plan's reads pass it by with no filter. No parent is compared: possibility is a fact about the
  world and not about the step that reached it, so a world that keeps a violation the present already
  has is as impossible as one that enters it. The marked world and the constraint's weighing are
  KEPT, not forgotten — forgotten, its candidate would be unweighed again and the next iteration would
  take it again, and kept, a pass can be continued and the runbook can count.
- *The present is validated, not repaired.* A constraint is no desire, so the derivation mints
  nothing from it; one the present violates is a contradiction between the world's state and its own
  word about what is possible, said in the log by every pass with its rows, and `orexis-onboard`
  refuses a world posed that way. Two vans posed on one cell no longer mint a want a drive parts: that
  was physics repaired as a preference. A prohibition the agent MAY enter and must leave stays a
  desire — an aversion, `planning:unmetWhen`, repaired when entered, weighed in grounds and never in
  possible worlds (`agent/planning/tests/plans/an_aversions_want_is_repaired_by_a_step.trig`).

  *Built 2026-10-05 (#902) as a desire's bound — the aversion weighed in every possible world and a
  world whose rows its parent's lacked refused, never-newly-enter, the 0.1.0 law's pruning at
  expansion — and reworked 2026-10-06 into the above after the sovereign's objection that the bound
  mixed modalities: the same shape was a want to repair in the ground and a wall in the search, and
  two vans posed on one cell were being mended by the agent as if the world's physics were its
  preference. What #902 learned stands: the verdict was first kept and the two reads filtered, and the
  `FILTER NOT EXISTS` inside the frontier's `MIN` subselect cost a quarter of every pass on the search
  bench, hanoi and the courier included, holders of no constraint; measured alternated, and refused —
  so the mark takes the verdict back rather than filtering it, and the reads carry no filter. On the
  parked van the worlds through van B are impossible, seven of them, and what the one mind finds is
  not the seven-step route round but a five-step delivery BY VAN B, which stands beside the parcel;
  with the parcel already aboard van A it moves van B aside and drives through, four steps where the
  route round is five. The route round was what a mind holding one van would find, and this mind holds
  both. The estimate is admissible and loose by one there, the step the constraint costs and the parcel
  does not owe. Every count the bound measured held under impossibility, since on the dispatcher's
  poses no world kept a violation the present had; the one pose where the two differ is both vans on
  one cell, where the aversion's one-step want is gone and the present is refused instead.*
- *A limit on acts in flight* — one driver drives one van at a time — is modelled as world state the
  constraint can read, a driver who must be aboard the van it drives, or not at all; the executor-held
  resource is refused below.

**A walking want is reconsidered when a want the footprint couples to it arrives.** Intentions are
commitments: stable by default, reconsidered on a trigger, which is Bratman's stance and IRMA's
filter with an override. The trigger here is a new want the constraint's footprint couples to one
an intention is walking. Then: a step in flight is committed and stays, it is the present's
prediction and the ground the re-search starts from; everything untaken is re-searchable, so the
coupled want — both instances — is searched from the ground after the in-flight step lands. If the
joint plan's first steps for the walking van match its intention, nothing changes and the second
plan fits around it; if they do not, the walking intention is ended, as a blocked step ends one
([planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)),
and the joint plan is adopted. A van turning back is then a legitimate outcome, found by the search
and decided by nobody. Nothing is sunk but the step in flight, since the present already holds the
van wherever it got to.

*Built 2026-10-06 (#905), as the sovereign put it that day: commitment has two grains,
[commitment](/domain/execution/commitment.md). HARD on the step in flight — handed to its taker and
not yet answered — which nothing planning decides cancels; it may still fail by itself. SOFT on the
plan, kept by default, with the one trigger above. The coupled want is a NEW want, under its own name
and about both instances, minted by the derivation as every coupled want is, saying which walking
want it reopens (`planning:reopens`) and minted at the instant that want's step in flight lands; the
walking want is not edited, and goes by the rules it always went by — withdrawn once its intention
has ended and the cluster is the coupled want's, or kept where its intention stands. That instant is
a ground of its own: the pass lays a boundary at each step in flight's landing, `landsAt` shifted by
how late the step was taken as the executor reads it, laid whatever it holds and so never collapsed
into the ground before it, and holding what the agent already sees then — a fictive drive wrote its
effect into the present when it was taken, so on the dispatcher it is the present's facts at a later
instant, and the joint plan opens there. Struck, the reopening want is found by no pass until its
instant has passed, and is then searched from the present while the walking intention walks on.
"Match" is read as the record's own words have it, the joint plan's FIRST steps: the plan agrees where
it begins with the walking intention's untaken steps, by action and filling, and then the intention
stands untouched and only the new part is published (`publish_plan`'s `kept`); a plan with the same
steps later does not agree, since two intentions are walked side by side and nothing holds a step of
one after a step of the other, so the order the joint plan was found safe in would not be the order
walked. Disagreeing, planning signals `reconsidered` and the executor marks the intention to end
after its step in flight (`execution:endsAfter`), closing the untaken steps' committed windows at
once, and resolves it `superseded` when the world answers the step. Measured, alternated against the
tree before: the coupled re-search costs what the coupled search from that ground costs — 108
candidates on the shipped pose, 112 on the corridor, the same on both trees, since a fictive drive's
landing ground holds the present's facts — and what changed is what is walked. Before, the coupled
want was searched from the present beside the walking want and both intentions drove van A: on the
shipped pose van A's intention ended `failed`, a step of it blocked by the other's, and the corridor
took twelve acts for ten; after, the walking intention ends `superseded` after its step in flight, or
stands where the joint plan begins with its steps, and ten acts deliver both parcels with two vans on
no cell (`world/dispatcher/tests/test_dispatcher.py`, [measure-the-search](/runbooks/measure-the-search.md)).*

**Two minds optimize alone and meet through prediction, the market and execution.** Two agents each
hold their own desire and neither sees the other's plan. Their channels are what the other did
(execution: a blocked step, patience, a re-search), what the other said (a peer's announced route is
a document believed as said, and a route is facts holding over periods, which is a prediction graph
laid into the grounds like any other), and what the market allocates (right-of-way as a lot, #568).
Laying another's plan as a prediction into one's grounds is the two-minds tool, and that is why this
record's first version was wrong for one mind: it used the tool for strangers on plans one mind sees
both of.

**A world whose steps land at once composes no future, where the vans move at once.** A coupled plan
is a sequence, and the executor walks a plan one head at a time, so two vans in one plan move one at
a time and the only collision the search can make is driving onto a cell a van stands on, which the
bound refuses with no time axis needed. The landing band
([a-landing-is-a-band-and-a-world-holds-over-a-period](/decisions/a-landing-is-a-band-and-a-world-holds-over-a-period.md))
is needed where two vans are to move at once — concurrent steps in one plan, which no plan says
yet — and for the resource, since two windows can overlap only once they have a length. *The
courier declares it since #901: a drive lands between half a minute and a minute after it is taken,
and a walk is a drive a pass. What that walk showed, which one pass had hidden: a pass in the middle
of the joint plan read the desire unmet for the parcel still astray alone, a cluster under a name of
its own, and minted it — a second want about an instance the coupled want still pursued, and a second
plan down the same cells. A cluster a standing want is already about is that want's now
(`derive_wants._covering`, `a_cluster_a_standing_want_is_about_is_not_minted_again`).*

# Against the principles

- *Nothing stands between a desire and a want* — KEPT: the derivation still mints every want, per
  cluster; the clustering rule changed, no minter was added.
- *A desire over instances says what each block is about, and a parcel astray is a want of its own*
  — AMENDED: a parcel astray is a want of its own unless a constraint can couple it to another, and
  then the two are one want; the 674-against-90 cost that record paid to avoid is paid only where
  the parcels can collide.
- *A want's estimate is the desire's with `$this` bound to its instance* (#893) — KEPT: a want about
  several instances takes the desire's sum over them, which `_instantiated` already leaves alone
  for a want about more than one.
- *A desire is weighed in grounds alone, in the planner's pass* — KEPT, after an amendment was
  undone: #902 weighed the aversion in possible worlds too, as a bound, and the rework returned a
  desire to the grounds; what is weighed in possible worlds is a constraint, another kind, by the
  same `weigh`.
- *Desire is bouletic, availability alethic* — KEPT, and this is what the rework restored: a wall
  in the search and a want in the ground were one shape with two modalities, and a constraint of its
  own kind gives the alethic one its name.
- *A search is never handed a DESIRE* — KEPT: what the search pursues is the coupled want; the
  constraint marks its worlds as a precondition admits candidates, read and never pursued.
- *A want an intention is walking is neither searched nor handed down again* — AMENDED: it is
  searched again, coupled, when a want the footprint joins to it arrives; the default stays
  commitment and the trigger is the constraint. Built (#905): the step in flight is kept and only
  the untaken steps are reopened.
- *A plan begun is walked to its end* (planning-and-execution-meet-at-the-store) — AMENDED: unless
  a reconsideration replaces its untaken steps, and then it ends after its step in flight.
- *Nothing ranks a want before the search that could rank it* — KEPT, and this is what the first
  version broke: sequencing made the store's order a ranking of elder over younger. Coupled, the
  search ranks the steps and no want is first.
- *Control the derivative, not the value* — KEPT: nothing picks a route; the constraint says what is
  not available and the search picks.

# What was refused

- **The issue's derived, temporary want** — "van B is not at cell X while van A crosses it", hung on
  the conflict. It is UNIVERSAL — hold throughout an interval — where a want is existential, so it
  is a desire wearing a want's name ([a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md));
  it restates the standing aversion for one cell and one interval, a second owner; and a search that
  mints it is a second minter beside `derive_wants`
  ([one-function-mints-every-want](/decisions/one-function-mints-every-want.md)). Coupled, the
  conflict never exists to be named: the colliding world is refused inside the one search.
- **The elder plan laid as the younger's ground — this record's first version.** Plan the first
  want, lay its steps into the imaginarium as predictions, search the second want in grounds that
  hold the first van where its plan puts it. It is cheap and it is prioritised planning, which is
  incomplete: where the elder's route blocks the younger entirely and nothing waits, the younger
  finds a detour or nothing; it makes the store's order a ranking nothing chose; and it throws away
  what one mind has, the sight of both plans at once, using for them the tool built for a peer's
  announced route. The sovereign's objection, 2026-10-05: an agent that knows in advance it holds
  two wants that may collide is expected to find the plan optimal for both, and only the coupled
  search does. The trigger for returning to it is a coupled group whose product no budget pays,
  where sequencing is the fallback that still finds something.
- **Independent plans reconciled afterwards** — conflict-based search: optimal plans per want, the
  constraints checked over the found plans together, a constraint added to one want where they
  collide, that want re-searched, branching on who yields. It is the textbook answer for many agents
  and optimal only with the branch, which is one more search per conflict; for one mind over a group
  the footprint has already shrunk, the coupled search reaches the same optimum in one search and
  needs no object for the conflict. Refused as the default for one mind; it is the shape the
  fallback above would take if the product ever outgrows the budget.
- **The bound alone.** None of the corridor's 68 worlds holds two vans, so a bound on the worlds of
  two separate searches refuses nothing there. It is the right half for a plan that breaks the
  aversion by itself and none for two plans that break it together; coupled, the two are one plan
  and the bound is whole.
- **Execution alone.** There is no readiness hold in Agent 0.2.0, a hold at take time would catch a
  van already standing on the cell and never two arriving in one drain, and it would decide in the
  executor what planning-and-execution-meet-at-the-store gave planning. For two minds it stays one
  of the three channels; for one it is not an answer.
- **The aversion as the drive's precondition.** It would catch the parked van and nothing of two
  plans, put the world's word into the domain, and state the aversion twice with nothing holding
  the two together.
- **A repair want minted from a foreseen ground two commitments make.** A third intention moving a
  van two intentions already move, the repair of a universal by an existential after the fact; the
  reconsideration above re-searches the coupled want instead of repairing around two plans.
- **The constraint as a reading of a desire, bounding the worlds it newly enters — this record's
  built second version (#902).** The dispatcher's aversion stayed a `planning:Desire`, minted a want
  in the ground where it already held and refused, in the search, a world whose rows its parent's
  lacked. It is cheap, it needs no term, and it is two modalities in one shape: the same select was
  a want to repair in the present and a wall in the search, so two vans posed on one cell were
  mended by the agent as if physics were its preference, and "never newly enter" had to compare each
  child to its parent to keep the repair possible. The sovereign refused it 2026-10-06: a constraint
  is a check that a world is possible and a met-test that it is desired, so a world violating a
  constraint is impossible — no parent, no repair, the present validated and refused — and the
  constraint is a kind of its own. Everything #902 measured about WHERE the verdict is written stands.
- **A resource as an executor hold over committed steps' windows — built as #903 and refused.**
  `execution:occupies` on an action, read by the timekeeper to hold a head back while another step
  of the same resource was in flight. Refused 2026-10-06 for two reasons: a committed window as
  placed is the PLAN's band and not the act's occupancy, so a select over committed steps cannot say
  what is in flight and the hold had to live in Python, a predicate only code reads, which is a side
  channel beside the store planning and execution meet at; and the limit it modelled — one driver,
  one van at a time — is world state the constraint can read, a driver who must be aboard the van it
  drives, or nothing. The trigger for returning to it is the first world that needs a schedule limit
  with no state behind it.

# Measured

| case | wants | weighings | worlds visited | holding two vans | note |
|---|---|---|---|---|---|
| the corridor, two wants | 2 | 33 and 33 | 68 | 0 | the aversion weighed in all 68 reads unmet in none, 0.56 ms a world |
| a van parked across the only shortest path | 1 | 58 | 66 | 11 | unmet in exactly those 11 |
| one want about both parcels, coupled (before a-parcel-astray) | 1 | 674 candidates | | | ten-step joint plan, 85 s at budget 1024; two apart cost 90 |
| the shipped pose, coupled by the aversion (#900, built) | 1 | 148 | 228 | 0 | ten-step joint plan, 2.6 s at budget 256, cut short at 128; two apart cost 50 and 0.21 s |
| the corridor, coupled (#900) | 1 | 216 | 296 | 18 | ten-step joint plan, 5.3 s at budget 512; nothing refuses the 18, the bound being #902's |
| the vans on disjoint grids (#900) | 2 | 23 and 23 | 50 | 0 | the aversion over the reach yields no row; two wants as before |
| the corridor, coupled, bounded (#902) | 1 | 210, and the aversion in 210 | 286 | 16, 13 refused and 3 passed over by hash | the same ten-step plan, walked with two vans on no cell; none of the 16 opened |
| the shipped pose, coupled, bounded (#902) | 1 | 148, and the aversion in 148 | 228 | 0 | unchanged: the aversion reads met in every world and refuses none |
| van B parked on `c2_1`, bounded (#902) | 1 | 49 | 56 | 8, 7 refused and 1 passed over | a five-step delivery BY VAN B; van A never moves |
| the parcel aboard van A, van B parked, bounded (#902) | 1 | 52 | 66 | 8, 5 refused | van B steps aside, van A drives through: four steps, the route round five; the estimate reads three |
| both vans on one cell, bounded (#902) | 2 | 4 and 75 | 128 | 14, 7 refused | the aversion's own want refused nothing, its one-step drive found; the joint want `Exhausted` at 128 as before |
| the corridor, coupled, the constraint a kind of its own (2026-10-06) | 1 | 210, and the constraint in 210 | 286 | 16, 13 impossible and 3 passed over by hash | the same ten-step plan, walked with two vans on no cell; 6.7 s against 6.2 s alternated, within the drift |
| the shipped pose, the same | 1 | 148, and the constraint in 148 | 228 | 0 | unchanged; 3.3 s against 3.1 s |
| van B parked on `c2_1`, the same | 1 | 49 | 56 | 8, 7 impossible | five steps BY VAN B; 434 ms against 373 |
| the parcel aboard van A, van B parked, the same | 1 | 52 | 66 | 8, 5 impossible | van B aside, van A through, four steps; 435 ms against 402 |
| both vans on one cell, the same | 1 | 75 | 128 | 14, 7 impossible | NO want from the constraint: the present is a contradiction, said and refused at onboarding; the joint want `Exhausted` at 128; 916 ms against 966 |
| the vans on disjoint grids, the same | 2 | 23 and 23, the constraint in 42 | 50 | 0 | unchanged; 357 ms against 378 |
| parcel B arriving mid-walk, as shipped, reconsidered (#905) | 1, reopening | 76, and the constraint in 76 | 108 candidates | 0 | the joint plan opens where van A's drive in flight lands; van A's intention `superseded` after it; ten acts. Before: searched from the present beside, van A's intention `failed` |
| parcel B arriving on the corridor, the same | 1, reopening | 87, and the constraint in 87 | 112 candidates | 7 impossible | the same, two vans on no cell; before, twelve acts for ten |
| parcel B arriving at van B's cell, agreeing (#905) | 1, reopening | 76 | 108 candidates | 0 | the joint plan begins with van A's drive and drop: its intention stands, van B's five steps adopted beside it |
| parcel B arriving on a disjoint grid (#905) | 1, alone | — | 37 candidates | 0 | nothing reopened; van A's intention untouched |
| one driver, the vans on disjoint grids, the two-vans constraint alone (#903) | 2 | 18 and 26, the constraint in 37 | 22 and 34 candidates | 0 | five steps and six, the second boarding first; walked side by side, van A driven with the driver aboard van B |
| the same, the driver's constraint held (#903) | 1 | 133, each constraint in 133 | 191 candidates | 0 | one plan of eleven: van A, the boarding, van B; walked one act at a time; 2.2 s at budget 256, `Exhausted` at 128 |

# Seams left open

- **The product's budget.** A coupled group costs the product of its members' moves, exponential in
  vans; the footprint keeps the group small and the bound prunes the colliding worlds, and the pass
  is still bounded by its budget in worlds. The first group whose joint plan no budget finds is the
  trigger for the fallback, sequencing or reconciliation, and for measuring which. Measured 2026-10-05:
  the shipped pose needs 228 candidates and the corridor 296 — 286 once the bound refuses its
  colliding worlds (#902), since the interleavings it prunes were never on the shortest path, and the
  shipped pose nothing, since no world of it collides; neither fits the default 128 — and both vans
  posed on one cell with their parcels where they stand — a joint delivery of thirteen steps — is found
  by neither 128 nor 512, the latter in 32 seconds, so the trigger is already in the suite, pinned as
  `Exhausted` in `world/dispatcher/tests/test_dispatcher.py`.
- **A plan that must pass through an impossible world has no plan.** A world that violates a
  constraint is impossible whatever the want's verdict there, so a want every route to which crosses
  one ends `Exhausted`, and nothing relaxes a constraint for a want that cannot otherwise be met —
  what cannot be cannot be wanted into being. Checked by reading on 2026-10-05 (#902): the dispatcher
  is the one shipped world that states a constraint, and on its grid every cell has a neighbour the
  other van is not on, so no shipped want is unreachable for it; the courier, the tower, the
  greenhouse and the market worlds state none and pay one query a pass. The trigger is the first
  world that poses a corridor one cell wide with a van at each end, where the honest answer is a
  `Wait` (the seam below) or the market's right-of-way (#568).
- **A present that violates a constraint is searched from as it stands.** The present is said and
  refused at onboarding, never marked, so a want is still searched from it and a world that keeps the
  violation is impossible while one that happens to repair it is not: the search may mend the
  contradiction on the way to a want and nothing asks it to. A world that reaches a contradicted
  present at runtime — a sensor reporting two vans on a cell — is the trigger for deciding whether
  the agent should do more than say so.
- **A constraint's footprint for the search is read by predicate, not over the reach.** A constraint
  is weighed in a scope's worlds where its text reads a predicate the scope's actions write — `at`,
  which the drive writes — so two vans on grids a continent apart pay the constraint's weighing in
  every world (42 on the disjoint pose, 0.7 ms each) though the reach already knows no world of
  theirs can hold two vans. Reading the reach there would be #900's analysis asked a second time, from
  the Planner, and the saving is a few tens of milliseconds on a pose that costs 350; the trigger is
  a holder with several constraints over a large scope, where the weighings outgrow the reach.
- **The joint want's estimate is the desire's whole sum.** A want a constraint coupled about several
  instances points at the desire's select with `$this` unbound, which sums over EVERY instance astray;
  where the coupled instances are all there are that is the joint plan's cost exactly, and where a
  third parcel is astray and coupled to neither its drives are counted too, an overstatement. Binding
  `$this` to several instances is a `VALUES` block in a text whose inner group the derivation cannot
  find without owning the select's grammar; the first world with three parcels decides how.
- **A reach is one scope's actions wide and the holder's own.** The reach is closed over every action
  the store holds with `$me` the holder, in the imaginarium of the scope the derivation runs in; a
  scope whose actions another scope's constraint reads is already one scope with it, so nothing is
  lost, and a coupling across two holders' desires in one store is not asked.
- **Concurrent steps.** A plan is a sequence and is walked one head at a time, so a coupled plan
  moves one van at a time. Two vans moving at once in one plan is a partial order over steps, which
  no plan says and no executor walks; its trigger is the first world whose driver is two. The landing
  band it needs is declared since #901 — a drive is a stretch, a step opens where the one before it
  lands — so what is left is the order alone: a step whose window may overlap the one before it,
  which `execution:then` cannot say.
- **A step that waits.** The courier has no action that does nothing for a stretch, so a van held
  back by the bound takes a detour where one act's wait would do — or, measured (#902), the mind moves
  the other van aside, which is one act too and is what it found; a `Wait` is the domain's to add,
  costed and banded like a drive.
- **A limit on acts in flight as world state, and coupled only by a constraint over it** (#903,
  `world/driver/`). One driver, two vans on two grids no drive crosses: a drive needs the driver
  aboard the van, and a boarding moves the driver to the other, so every plan moves one van at a
  time by construction and the two-vans constraint is never at stake. It does not couple the two
  parcels, though both their plans move the driver: the derivation couples instances where a
  constraint's rows over the reach join them and on nothing else, and the two-vans constraint over
  two grids yields no row — two wants, five steps and six, measured, and walked side by side van A
  was driven with the driver aboard van B, since a head falling due inside a walk is taken without
  its precondition asked again. So the world states the driver's own constraint, a driver aboard one
  van at a time: no plan breaks it, since a boarding takes away the van left, and over the
  delete-free reach the driver is aboard both, which joins the vans and so the parcels — one want, one
  plan of eleven steps, walked one act at a time. Coupling the wants whose plans merely write one
  fact, with no constraint saying why that collides, is the kernel change this left unbuilt: a shared
  write is not a collision where both plans may write it in turn, and the constraint is what says
  this one is a body that cannot be in two places. Its trigger is a world whose shared state no
  constraint can honestly be stated over.
- **A surprise after coupling.** A joint plan walked with one van late still holds, since it is one
  sequence; a step that fails ends the intention and the coupled want is searched again from the
  present, as any failed plan is. What is not decided is a late landing in the concurrent case
  above, which does not exist yet.
- **The joint plan opens at the step in flight's earliest landing and waits on no answer** (#905). A
  plan opens each step where the one before it lands at the earliest, and the joint plan opens where
  the reconsidered intention's step in flight does; but the executor holds a head to the step before
  it in its own intention and to nothing of another's, so a step in flight the world answers late —
  a real actuator, not a fictive drive, which answers exactly then — overlaps the joint plan's first
  step by as much. No shipped world reconsiders a step that is not fictive; the trigger is the first
  that does.
- **The landing ground applies no prediction of the step in flight itself.** It holds what the agent
  already sees then, which is right for a fictive step, whose effect is in the present, and for one a
  drift reads as a committed step, whose effect is in the predictions; a step that reaches the world
  and that no drift reads lands in a ground that lacks its effect, and the joint search would plan as
  if it had not landed. Applying the step's own `execution:adds` there was refused while a drift can
  already state it, since the two would count it twice; the trigger is the first such world that
  reconsiders.
- **A joint plan with the walking steps later is reconsidered, not kept.** Agreement is read as the
  joint plan beginning with the untaken steps, so a plan that walks the same steps after a step of the
  arriving want's ends the intention and re-adopts them in the joint plan — the shipped arrival does,
  measured — which costs an intention and no act. Keeping it would need an order between two
  intentions, which nothing says; the trigger is a world where the re-adoption costs something.
- **A reconsideration the budget cuts short reconsiders nothing yet.** The reopening want's search is
  continued by the passes after, as any cut search is, and the walking intention walks on meanwhile,
  so the ground the search was rooted in may be behind the present by the time it ends; the joint
  plan is still held against the intention's untaken steps as they then stand. Measured on no shipped
  pose, since both arrivals fit the dispatcher's budget of 256.
- **Two minds' announced routes.** A peer's route laid as a prediction is the tool this record
  reassigns to two agents; what a peer says, in which document kind, and how the market resolves two
  predictions that collide is #568's, and nothing of it is built.

# What it amends

- The AGENTS.md line *a desire is weighed in grounds alone, in the planner's pass, and the walk
  comes after it*, and the line this record's first version wrote in its place; the line now
  carries coupling.
- [a-parcel-astray-is-a-want-of-its-own](/decisions/a-parcel-astray-is-a-want-of-its-own.md): a
  parcel astray is a want of its own unless a constraint can couple it to another.
- The two-vans seam of [a-scope-is-a-predicate-on-a-key](/decisions/a-scope-is-a-predicate-on-a-key.md),
  which named the derived want and then the sequenced plans as what would separate the vans.
- The maintenance seam of [a-desire-is-universal-and-a-want-is-existential](/decisions/a-desire-is-universal-and-a-want-is-existential.md):
  a maintenance constraint is judged at every state of a candidate plan, as a bound.
- The IRMA seam of [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md):
  laying a plan as a prediction into the grounds is for a peer's announced plan, not for one mind's
  own second want.
- #565's closing word that the coordination half was untouched, and #567's mechanism, rewritten to
  this record.
- Its own built second version (#902): the constraint as a reading of a desire and the bound as
  never-newly-enter are refused above; `planning:refused` is retired and `planning:Constraint`,
  `planning:ConstraintGraph` and `planning:impossible` declared; the dispatcher's aversion is its
  constraint, in `world/dispatcher/constraints.ttl`.
- #903's resource, `execution:occupies` and the executor's hold, refused above and not merged.
