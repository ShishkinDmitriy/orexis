---
type: Decision
title: A rule that changes the state is a transition, triggered once by what arrives; a rule that concludes is an inference, and never deletes
description: >-
  The sovereign, 2026-10-10 - it is not the first time a rule has needed to remove triples, since
  actions, predictions and belief revision all change triples rather than only add them. Decided -
  two kinds of rule, told apart by whether the result depends on what it replaces. An inference
  constructs, runs to a fixpoint, only adds, and is re-derivable from its source, as SHACL's draft
  says. A transition deletes and inserts, is a typed rule triggered once by each arrival of
  testimony, its WHERE saying what it is about, reads the arrival and the state before, and changes
  the agent's own state, in orders as an effect's rules already run, into a state graph the runner
  prepares. An action's effect is a transition the agent causes in a possible world; a percept's
  transition is one the world causes in the belief state; one machine runs both, belief's.
  Testimony is never a transition's target. The hysteresis becomes the domain's transition, written
  per property, and sensing's mapping words, `sensing:judged` and `believe` go. Amended the same
  day - a transition declares no trigger and no target. Refused - change done by a Python writer
  per need, a functional property replaced by the deliberator, rules that delete run to a fixpoint,
  and one rule judging every range.
status: accepted
timestamp: 2026-10-10T12:00:00Z
---

