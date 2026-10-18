---
type: Decision
title: A flow is integrated where the ground is laid, and the predictor writes no forecast
status: accepted
timestamp: 2026-10-18T12:00:00Z
description: >-
  The sovereign asked on 2026-10-18 whether the flows should be summed as the grounds are laid,
  since a prediction is made of beliefs and forecasts and a ground is where both stand at an
  instant. Decided - yes. The prediction package stays the owner of the dynamics and integrates
  the flows, but it integrates FROM EACH GROUND, handed to the planner at link, every key of the
  agent advancing together between one ground and the next; a crossing of a range bound lays a
  ground where the transitions judge the predicted number, and the predictor's own foresight
  lives in the imaginarium and nowhere else. The kernel forecast kind keeps two authors, a
  forecast received and a committed step; the predictor is none. Refused - flows reading the
  grounds while the predictor still wrote forecasts, planning integrating the flows itself, a
  cycle iterated to a fixpoint, and the stretches kept as beliefs for eyes. Left open - a flow
  integrated inside a possible world.
---

> **Decided 2026-10-18, and built by [#1000](https://github.com/ShishkinDmitriy/orexis/issues/1000).**
> Until that issue closes, the code is as
> [a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md)
> describes it, which this record supersedes in part.

# The question

The sovereign asked two things in one breath, after #992 had made the predictor's own stretches one
forecast kind with everything else foreseen: *when do we sum the flows?* and *should it be at the
stage when we calculate the ground, since we predict when beliefs will change based on beliefs and
forecasts?*

The first has a plain answer. The flows were summed in one place, the prediction package, at the
moment a percept or a belief arrived: `predict` walked from the observation in hand to the horizon,
asked every flow for its rate at each segment, added the answers, placed each crossing of a range
bound exactly and wrote one forecast graph per stretch between crossings. The planner then laid a
ground per stretch and ran the domain's transitions on the predicted number there, so the state ahead
- dry, moist - was made in the ground and nowhere else (#944).

The second is the question this record answers, and reading the code for it made the case stronger
than the question supposed.

# What the tree held, verified 2026-10-18

- **The predictor read no ground.** What a flow read at a future instant was the union of the graphs
  holding then in the belief base - `graphs_of(BELIEF, RECORD, OBSERVATION_GRAPH, at=at)` in the
  `predict` module since retired - never a ground. But a state ahead exists only in a ground: the
  transitions run there, and a key is superseded there. So a flow conditioned on a FORESEEN state would
  have read the present's state instead. No shipped flow did: drying reads a constant of the bed, rain
  reads a forecast hour's number, the dose reads a committed step and the present reading. The gap was
  latent, and the first flow to read a foreseen state - evaporation only while the frame is warm, read
  off the air's predicted state - would have fallen into it.
- **Two readers of the future.** The predictor collected the happenings as every graph start and end
  inside the horizon (`_happenings`); `lay_ground` collected the boundaries as the starts of the pieces
  ahead (`_foreseen`). One set, two readers, and one of them not reading the state the other made.
- **An order and a refusal standing in for a sum.** #996 predicted the keys in the order their flow
  texts read each other, so that the soil's drying read the air as the agent foresaw it, and refused at
  onboarding two properties each moving by the other. In a ground every key advances together from one
  state, so soil reading air and air reading soil is two simultaneous rates - what system dynamics
  means by coupled flows. The order was a workaround for a symptom of integrating one key at a time
  from a store with no ground in it.
- **Most of #992's provenance was scaffolding for this.** `lay_ground` told the predictor's own
  stretches from a forecast received by `orexis:arrivedBy orexis:Recorded`, kept them out of the
  present, and ran the transitions on those alone. With the stretches gone the one recorded forecast
  left is the committed step, which triggers no transition, and the distinction leaves `lay_ground`.
- **The cost was the same work in another place.** A pass runs on every arrival (`runtime.every(0,
  plan)`), so integrating once a pass per scope is as often as integrating once an arrival per key.

# The decision

**A flow is integrated where the ground is laid, from each ground.** A ground is the state the agent
foresees at an instant, with the beliefs and forecasts holding then beside it; the flows are its
derivative. So the thing that asks "what moves from here" asks it IN the ground, and what it finds
decides where the next ground is laid. The planner lays the present ground, asks the integrator what
moves from it, and the next boundary is the earliest of three: the next belief ahead beginning or a
step landing, as before; the next crossing of a range bound by any key's trajectory; and the cap on
how long a rate is held before it is asked again, an hour. At a crossing a ground is laid and the
predicted observation arrives in it, as an arrival of testimony does in the present, so the
transitions judge the number there, beside the state the ground before held and with the margin the
range states (#944, [transition](/domain/belief/transition.md)); at a boundary that crosses nothing
the ground is laid for what begins there and the integration continues into it; between, the rates are
asked again each hour and nothing is laid. A ground that changes no state collapses by hash into the
one before it, as every ground has since #953.

**The prediction package keeps the dynamics and the planner keeps the state.** Planning imports
nothing of prediction and prediction nothing of planning, which the layout tests hold and this record
does not loosen. They meet as planning and execution do - at link, through the runtime, which hands
the planner the integrator as it hands the executor the planner's signals
([a-package-starts-itself](/decisions/a-package-starts-itself.md),
[planning-and-execution-meet-at-the-store](/decisions/planning-and-execution-meet-at-the-store.md)). A
planner that is no predictor is handed none and foresees nothing, as it wrote no forecast before; a
predictor that is no planner foresees for nobody. The integrator reads the keys off the belief base -
each sensor's latest percept, its number and its instant, the one read at the boundary prediction has
always made (#944) - and everything after that off the imaginarium: the ground, the graphs holding at
the instant beside it, and `$value`, the number it hands each flow, which is the one number a flow is
owed. `actuation:Dosed` read the number off the reading to size the rise; it reads `$value`, which is
what the token was for.

**Every key advances together, and nothing orders them.** Between one ground and the next, every
flow of every key is asked at the same instants, reading the same ground and the keys' current numbers,
and every key moves by its sum. A flow reading another key's number reads it as it stands at that
instant - the soil's drying reading the air's humidity as the agent foresees it, which was #996's
whole purpose - and two keys reading each other are two coupled flows, not a cycle. `order` and the
onboarding refusal of a cycle go, and so does the rule that a key is predicted after the keys it reads.

**The predictor writes no forecast.** Its foresight is the grounds: the knots of the integration, each
with the state the transitions made of it, in the imaginarium of the scope the key is placed in, for
the life of the cone. No `orexis:ForecastGraph` of the predictor's own is written into the belief
base, so none is hashed, cut, laid or forgotten, and `prov:hadPrimarySource` has no row to stand on.
The kernel kind keeps the two authors that remain: a forecast received, which sensing writes from a
series and speech may from a peer's statement, and a committed step, which the executor writes for an
adopted plan ([forecast](/domain/kernel/forecast.md), [committed step](/domain/execution/committed-step.md)).
Both are beliefs ahead and are laid where they begin, as #987 decided; the integrator reads them
there, so a future that contains the earlier plan is still what a later want is searched against
(#849), and a peer's route laid as a forecast is still the two-minds tool (#568).

**A flow reads a belief ahead by its period, and lays no ground for it.** A belief ahead is laid into
a ground where a text of the pass or a transition reads it (#987), and a ground keeps what is laid
into it past the belief's end, since a value stands until its key is assigned. A flow cannot read a
forecast hour that way: the hour's node carries its start and not its end, so laid into the ground it
would rain for ever. So the flows read what they read as the planner's own readers do - the ground, and
beside it every graph holding at the instant asked, by the period its row states - and a belief only a
flow reads, a committed step or a forecast hour, is a remainder the flows see exactly while it holds and
lays no ground, as it laid none before. What gates a belief ahead is unchanged, and so is the hash: a
world is hashed within what the pass's texts read, so a number moving between two grounds tells them
apart by nothing, and the cone is not dropped for a reading inside its band (#632,
[cone](/domain/planning/cone.md)).

**The ground holds the state and no number.** The predicted observation arrives in a ground and is
judged there; what the ground keeps is what the transitions concluded of it. The numbers stay the
integrator's, in a working graph of the imaginarium beside the grounds, read by the flows and by
nothing of the mind - which is where #944 put them, now without a graph of the belief base to carry
them in.

# Why

- **A prediction is made of beliefs and forecasts, and a ground is where both stand at an instant.**
  The sovereign's premise is the architecture's own: the ground was built so that a desire asked at a
  future instant sees the present with the predictions applied and nothing stale beside it. A flow is a
  question about a future instant too, and had been asked of the belief base, where the stale and the
  foreseen stand side by side - exactly the failure the ground exists to close, one layer down.
- **Control the derivative, not the value.** The ground is the value and the flows are its
  derivative; the package that owns the state should not compute the derivative, and the package
  that owns the derivative should not store the value. Handing the planner an integrator, and the
  integrator a ground, is the one shape in which each owns its own
  ([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).
- **One reader of the future.** The happenings and the boundaries were one set computed twice, and
  the state ahead was made by one reader and not seen by the other. There is now one walk, and
  everything the agent foresees is in it.
- **A dissolved problem beats a solved one.** The order of keys, the cycle refusal, the recorded
  forecast's special path through `lay_ground` and `world_at`, and the primary-source row were each
  built to make the arrival-driven integration consistent with the grounds. None is needed once the
  integration is the grounds'.
- **A number is not a belief.** The predictor's stretches were beliefs of the agent's own carrying a
  number the mind never read (#944); as beliefs they were hashed, cut, laid, revised, forgotten and
  told from the received by provenance, all for a reader that was the planner alone. A conclusion
  computed for one reader each pass is computed, not stored
  ([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).

# What was refused

- **Flows reading the grounds while the predictor still wrote forecasts.** It keeps two readers of the
  future, and it is circular: the ground is laid from the forecasts, and the forecast would be derived
  from a ground of one scope and then written as a belief read in every scope. The predictor would have
  to run inside the pass to see a ground at all, at which point it is the integrator this record hands
  the planner, with a belief base write in the middle for nobody.
- **Planning integrating the flows itself.** The flows' kind is the kernel's (`orexis:FlowGraph`), so
  the planner could read them; but `prediction:Flow`, `prediction:rate` and `prediction:moves` are
  prediction's words, the corridor and the ranges are prediction's code, and a planner that is no
  predictor would run the dynamics of a role it does not play. The package stays, and the planner is
  handed a function.
- **Iterating a cycle to a fixpoint.** #996 refused it for the arrival-driven integration and this
  record does not revisit that: a cycle is not iterated because it is not a cycle. Two keys reading
  each other advance together, as every pair of coupled rates does.
- **The stretches kept as beliefs for eyes.** A tool or a test could read what the agent foresaw after
  the pass. Reflection reads the series and never the beliefs
  ([reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)),
  so a figure for eyes is a point the agent writes to the series, not a graph it believes; and a
  stored conclusion outlives its premises
  ([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md)).

# Seams left open

- **A flow inside a possible world.** The search still asks no flow: a step's effect on the dynamics
  is seen only after adoption, through the committed step, by the next pass, and a world forked from a
  ground inherits the ground's foresight unmoved by the step. Integrating from every forked world is
  PDDL+ whole - processes running during search - and a question of budget, since a fork is the unit the
  budget counts. This record moves the integration from the belief base to the grounds and stops there;
  the trigger for the next move is a want whose plan depends on how its own steps change the rates, which
  no shipped world has.
- **A recovery across a margin is seen within the hour.** A knot is laid where a trajectory crosses a
  bound, and the transitions judge the number there with the range's margin, which prediction does not
  read ([a-belief-is-crisp-and-an-estimator-may-reason-with-probability](/decisions/a-belief-is-crisp-and-an-estimator-may-reason-with-probability.md)).
  A state held past its bound by the margin flips when the next arrival clears it; the number laid at a
  crossing is the one at the far end of the stretch it opens, as the stretches' was, so the common case
  flips at once, and the rest at the next re-asking.
- **The predictor writes no point to the series.** What the agent foresaw is gone with the cone, so
  `orexis-explain` cannot yet say what it was; the point is the predictor's to write when a question
  needs it ([reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)).
- **A predictor that is no planner.** It is loaded and foresees for nobody. Whether planning's shape
  should refuse the declaration, as it refuses an executor that is no planner, is a question for the
  first world that declares one.
- **The corridor is still one number per ground.** Carried over from the record this one amends.

# How it is built

#1000 carries the whole of it: the integrator handed to the planner at link and asked ground by
ground in `lay_ground`; every key advanced together; `order` and the onboarding cycle check retired;
the recorded-forecast path out of `lay_ground` and `world_at`; the dose flow reading `$value`; the flows
reading a belief ahead by its period and never off the ground; the
prediction cases restated over the knots and the grounds they lay; and the pages - prediction,
predictor, forecast, committed step, changeable, imaginarium, cone - reconciled in the same change.
