# Domain

The shared dictionary: what each word MEANS, one page per concept, filed in the folder of the
package that owns the word — the same package whose namespace declares its term. The sections run
in the order a pass does: a world is booted, bytes become observations, the rules revise them, the
future is predicted, wants are derived and searched, and the plans are carried out.

# Kernel — what every package meets at

* [agent](/domain/kernel/agent.md) - One process, one store, one world, told its local id; acts for a subject and holds its desires. Nothing is granted.
* [world](/domain/kernel/world.md) - A directory of documents, each saying which graph it is; imports its domains, and its tests live beside it.
* [domain](/domain/kernel/domain.md) - A vocabulary, its actions, shapes and rules as documents in `domains/<name>/`, imported by the worlds that speak it.
* [action](/domain/kernel/action.md) - One way of acting as one node: what it takes, its precondition, its effect, its implementation, its cost.
* [runtime](/domain/kernel/runtime.md) - Boots a world into a store, then runs pass by pass, and stops when nothing is held or wanted.
* [part](/domain/kernel/part.md) - What a package contributes to a running agent: created, linked to the others, started, stopped last-first.
* [event](/domain/kernel/event.md) - What a signal carries: a class its package declares, said whole; it may mark what is reported and answer a history point.
* [level](/domain/kernel/level.md) - A reported field that is the state now, read by its store's owner and written as it last stood in a window.
* [signal](/domain/kernel/signal.md) - A package's own word for what just happened, on its object, carrying one event; connected when parts link, never stored.
* [modality](/domain/kernel/modality.md) - What a graph asserts — is, will be, would be, wanted, owed, doing — carried as its kind on the catalogue.
* [inference](/domain/kernel/inference.md) - The boot materialises the subclass closure, so a reader asks what a thing is and walks no path.
* [package](/domain/kernel/package.md) - A directory of `agent/` owning a concern and its words, importing only what lies beneath it.
* [sovereign](/domain/kernel/sovereign.md) - Whoever writes a world's documents: picks the ranges and values, never an act. Outside the society.
* [series](/domain/kernel/series.md) - What a person watches and the agent never reads: history and metrics, both what the packages' events say, written by a part hearing every signal.

# Sensing — bytes become observations

* [scaling](/domain/sensing/scaling.md) - A rescale, a probe's count a moisture: two points the world states beside the sensor, applied by sensing's rule.
* [sensing](/domain/sensing/sensing.md) - A transport's bytes become one observation per key, holding until the next is due; says when a sensor falls silent.
* [observation](/domain/sensing/observation.md) - One act of observing in SOSA's words, one per key, replaced whole by the next; the premise everything else derives from.
* [reading](/domain/sensing/reading.md) - The number an observation carries: what a side is concluded of, what a drift predicts, what a dose is sized from.
* [calibration](/domain/sensing/calibration.md) - A correction within one unit, two points the world states beside the sensor, applied by sensing's rule after any scaling.
* [forecast](/domain/sensing/forecast.md) - Another party's word about a stretch ahead: what a sensor reading a series writes, one graph per stretch. Testimony, never a prediction.
* [region](/domain/sensing/region.md) - SSN-System's operating and survival ranges, stated by the world; the rules say which side a reading is on.
* [stuck](/domain/sensing/stuck.md) - A sensor reporting one number for a limit of its cadences is said stuck until a differing number ends it; the doubt beside age.

# Transport — reaching the society

* [transport](/domain/transport/transport.md) - The contract the container holds of any member, several held as one; MQTT speaks MQTT4SSN, HTTP the Thing Description, neither declaring a word.

# Belief — what follows from what was written

* [belief-base](/domain/belief/belief-base.md) - One store per agent, and a catalogue describing every graph: its kind, owner, arrival and period.
* [revision](/domain/belief/revision.md) - A belief derived from beliefs by SHACL 1.2's rules, adopted as they stand, into a graph of the source's own, on the present only.
* [deliberator](/domain/belief/deliberator.md) - The revision pass over what changed, within a budget of rule executions; a cut is continued, across a restart too.

# Prediction — the stretches ahead

* [prediction](/domain/prediction/prediction.md) - Drifts answer rates that add, accumulated between happenings; one graph per stretch between range crossings; a ground per stretch.
* [corridor](/domain/prediction/corridor.md) - A rate known as a range gives the lowest and highest trajectory; a stretch is the corridor's worst side.

# Planning — what is wanted, and how to get there

