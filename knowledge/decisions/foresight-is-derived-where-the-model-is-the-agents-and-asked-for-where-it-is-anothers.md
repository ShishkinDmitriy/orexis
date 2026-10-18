---
type: Decision
title: Foresight is derived where the model is the agent's and asked for where it is another's, and an actor is whoever is asked
description: >-
  The sovereign, 2026-10-18, asking whether the terrace's rain forecast and a peer van's route are
  one thing, and whether the agent should sense the future itself or ask an actor for its plan.
  Decided - what will hold later is derived by the agent where it holds the model (drying, from its
  own reading and the domain's flow) and asked for where another holds it (rain, a peer's route,
  a person's intention); an ACTOR is whoever the agent asks what will hold, and whether that actor
  controls the thing is a separate relation, stated per domain, that decides only whether there is
  anything to bargain about; a FORECAST is the one word for anyone's word about what will hold
  later - the weather service's, a peer's, the executor's committed step, and the predictor's own,
  which is a forecast whose author is this agent - one kind, the author provenance, each laid into
  the ground of its period as it stands; nobody is ever asked for a plan, only for a forecast; and
  the prediction package is the agent's foresight for the models it holds and nothing more.
  Refused - sensing every future fact, an actor that controls, a kernel Actor class, delegating
  what nobody can be asked, two kinds for one shape, and moving the weather to speech now.
status: accepted
timestamp: 2026-10-18T10:00:00Z
---

# Context

The terrace holds a rain forecast from a weather service; the dispatcher's two-minds world will hold
a peer van's route, asked for over speech ([two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict](/decisions/two-minds-meet-by-saying-their-routes-and-drawing-lots-on-a-conflict.md)).
Reading how a [ground](/domain/planning/imaginarium.md) is laid, the sovereign asked whether these are
one thing. Both are somebody else's word about a stretch ahead; one is about the air around the bed
and the other about the predicate the plan reads. Two framings were put:

- **Sense the future.** The weather is a sensor whose readings happen to be about later; a peer's
  route would be the same, read off its motion. The agent foresees everything itself.
- **Ask an actor.** The agent believes some actor controls the rain, as it believes a driver controls
  the other van, and asks each for its plan. The weather service is not an agent, but it behaves like
  one over REST, and the agent need not know the difference.

The sovereign's own words on the second: like belief in God; the agent believes the actor controls
the thing, cannot ask it to change, and can only ask what it will do.

# What the tree holds today, verified

- A forecast is a `orexis:ForecastGraph` written by sensing from a software `sosa:Sensor` reading a
  series, one graph per hour ([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).
  It reaches a ground only through the `climate:Raining` flow, which reads it as a rate for the bed's
  soil. Its own start and end are happenings to the predictor and boundaries to nothing.
- A prediction is an `orexis:ForecastGraph` the predictor derives from a sensor's latest percept and
  the flows moving its property ([a-prediction-accumulates-rates-between-happenings](/decisions/a-prediction-accumulates-rates-between-happenings.md)).
  It is the one kind `lay_ground` lays a ground ahead for. `predict` requires a numeric result and a
  `sosa:madeBySensor`; a cell is neither, so a peer's route has no path, and the dispatcher's tests
  write a `ForecastGraph` about the peer's van by hand.
- The air humidity on the terrace is read by no flow, transition, desire or action, and reaches no
  prediction and no ground. It is a belief and nothing more.
- The terrace agent plays an observer and a predictor and wants nothing, so it lays no grounds at all.

> **Verified again after #987, #996 and #992.** Sensing's forecast, the predictor's prediction and the
> executor's committed step are one kind, `orexis:ForecastGraph`, beneath `orexis:BeliefGraph`; a forecast
> of any author is laid where its period begins if a text of the pass or a transition reads what it says,
> so an hour is a boundary where something reads it; a flow reads a forecast of any author at its instant,
> the agent's own predictions among them; and a recorded forecast is never the present's. The list above
> stands as the tree was on the morning this record was written.

# The decision

**Who holds the model decides.** For every predicate a plan reads, what will hold later comes from
whoever has the model of it:

- the bed's drying is the agent's own model, a flow over its own latest reading, and nobody can be
  asked for it: **derived**;
- rain is the weather service's model, which the agent will never hold: **asked for**;
- the other van's cells are the peer's plan, which only the peer knows: **asked for**;
- the agent's own dose is its committed step: **known**.

So the question "sense it ourselves or delegate" has no single answer and needs none. The agent
cannot delegate drying and cannot derive rain. Both paths stay.

**An actor is whoever the agent asks what will hold.** The weather service, a peer and a person are
actors; a thermometer is not, since it cannot be asked about tomorrow. That is the whole of the word,
and it carries the half of the second framing that is useful: the forecast is somebody's prediction,
not a reading, and the agent relies on their model as it relies on the peer's plan.

**Control is a separate relation.** Whether an actor controls the thing it is asked about is stated
per domain, where a plan branches on it — `courier:drivenBy` is one such statement — and it decides one
thing only: whether there is anything to bargain about. The [host](/domain/market/host.md) controls the
water, so there is a market. The peer controls its van, so there is a draw. The weather service controls
nothing, so its answer is final and there is nobody to bargain with. The agent that attributed control to
the weather would reach for the draw or the market and find no counterparty; "belief in God" is harmless
exactly as long as the agent asks only for knowledge.

**A forecast is the one word, and a prediction is a forecast whose author is this agent.** The
sovereign asked for fewer concepts, and the shape admits it: a weather hour, a peer's answer about its
van, the executor's committed step and the predictor's stretch are each a belief holding over a stretch
ahead, saying what will hold there, replaced by its author when its author knows better. What PDDL
calls a timed initial literal. They differ in who said it — the service through sensing, the peer
through speech, the executor, the predictor from a percept and the flows — and whose a graph is, is
provenance and never its kind ([the-state-is-what-a-scope-can-change-and-everything-known-is-belief](/decisions/the-state-is-what-a-scope-can-change-and-everything-known-is-belief.md)
folded the public kind by the same rule). So the predictor's `orexis:PredictionGraph` and sensing's `sensing:ForecastGraph` became
one kernel kind, `orexis:ForecastGraph`, with `execution:CommittedStepGraph` beneath it, once #987 had taken
away the one reader that told them apart (#992). Nothing a plan selects depends on which author said a forecast; what depends on
the author is who replaces it, and the author's own provenance finds it.

**Every forecast is laid into the ground of its period as it stands.** A ground is laid at every
instant a forecast begins, and the forecast holds in the grounds from there — its end lays none, since
a ground keeps a value until something assigns its key, as a prediction's last stretch stands past the
horizon (#987 refined the "or stops holding" this first said). The planner needs one thing of it, that it holds later, and that is a fact about the
timeline and not about a class of beings. Where the forecast is about the predicate the plan reads, as a
peer's cells are, nothing is computed; where it is about something else, as rain is, the domain's flow
says what it does to the planned quantity, and the predictor forecasts from it as it does now.

**Nobody is asked for a plan.** A plan is private to the mind that found it, the asker's and the
answerer's alike. What crosses between agents is a forecast: the peer is asked where its van will be
over these periods, as the weather service is asked how much will fall, and answers from what it has
committed to and what it intends, restricted to what was asked. #923's "route" is that answer and
nothing more; the word goes.

**The prediction package is the agent's foresight for the models it holds, and nothing more.** It
integrates the flows for what nobody can be asked about and writes the forecasts it alone can author.
Everything else the agent foresees is asked for.

**The weather stays on sensing's channel.** It is trusted like an instrument — it has no stake in the
bed, it is wrong by noise, and sensing has the words for a stale or silent forecast — and it is polled
on a cadence, which suits a model that changes slowly. Moving it to speech would make the words uniform
with a peer's answer and change no plan.

# Why

**The border with a sensor is control and interest, and a sensor has neither.** A thermometer that
read 30 did not make it 30; a peer that says `c2_1` at T will make it so, or not, by choice. A sensor is
wrong by noise, and sensing already has the words for that: a margin, stuck, silent. An actor may be
wrong by interest, which is why the draw commits before it reveals and a peer answers only under a
constraint it shares. The weather service reports rain it does not make and has no stake in the bed, so
on both counts it sits with the instruments. Treating every sensor as an actor would make the
thermometer's noise a possible lie and the peer's lie a kind of noise; the project keeps them apart,
sensing for bytes and speech for documents ([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)),
and this is the reason underneath that split.

**A plan branches on none of the alternatives, so the model stays first-order.** Beliefs about other
agents stay what they said, never what they are ([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).
No plan branches on "the weather is an actor"; a plan does branch on "driver B is aboard van B", which
is why that one is a term already. The rule asks of each predicate who holds the model, and that is a
question about the world, answered by the domain, not a class in the kernel.

**The timeline is where the two framings agree.** Both need "it holds later and I did not derive
it", and laying every such belief per period gives it to both without deciding between them. It is also
what #923 needs: a peer's answer then needs no carrying into a prediction, since it holds in the
grounds of its period by itself.

**The general form of #923's rule falls out.** Ask the controller of every predicate your plan reads
that you do not write. The courier's constraint reads `courier:at` and Drive writes only our van's, so
the other van's controller is asked. The grower's flow reads precipitation, nothing of ours writes it,
so the forecast is polled. Same rule, two channels.

# PDDL, term for term

| PDDL | here |
|---|---|
| a timed initial literal (2.2): a fact known to hold over a window, from anyone, never re-derived | a forecast: a belief holding over a stretch ahead, whoever's word, laid per period |
| a process (PDDL+): continuous change while its condition holds, chosen by nobody | a flow, integrated by the predictor for the models the agent holds |
| an event (PDDL+): discrete change when its condition becomes true | a transition, run where a predicted or forecast observation arrives in a ground |
| the planner's happenings: TIL times and process start and stop points | a ground per instant a belief the present has not reached begins (#987) |

PDDL has no word for who said a TIL, and that is where this record goes further: a TIL from the
weather service and one from a self-interested peer are the same to it. Here whose word it is stays
on the row, and the draw decides which answers count.

# What was refused

- **Sensing every future fact** (the first framing taken whole). A peer's intention cannot be sensed,
  only inferred from its motion, and inferring where a seen van may go was refused in #922's first
  version as "anywhere it can reach". Where the model is another's, asking is the only path.
- **An actor that controls** (the second framing taken whole). It attributes to the weather a power
  it lacks and makes the agent reach for a bargain nobody can hold. Control is kept as a relation a
  domain states where a plan branches on it.
- **A kernel `Actor` class.** Nothing a plan selects depends on it, and it would make a belief about
  another agent second-order: what it is, not what it said.
- **Delegating what nobody can be asked.** Drying has no actor; the agent's own flow over its own
  reading is the only model there is. The prediction package stays for exactly this.
- **Two kinds for one shape.** The predictor's prediction graph and sensing's forecast graph held the same thing,
  an observation of a stretch ahead, and were told apart only by `lay_ground`, which laid a ground for
  the one and not the other. With a ground at every forecast's boundary nothing reads the difference,
  and a term nobody reads is annotation. The author stays on the row as provenance, which is where
  the public fold put it too.
- **Moving the weather to speech now.** It would cost an extraction rule and the cadence words and
  change no plan. The trigger for moving it: the first external source the agent must ask on demand
  rather than poll, or one that answers in a shape sensing's pointers cannot read.

# Seams left open

- **A person as an actor.** Someone who waters the bed by hand, or says they will tomorrow, controls
  the soil and can be asked, over speech; today their act arrives as a surprise. The trigger: the first
  world in which a person acts on a subject an agent acts for. #862 is adjacent.
- **A simulated weather actor.** On the bench, a weather process that publishes its plan the way a
  simulated peer will would make the terrace's tests and the two-minds tests one harness. Test
  infrastructure, not the agent's model.
- **The word's page.** This record coins `actor` in prose and declares no term; the page is written in
  the change that first reads the word, with #923 or the person's case above, whichever comes first.

# How it is built

The record emits the issues that make it true: a ground at every happening, with the check that a
belief holding later is never laid into the present (#987); `orexis:retracts` dropped from a
prediction's row, the key saying what it supersedes (#988); `CARRIED_S` removed, the state a ground
inherits standing where the carried prediction stood (#989); a person as an actor (#990); the two
kinds folded into one kernel forecast kind with the committed step beneath it, after #987 (#992); and
#923's rule stated in its general form. The prediction page opens with what the package is for.