> **Amended 2026-10-10 (#947): a transition declares no trigger and no target.** As first built, a
> transition declared the kind of graph whose arrival set it off, and inserted into a graph of a
> kind of the belief package's own. Both went. A transition is a typed rule, `belief:Transition`,
> beneath `sh:SPARQLRule`, and that type is how the runner finds it and how revision and planning's
> bridge reader pass over it. **Each arrival of testimony — a graph received or heard — triggers
> every transition once**, as a database trigger runs once on each row inserted; the agent's own
> graphs, derived or recorded, trigger none, so a transition's output can never trigger it again.
> Its WHERE says what it is about: it is handed the arrival and no other testimony, so climate's
> soil transition, asking for an observation of soil moisture, matches only a soil reading that has
> just arrived and changes nothing on an air reading. **The runner prepares the target**, as every
> runner does — inference the source's revision graph, an effect the possible world it forked, and
> `trigger` a state graph of the arrival's own, the kernel's `orexis:StateGraph`, derived and
> holding over the arrival's period; a rule never knows the kind of graph it writes. Measured on
> the greenhouse over 24 readings, its only testimony is its two sensors' observations, two rule
> executions and about 3 ms each — what an observation already cost when both of climate's
> transitions declared the observation's kind — and its predictions and committed steps spend none.
> The body below is amended to all of it.

# The question

Slice 1 of #944 (#947) needed a subject's state to be replaced by the next reading's, with the state
before as a premise of the new one. A rule could not say it: revision only adds, and a conclusion
equal to what is held is no inference. So the build concluded the state on the observation
(`sensing:judged`), had a Python writer (`believe`) copy it onto the subject and forget the belief
before, and asked the domain to declare five of sensing's words so that sensing could name a state
it does not understand. The sovereign refused the words — which state a reading means is the
domain's, not sensing's — and then named the pattern: actions, predictions and belief revision all
change triples, and each has found its own way around rules that cannot.

# What the tree held, read on 2026-10-10

- **Revision only adds.** `agent/belief/revise.py` runs SHACL 1.2's inference rules as the draft
  says: `sh:construct`, layer by layer to a fixpoint, what is inferred being what the evaluation
  graph does not already hold, written into the source's revision graph, and replaced only by the
  source being rewritten. [Revision](/domain/belief/revision.md) says it: "a rule states what it adds
  and nothing about what it removes".
- **An action's effect already deletes.** `agent/planning/take.py` runs an effect's rules: a
  `sh:SPARQLRule` whose `sh:construct` is what it adds or whose `planning:update` is a `DELETE …
  WHERE`, grouped by `sh:order`, every rule of one order reading the same world, its deletions
  applied before its additions and a later order reading what the earlier made, each run once,
  scoped to the world it changes and naming no graph. pySHACL would run the same rules to a
  fixpoint, "the opposite shape" ([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)).
- **Everything else that changes a triple is Python.** Prediction forgets a key's predictions and
  writes new ones (`agent/prediction/predict.py`); the executor closes a committed step by
  forgetting it (`agent/execution/executor.py`); and slice 1's `believe` replaced a subject belief.
- **The two kinds were already told apart in AGENTS.md, by package rather than by what they do**:
  "the effect deletes because a possible world is where taking something away is the point; the
  never-delete rule is belief revision's".

# The decision

**There are two kinds of rule, and what tells them apart is whether the result depends on what it
replaces.**

- **An inference concludes.** A `sh:construct`, run by revision over a source to a fixpoint, adding
  only, into the source's revision graph; a function of its premises, re-derivable, gone with its
  source. A side, a quantity from a raw count, a calibration, the closure. Unchanged.
- **A transition changes the state.** A rule that deletes and inserts — the shape an effect's rules
  already have, a delete's `DELETE … WHERE` beside a construct's additions, grouped by `sh:order` —
  typed `belief:Transition` and triggered **once** by each arrival of testimony, reading the arrival
  and the state before it, and changing the agent's own state. Not to a fixpoint. Its result is not re-derivable
  from anything still held, since one of its premises is the state it replaced: it IS the state.

**An action's effect and a percept's transition are one thing seen from two sides.** An effect is a
transition the agent causes, applied in a possible world by planning; a percept's transition is one
the world causes, applied to the belief state when an observation arrives. One machine runs both,
and it is belief's — this is belief revision proper, the row of the stack where what arrives
becomes what is believed ([the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)).
Planning, above belief, applies an effect through it in the world it forks. The delete's word moves
with the machine.

**A transition declares no trigger, and the runner prepares where it writes.** Every arrival of
testimony triggers every transition once, and the agent's own graphs trigger none; the WHERE says
what a transition is about. Where it reads and writes is the runner's, as a rule's world is
([a-rule-does-not-say-which-world-it-reads](/decisions/a-rule-does-not-say-which-world-it-reads.md)):
it reads the arrival with its revisions, the public graphs and the agent's own state, and no other
testimony, so a WHERE asking for an observation of a property can match only the arrival; what it
inserts goes into a state graph the runner prepares of the arrival's own, the kernel's kind, holding
over the arrival's period, and what it deletes is taken out of whichever of the agent's own state
graphs holds it, a graph left empty forgotten. So a state replaced is replaced wherever it stood, a state written lasts as long as the
reading it was made of, and a silence ends it as it ends the observation.

**In the order an effect's rules run, and inference first.** An arrival is concluded on before it is
transitioned on: its revision settles, so a transition reads the quantity the pipeline concluded and
not the raw count. Then the transitions it triggers run in `sh:order` groups: every rule of one order
reads the same state, its deletions are applied before its additions, a later order reads what the
earlier made, and nothing runs twice for one arrival. Revision's budget counts a transition's
execution, and an order is applied whole or not at all, so a budget never leaves a state half
changed.

**Testimony is never a target.** A transition deletes only from the agent's own derived state —
never an observation, a forecast, a peer's document, the world or an ontology. What arrives is
accepted as it stands, and a transition changes what the agent made of it.

**The hysteresis is the domain's transition.** A soil-moisture observation triggers one of climate's:
the reading against the subject's operating range, its condition's `sensing:margin` and the soil's
state before — dry stays dry until the reading reaches the floor and the margin — deleting the state
before and inserting the new one, `:bed climate:soil climate:Dry`; and one on an air temperature,
alike. Written per property, by the domain that owns the property: what a state is, and when it
holds, is the domain's meaning.

# Why

**A transition is what belief revision is.** Revising a belief base takes things away as well as
adding them; what only adds is inference, and the tree had been calling inference revision and
finding ways around it wherever a belief had to change. The hold showed it plainly: its premise is
the state it replaces, which no rule that only adds can read and then remove.

**One machine instead of a workaround per need.** The effect's runner already does what a percept's
transition needs — deletes beside additions, ordered, once, scoped by the runner. Written again for
belief revision, there would be two engines for one shape; written in Python per package, as
`believe` was, every package that changes a state grows its own.

**Once per arrival, in a stated order, is bounded where deleting to a fixpoint is not.** Rules that
delete and run until nothing changes can undo each other for ever, and what they leave depends on
the order they fire in. A transition is triggered once by each arrival of testimony, never by its
own output, and runs in an order the rules state, so what it leaves is a function of the state before and what arrived.

**The domain's state need not be a side of a range.** One rule judging every range made every state
"below, inside or above the operating range" and had sensing name it. A domain's transition can say
frost below nought whatever the range, waterlogged after rain, or a state read off two properties.

# What was refused

- **Change done by a Python writer per need** — `believe` beside `predict`'s rewriting and the
  executor's closing. Each is a second engine for a shape the effect's runner already runs, and
  `believe` needed a word on the observation (`sensing:judged`) only so that the writer had
  something to copy.
- **A functional property replaced by the deliberator** — `owl:FunctionalProperty` declared of the
  state's word, and a conclusion of it replacing the subject's value before. Proposed on 2026-10-10
  and passed over: it replaces one value of one property and nothing else, so a transition that
  changes two triples together, or deletes without inserting, falls outside it; and it still needed
  what stands beside a source to stop counting as already inferred.
- **Rules that delete, run to a fixpoint** — production rules with retraction. Unbounded, and
  dependent on the order of firing, as above.
- **One rule judging every range, the domain naming the states** — sensing's `stateAs`, `belowAs`,
  `insideAs` and `aboveAs` (#947's first build). Domain meaning spoken in sensing's namespace, and
  every state forced to be a side of the operating range. Its argument — the hold written once
  cannot drift between properties — is real and is what this costs: climate writes the hold twice,
  for the soil and the air.

# Consistent with, and named so it is not mistaken for a reversal

- **[an-observation-is-a-percept-and-the-mind-reads-only-beliefs](/decisions/an-observation-is-a-percept-and-the-mind-reads-only-beliefs.md)**
  stands: an observation is a percept, the mind reads beliefs in the domain's words, and a state is
  held by the belief it replaces. How that belief is made is this record's — the domain's
  transition, where it said one rule of sensing's.
- **A rule does not say which world it reads** — a transition says neither what triggers it nor where
  it writes; the runner says where it reads and writes.
- **The search runs no rules** — a transition is triggered by testimony arriving in the present,
  never in a search; an effect in a search is applied by planning, as before.

# Seams left open

- **Whether a prediction arriving triggers transitions.** A prediction is the agent's own, recorded,
  and no testimony, so today it triggers nothing. Slice 3 decides whether a predicted stretch
  triggers the transitions too, beside the state before it — the present's for the first stretch,
  the stretch before for the rest — with what it writes and deletes confined to its prediction's own
  graphs, the foreseen, never the present's; what would reopen anything more is a prediction that
  needs to delete from the present.
- **A forecast is testimony, and triggers every transition.** An observation in it of a property a
  transition is about would be judged as a reading is, over the forecast's stretch. The one shipped
  forecast, the terrace's precipitation, is about nothing a transition judges; what would reopen it
  is a domain forecasting a property it judges, whose WHERE must then say which of the two it means.
- **Prediction's rates and the executor's intentions stay Python.** Integrating rates is arithmetic
  over a trajectory, and the intentions are the executor's to write alone; neither is a triple
  changed because something arrived. What would reopen it is either one coming to be stated in rules.
- **A transition triggered by something other than an arrival of testimony** — a timer, a silence
  as such. None is needed: a state ends with its arrival's period. What would reopen it is a state
  that must change when nothing arrives.