* [desire](/domain/planning/desire.md) - A desire stands and is never searched; a want is minted where it bites, searched, and withdrawn once met.
* [constraint](/domain/planning/constraint.md) - What the world says is possible, stated as a desire is; a world violating it is impossible, never repaired, and its footprint couples wants.
* [shape](/domain/planning/shape.md) - A met-test is a SHACL shape a domain declares, compiled to the select whose rows are its violations.
* [planner](/domain/planning/planner.md) - One pass: grounds laid, wants derived, each searched best-first within a budget, the plans published down.
* [imaginarium](/domain/planning/imaginarium.md) - The in-memory store a search forks worlds in, one per scope, kept from pass to pass.
* [cone](/domain/planning/cone.md) - The worlds and weighings a search leaves; the next pass finds the present among them by hash, or drops them.
* [scope](/domain/planning/scope.md) - Predicates joined wherever one action or derivation touches both; wants in different scopes cannot contradict.
* [footprint](/domain/planning/footprint.md) - What one text reads and what it writes, as predicates, taken from the text; unreadable is anything.
* [precondition](/domain/planning/precondition.md) - The select whose rows in a world are the steps it admits; asked of the present again, never copied onto a step.
* [effect](/domain/planning/effect.md) - Rules run on the possible world a step makes, a delete among them; the one declaration the world is held to.
* [wait](/domain/planning/wait.md) - The search's own move, every agent's: does nothing, and lands where the next ground the search can tell apart begins.
* [plan](/domain/planning/plan.md) - One want's steps on the winning path, what they spent, and why the search ended — an empty plan is an answer.
* [budget](/domain/planning/budget.md) - A ceiling each call states in the unit it spends: candidates for a search, rule executions for revision.
* [bridge](/domain/planning/bridge.md) - A rule concluding one domain's fact from another's, authored by the world combining them; run forwards over beliefs, backwards to refine a step.
* [refinement](/domain/planning/refinement.md) - A step whose predicted fact a bridge concludes is kept below, as a want whose met-test is the landing world regressed.

# Execution — carrying a plan out

* [executor](/domain/execution/executor.md) - Commits plans as intentions, takes each step when due, moves on only when the world answers.
* [intention](/domain/execution/intention.md) - One plan committed to for one want, standing at a step until done, failed, superseded or abandoned.
* [commitment](/domain/execution/commitment.md) - Hard on the step in flight, never cancelled; soft on the plan, kept until a want a constraint couples to it arrives.
* [step](/domain/execution/step.md) - An action picked with its values: the two graphs it predicts in, when it may be taken and lands.
* [committed-step](/domain/execution/committed-step.md) - A step an intention adopted, believed over its landing window, so a drift reads it and a later search sees the plan.
* [act](/domain/execution/act.md) - The record that a step was taken, and when; the world, not the act, says whether it landed.
* [implementation](/domain/execution/implementation.md) - How an action is carried out when a step is taken: operations grouped by order, sized from the present, never read by a search.
* [operation](/domain/execution/operation.md) - One thing taking a step does — a command, a saying, or the fictive write. Not an act, which is the record.

# Speech — what peers say

* [speech](/domain/speech/speech.md) - A peer's word is a document: heard where it is state and replaces only a peer's word, and what the agent said, believed as said.

# Market — a domain of documents

* [market](/domain/market/market.md) - A venue: one place a scarce good is traded, hosted by its holder, bid in by those who want it.
* [auction](/domain/market/auction.md) - Six actions, each saying a document; nobody runs it, each side plans its part for its own desires.
* [call](/domain/market/call.md) - A bidder in trouble asks for a round; to the host it is a want arriving.
* [round](/domain/market/round.md) - One allocation of the lot, open until it closes, then cleared pay-as-bid.
* [claim](/domain/market/claim.md) - What a winner holds and the host owes: issued, presented when needed, served and said discharged.
* [host](/domain/market/host.md) - Whoever holds the good: two desires, no call unanswered and no presented claim unserved.
* [supplier](/domain/market/supplier.md) - The allotment's host, acting for the water and holding the valves; the only agent able to pour.

# Actuation — touching the world

* [actuation](/domain/actuation/actuation.md) - Devices an agent holds change its subject; an action predicts the side, its command sizes the act when taken.

# Onboarding — from a world to a society

* [onboarding](/domain/onboarding/onboarding.md) - Buckets, credentials, the ACL, compose and dashboards, each read off the world; decides nothing, so re-running is safe.
* [deployment](/domain/onboarding/deployment.md) - What must run and where it answers, a graph onboarding alone reads; an agent is told it as environment, and never a credential.
