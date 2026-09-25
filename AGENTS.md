# Working on Orexis

A society of self-interested agents that bid for a scarce resource. The v1 domain is plant
watering, but the domain is a plug-in — plant/water language is the example, not the
architecture.

Read [`knowledge/index.md`](knowledge/index.md) before changing anything structural. It is the
durable "what and why"; the code follows it, not the other way round.

## Use the OKF skill for anything under `knowledge/`

`knowledge/` is an **Open Knowledge Format v0.1 bundle** (https://okf.md), not a docs folder.
Invoke the `okf-open-knowledge-format` skill when adding, editing or checking documents there.
If it is unavailable, the rules are short enough to follow by hand:

- every concept `.md` has YAML frontmatter with a non-empty `type`, plus `title` and
  `description` — and a `domain/` page whose word the T-Box carries binds it with `term:`,
  which `tests/test_knowledge.py` holds to what the ontologies (ours vendored under
  `tests/fixtures/vocabularies/` for the external ones) actually declare. **Eight types, and the one to reach for is the one that answers what KIND of
  thing the page is:**

  | | |
  |---|---|
  | `Decision` | why the code is as it is. Closed by nothing; superseded or amended |
  | `Domain Concept` | a **thing** in the model — a claim, a good, a step, a world |
  | `Process` | something that **happens**, with phases and an end — an auction, a round, onboarding |
  | `Capability` | a named ability with **interchangeable implementations**, granted by its own premise and provided by a package — rule 2's unit |
  | `Role` | a kind of **principal** with something at stake — an agent, a supplier, a dealer |
  | `Service` | a part of the implementation that **holds logic** — the deliberator, the revision seam |
  | `Repository` | a part that **passively holds data**, scoped to one agent — the belief base, the imaginarium |
  | `Runbook` | how to **operate** it |

  The split was asked for by the pages: `auction` opened "an auction is a PROCESS", `bid-matching`
  called itself "the STEP that…", `onboarding` "the PHASE between…" — three pages naming their own
  type in prose because the field could not hold it. **A type that falls to one member is a type
  to fold back**, not to defend; the split landed at 10 / 5 / 5 / 4 / 4;
- a **decision** additionally carries `status` (`accepted`, `superseded`, `superseded-in-part`)
  and `timestamp`, and a superseded one carries `superseded-by`. **No other type carries any of
  those**: a concept, a process, a capability, a role, a service and a repository have no state to be in,
  being either current or wrong. `stage` and `tags` are
  gone — `stage` said `v1` in every record, and `tags` had 147 values of which 86 were used
  once and nothing read any of them;
- **quote or fold anything with a colon in it.** A `description` reading `on one axis: the
  agent asks` is not valid YAML, and 27 files were unreadable to every OKF consumer while
  passing the vendored check, which greps rather than parses. Use `>-` and indent;
- `index.md` carries **no** frontmatter — it is navigation, and its title is its heading. Only
  `knowledge/index.md` may declare `okf_version`;
- **an index entry is the claim, not the abstract** — 26 words is the cap, the abstract lives
  in the record's own `description`, and the argument lives in the record;
- validate with `./tools/validate-okf.sh knowledge` — vendored from the skill, because a gate
  that only runs from one person's home directory cannot be run by a fresh clone or by CI. It
  checks the OKF spec and nothing about THIS project, so do not edit it: the project's own
  rules are `tests/test_knowledge.py`, which runs under `pytest` and fails on unparseable
  frontmatter, an orphan document, a dead link, an over-long index entry, or a document naming
  a path that is not on disk.

**`knowledge/domain/` is the shared dictionary, and a term is defined before it is used.** The
pages there fix what our words MEAN — step, gap, imaginarium, capability, action, lot, venue
— and a discussion, a commit message, a docstring or an issue that uses one of them uses it the
way its page does. **If a change needs a word the bundle does not have, write the page in the SAME
change, first.** A word used before it is defined is a word everyone defines differently, and the
definitions never meet. This is the discipline
`tests/test_knowledge.py::test_no_two_domain_pages_state_the_same_claim` already enforces between
pages — one claim, one owner — applied to the vocabulary itself.

**A concept is defined once and then used by its name — ubiquitous language.** A page grounds a
word in prose, and that prose is where the meaning lives; every later use — a page, a commit
message, a docstring, an issue, an answer to the sovereign — uses THE WORD, never a synonym and
never a paraphrase. A plan is steps, so a plan is not a "chain" and a step is not a "move" or a
"link"; a precondition is not "what the rule read" once its page has said that is what it is. A
synonym is how one concept becomes two: a reader meets both words, looks for the difference, and
the definitions drift apart from there. The one legitimate second name is the term's — the page
says which IRI it is bound to, and code speaks the term where prose speaks the word — and where
a page and its term disagree that is a debt to settle, not a licence to alternate. One was
settled by that rule: the precondition page was bound to a term of another name, so a step's own
facts had two names in one repo, and #580 renamed the term and every identifier that read it —
leaving no dangling spelling, which `tests/test_layout.py` holds these documents to.
A word with a SECOND meaning is not that debt: a rule's premises and a capability's premise are
their own concept and keep the word. A synonym found in a page is fixed in the page, not
tolerated by the reader.

**One concept, one article.** If a page turns out to define a second thing, that thing gets an
article and the two link — ownership is then structural, and there is nothing to keep in step.
Three clauses make that workable, and each was learned by getting it wrong:

- **Where an owner already exists, POINT — do not extract.** Extraction is for a claim that has no
  page yet. `capability.md` restated capability-aware validation, the materialised closure and
  "refusing to start is not self-report" before the gate objected; all three already had owners,
  one of them a page written in the same commit.
- **A pointer that restates is a second owner.** A stub saying what the other page says has not
  moved the claim, it has copied it. Say what THIS page does with the thing, and link.
- **A relationship can be the concept**, and the test is whether each half stands alone.
  `means` and `lever` split because each looked like it had content of its own — a means was
  the joint three subsystems met at; a lever was an instance whose absence removes a row. Both
  folded in the end: `means` into `action` when the three subsystems became one node, because a
  joint between one thing and itself is nothing (the-action-is-the-kind), and `lever` into the
  BINDING when an action came to declare what it takes, because "the instance in the `via`
  column" is not a concept once there is no `via` column (an-action-takes-parameters).
  `model-and-unit` does not split: its whole content is what a unit inherits from its model, so
  two pages would each have to restate the relationship, and the gate would refuse them.

The gate is `tests/test_knowledge.py::test_no_two_domain_pages_state_the_same_claim` — overlapping
runs of eight words between any two domain pages, capped at four. It does not care about topic,
only about restatement, which is the thing that rots.

**Durable knowledge goes in the bundle, never in a new README.** `domain/` says what a thing is
and how to use it; `decisions/` says why a choice was made and which seams it leaves open. The
existing READMEs (root, `firmware/*/`) are operational entry points and stay, but do
not add more for design knowledge.

**Reconciling the bundle is part of the change, not follow-up.** After changing behaviour, grep
`knowledge/` for claims the change made false and fix them in the same commit. A stale decision
record is worse than none, because it is still cited.

## Principles, one line each

**This is the default place for what a change taught, and a decision record is the exception.**
Most work ends with a line here plus a commit message; a record is for the rarer case where a
real alternative was weighed and refused, and the argument has to survive. A principle earns a
line when it would have changed a decision, and it stays one sentence — if it needs a paragraph
it is a record wearing a bullet.

- **An RDF URI beats a homemade id for referring to an agent**, and the exception proves it: the
  one name that stays a short string is the one that must also be a broker principal, a bucket, a
  container and a directory.
- **A term nobody reads is annotation**, however many instances state it.
- **A word used before it is defined is a word everyone defines differently** — `duty` ran to 64
  code sites and 13 pages with no page of its own, meaning `obligation` all along.
- **Desire is bouletic, obligation deontic, availability alethic, freshness epistemic** — different
  logics rather than strengths of one, which is why an unmet want is a gap and an unpaid debt is
  a breach.
- **A repository holds data and a service holds logic**, and a thing that decides nothing is a
  repository's support function rather than a service.
- **Deciding nothing is the finding** — writing no graph is only the hint, since three services
  write none and stay services.
- **Verify a claim in the bundle against the code before repeating it**; nothing gates prose
  against the thing it describes.
- **A rename is done when the suite says so**, not when the thing you grepped for is gone.
- **A word-boundary sweep bites a hyphenated slug and a variable named after the word** —
  `\bstake\b` matches inside `the-stake-is-sensings-want`, so 45 files came to cite a record
  that does not exist, and a local `stake` is spelled like the word it was named after, so nine
  files grew `(region want := ...)` and stopped parsing; hold out the words that merely contain
  the letters (`mistake`, `stakeholder`) before starting, and let the parser and the suite find
  the rest.
- **Search every tree that loads the vocabulary before calling a term dead** — `assembly/` reads
  ontologies that `agent/` never mentions.
- **A record earns its place by refusing something**; "we could have not done it" is not an
  alternative.
- **A record is engaged by its premises, not cited by its conclusion** — the mind's record
  refuses a granted mind, and was nearly spent against unconditional layer trees it never
  argued about.
- **A prune is only as good as when its bound arrives** — an admissible estimate refused
  nothing under breadth-first, because the first achiever came last, and the same estimate
  refused sixty percent of the courier's forks the day the search followed it.
- **The layer that waits does the waiting** — a module that keeps its own timer and checks
  its own trigger has rebuilt the middle layer inside a capability; adopt with a condition and
  a deadline, and say only what you wait for.
- **A kind said by absence is a kind two readers disagree about** — an action with no effect
  was "an act the reflex may take" to one reader and "passed over, plan partial" to another,
  until the gate held every action to both texts or neither, and a class for the second kind
  was weighed and dropped as a term nobody would read.
- **An action that touches nothing the want reads is never simulated, and the closure is what
  makes that safe** — filtering to the goal's predicates deletes every chain; closing backward
  through preconditions keeps the bid that makes the dose possible.
- **A want is authored positive and the kernel writes the negation** — rows are
  existential and a want is universal, so somebody turns the shape inside out, and a compiler
  held to the judge by parity does it once where every author would do it differently.
- **A plan that worked is kept, and the world verifies it, not a search** — a remembered plan is
  adopted where the facts its steps read still hold, since every step is checked when it is
  taken and a failed step drops the tail; re-simulating it first would be a search per reuse,
  and hashing the whole world keyed it to facts it never read.
- **A level is a vocabulary, and a taker-less action is a promise the level beneath keeps** —
  a search never leaves the vocabulary its want is written in; the bridge translates a step's
  promised fact downward when the step is reached, and the verdict back, never the world.
- **A method is walked, never searched** — the steps an abstract action comes to are the
  package's protocol, not a choice, so the keeper expands them at adoption and each step says
  what it waits for; simulating them would spend the budget on worlds the measure cannot tell apart.
- **A step is an action PICKED for execution, and what it adds is at least the variables** —
  planning finds a plan and every action in a plan is a step, so a world merely ADMITS one per
  action per legal filling and the search picks; an `Affordance` carried four of a step's fields
  and a `from_row` copied them across, which is two classes for one shape and a second word doing
  no work the absent fields were not. The service between the two collections fetched nothing and
  decided nothing once the word was gone, so the loop is `Steps.find_all` and every identity it
  held is a criterion of the ask (a-row-is-a-step).
- **An action declares what it is filled with, and the kernel names no column** — a parameter's
  local part is the variable its precondition projects, the `$token` its rules read and the
  predicate a step is written under, so one spelling serves three places; five named columns
  stood here instead, two of them the kernel's own inventions and one read by nothing, which is
  how a disk came to be called a lever and a peg a property, and how a venue and a valve came to
  be written into one slot by two different writers (an-action-takes-parameters).
- **An action is a point its taker contributes to** — `@contributes(<action>)` on a module says who
  and how in one place, a triple restating who was retired as a duplicate, and a gate in the
  repo, at onboarding and at boot holds a family to its actions, because a taker missing at
  runtime looked exactly like an actor that was busy.
- **An effect is one declaration** — the diff the search planned on rides on the step and is
  what the world is held to, so no actor sizes an expectation of its own; the one thing an
  actor adds is how close, and that is a bounded pick rather than a kernel constant.
- **The desire owns the term and the package owns the COST** — a want says `unmetWhen` and
  `estimates`; what the pattern means and that the estimate never overstates are promises about
  the package's own actions and costs, which a world file cannot keep. It owned a MEASURE too,
  of how badly a want was unmet in a given world, and that was a second judgment beside the
  met-test the judge was already held to; the met-test is the only one now, and what still
  orders the frontier is the estimate.
- **A want is judged by its met-test, and nothing scores a world by degree** — the search sees
  no partial progress, so a repair is found where the plan REACHES the met state, by one step
  or by several; what that cost is the slope's pruning, and what it bought is one judgment
  path, a stricter one — a lever that wrote a reading without retracting the one it replaced
  passed the measure and does not pass the met-test.
- **A ceiling on compute is stated in the unit the search spends** — depth was that unit
  under breadth-first and stopped being it under best-first, and a budget of worlds is what a
  sovereign can size from a measured cost per fork.
- **An interval is how this project says it does not know, and membership in one is CRISP** —
  a band in value, a period in time, a narrowing set of bands further out; the continuous part
  lives in the measure, which is why a reading is never 0.7 in its region and why expected
  values were refused where a set of possibilities would do.
- **A row whose presence is meant to BE a fact is named for the state, not for the instant it
  ends** — a cooldown row saying when the host may convene again was true the whole time it was
  written, so its presence said nothing and every reader did the arithmetic; `market:coolingUntil`
  is present while the venue cools, and the instant it carries is the horizon a sweep reads
  rather than a number to compare.
- **A base class is an import and an annotation is not** — a layer contract named in a
  signature costs nothing at assembly; subclassed, it loads the layer, which is why sensing's
  row types live behind the touch (#455).
- **A verdict the search reads is a query, and the judge stays at the gates** — a shape
  compiled to the select whose rows are its violations costs a millisecond where the judge's
  reader floors at tens, and holding the two to one answer by parity is what makes that safe.
- **The present is identified among the root's children, never asserted from one** — a child is
  a prediction and the present is observed, so what execution decides is which imagined world
  the real one landed in, and the cone under the match survives while its siblings die.
- **The claims a host issued are its demand** — a demand prediction was asked for as a new
  belief and found in the ledger the host already kept: a debt with a window is an occurrence
  about the window, and a drift that reads it drains the vessel ahead of the arrivals (#626).
- **A plan is placed at the instant of the root it was found from, never by subtraction from
  a deadline** — a bid placed at the crossing less the plan's duration landed in a round that
  had closed; the bid is taken while the round is open, and what waits for the instant is the
  claim's presenting, which the claim's own window places (#625).
- **What a search may see at a future instant is the instant's to say, and the reader names it** — a round row with no
  period was still open to a root standing hours ahead, and a bid was placed into a round that
  had closed; a round is a graph holding during its period now, and the rule never learned the
  time (#620).
- **A retraction is canonicalised like an addition** — a reading retracted without its type is
  two plain triples that cancel nothing, and a node's diff claimed the old value beside the
  new until the drift kept the whole node it took (#619); the bug hid because novelty needs
  only a difference, and a world claiming two readings for one key is still a different world.
- **A search is never handed a DESIRE** — what is pursued is a WANT derived from one, with a
  binding of its own; and the desire is not the law, because the region a want names, under
  never-newly-enter refused the very dose that repairs it: a replaced reading is a new node, so
  every standing violation re-read as newly entered (#618, measured before it was believed).
  It was "a desire is a ROOT", from when there were root desires and children derived under
  them; there is one kind of desire and wants are derived FROM it, so the word is retired
  wherever it meant one — `planner`'s `root` is the root WORLD a pass stands in and stays.
- **A round is the allocation under scarcity, and what makes buying available is a fact that
  holds at the instant the search stands at** — a host whose stock covers an ask grants a
  claim with no round, and a claim held, unlike a round, holds at every instant, so the plan
  is placed at the latest start; Acquiring on a want's instant alone placed the plan past the
  round a scarce host convenes now, and was refused.
- **A plan waiting at its last step is in progress** — held or placed, the world has not
  answered, and a search there found buying available on the very claim the plan was about
  to present and adopted it twice; only the round's close had hidden that.
- **A package's words are the package's, however long the kernel spoke them** — the ledger's
  vocabulary sat in `orexis:` because the ledger was the kernel's once, and the planner judged
  a debt met by naming its discharge itself; the host's desire carries the met-test in the
  ledger's words — the debt's own from #635 until the one derivation put it on the desire —
  `market:dischargedAt` is the market's, and the kernel names no word of it (#635).
- **A fallback is held to the case it was written for** — one want about everything a desire
  is about was for a desire UNMET now whose select yields no rows, and it minted a want under
  a met desire with nothing foreseen the first time the derivation ran without a judgment in
  hand.
- **A prediction is bands, and the width never leaves the rule** — a drift types the reading it
  predicts with every band the instrument's noise and the rate's spread reach, inside its own
  text; sensing writes what the drifts predict as graphs holding during their windows, the
  next reading's window first, and no kernel or sensing line adds a width to a centre (#642).
- **The agent keeps one timeline, and its clock may run fast** — two worlds ran their physics a
  hundred and forty-four times faster than the agent predicted by, because the stand-ins
  scaled their clock and the agent kept the wall's; every instant and stretch is in one
  timeline now, `clock.now()` is the only read, the pace is a deployment fact converted once
  where something sleeps, and no rule learned a unit (#646).
- **The core's word has priority, and a package speaks around it** — the keeper's row was
  renamed to "watch" to make room for a package's use of "expectation", before asking whether the
  package needed the word at all; it did not — sensing writes predictions, the first is what the
  next reading is held to — and "watch" was sensing's own, the instrument's, already (#640).
- **What ends by the clock is a graph with a period, and one sweep drops it** — four
  sweeps each knew its kind and each was a copy, a cooling row kept a timer a restart lost, and
  a claim past its window was let go by hand; a reader asking at an instant is handed no ended graph,
  upkeep drops whatever has ended on its tick and at boot, and what the ending MEANS stays
  the owner's, told `orexis:outdated` before the drop — which is where a debt's verdict is
  written, since the ledger keeps the verdict and not the want (#645).
- **The mind wakes on contradiction, not on time, and a set of bands is what a reading
  contradicts** — the actuator marked the region want on every reading and the dwell (#615) was
  weighed to slow it; a reading inside the bands the next observation was expected in leaves
  no mark now, one outside is a surprise the pass names, and a boundary crossed inside the
  set is the hysteresis a margin would have bought, without the margin (#632).
- **A step's band is the prediction from its landing, and a reading is compared once** — the
  keeper told sensing what a reading answering a step looked like and held a shape per step,
  and a node stating no value passed a constraint on a value; it tells the predictor the
  intended branch now, the ladder shows it from the landing, and one comparison at arrival is
  the verdict, met in the band and unmet outside it past the landing (#639).
- **What a plan changed is read off the signature, never off node identity** — a look
  re-stamps the node it finds and a purchase mints a new one, so by identity the look kept a
  pot from drying for five hours and the purchase could not stop the prediction emptying the
  barrel it had just filled; a key is changed when its canonical facts are, which is what a
  look's diff netting to nothing already said (#643).
- **A rule saying which world it reads is a package claiming something about every other
  package's actions** — `GRAPH $state` means a plan can change this and an unqualified pattern
  means it cannot, which depends on the whole loaded action set and is chosen from inside one
  package; climate's outside read carries the correction (#589), and the fix is precedence in
  the engine rather than a better guess.
- **What a fork may skip is bounded by what a rule may READ, never by what a step changed** —
  hanoi's Move walks a tower it has not touched inside `GRAPH $state`; narrowing took a padded
  solve from 58% of its time forking to 2% and was not taken, because a real pass forks for
  0.1% of it and reads for fifteen (#662).
- **A rule does not say which world it reads, and the list the runner builds says it instead** — naming it
  (`GRAPH $state` for a fact a plan can change, unqualified for one it cannot) is one package
  claiming what every OTHER package's actions can change, including packages that do not exist
  yet; climate's outside read carried the scar (#589), and taking the choice away deleted five
  doubled clauses and a UNION along with it, for no measurable cost (#666).
- **A/B on this bench is alternated within one session or it is not a measurement** — the Pi
  drifts about twofold between invocations, and two sides timed minutes apart made a change
  that does nothing read as a thirty-percent win (#666).
- **A repository is a collection of domain objects and not a store, and nothing here is one
  any more** — the convention was two instances, `Wants` and `Desires`, and both are functions
  over a store now; what a class still earns its keep for is owning a store whose nature is its
  decision (a MODALITY) or reaching the choir, neither of which is a collection. `Store` is
  infrastructure and keeps its name, and the layer above it is absent rather than mostly so.
- **A long-lived object and situational data about it is one shape three times, and only
  testimony is kept** — a desire and a judgment, an action and a step, a property and an
  observation; the observation is stored because it IS the premise, the other two are conclusions
  whose premises are stored and would outlive them, and the differences the likeness hides are
  cardinality (nine of eleven actions afford nothing, one afforded three), provenance
  (contributed, derived, received) and whether two agents may differ and both be right.
- **A graph's name is for eyes, and code relies on its classification alone** — an owner
  classifies what it writes when it creates it, a reader asks by class, and the name is a
  readable convention nothing depends on; boot used to type every per-agent graph by matching
  its name against a prefix its class declared, the planner and the projection named five,
  and asked which graphs could be renamed freely the answer was none — it is all of them now.
- **A graph class is named for the rows it holds, and a retired spelling may return with a
  different claim** — `RootsGraph` named the derivation's role for rows `orexis:Desire` already
  typed, the asserted graph said desire and held wants, and `orexis:DesireGraph`, retired as a
  modality class, returns as a content one, because a second spelling for a graph of desires
  would be the synonym the dictionary refuses.
- **A content class may not say how a graph arrived, and the cost of one that did was a second
  judging pass** — the asserted-desire class said its arrival in its NAME and the pursued class
  said nothing else at all, so no read could ask for *a graph of wants* and mean both the
  derivation's and a world's; the kernel read its own and compiled and judged the world's at
  read time, and `find_wants` alone answers for every want now. Both spellings are gone from
  this file too, because a retired term named in prose is the dangling spelling the rename rule
  refuses — `tests/test_layout.py` caught these two.
- **A graph is classified per kind it HOLDS, and a graph holding two kinds is two graphs** — one
  asserted graph was a graph of desires AND a graph of wants because four worlds put different
  content in it, which is a graph whose content no reader can predict; `graph/desire/asserted`
  and `graph/want/asserted` have one content class each, and `test_modalities` stopped
  exempting them from the rule it exists to state.
- **A want is one-shot and carries where it has got to; a desire has no stages** — recognized,
  planning, ready, pursued, done, failed, unreachable, each written by whoever DECIDES it and
  never inferred, because computing each from its own corner is how one question comes to have
  six answerers; a desire stands for the agent's life and is good or bad at the instant it is
  asked about, computed and stored nowhere.
- **A terminal state is an invariant, not an ordering rule** — the deliberator marked a want it
  had already reached `Done` and answered with no plan, and the caller, seeing no plan, wrote
  `Unreachable` over it, so hanoi solved its tower and reported it unreachable; nothing moves a
  want out of `Done`, and neither writer has to know the other exists.
- **Deciding a thing is finished and clearing it away are two acts** — every site that withdrew
  a want was guarded on how the want had been WRITTEN, so a want a world authored was withdrawn
  at none of them; `forget_wants` is garbage collection over whatever is `Done`, on the pass, as
  the keeper's sweep already was for what ends by the clock (#645).
- **Never count what a class answers for** — two tests asserted eight public graphs, which meant
  "as many as there are today" and went red over a vocabulary change they were not about; what
  they each meant was that the answer is not empty, and that a set is unchanged.
- **A case is held to the whole store it leaves, never to a reading of it** — the derivation's
  cases compared five things per want where a want writes nineteen quads, so a label, a link,
  a period or an owner could be wrong with every case green; a snapshot compared whole catches
  under-reporting, and a behaviour change is a diff regenerated by a flag and reviewed by eyes.
- **A read is handed a store and nothing else, because an agent id is another aggregate root's
  identity** — which store is the agent's decision since it owns them; identity travels as a
  query criterion, and the reads need none at all, since one agent, one volume means the store
  IS the scope.
- **A capability that asks for a derivation is not minting** — the ledger, having written a
  debt and what it predicts of it, calls `derive_wants` so a claim arriving is a want arriving
  and not a want on the next tick; what it writes is the instance and the prediction, and what
  stands afterwards is deliberation's, about that debt — and every other desire's, since the
  derivation is about all of them.
- **Nothing stands between a desire and a want** — `derive_wants` judges every desire at the
  present and at each foreseen instant and mints a want per cluster of what the met-tests read
  unmet, in one function and one contract; `scope_actions` writes the scopes at boot, so the
  derivation reads no action. It was two functions with a written judgment between them, and
  no caller ever took one half.
- **A want exists because its desire read unmet, so the same rows withdraw it** — a want the
  decomposition no longer produces is met, and running the want's own met-test to discover
  that asked twice what one pass had already concluded; withdrawal is against the WHOLE
  decomposition, present and foreseen, since a presented debt's rows do not mention the
  unpresented debt whose want was minted at its lapse, and dropping on the present alone took
  it. A want a plan is walking is kept whatever its desire reads.
- **A possible world is kept, and its diff was a memo** — a world's graph was dropped once
  its node was expanded and re-made from the nearest kept ancestor, so a node carried the two
  lists its step's rules had answered; two measurements retired that, since a world's readings
  are 2 quads on the courier and 26 on the greenhouse against the ~5,000 shared quads a pass
  copies once, and the diff is derivable anyway — it is what a step's own rules produce from
  its parent, and the step's row already names the action and every binding they take. The
  memory argument was made when a node ALSO carried a flat rdflib copy of the whole world
  (#481), and did not outlive it.
- **The one function over TWO stores is the filling of a possible world** — `init_imaginarium` takes
  the beliefs and an empty store the caller made, copies every public graph whatever its
  period and the catalogue with them, and hands the second back; everything that happens to
  that world afterwards happens to it the ordinary way, so this is the seam rather than a
  wrapper. Narrowing what crosses — four named graphs, or the graphs of one scope — was
  measured at 10.4 ms against 0.6 on a pass costing over a second, and fails silently: a
  pattern reaching a graph nobody copied returns an EMPTY RESULT, not an error.
- **A function over the store is handed the engine and nothing else** — `derive_wants` and
  `scope_actions` take `pyoxigraph.Store` and no wrapper: which graphs they read they ask of
  the catalogue in their own texts, whose a desire is they read off `orexis:holds`, and the
  present is the clock's; the wrapper caching a view of the store cannot see a write it did
  not make, so asking it for the engine (`Store.engine`) is what makes it forget.
- **A met-test asked by band names which way it broke, and tests no topology** — a reading is
  the band it is in, so a desire says *it should be inside* once per way of failing and each
  block declares its side, which the WANT carries (`orexis:violationIs`: below, above,
  unmeasured, stale) because that is what decides the repair — a look answers the unmeasured
  one and no act of any kind does. A test that walked the topology instead would be satisfiable by
  moving the sample off the subject or by re-pointing what counts as ideal, which is the goal
  repaired by editing its own premises; a structural repair stays reachable because the
  closure walks back from what the want reads to whatever changes it.
- **One module reads predictions, and it takes them as given** — `judging` enumerates the
  states, the present and every instant a prediction reaches, and runs each desire's met-test
  at each; what it reads is a WITNESS, computed where it is needed and stored nowhere, so the
  minting and a crossing get the same answer from the same code rather than from two paths
  that could disagree.
- **A derivation asks nothing the met-tests do not answer** — a foresight filtered a foreseen
  failure the reading already dated, and was two states in practice, unbounded and absent;
  how far ahead the agent sees is the horizons each drift predicts at, and the pick, the
  extension point and the kernel property are gone.
- **A partition of the vocabulary belongs to the store, not to an agent** — the scopes are a
  function of the actions the store holds and the derivations loaded, so every agent reading
  one store computes the same one and there is nobody to name it after; genesis puts the
  derivations' read and write predicates in the store beside the actions, which were there
  all along.
- **What was foreseen may arrive early, and the present outranks the instant** — a want
  minted at a predicted crossing or lapse says *hold at T* and its plan is placed to land at
  T, so when the holder presented an hour early the serve was placed at the deadline; a
  cluster unmet now whose want still names an instant is re-minted at none, same name.
- **One function mints every want, and a package writes instances and predictions** — a desire
  is one and universal, its met-test's violation rows are the instances in trouble and each
  prediction's start is when, a want is minted per scope of them, and the ledger's own
  decomposition never had a runtime form; the per-instance DESIRE level was drawn and
  struck, because the instance is the want's grain.
- **A want states no time semantics of its own** — the KIND is its type, the INTERVAL is its
  graph's period, the INSTANT is `orexis:holdsAt`, and the FAMILY a reader filtering on a binding
  actually wanted is the graph's classification; the binding property said all four a fifth
  time, was computed from whether an instant was known, and the planner its own comment named
  as its reader never branched on it (#681).
- **A kind is a type, not a binding** — the always-binding had six readers and every one asked
  it which KIND a node was, while the planner it named as its reader never branched on it; a node
  could be a desire by type and a want by binding at once, which three shipped worlds were, and
  neither collection could see them.
- **`orexis:Want` is not a subclass of `orexis:Desire`** — the closure is materialised once at
  genesis and a want is minted long after, so the entailment never reached one and every writer
  hand-wrote both types; what the axis actually did was make `?d a orexis:Desire` match both
  kinds, so a collection of desires had to filter on a binding to find its own contents.
- **Standing versus occasioned is the axis, and who wrote it is provenance** — three worlds
  ratify a WANT directly, authored and standing and handed to a search, so declared-versus-derived
  was never the distinction it was written up as.
- **A desire is declared and a judgment is made** — the class called `Desire` carried an
  urgency and an expiry, was built fresh by whichever capability held the region want and was never
  written down or read back, while the row a package's rule writes at genesis had no type at
  all; naming the second thing let the first become data. The name has since gone the way of
  the thing: nothing stands between a desire and a want, and what a judgment carried — the
  reading and which way it broke — a WANT carries, made fresh where it is made fresh and
  stored where it is stored; the urgency it also carried is gone, and the line below says why.
- **Nothing ranks a want before the search that could rank it** — a want carried an urgency
  four packages each computed their own way, and `Deliberator.pursued` plans for EVERY want it
  is handed, so the rank only ever decided which was searched first; what would compare a
  thirsty fern to an overdue debt is what their plans cost and how long they take, which is
  the search's answer and no contributor's.
- **A read over stored rows is handed a store, and one over contributed answers is handed the
  agent** — `find_wants` reads graphs so it takes somewhere to search, `Pursuing` asks the choir
  so it must reach the choir, and the asymmetry is what tells the two kinds of read apart.
- **The function that decides a thing owns writing it, and a read only reads** — `Wants`
  carried `save`/`delete_by_uri` beside the module functions the derivation called, plus
  `on_saved`/`on_deleted` so a write could announce itself; the announcement had one live
  producer and one live consumer and both were rebuilding the desire projection, and the
  collection's own writers had no caller but their tests. A want's graph, its catalogue row
  and its period are decided where the want is, and whoever wrote says what changed.
- **Two readings of one met-test are not a duplicate when the compiler, the source and the
  cache all differ** — the derivation wants WITNESSES from the graphs of desires and wants and
  caches nothing; the kernel lifting a ratified want wants a BOOLEAN from public knowledge,
  where a package's shape lives, and caches per want because an asserted one cannot change
  while the agent runs. Merging them was attempted and refused on all three counts.
- **A synchronous twin of a pass is a second pass, and it drifts** — `deliberate_on_gaps` was
  what a test called to have the consequences before it asserted, and it read what the agent
  was considering DIRECTLY where the real pass derives first; so every test went down a path
  production does not have, missing the one step the seam was built to add. One pass with two
  endings (`consider` marks, `consider_now` takes) sharing the generator that derives is what
  stops that: the difference is where the work happens, and nothing else can differ.
- **A pass begins in one place, and judging happens once in it** — the container re-ran a
  want's own met-test to correct a row gone stale, which is asking twice what one pass had
  concluded; it went stale because the derivation ran only where a package wrote something a
  desire reads, so what fixed it was not a better re-judging but `pursuit.consider` deriving
  every pass — the third reading above, and the reason it existed, both gone with the seam.
- **The layer that waits does the waiting, and a package has ONE way in** — deliberation kept
  a `Timer` and its landing reached back into the container's collection, so the two reached
  into each other and no single place was where a pass began; the container holds the clock
  now and calls `pursuit.consider`, and what a want IS stays in the package that has the word.
- **Considering and pursuing are a pass apart** — `consider` derives what is wanted and hands
  what may be acted on to the search, `pursue` plans one of them and commits, so a want nobody
  may act on yet is CONSIDERED and never pursued; the collection was `Pursuing` while the
  container held it and the pass had no name of its own.
- **A want somebody else sourced is still an INSTANCE under a standing desire** — a call was
  lifted per call by `hosting.desires()`, the one want here no derivation minted, so it had no
  provenance, no graph and no period, and the planner could judge it only by asking a
  capability how unmet it was; a host holds *no unanswered calls* over its venues now and the
  call is the row that desire is about, which is the shape the ledger's debts already had.
- **A criterion is an argument, never a name** — `Wants` was five finders over ONE query with a
  `where` clause swapped, three of them called by nothing but their own test, because the Spring
  Data spelling put each criterion in a method name and so charged a name per combination;
  `find_wants(store, desire=…, derived=True)` says at the call site what `find_first_by_desire`
  hid, and the one distinction worth a name of its own is the answer's SHAPE — a page against
  one-or-None.
- **A model is a Python type only where something READS its fields** — `Want` is one:
  nineteen modules import it, capabilities subclass it to add their own, and its state, its
  instant and what it is about are all read. `Desire` was not: it was built from a query and
  discarded, because the two callers wanted a boolean and a uri and the third wanted uris, so
  the reads answer those and there is no type. A class that carries a uri out of a query is
  the store duplicated in Python for the length of one expression.
- **A model gets its OWN file when it is cheaper alone** — `want.py` imports nothing but the
  standard library, so naming the type costs its nineteen importers nothing; folding it into
  `wants.py` would make every one load progression's clock, ontology and store (#455, the
  reason sensing's rows sit behind a touch).
- **An update takes no dataset** — `Store.query` is handed its graphs per call, which is the
  door, and `Store.update` names them only in its own text; so what chooses which graphs are
  the world at an instant is Python or a materialised view, a derivation that needs neither
  is a rule, and a search — an order, a budget, a stop — is neither and stays Python.
- **Deliberation is on triples, and a number is not special** — how a domain describes its
  world, exact numbers, ranges or classes, is decided inside the domain, and its actions'
  preconditions and effects are described the same way; the core compares triples and
  interprets no literal, and progression sizes the act when it is taken. A partition and an
  interval were both built into the core and refused on reading.
- **One graph describes every graph and itself** — what a graph is, whose it is, how it arrived,
  when it holds and what loaded it were three meta-graphs each reader named by kind; the
  catalogue is found by its own row, `a orexis:CatalogueGraph`, genesis alone spells its name
  because genesis creates it, and it is neither public nor the agent's own, so a mention of a
  graph is never a fact in a world.
- **A reader states the kinds it reads, and the store decides nothing** — four doors each
  assembled a dataset by a rule of the store's, and which graphs were the agent's own was five
  classes it excluded and a tree it walked, so a package chose its treatment by a superclass
  and a caller never said what it read; a query is handed its graphs now, `graphs_of` answers
  by kind and instant, every row carries every kind, and the union of everything was refused
  as the default because it reads every sibling world and next hour's readings as the present.
- **A rule concludes and never deletes, and what replaces a revision is its source
  rewritten** — SHACL 1.2 Inference Rules and the sovereign's instinct agree; the revisions
  of a graph live in a graph of their own, derived from it, and go when it goes, so no rule
  ever names what it takes away; the rules are the draft's, adopted as they stand — a rules
  graph, a rule set, SPARQL rules by layer and order — with nothing of ours on them
  (`agent/belief/revise.py`).
- **Any belief is accepted, and revised; validation was built beside revision and struck the
  same day** — every new graph held to the packages' shapes and forgotten whole on a
  violation; belief revision keeps the new information, dropping testimony over a shape is a
  gate wearing revision's name, and a law's objection to a graph is a revision a rule can conclude for the mind to want repaired.
- **A state that served a gate goes with the gate** — a proposal, a graph classified as not
  yet believed until `believe` retyped it, bought only that a graph was never seen without its
  revisions; a graph with no catalogue row is already invisible to every reader, so the
  writer concludes and then classifies, and a class, a property, two acts and a page said
  nothing the row's absence did not.
- **Revision's ceiling is a budget in rule executions, and a source the budget cuts short is
  continued by the next pass** — `revise` capped its own iterations at a number the module
  chose, where the search's ceiling is the container's in the unit it spends; a cut keeps what
  was concluded with the row saying so, the deliberator re-queues such rows at boot, and a
  rule set that never settles spends a budget every pass and is reported rather than looped on.
- **Sensing observes and says when a sensor has gone silent, and prediction is a package of
  its own** — `received` writes one `sosa:Observation` per key with its number, holding until
  the next is due by the sensor's `ssn-system:Frequency`, `missed` answers the readings fallen
  due on the container's tick and says `sensing:silentSince` of a sensor silent past a limit of
  its cadences, and the side is a revision the three rules sensing ships conclude; no band,
  no side, no want, no verdict on a prediction is sensing's own write. `agent/prediction/`
  bisects every crossing of a range bound between the ladder's rungs and writes one prediction
  per stretch, finds the observation by the kernel's kind and `sosa:madeBySensor` and imports
  nothing of sensing — a stretch already says when a rule's result changes, and the planner's
  re-root tells a surprise — and a range is SSN-System's as the world states it, nothing minted.
- **Sensing speaks SOSA and SSN, and declares only what they lack** — a sensor
  `sosa:observes` a property and `sosa:isHostedBy` what it is mounted in, which is the
  observation's key, and the layer's own words are the observation graph's kind, the silence,
  the three sides and the pipeline's — a codec and a scaling as families, a sensor's binding to
  a member of each, JSON and identity as the members that ship, and the pointer — since neither
  standard says how bytes become a number, while the drift (a value moving by itself, which no
  `sosa:Procedure` is) is the prediction package's one word;
  `polls`, `monitors`, `samples` and `senseMode` were SSN restated, `atHorizon` had a drift
  declare the scan's reach, and the wiring module that read them had no caller, so the ladder
  is sensing's, a transport hands `received` the sensor's IRI and bytes and sensing knows no
  transport — the contract a member answers is the family's own, `Transport` at
  `agent/transport/` — and the layout test holds every `sensing:` word the tree speaks to the
  ontology beside it.
- **The transport speaks MQTT4SSN, and a topic is named by the filters that match it** — the
  ontology that extends SSN and SOSA with the protocol in the OASIS terms is adopted as it stands,
  as SHACL's rules were, and `agent/transport/mqtt/` declares no word of its own; a sensor
  `mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and since MQTT4SSN
  gives a topic no name but the `mqtt4ssn:hasFilterPattern` of a `mqtt4ssn:TopicFilter` that
  `mqtt4ssn:matchesTopic` it — and a topic name is itself a valid filter — the agent subscribes by
  the pattern and publishes a command to one with no wildcard; what it listens to is derived from
  what it acts for, and the broker's address stays in the environment.
- **A world's words are its own or a domain's it imports, and the runtime boots from its files** — Hanoi's puzzle was a
  tool package with an ontology and one action; in 0.2.0 the puzzle is the domain
  `domains/hanoi/` and `world/hanoi/` imports it beside its desires and state, `agent/runtime.py` reads the kernel's
  T-Box, every package's and the world's as graphs of their own and derives the closure into
  one more, and the world's tests live with the world, since the target state is no global tests.
- **The runtime stops when no desire is held and every want is reached** — a desire is universal
  and asks at every instant, so an agent holding one runs for as long as the process does; a
  want is one-shot, and a pass that weighs one met in the present ground withdraws it from the
  imaginarium and the beliefs whoever authored it, so Hanoi's mover, holding a want and no
  desire, exits once the tower stands. Wants standing with nothing walking is either a search
  the budget cut short, which `planning:Exhausted` says and the next pass continues, or
  unreachable, which an agent holding no desire exits saying. A pass at the same instant
  as the last re-lays the present under its name and the search starts over, so a clock that
  does not tick is a test's mistake and not a runtime's.
- **A document says which graph it is, and the file's name is for eyes** — a Turtle file is one
  graph named by its own IRI and `<> a orexis:StateGraph` says what it is, a TriG file names its
  graphs and says so in its default graph, and the loader moves those rows to the catalogue and
  adds the arrival and the owner, which a document may not state; the runtime knew five file
  names and one vocabulary graph before, and now every ontology and rule set is a graph of its
  own that a lived-in volume reads again at boot, so updating one is editing its file; and no
  `owl:Ontology` header, since nothing read one — a package's prose about itself is a comment.
- **A pass weighs its grounds, and a candidate is weighed where it is taken** — the pass's own
  loop weighed every unweighed pair, so the candidates a budget cut left untaken were weighed
  and never offered to the expansion that takes them; the courier's corner at sixteen a pass
  emptied its frontier short of the door and read EXHAUSTED for ever, while Hanoi's cuts had
  happened to leave nothing behind.
- **A vocabulary two worlds speak is a domain, and a world imports it** — `domains/<name>/` holds
  the words, the actions and the shapes a desire points at, and a world says
  `owl:imports <../../domains/hanoi/ontology.ttl>`, which resolves to the `file:` IRI the graph is
  loaded under, so the import names the graph it brings and the boot loads only what a world
  asks for; the shapes are `orexis:ShapesGraph`, their own kind, because crossing every ontology
  graph into the planner's view cost thirty times crossing the desires.
- **A graph of actions is an `orexis:ActionGraph`, and the planner reads actions from those
  alone** — the kind was 0.1.0's and the 0.2.0 census dropped it because nothing asked for it,
  so Hanoi's actions were typed the bare `orexis:PublicGraph` and `admit`, `take` and
  `footprint` read every public graph to find them; named for what it holds, and asked for by
  the three reads, it is a term somebody reads.
- **The search runs no rules, so a reading's revisions travel with it and an effect speaks the
  concept they conclude** — a side is what the rules concluded of a reading, in a graph derived
  from the reading's; the imaginarium takes every graph derived from what crosses, the present
  ground holds the readings and their revisions, a prediction is laid with its own, and the
  executor answers a step over both, so a dose that predicts the soil `inside` its range is
  answered when the next reading is revised to it (`store.revisions_of`) — a revision is a
  belief and a drift's prediction, derived from the same observation, is not, which is what
  keeps the foreseen reading out of the present.
- **0.1.0 is not started any more, so it is amended, not copied** — a package 0.2.0 needs moves
  into a domain and changes there, and the 0.1.0 suite that built on it is switched off in the
  gates rather than propped up; the four files in `tests/` that read the whole tree still run.
- **A step is sized when it is taken, from the present, and the search only says the side it
  reaches** — a dose's effect is the soil coming to be inside its range; `execution:command` on the
  action is run over the beliefs as they stand when the step is taken and answers the actuator and
  the payload, the dose's size from how far the reading is below the middle of the range, and the
  runtime sends it through the transport's `actuate`.
- **A world speaks for its readings' revisions** — `world_at` hands a rule every known graph but
  those a world speaks for, and once a ground carries the sides beside the readings, the revision
  graphs are among them: read beside a possible world, a dry reading's `below` outlived the dose
  that answered it, and the greenhouse's search offered the same dose for ever.
- **The plant's surroundings are one domain** — water and climate were two 0.1.0 packages, and the
  soil's moisture, the air's temperature, the source and the heater are one `climate:` vocabulary
  in `domains/climate/`; actuation is the other, the devices and the dose.
- **A broker's address is the world's to state and the agent's to be told** — MQTT4SSN names a
  broker and no port, so the world says `schema:url` on its `mqtt4ssn:Broker` and the operator's
  tools read it to run the broker and write each agent's environment; the agent reads only its
  environment, as the transport's principle has it, and `orexis-agent` runs the 0.2.0 runtime.
- **Signing is between agents, and an agent trusts itself** — a signature proves to a device that
  the agent asking for an act was authorised by another, which is the market's case; an agent
  dosing its own bed through its own pump has no second party to convince, and the broker's ACL
  already admits only the holder to its devices' command topics, so 0.2.0 signs nothing until the
  market returns (authn-authz-capabilities).
- **The 0.2.0 kernel's T-Box is what the tree reads** — `agent/ontology.ttl` is extracted from the
  0.1.0 file by a census of query texts, term constants and the packages' vocabularies, closed
  over what each declaration reaches; a mention in prose is not a read, and a term nothing reads
  is annotation and goes.
- **A belief kind enters through `propose`, and a package's working graph is not a belief** —
  the belief package's layout test holds every writer in the tree to the door, and what
  bypasses it is what no rule reads as the world.
# Working on Orexis

A society of self-interested agents that bid for a scarce resource. The v1 domain is plant
watering, but the domain is a plug-in — plant/water language is the example, not the
architecture.

Read [`knowledge/index.md`](knowledge/index.md) before changing anything structural. It is the
durable "what and why"; the code follows it, not the other way round.

## Use the OKF skill for anything under `knowledge/`

`knowledge/` is an **Open Knowledge Format v0.1 bundle** (https://okf.md), not a docs folder.
Invoke the `okf-open-knowledge-format` skill when adding, editing or checking documents there.
If it is unavailable, the rules are short enough to follow by hand:

- every concept `.md` has YAML frontmatter with a non-empty `type`, plus `title` and
  `description` — and a `domain/` page whose word the T-Box carries binds it with `term:`,
  which `tests/test_knowledge.py` holds to what the ontologies (ours vendored under
  `tests/fixtures/vocabularies/` for the external ones) actually declare. **Eight types, and the one to reach for is the one that answers what KIND of
  thing the page is:**

  | | |
  |---|---|
  | `Decision` | why the code is as it is. Closed by nothing; superseded or amended |
  | `Domain Concept` | a **thing** in the model — a claim, a good, a step, a world |
  | `Process` | something that **happens**, with phases and an end — an auction, a round, onboarding |
  | `Capability` | a named ability with **interchangeable implementations**, granted by its own premise and provided by a package — rule 2's unit |
  | `Role` | a kind of **principal** with something at stake — an agent, a supplier, a dealer |
  | `Service` | a part of the implementation that **holds logic** — the deliberator, the revision seam |
  | `Repository` | a part that **passively holds data**, scoped to one agent — the belief base, the imaginarium |
  | `Runbook` | how to **operate** it |

  The split was asked for by the pages: `auction` opened "an auction is a PROCESS", `bid-matching`
  called itself "the STEP that…", `onboarding` "the PHASE between…" — three pages naming their own
  type in prose because the field could not hold it. **A type that falls to one member is a type
  to fold back**, not to defend; the split landed at 10 / 5 / 5 / 4 / 4;
- a **decision** additionally carries `status` (`accepted`, `superseded`, `superseded-in-part`)
  and `timestamp`, and a superseded one carries `superseded-by`. **No other type carries any of
  those**: a concept, a process, a capability, a role, a service and a repository have no state to be in,
  being either current or wrong. `stage` and `tags` are
  gone — `stage` said `v1` in every record, and `tags` had 147 values of which 86 were used
  once and nothing read any of them;
- **quote or fold anything with a colon in it.** A `description` reading `on one axis: the
  agent asks` is not valid YAML, and 27 files were unreadable to every OKF consumer while
  passing the vendored check, which greps rather than parses. Use `>-` and indent;
- `index.md` carries **no** frontmatter — it is navigation, and its title is its heading. Only
  `knowledge/index.md` may declare `okf_version`;
- **an index entry is the claim, not the abstract** — 26 words is the cap, the abstract lives
  in the record's own `description`, and the argument lives in the record;
- validate with `./tools/validate-okf.sh knowledge` — vendored from the skill, because a gate
  that only runs from one person's home directory cannot be run by a fresh clone or by CI. It
  checks the OKF spec and nothing about THIS project, so do not edit it: the project's own
  rules are `tests/test_knowledge.py`, which runs under `pytest` and fails on unparseable
  frontmatter, an orphan document, a dead link, an over-long index entry, or a document naming
  a path that is not on disk.

**`knowledge/domain/` is the shared dictionary, and a term is defined before it is used.** The
pages there fix what our words MEAN — step, gap, imaginarium, capability, action, lot, venue
— and a discussion, a commit message, a docstring or an issue that uses one of them uses it the
way its page does. **If a change needs a word the bundle does not have, write the page in the SAME
change, first.** A word used before it is defined is a word everyone defines differently, and the
definitions never meet. This is the discipline
`tests/test_knowledge.py::test_no_two_domain_pages_state_the_same_claim` already enforces between
pages — one claim, one owner — applied to the vocabulary itself.

**A concept is defined once and then used by its name — ubiquitous language.** A page grounds a
word in prose, and that prose is where the meaning lives; every later use — a page, a commit
message, a docstring, an issue, an answer to the sovereign — uses THE WORD, never a synonym and
never a paraphrase. A plan is steps, so a plan is not a "chain" and a step is not a "move" or a
"link"; a precondition is not "what the rule read" once its page has said that is what it is. A
synonym is how one concept becomes two: a reader meets both words, looks for the difference, and
the definitions drift apart from there. The one legitimate second name is the term's — the page
says which IRI it is bound to, and code speaks the term where prose speaks the word — and where
a page and its term disagree that is a debt to settle, not a licence to alternate. One was
settled by that rule: the precondition page was bound to a term of another name, so a step's own
facts had two names in one repo, and #580 renamed the term and every identifier that read it —
leaving no dangling spelling, which `tests/test_layout.py` holds these documents to.
A word with a SECOND meaning is not that debt: a rule's premises and a capability's premise are
their own concept and keep the word. A synonym found in a page is fixed in the page, not
tolerated by the reader.

**One concept, one article.** If a page turns out to define a second thing, that thing gets an
article and the two link — ownership is then structural, and there is nothing to keep in step.
Three clauses make that workable, and each was learned by getting it wrong:

- **Where an owner already exists, POINT — do not extract.** Extraction is for a claim that has no
  page yet. `capability.md` restated capability-aware validation, the materialised closure and
  "refusing to start is not self-report" before the gate objected; all three already had owners,
  one of them a page written in the same commit.
- **A pointer that restates is a second owner.** A stub saying what the other page says has not
  moved the claim, it has copied it. Say what THIS page does with the thing, and link.
- **A relationship can be the concept**, and the test is whether each half stands alone.
  `means` and `lever` split because each looked like it had content of its own — a means was
  the joint three subsystems met at; a lever was an instance whose absence removes a row. Both
  folded in the end: `means` into `action` when the three subsystems became one node, because a
  joint between one thing and itself is nothing (the-action-is-the-kind), and `lever` into the
  BINDING when an action came to declare what it takes, because "the instance in the `via`
  column" is not a concept once there is no `via` column (an-action-takes-parameters).
  `model-and-unit` does not split: its whole content is what a unit inherits from its model, so
  two pages would each have to restate the relationship, and the gate would refuse them.

The gate is `tests/test_knowledge.py::test_no_two_domain_pages_state_the_same_claim` — overlapping
runs of eight words between any two domain pages, capped at four. It does not care about topic,
only about restatement, which is the thing that rots.

**Durable knowledge goes in the bundle, never in a new README.** `domain/` says what a thing is
and how to use it; `decisions/` says why a choice was made and which seams it leaves open. The
existing READMEs (root, `firmware/*/`) are operational entry points and stay, but do
not add more for design knowledge.

**Reconciling the bundle is part of the change, not follow-up.** After changing behaviour, grep
`knowledge/` for claims the change made false and fix them in the same commit. A stale decision
record is worse than none, because it is still cited.

## Principles, one line each

**This is the default place for what a change taught, and a decision record is the exception.**
Most work ends with a line here plus a commit message; a record is for the rarer case where a
real alternative was weighed and refused, and the argument has to survive. A principle earns a
line when it would have changed a decision, and it stays one sentence — if it needs a paragraph
it is a record wearing a bullet.

- **An RDF URI beats a homemade id for referring to an agent**, and the exception proves it: the
  one name that stays a short string is the one that must also be a broker principal, a bucket, a
  container and a directory.
- **A term nobody reads is annotation**, however many instances state it.
- **A word used before it is defined is a word everyone defines differently** — `duty` ran to 64
  code sites and 13 pages with no page of its own, meaning `obligation` all along.
- **Desire is bouletic, obligation deontic, availability alethic, freshness epistemic** — different
  logics rather than strengths of one, which is why an unmet want is a gap and an unpaid debt is
  a breach.
- **A repository holds data and a service holds logic**, and a thing that decides nothing is a
  repository's support function rather than a service.
- **Deciding nothing is the finding** — writing no graph is only the hint, since three services
  write none and stay services.
- **Verify a claim in the bundle against the code before repeating it**; nothing gates prose
  against the thing it describes.
- **A rename is done when the suite says so**, not when the thing you grepped for is gone.
- **A word-boundary sweep bites a hyphenated slug and a variable named after the word** —
  `\bstake\b` matches inside `the-stake-is-sensings-want`, so 45 files came to cite a record
  that does not exist, and a local `stake` is spelled like the word it was named after, so nine
  files grew `(region want := ...)` and stopped parsing; hold out the words that merely contain
  the letters (`mistake`, `stakeholder`) before starting, and let the parser and the suite find
  the rest.
- **Search every tree that loads the vocabulary before calling a term dead** — `assembly/` reads
  ontologies that `agent/` never mentions.
- **A record earns its place by refusing something**; "we could have not done it" is not an
  alternative.
- **A record is engaged by its premises, not cited by its conclusion** — the mind's record
  refuses a granted mind, and was nearly spent against unconditional layer trees it never
  argued about.
- **A prune is only as good as when its bound arrives** — an admissible estimate refused
  nothing under breadth-first, because the first achiever came last, and the same estimate
  refused sixty percent of the courier's forks the day the search followed it.
- **The layer that waits does the waiting** — a module that keeps its own timer and checks
  its own trigger has rebuilt the middle layer inside a capability; adopt with a condition and
  a deadline, and say only what you wait for.
- **A kind said by absence is a kind two readers disagree about** — an action with no effect
  was "an act the reflex may take" to one reader and "passed over, plan partial" to another,
  until the gate held every action to both texts or neither, and a class for the second kind
  was weighed and dropped as a term nobody would read.
- **An action that touches nothing the want reads is never simulated, and the closure is what
  makes that safe** — filtering to the goal's predicates deletes every chain; closing backward
  through preconditions keeps the bid that makes the dose possible.
- **A want is authored positive and the kernel writes the negation** — rows are
  existential and a want is universal, so somebody turns the shape inside out, and a compiler
  held to the judge by parity does it once where every author would do it differently.
- **A plan that worked is kept, and the world verifies it, not a search** — a remembered plan is
  adopted where the facts its steps read still hold, since every step is checked when it is
  taken and a failed step drops the tail; re-simulating it first would be a search per reuse,
  and hashing the whole world keyed it to facts it never read.
- **A level is a vocabulary, and a taker-less action is a promise the level beneath keeps** —
  a search never leaves the vocabulary its want is written in; the bridge translates a step's
  promised fact downward when the step is reached, and the verdict back, never the world.
- **A method is walked, never searched** — the steps an abstract action comes to are the
  package's protocol, not a choice, so the keeper expands them at adoption and each step says
  what it waits for; simulating them would spend the budget on worlds the measure cannot tell apart.
- **A step is an action PICKED for execution, and what it adds is at least the variables** —
  planning finds a plan and every action in a plan is a step, so a world merely ADMITS one per
  action per legal filling and the search picks; an `Affordance` carried four of a step's fields
  and a `from_row` copied them across, which is two classes for one shape and a second word doing
  no work the absent fields were not. The service between the two collections fetched nothing and
  decided nothing once the word was gone, so the loop is `Steps.find_all` and every identity it
  held is a criterion of the ask (a-row-is-a-step).
- **An action declares what it is filled with, and the kernel names no column** — a parameter's
  local part is the variable its precondition projects, the `$token` its rules read and the
  predicate a step is written under, so one spelling serves three places; five named columns
  stood here instead, two of them the kernel's own inventions and one read by nothing, which is
  how a disk came to be called a lever and a peg a property, and how a venue and a valve came to
  be written into one slot by two different writers (an-action-takes-parameters).
- **An action is a point its taker contributes to** — `@contributes(<action>)` on a module says who
  and how in one place, a triple restating who was retired as a duplicate, and a gate in the
  repo, at onboarding and at boot holds a family to its actions, because a taker missing at
  runtime looked exactly like an actor that was busy.
- **An effect is one declaration** — the diff the search planned on rides on the step and is
  what the world is held to, so no actor sizes an expectation of its own; the one thing an
  actor adds is how close, and that is a bounded pick rather than a kernel constant.
- **The desire owns the term and the package owns the COST** — a want says `unmetWhen` and
  `estimates`; what the pattern means and that the estimate never overstates are promises about
  the package's own actions and costs, which a world file cannot keep. It owned a MEASURE too,
  of how badly a want was unmet in a given world, and that was a second judgment beside the
  met-test the judge was already held to; the met-test is the only one now, and what still
  orders the frontier is the estimate.
- **A want is judged by its met-test, and nothing scores a world by degree** — the search sees
  no partial progress, so a repair is found where the plan REACHES the met state, by one step
  or by several; what that cost is the slope's pruning, and what it bought is one judgment
  path, a stricter one — a lever that wrote a reading without retracting the one it replaced
  passed the measure and does not pass the met-test.
- **A ceiling on compute is stated in the unit the search spends** — depth was that unit
  under breadth-first and stopped being it under best-first, and a budget of worlds is what a
  sovereign can size from a measured cost per fork.
- **An interval is how this project says it does not know, and membership in one is CRISP** —
  a band in value, a period in time, a narrowing set of bands further out; the continuous part
  lives in the measure, which is why a reading is never 0.7 in its region and why expected
  values were refused where a set of possibilities would do.
- **A row whose presence is meant to BE a fact is named for the state, not for the instant it
  ends** — a cooldown row saying when the host may convene again was true the whole time it was
  written, so its presence said nothing and every reader did the arithmetic; `market:coolingUntil`
  is present while the venue cools, and the instant it carries is the horizon a sweep reads
  rather than a number to compare.
- **A base class is an import and an annotation is not** — a layer contract named in a
  signature costs nothing at assembly; subclassed, it loads the layer, which is why sensing's
  row types live behind the touch (#455).
- **A verdict the search reads is a query, and the judge stays at the gates** — a shape
  compiled to the select whose rows are its violations costs a millisecond where the judge's
  reader floors at tens, and holding the two to one answer by parity is what makes that safe.
- **The present is identified among the root's children, never asserted from one** — a child is
  a prediction and the present is observed, so what execution decides is which imagined world
  the real one landed in, and the cone under the match survives while its siblings die.
- **The claims a host issued are its demand** — a demand prediction was asked for as a new
  belief and found in the ledger the host already kept: a debt with a window is an occurrence
  about the window, and a drift that reads it drains the vessel ahead of the arrivals (#626).
- **A plan is placed at the instant of the root it was found from, never by subtraction from
  a deadline** — a bid placed at the crossing less the plan's duration landed in a round that
  had closed; the bid is taken while the round is open, and what waits for the instant is the
  claim's presenting, which the claim's own window places (#625).
- **What a search may see at a future instant is the instant's to say, and the reader names it** — a round row with no
  period was still open to a root standing hours ahead, and a bid was placed into a round that
  had closed; a round is a graph holding during its period now, and the rule never learned the
  time (#620).
- **A retraction is canonicalised like an addition** — a reading retracted without its type is
  two plain triples that cancel nothing, and a node's diff claimed the old value beside the
  new until the drift kept the whole node it took (#619); the bug hid because novelty needs
  only a difference, and a world claiming two readings for one key is still a different world.
- **A search is never handed a DESIRE** — what is pursued is a WANT derived from one, with a
  binding of its own; and the desire is not the law, because the region a want names, under
  never-newly-enter refused the very dose that repairs it: a replaced reading is a new node, so
  every standing violation re-read as newly entered (#618, measured before it was believed).
  It was "a desire is a ROOT", from when there were root desires and children derived under
  them; there is one kind of desire and wants are derived FROM it, so the word is retired
  wherever it meant one — `planner`'s `root` is the root WORLD a pass stands in and stays.
- **A round is the allocation under scarcity, and what makes buying available is a fact that
  holds at the instant the search stands at** — a host whose stock covers an ask grants a
  claim with no round, and a claim held, unlike a round, holds at every instant, so the plan
  is placed at the latest start; Acquiring on a want's instant alone placed the plan past the
  round a scarce host convenes now, and was refused.
- **A plan waiting at its last step is in progress** — held or placed, the world has not
  answered, and a search there found buying available on the very claim the plan was about
  to present and adopted it twice; only the round's close had hidden that.
- **A package's words are the package's, however long the kernel spoke them** — the ledger's
  vocabulary sat in `orexis:` because the ledger was the kernel's once, and the planner judged
  a debt met by naming its discharge itself; the host's desire carries the met-test in the
  ledger's words — the debt's own from #635 until the one derivation put it on the desire —
  `market:dischargedAt` is the market's, and the kernel names no word of it (#635).
- **A fallback is held to the case it was written for** — one want about everything a desire
  is about was for a desire UNMET now whose select yields no rows, and it minted a want under
  a met desire with nothing foreseen the first time the derivation ran without a judgment in
  hand.
- **A prediction is bands, and the width never leaves the rule** — a drift types the reading it
  predicts with every band the instrument's noise and the rate's spread reach, inside its own
  text; sensing writes what the drifts predict as graphs holding during their windows, the
  next reading's window first, and no kernel or sensing line adds a width to a centre (#642).
- **The agent keeps one timeline, and its clock may run fast** — two worlds ran their physics a
  hundred and forty-four times faster than the agent predicted by, because the stand-ins
  scaled their clock and the agent kept the wall's; every instant and stretch is in one
  timeline now, `clock.now()` is the only read, the pace is a deployment fact converted once
  where something sleeps, and no rule learned a unit (#646).
- **The core's word has priority, and a package speaks around it** — the keeper's row was
  renamed to "watch" to make room for a package's use of "expectation", before asking whether the
  package needed the word at all; it did not — sensing writes predictions, the first is what the
  next reading is held to — and "watch" was sensing's own, the instrument's, already (#640).
- **What ends by the clock is a graph with a period, and one sweep drops it** — four
  sweeps each knew its kind and each was a copy, a cooling row kept a timer a restart lost, and
  a claim past its window was let go by hand; a reader asking at an instant is handed no ended graph,
  upkeep drops whatever has ended on its tick and at boot, and what the ending MEANS stays
  the owner's, told `orexis:outdated` before the drop — which is where a debt's verdict is
  written, since the ledger keeps the verdict and not the want (#645).
- **The mind wakes on contradiction, not on time, and a set of bands is what a reading
  contradicts** — the actuator marked the region want on every reading and the dwell (#615) was
  weighed to slow it; a reading inside the bands the next observation was expected in leaves
  no mark now, one outside is a surprise the pass names, and a boundary crossed inside the
  set is the hysteresis a margin would have bought, without the margin (#632).
- **A step's band is the prediction from its landing, and a reading is compared once** — the
  keeper told sensing what a reading answering a step looked like and held a shape per step,
  and a node stating no value passed a constraint on a value; it tells the predictor the
  intended branch now, the ladder shows it from the landing, and one comparison at arrival is
  the verdict, met in the band and unmet outside it past the landing (#639).
- **What a plan changed is read off the signature, never off node identity** — a look
  re-stamps the node it finds and a purchase mints a new one, so by identity the look kept a
  pot from drying for five hours and the purchase could not stop the prediction emptying the
  barrel it had just filled; a key is changed when its canonical facts are, which is what a
  look's diff netting to nothing already said (#643).
- **A rule saying which world it reads is a package claiming something about every other
  package's actions** — `GRAPH $state` means a plan can change this and an unqualified pattern
  means it cannot, which depends on the whole loaded action set and is chosen from inside one
  package; climate's outside read carries the correction (#589), and the fix is precedence in
  the engine rather than a better guess.
- **What a fork may skip is bounded by what a rule may READ, never by what a step changed** —
  hanoi's Move walks a tower it has not touched inside `GRAPH $state`; narrowing took a padded
  solve from 58% of its time forking to 2% and was not taken, because a real pass forks for
  0.1% of it and reads for fifteen (#662).
- **A rule does not say which world it reads, and the list the runner builds says it instead** — naming it
  (`GRAPH $state` for a fact a plan can change, unqualified for one it cannot) is one package
  claiming what every OTHER package's actions can change, including packages that do not exist
  yet; climate's outside read carried the scar (#589), and taking the choice away deleted five
  doubled clauses and a UNION along with it, for no measurable cost (#666).
- **A/B on this bench is alternated within one session or it is not a measurement** — the Pi
  drifts about twofold between invocations, and two sides timed minutes apart made a change
  that does nothing read as a thirty-percent win (#666).
- **A repository is a collection of domain objects and not a store, and nothing here is one
  any more** — the convention was two instances, `Wants` and `Desires`, and both are functions
  over a store now; what a class still earns its keep for is owning a store whose nature is its
  decision (a MODALITY) or reaching the choir, neither of which is a collection. `Store` is
  infrastructure and keeps its name, and the layer above it is absent rather than mostly so.
- **A long-lived object and situational data about it is one shape three times, and only
  testimony is kept** — a desire and a judgment, an action and a step, a property and an
  observation; the observation is stored because it IS the premise, the other two are conclusions
  whose premises are stored and would outlive them, and the differences the likeness hides are
  cardinality (nine of eleven actions afford nothing, one afforded three), provenance
  (contributed, derived, received) and whether two agents may differ and both be right.
- **A graph's name is for eyes, and code relies on its classification alone** — an owner
  classifies what it writes when it creates it, a reader asks by class, and the name is a
  readable convention nothing depends on; boot used to type every per-agent graph by matching
  its name against a prefix its class declared, the planner and the projection named five,
  and asked which graphs could be renamed freely the answer was none — it is all of them now.
- **A graph class is named for the rows it holds, and a retired spelling may return with a
  different claim** — `RootsGraph` named the derivation's role for rows `orexis:Desire` already
  typed, the asserted graph said desire and held wants, and `orexis:DesireGraph`, retired as a
  modality class, returns as a content one, because a second spelling for a graph of desires
  would be the synonym the dictionary refuses.
- **A content class may not say how a graph arrived, and the cost of one that did was a second
  judging pass** — the asserted-desire class said its arrival in its NAME and the pursued class
  said nothing else at all, so no read could ask for *a graph of wants* and mean both the
  derivation's and a world's; the kernel read its own and compiled and judged the world's at
  read time, and `find_wants` alone answers for every want now. Both spellings are gone from
  this file too, because a retired term named in prose is the dangling spelling the rename rule
  refuses — `tests/test_layout.py` caught these two.
- **A graph is classified per kind it HOLDS, and a graph holding two kinds is two graphs** — one
  asserted graph was a graph of desires AND a graph of wants because four worlds put different
  content in it, which is a graph whose content no reader can predict; `graph/desire/asserted`
  and `graph/want/asserted` have one content class each, and `test_modalities` stopped
  exempting them from the rule it exists to state.
- **A want is one-shot and carries where it has got to; a desire has no stages** — recognized,
  planning, ready, pursued, done, failed, unreachable, each written by whoever DECIDES it and
  never inferred, because computing each from its own corner is how one question comes to have
  six answerers; a desire stands for the agent's life and is good or bad at the instant it is
  asked about, computed and stored nowhere.
- **A terminal state is an invariant, not an ordering rule** — the deliberator marked a want it
  had already reached `Done` and answered with no plan, and the caller, seeing no plan, wrote
  `Unreachable` over it, so hanoi solved its tower and reported it unreachable; nothing moves a
  want out of `Done`, and neither writer has to know the other exists.
- **Deciding a thing is finished and clearing it away are two acts** — every site that withdrew
  a want was guarded on how the want had been WRITTEN, so a want a world authored was withdrawn
  at none of them; `forget_wants` is garbage collection over whatever is `Done`, on the pass, as
  the keeper's sweep already was for what ends by the clock (#645).
- **Never count what a class answers for** — two tests asserted eight public graphs, which meant
  "as many as there are today" and went red over a vocabulary change they were not about; what
  they each meant was that the answer is not empty, and that a set is unchanged.
- **A case is held to the whole store it leaves, never to a reading of it** — the derivation's
  cases compared five things per want where a want writes nineteen quads, so a label, a link,
  a period or an owner could be wrong with every case green; a snapshot compared whole catches
  under-reporting, and a behaviour change is a diff regenerated by a flag and reviewed by eyes.
- **A read is handed a store and nothing else, because an agent id is another aggregate root's
  identity** — which store is the agent's decision since it owns them; identity travels as a
  query criterion, and the reads need none at all, since one agent, one volume means the store
  IS the scope.
- **A capability that asks for a derivation is not minting** — the ledger, having written a
  debt and what it predicts of it, calls `derive_wants` so a claim arriving is a want arriving
  and not a want on the next tick; what it writes is the instance and the prediction, and what
  stands afterwards is deliberation's, about that debt — and every other desire's, since the
  derivation is about all of them.
- **Nothing stands between a desire and a want** — `derive_wants` judges every desire at the
  present and at each foreseen instant and mints a want per cluster of what the met-tests read
  unmet, in one function and one contract; `scope_actions` writes the scopes at boot, so the
  derivation reads no action. It was two functions with a written judgment between them, and
  no caller ever took one half.
- **A want exists because its desire read unmet, so the same rows withdraw it** — a want the
  decomposition no longer produces is met, and running the want's own met-test to discover
  that asked twice what one pass had already concluded; withdrawal is against the WHOLE
  decomposition, present and foreseen, since a presented debt's rows do not mention the
  unpresented debt whose want was minted at its lapse, and dropping on the present alone took
  it. A want a plan is walking is kept whatever its desire reads.
- **A possible world is kept, and its diff was a memo** — a world's graph was dropped once
  its node was expanded and re-made from the nearest kept ancestor, so a node carried the two
  lists its step's rules had answered; two measurements retired that, since a world's readings
  are 2 quads on the courier and 26 on the greenhouse against the ~5,000 shared quads a pass
  copies once, and the diff is derivable anyway — it is what a step's own rules produce from
  its parent, and the step's row already names the action and every binding they take. The
  memory argument was made when a node ALSO carried a flat rdflib copy of the whole world
  (#481), and did not outlive it.
- **The one function over TWO stores is the filling of a possible world** — `init_imaginarium` takes
  the beliefs and an empty store the caller made, copies every public graph whatever its
  period and the catalogue with them, and hands the second back; everything that happens to
  that world afterwards happens to it the ordinary way, so this is the seam rather than a
  wrapper. Narrowing what crosses — four named graphs, or the graphs of one scope — was
  measured at 10.4 ms against 0.6 on a pass costing over a second, and fails silently: a
  pattern reaching a graph nobody copied returns an EMPTY RESULT, not an error.
- **A function over the store is handed the engine and nothing else** — `derive_wants` and
  `scope_actions` take `pyoxigraph.Store` and no wrapper: which graphs they read they ask of
  the catalogue in their own texts, whose a desire is they read off `orexis:holds`, and the
  present is the clock's; the wrapper caching a view of the store cannot see a write it did
  not make, so asking it for the engine (`Store.engine`) is what makes it forget.
- **A met-test asked by band names which way it broke, and tests no topology** — a reading is
  the band it is in, so a desire says *it should be inside* once per way of failing and each
  block declares its side, which the WANT carries (`orexis:violationIs`: below, above,
  unmeasured, stale) because that is what decides the repair — a look answers the unmeasured
  one and no act of any kind does. A test that walked the topology instead would be satisfiable by
  moving the sample off the subject or by re-pointing what counts as ideal, which is the goal
  repaired by editing its own premises; a structural repair stays reachable because the
  closure walks back from what the want reads to whatever changes it.
- **One module reads predictions, and it takes them as given** — `judging` enumerates the
  states, the present and every instant a prediction reaches, and runs each desire's met-test
  at each; what it reads is a WITNESS, computed where it is needed and stored nowhere, so the
  minting and a crossing get the same answer from the same code rather than from two paths
  that could disagree.
- **A derivation asks nothing the met-tests do not answer** — a foresight filtered a foreseen
  failure the reading already dated, and was two states in practice, unbounded and absent;
  how far ahead the agent sees is the horizons each drift predicts at, and the pick, the
  extension point and the kernel property are gone.
- **A partition of the vocabulary belongs to the store, not to an agent** — the scopes are a
  function of the actions the store holds and the derivations loaded, so every agent reading
  one store computes the same one and there is nobody to name it after; genesis puts the
  derivations' read and write predicates in the store beside the actions, which were there
  all along.
- **What was foreseen may arrive early, and the present outranks the instant** — a want
  minted at a predicted crossing or lapse says *hold at T* and its plan is placed to land at
  T, so when the holder presented an hour early the serve was placed at the deadline; a
  cluster unmet now whose want still names an instant is re-minted at none, same name.
- **One function mints every want, and a package writes instances and predictions** — a desire
  is one and universal, its met-test's violation rows are the instances in trouble and each
  prediction's start is when, a want is minted per scope of them, and the ledger's own
  decomposition never had a runtime form; the per-instance DESIRE level was drawn and
  struck, because the instance is the want's grain.
- **A want states no time semantics of its own** — the KIND is its type, the INTERVAL is its
  graph's period, the INSTANT is `orexis:holdsAt`, and the FAMILY a reader filtering on a binding
  actually wanted is the graph's classification; the binding property said all four a fifth
  time, was computed from whether an instant was known, and the planner its own comment named
  as its reader never branched on it (#681).
- **A kind is a type, not a binding** — the always-binding had six readers and every one asked
  it which KIND a node was, while the planner it named as its reader never branched on it; a node
  could be a desire by type and a want by binding at once, which three shipped worlds were, and
  neither collection could see them.
- **`orexis:Want` is not a subclass of `orexis:Desire`** — the closure is materialised once at
  genesis and a want is minted long after, so the entailment never reached one and every writer
  hand-wrote both types; what the axis actually did was make `?d a orexis:Desire` match both
  kinds, so a collection of desires had to filter on a binding to find its own contents.
- **Standing versus occasioned is the axis, and who wrote it is provenance** — three worlds
  ratify a WANT directly, authored and standing and handed to a search, so declared-versus-derived
  was never the distinction it was written up as.
- **A desire is declared and a judgment is made** — the class called `Desire` carried an
  urgency and an expiry, was built fresh by whichever capability held the region want and was never
  written down or read back, while the row a package's rule writes at genesis had no type at
  all; naming the second thing let the first become data. The name has since gone the way of
  the thing: nothing stands between a desire and a want, and what a judgment carried — the
  reading and which way it broke — a WANT carries, made fresh where it is made fresh and
  stored where it is stored; the urgency it also carried is gone, and the line below says why.
- **Nothing ranks a want before the search that could rank it** — a want carried an urgency
  four packages each computed their own way, and `Deliberator.pursued` plans for EVERY want it
  is handed, so the rank only ever decided which was searched first; what would compare a
  thirsty fern to an overdue debt is what their plans cost and how long they take, which is
  the search's answer and no contributor's.
- **A read over stored rows is handed a store, and one over contributed answers is handed the
  agent** — `find_wants` reads graphs so it takes somewhere to search, `Pursuing` asks the choir
  so it must reach the choir, and the asymmetry is what tells the two kinds of read apart.
- **The function that decides a thing owns writing it, and a read only reads** — `Wants`
  carried `save`/`delete_by_uri` beside the module functions the derivation called, plus
  `on_saved`/`on_deleted` so a write could announce itself; the announcement had one live
  producer and one live consumer and both were rebuilding the desire projection, and the
  collection's own writers had no caller but their tests. A want's graph, its catalogue row
  and its period are decided where the want is, and whoever wrote says what changed.
- **Two readings of one met-test are not a duplicate when the compiler, the source and the
  cache all differ** — the derivation wants WITNESSES from the graphs of desires and wants and
  caches nothing; the kernel lifting a ratified want wants a BOOLEAN from public knowledge,
  where a package's shape lives, and caches per want because an asserted one cannot change
  while the agent runs. Merging them was attempted and refused on all three counts.
- **A synchronous twin of a pass is a second pass, and it drifts** — `deliberate_on_gaps` was
  what a test called to have the consequences before it asserted, and it read what the agent
  was considering DIRECTLY where the real pass derives first; so every test went down a path
  production does not have, missing the one step the seam was built to add. One pass with two
  endings (`consider` marks, `consider_now` takes) sharing the generator that derives is what
  stops that: the difference is where the work happens, and nothing else can differ.
- **A pass begins in one place, and judging happens once in it** — the container re-ran a
  want's own met-test to correct a row gone stale, which is asking twice what one pass had
  concluded; it went stale because the derivation ran only where a package wrote something a
  desire reads, so what fixed it was not a better re-judging but `pursuit.consider` deriving
  every pass — the third reading above, and the reason it existed, both gone with the seam.
- **The layer that waits does the waiting, and a package has ONE way in** — deliberation kept
  a `Timer` and its landing reached back into the container's collection, so the two reached
  into each other and no single place was where a pass began; the container holds the clock
  now and calls `pursuit.consider`, and what a want IS stays in the package that has the word.
- **Considering and pursuing are a pass apart** — `consider` derives what is wanted and hands
  what may be acted on to the search, `pursue` plans one of them and commits, so a want nobody
  may act on yet is CONSIDERED and never pursued; the collection was `Pursuing` while the
  container held it and the pass had no name of its own.
- **A want somebody else sourced is still an INSTANCE under a standing desire** — a call was
  lifted per call by `hosting.desires()`, the one want here no derivation minted, so it had no
  provenance, no graph and no period, and the planner could judge it only by asking a
  capability how unmet it was; a host holds *no unanswered calls* over its venues now and the
  call is the row that desire is about, which is the shape the ledger's debts already had.
- **A criterion is an argument, never a name** — `Wants` was five finders over ONE query with a
  `where` clause swapped, three of them called by nothing but their own test, because the Spring
  Data spelling put each criterion in a method name and so charged a name per combination;
  `find_wants(store, desire=…, derived=True)` says at the call site what `find_first_by_desire`
  hid, and the one distinction worth a name of its own is the answer's SHAPE — a page against
  one-or-None.
- **A model is a Python type only where something READS its fields** — `Want` is one:
  nineteen modules import it, capabilities subclass it to add their own, and its state, its
  instant and what it is about are all read. `Desire` was not: it was built from a query and
  discarded, because the two callers wanted a boolean and a uri and the third wanted uris, so
  the reads answer those and there is no type. A class that carries a uri out of a query is
  the store duplicated in Python for the length of one expression.
- **A model gets its OWN file when it is cheaper alone** — `want.py` imports nothing but the
  standard library, so naming the type costs its nineteen importers nothing; folding it into
  `wants.py` would make every one load progression's clock, ontology and store (#455, the
  reason sensing's rows sit behind a touch).
- **An update takes no dataset** — `Store.query` is handed its graphs per call, which is the
  door, and `Store.update` names them only in its own text; so what chooses which graphs are
  the world at an instant is Python or a materialised view, a derivation that needs neither
  is a rule, and a search — an order, a budget, a stop — is neither and stays Python.
- **Deliberation is on triples, and a number is not special** — how a domain describes its
  world, exact numbers, ranges or classes, is decided inside the domain, and its actions'
  preconditions and effects are described the same way; the core compares triples and
  interprets no literal, and progression sizes the act when it is taken. A partition and an
  interval were both built into the core and refused on reading.
- **One graph describes every graph and itself** — what a graph is, whose it is, how it arrived,
  when it holds and what loaded it were three meta-graphs each reader named by kind; the
  catalogue is found by its own row, `a orexis:CatalogueGraph`, genesis alone spells its name
  because genesis creates it, and it is neither public nor the agent's own, so a mention of a
  graph is never a fact in a world.
- **A reader states the kinds it reads, and the store decides nothing** — four doors each
  assembled a dataset by a rule of the store's, and which graphs were the agent's own was five
  classes it excluded and a tree it walked, so a package chose its treatment by a superclass
  and a caller never said what it read; a query is handed its graphs now, `graphs_of` answers
  by kind and instant, every row carries every kind, and the union of everything was refused
  as the default because it reads every sibling world and next hour's readings as the present.
- **A rule concludes and never deletes, and what replaces a revision is its source
  rewritten** — SHACL 1.2 Inference Rules and the sovereign's instinct agree; the revisions
  of a graph live in a graph of their own, derived from it, and go when it goes, so no rule
  ever names what it takes away; the rules are the draft's, adopted as they stand — a rules
  graph, a rule set, SPARQL rules by layer and order — with nothing of ours on them
  (`agent/belief/revise.py`).
- **Any belief is accepted, and revised; validation was built beside revision and struck the
  same day** — every new graph held to the packages' shapes and forgotten whole on a
  violation; belief revision keeps the new information, dropping testimony over a shape is a
  gate wearing revision's name, and a law's objection to a graph is a revision a rule can conclude for the mind to want repaired.
- **A state that served a gate goes with the gate** — a proposal, a graph classified as not
  yet believed until `believe` retyped it, bought only that a graph was never seen without its
  revisions; a graph with no catalogue row is already invisible to every reader, so the
  writer concludes and then classifies, and a class, a property, two acts and a page said
  nothing the row's absence did not.
- **Revision's ceiling is a budget in rule executions, and a source the budget cuts short is
  continued by the next pass** — `revise` capped its own iterations at a number the module
  chose, where the search's ceiling is the container's in the unit it spends; a cut keeps what
  was concluded with the row saying so, the deliberator re-queues such rows at boot, and a
  rule set that never settles spends a budget every pass and is reported rather than looped on.
- **Sensing observes and says when a sensor has gone silent, and prediction is a package of
  its own** — `received` writes one `sosa:Observation` per key with its number, holding until
  the next is due by the sensor's `ssn-system:Frequency`, `missed` answers the readings fallen
  due on the container's tick and says `sensing:silentSince` of a sensor silent past a limit of
  its cadences, and the side is a revision the three rules sensing ships conclude; no band,
  no side, no want, no verdict on a prediction is sensing's own write. `agent/prediction/`
  bisects every crossing of a range bound between the ladder's rungs and writes one prediction
  per stretch, finds the observation by the kernel's kind and `sosa:madeBySensor` and imports
  nothing of sensing — a stretch already says when a rule's result changes, and the planner's
  re-root tells a surprise — and a range is SSN-System's as the world states it, nothing minted.
- **Sensing speaks SOSA and SSN, and declares only what they lack** — a sensor
  `sosa:observes` a property and `sosa:isHostedBy` what it is mounted in, which is the
  observation's key, and the layer's own words are the observation graph's kind, the silence,
  the three sides and the pipeline's — a codec and a scaling as families, a sensor's binding to
  a member of each, JSON and identity as the members that ship, and the pointer — since neither
  standard says how bytes become a number, while the drift (a value moving by itself, which no
  `sosa:Procedure` is) is the prediction package's one word;
  `polls`, `monitors`, `samples` and `senseMode` were SSN restated, `atHorizon` had a drift
  declare the scan's reach, and the wiring module that read them had no caller, so the ladder
  is sensing's, a transport hands `received` the sensor's IRI and bytes and sensing knows no
  transport — the contract a member answers is the family's own, `Transport` at
  `agent/transport/` — and the layout test holds every `sensing:` word the tree speaks to the
  ontology beside it.
- **The transport speaks MQTT4SSN, and a topic is named by the filters that match it** — the
  ontology that extends SSN and SOSA with the protocol in the OASIS terms is adopted as it stands,
  as SHACL's rules were, and `agent/transport/mqtt/` declares no word of its own; a sensor
  `mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and since MQTT4SSN
  gives a topic no name but the `mqtt4ssn:hasFilterPattern` of a `mqtt4ssn:TopicFilter` that
  `mqtt4ssn:matchesTopic` it — and a topic name is itself a valid filter — the agent subscribes by
  the pattern and publishes a command to one with no wildcard; what it listens to is derived from
  what it acts for, and the broker's address stays in the environment.
- **A world's words are its own or a domain's it imports, and the runtime boots from its files** — Hanoi's puzzle was a
  tool package with an ontology and one action; in 0.2.0 the puzzle is the domain
  `domains/hanoi/` and `world/hanoi/` imports it beside its desires and state, `agent/runtime.py` reads the kernel's
  T-Box, every package's and the world's as graphs of their own and derives the closure into
  one more, and the world's tests live with the world, since the target state is no global tests.
- **The runtime stops when no desire is held and every want is reached** — a desire is universal
  and asks at every instant, so an agent holding one runs for as long as the process does; a
  want is one-shot, and a pass that weighs one met in the present ground withdraws it from the
  imaginarium and the beliefs whoever authored it, so Hanoi's mover, holding a want and no
  desire, exits once the tower stands. Wants standing with nothing walking is either a search
  the budget cut short, which `planning:Exhausted` says and the next pass continues, or
  unreachable, which an agent holding no desire exits saying. A pass at the same instant
  as the last re-lays the present under its name and the search starts over, so a clock that
  does not tick is a test's mistake and not a runtime's.
- **A document says which graph it is, and the file's name is for eyes** — a Turtle file is one
  graph named by its own IRI and `<> a orexis:StateGraph` says what it is, a TriG file names its
  graphs and says so in its default graph, and the loader moves those rows to the catalogue and
  adds the arrival and the owner, which a document may not state; the runtime knew five file
  names and one vocabulary graph before, and now every ontology and rule set is a graph of its
  own that a lived-in volume reads again at boot, so updating one is editing its file; and no
  `owl:Ontology` header, since nothing read one — a package's prose about itself is a comment.
- **A pass weighs its grounds, and a candidate is weighed where it is taken** — the pass's own
  loop weighed every unweighed pair, so the candidates a budget cut left untaken were weighed
  and never offered to the expansion that takes them; the courier's corner at sixteen a pass
  emptied its frontier short of the door and read EXHAUSTED for ever, while Hanoi's cuts had
  happened to leave nothing behind.
- **A vocabulary two worlds speak is a domain, and a world imports it** — `domains/<name>/` holds
  the words, the actions and the shapes a desire points at, and a world says
  `owl:imports <../../domains/hanoi/ontology.ttl>`, which resolves to the `file:` IRI the graph is
  loaded under, so the import names the graph it brings and the boot loads only what a world
  asks for; the shapes are `orexis:ShapesGraph`, their own kind, because crossing every ontology
  graph into the planner's view cost thirty times crossing the desires.
- **A graph of actions is an `orexis:ActionGraph`, and the planner reads actions from those
  alone** — the kind was 0.1.0's and the 0.2.0 census dropped it because nothing asked for it,
  so Hanoi's actions were typed the bare `orexis:PublicGraph` and `admit`, `take` and
  `footprint` read every public graph to find them; named for what it holds, and asked for by
  the three reads, it is a term somebody reads.
- **The search runs no rules, so a reading's revisions travel with it and an effect speaks the
  concept they conclude** — a side is what the rules concluded of a reading, in a graph derived
  from the reading's; the imaginarium takes every graph derived from what crosses, the present
  ground holds the readings and their revisions, a prediction is laid with its own, and the
  executor answers a step over both, so a dose that predicts the soil `inside` its range is
  answered when the next reading is revised to it (`store.revisions_of`) — a revision is a
  belief and a drift's prediction, derived from the same observation, is not, which is what
  keeps the foreseen reading out of the present.
- **0.1.0 is not started any more, so it is amended, not copied** — a package 0.2.0 needs moves
  into a domain and changes there, and the 0.1.0 suite that built on it is switched off in the
  gates rather than propped up; the four files in `tests/` that read the whole tree still run.
- **A step is sized when it is taken, from the present, and the search only says the side it
  reaches** — a dose's effect is the soil coming to be inside its range; `execution:command` on the
  action is run over the beliefs as they stand when the step is taken and answers the actuator and
  the payload, the dose's size from how far the reading is below the middle of the range, and the
  runtime sends it through the transport's `actuate`.
- **A world speaks for its readings' revisions** — `world_at` hands a rule every known graph but
  those a world speaks for, and once a ground carries the sides beside the readings, the revision
  graphs are among them: read beside a possible world, a dry reading's `below` outlived the dose
  that answered it, and the greenhouse's search offered the same dose for ever.
- **The plant's surroundings are one domain** — water and climate were two 0.1.0 packages, and the
  soil's moisture, the air's temperature, the source and the heater are one `climate:` vocabulary
  in `domains/climate/`; actuation is the other, the devices and the dose.
- **A broker's address is the world's to state and the agent's to be told** — MQTT4SSN names a
  broker and no port, so the world says `schema:url` on its `mqtt4ssn:Broker` and the operator's
  tools read it to run the broker and write each agent's environment; the agent reads only its
  environment, as the transport's principle has it, and `orexis-agent` runs the 0.2.0 runtime.
- **Signing is between agents, and an agent trusts itself** — a signature proves to a device that
  the agent asking for an act was authorised by another, which is the market's case; an agent
  dosing its own bed through its own pump has no second party to convince, and the broker's ACL
  already admits only the holder to its devices' command topics, so 0.2.0 signs nothing until the
  market returns (authn-authz-capabilities).
- **The 0.2.0 kernel's T-Box is what the tree reads** — `agent/ontology.ttl` is extracted from the
  0.1.0 file by a census of query texts, term constants and the packages' vocabularies, closed
  over what each declaration reaches; a mention in prose is not a read, and a term nothing reads
  is annotation and goes.
- **A belief kind enters through `propose`, and a package's working graph is not a belief** —
  the belief package's layout test holds every writer in the tree to the door, and what
  bypasses it is what no rule reads as the world.
- **A prediction is a diff, and only a ground has applied it** — the derivation judged a
  foreseen instant over the state graph beside the prediction holding then, so a tank low now
  with a forecast refilling it read unmet for ever while the search beside it read the grounds
  laid for exactly that; one reader answers both now (`world_at`), refuses a store with no
  ground, and the case that would have caught it is in the suite.
- **What a pass worked out about a world for a want is a WEIGHING, and the frontier is a
  query** — a heap of Python nodes was the open list, so no pass could be continued and "no
  candidate" was a boolean; a world's row says what is true of it whoever asks, a weighing per
  want says met, open, expanded, and a candidate passed over is weighed too, which the
  predecessor had and the first cut of the planning package lost.
- **A module named for an act exports that act alone, and a module named for a thing may
  answer several questions about it** — `planner.py` held the loop, the frontier, the
  met-test and the read that hands it the wants, six hundred lines of which a reader wanting
  the pass needed a hundred; `expand.py` is where `expand` is, and the layout test holds the
  planning tree to it, with the nouns listed.
- **A desire weighed in a ground and a want weighed in a possible world are one judgment at
  two grains** — a ground is a world, a want is a desire at one instance, and the met-test's
  report in that world is what both read; the search reads whether it has a row, the derivation
  reads the rows across the grounds, which give each its stretch. The derivation kept a
  witness dataclass for what a weighing already was, and `planning:Weighing` carries its
  `planning:violation` rows now for either.
- **A function of the planning package starts in the store and ends in it, and takes the
  names of what it is about** — `weigh(store, want, world)`, `take(store, candidate, me)`,
  `expand(store, want, world)`; what one act needs from another it reads off the rows the
  other wrote, so a candidate and a witness are rows and not values in flight, and the price
  is measured per pass rather than argued.
- **Public is public to the package, and public means tested** — outside `agent/planning/`
  the one name the tree imports is `Planner`, and every module with a public function has a
  test named for it, an act over the store by a case directory; the layout test holds both,
  and ten modules had no test named for them when it was first written.
- **The planning package is a star, not a chain** — the `Planner` sequences the acts as its
  own methods (`plan`, `search`, `expand`), an act calls no other act, and what one needs of
  another's work it reads off the rows the other wrote; the pass called the search, the search
  the expansion and the extraction, the derivation the weighing, and what a pass did was spread
  over every file it went through. A primitive two acts share is the store's (`fork`).
- **A read that finds the catalogue by its row and then asks OPTIONALs inside that group is
  evaluated per named graph** — `GRAPH ?cat { ?cat a orexis:CatalogueGraph . OPTIONAL … }` cost
  0.5 to 1.0 ms a read on a store of sixteen possible worlds where the same read over the one
  bound graph cost 0.1 to 0.2; a pass asks the store for the catalogue's name once
  (`catalogue_of`, remembered) and splices it, which is asking and not spelling — and spelling would buy nothing more, since every
  `?cat` replaced by the constant at the engine's door ran the three-disk bench at 163 ms
  against 168, inside one session's noise. And a read asked per iteration is sized by what the iteration opens: `unweighed` narrowed to one want
  and one world took the three-disk bench from 496 ms to 158.
- **The imaginarium outlives the pass, and the present is identified in it by hash** — a
  planner called every minute imagined the same cone afresh each time and handed down an
  intention per pass for one want; the Planner keeps an imaginarium per scope now, `reroot`
  finds the world of the last pass whose `orexis:hash` the new ground repeats — the old
  present when nothing happened, a child when a step landed as predicted — hands its
  candidates to the ground, re-stamps the cone's instants and rebases its spent, and drops the
  rest; three disks re-planned after the first move in 34 ms against 132 fresh, and a minute
  later with nothing happened in 42 against 156. A surprise matches nothing and everything
  goes; a name is never trusted, so a re-laid ground's old cone goes too.
- **A want an intention is walking is neither searched nor handed down again** — the world has
  not answered yet, so re-deciding is the executor's verdict on a step and not the clock's;
  `Executor.walking` is the one read, the Planner skips those wants and keeps them from
  `withdraw`, and `publish_plan` hands no plan down for one, since the plan graph of an earlier
  pass is still in the kept imaginarium.
- **What crosses into the imaginarium is taken back before it crosses again, and what the
  store made for itself stays** — a refresh forgets every graph of a crossing kind the store
  did not make (grounds, worlds, plans and the derivation's own wants are its), so a reading
  replaced is replaced and a forecast swept is gone; laid on top, the old facts stood beside
  the new.
- **The estimate rides on the weighing, and the frontier is A\* by reading it** — a want's
  `orexis:estimates` select, the package's promise of what is left in the unit the search
  spends, is run where the world is weighed and written as `planning:remaining`, so ordering
  by spent plus remaining costs the frontier nothing per iteration and the first achiever
  bounds the sum; the courier's corner delivery went from exhausting a budget of 128 to
  arriving after 45 candidates, hanoi from 56 to 50, and a want with no estimate is
  uniform-cost, because an absent figure reads nought and a broken select writes none.
- **A search the budget cuts short is finished by the passes after, and the passes together
  are the one-shot search** — the budget is each call's and the frontier is rows, so three
  disks at twenty a pass read EXHAUSTED twice, hand nothing down, and reach their seven moves
  on the third pass having weighed the fifty one pass with room weighs, not one more; a
  ceiling on compute per pass is then a ceiling on latency, and what is spent in all is the
  problem's.
- **A variable in predicate position writes what a `VALUES` block in its own text binds it
  to, and anything only where nothing bounds it** — the range of a filling is the
  precondition that enumerates it and a range declared beside a text is a promise nothing
  holds the text to, so the one range the scopes honour is SPARQL's own, in the text the
  engine runs; `footprint` read every variable predicate as anything before, which under a
  derived fork would have copied the whole store per world for a two-valued predicate.
- **The executor owns the intentions and alone writes them, any plan among them is
  scheduled, and the two threads are two doors** — the timekeeper's pass is `tick` (the head steps due, by `execution:notBefore`,
  handed to the queue) and the executing thread's is `drain` (each step taken, its
  `execution:Act` written, `execution:by` moved, the last step resolving `done`), so a test
  drives a plan through at instants it chooses and the threads call the same two; the
  keeper was renamed rather than kept beside it, since one store has one owner, and what
  taking a step IS today is saying its name.
- **"Ledger" is the market's word, for the book of what an agent owes, and the intentions
  are called the intentions** — the 0.1.0 keeper's intention ledger and the ower's ledger of
  debts shared one word with no page for either, and a reader of "the ledger's debts" beside
  "the ledger is walking a want" met two things; `agent/` says intentions, intentions store
  and execution's own words now, and leaves the word to the package that has no other.
- **The world moves an intention, and the executor only says what happened** — a step carries
  the diff the search planned on (`execution:predicts`, the canonical facts of the world it
  reaches less the one it leaves) and a taken head waits at its `landsAt` for the present to
  hold every addition and none of the retractions, over the readings; then `execution:by`
  moves, and past the landing by the patience with no answer the intention is `failed` and
  the want is the search's again. A pure simulation has nothing to answer with, so an action may
  be FICTIVE (`execution:fictive` on its row, carried onto its steps) and the executor writes
  its prediction into the readings itself — hanoi's physics is its own effect — and that is
  the feedback a plan promoted to a method would be judged by.
- **A `NOT EXISTS` is evaluated per row from its FIRST pattern, so the bound variable goes
  first** — `?x a planning:Weighing ; … ; planning:weighs ?about` scanned every weighing per
  candidate and cost 74 ms on a kept three-disk cone, answering nothing; `?x planning:weighs
  ?about ; …` costs 4, and an act that means to admit a world it already admits is idempotent
  by FILLING, not by name, since a candidate handed on by a re-root keeps the name it was
  made with.
- **A prologue goes at the head of a joined update, and the engine refuses one after `;`** —
  every retraction carries its package's `PREFIX`, so joining the copy and the retraction into
  one text skipped every retraction, at the log level and green; hoist the declarations, and
  run apart the two texts that spell one label two ways.

## The rules the code lives by

1. **Code may reference T-Box terms; never an instance.** `term("Subscribing")` is fine;
   `"supplier"`, `"sensors/fern/moisture"`, a world's `:world` node are not. The single exception is the one
   identifier a process is handed at boot: its own agent id. Everything else is discovered from
   the graph. See [capability-packages](knowledge/decisions/capability-packages.md).
2. **A capability is a named ability with interchangeable implementations. A DIRECTORY IS A
   PACKAGE, and a package may hold several.** The ability is a **family** — the slot; the
   implementations are its members. `sensing:SensingCapability` is a family and `sensing:Subscribing`
   and `sensing:Listening` are two ways of having it, chosen by what the hardware can do. That is the
   shape to reach for: a capability worth naming is one where the *how* could differ. Reviewing
   your own settings by strict rules or by asking a model is one ability with two
   implementations; pay-as-bid and uniform-price are one auction with two. Where nothing could
   differ, you have a function, not a capability.

   The two are not the same axis, and saying "a capability is a directory" hid that.
   `packages/orexis-capability-market/` provides three — bidding, hosting, and the matching family — and it is
   one package. **What isolates a capability is `PROVIDES` and its term, never the directory
   boundary**: `hosting.py` asks `agent.provider(BID_MATCHING)` and never learns which member
   answered, so uniform price landed without touching a line of it. A directory is how a package
   is FOUND and how one is deleted. See
   [a-package-owns-its-namespace](knowledge/decisions/a-package-owns-its-namespace.md).

   **There is ONE package tree and one mechanic.** `packages/orexis-<family>-<name>/` holds whichever
   of `ontology.ttl`, `shapes.ttl`, `rules.ru`, `actions.ttl`, `review.rq` and Python it wants — every one
   optional, and an omission is a statement. Two files are NOT optional: a `pyproject.toml`,
   because **every package is its own distribution with its own dependencies**
   (`orexis-<family>-<name>`), and the `__init__.py` manifest. A dependency is declared by
   whoever imports it and `tests/test_projects.py` holds each list to the imports in both
   directions — a missing one and an unused one both fail. `packages/` and `packages/<family>/`
   are PEP 420 namespace portions belonging to no distribution, which is what lets a package
   from another repository join the same import root. See
   [every-package-is-a-project](knowledge/decisions/every-package-is-a-project.md). `packages/orexis-part-esp32/` is an ontology and nothing
   else because a board has no behaviour a runtime could load; `packages/orexis-capability-market/` has
   all of it. Neither is more of a package than the other, and that is the point: a plant, a
   part and a capability are the same kind of thing to the loader.

   A package may declare **its own namespace**, in its `ontology.ttl` and mirrored in
   `terms.py`. `agent.loader` reads every project namespace off the ontology that declares it,
   so `market:` reaches a query without `store.PREFIXES` learning the package exists. Nothing
   lists them — `agent.loader` finds them one level down, and the FAMILY is the second segment of
   the package's own NAME — which is also its distribution name and, with underscores, its
   module — so `kind` distinguishes a plant from a part without a registry and without a second
   place to state it. `PROVIDES` in `__init__.py` is how an implementation registers, and its absence
   is what makes a package knowledge-only. A package implements the terms IT declares —
   which is what lets imports follow grants: a runtime imports only the packages its own
   capabilities name (#216) — and, beneath the grants, a REQUIRED injection pulls the package
   providing its key into the load set, needs after needs, while a soft one (`X | None`)
   injects only what is already there and loads nothing (#455). Adding one is adding a directory. Packages never
   import each other's Python ACROSS a layer: ask `agent.provider(family)` or contribute via
   the choir's extension points (`desires`, every ACTION, `notices`, `series`, `quiet` — and, in sensing's
   words through `agent.ask`, `annotate`, `bounds`).
   The one ordinary import is DOWNWARD, of the contract of the layer beneath: a family's plug-ins
   import the family's contract — `packages/orexis-codec-*`, `packages/orexis-scaling-*` and
   `packages/orexis-transport-*` import sensing's `Codec`, `Scaling` and `pointer`, because those
   are the contracts they exist to implement (see
   [sensing-owns-the-reading-pipeline](knowledge/decisions/sensing-owns-the-reading-pipeline.md))
   — and THE KERNEL IS THREE LAYER PACKAGES in the same tree, each importing only the layers
   beneath it: the reactive loop (`packages/orexis-agent-reactive/`, importing nothing of
   ours), progression (`packages/orexis-agent-progression/`, the ledger and the store
   engine, the lowest layer that persists) and deliberation
   (`packages/orexis-agent-deliberation/`, the belief base, the desires and the search). There
   is no floor beneath them: what a lower layer has to say upward it says as an EVENT through
   the choir. `agent/` is the CONTAINER that assembles them and may import all three; nothing
   imports it from below, and a capability may import any layer's contract (see
   [a-layer-is-a-package-and-need-loads-it](knowledge/decisions/a-layer-is-a-package-and-need-loads-it.md)).
   The order is spelled once, `LAYERS` in `tests/test_projects.py`, and `tests/test_layering.py`
   holds every arrow, finding each layer by its family.
   **A layer with words of its own owns a namespace** (#529) — `progression:` for the ledger,
   `deliberation:` for the trace and the budget, each declared in the layer package's own
   `ontology.ttl`; the reactive layer has no vocabulary — and a term one layer reads and writes
   carries its prefix, so a query says which layer it speaks for. What every layer and every
   package writes in — `orexis:Agent`, `orexis:Action`, a want's grammar, the choir's extension
   points — stays `orexis:`, and a file naming a HIGHER layer's prefix fails
   `tests/test_layering.py` as an upward import would.
   A transport is also a capability the fact of its bus grants — how the agent reaches its
   society, connection, delivery loop and watchdog in the transport's module, reached through
   the choir (`subscriptions`, `handle`, `send`) — and the kernel has no mailbox (see
   [the-kernel-has-no-mailbox](knowledge/decisions/the-kernel-has-no-mailbox.md)).

   **TWO KERNEL TREES, FOR NOW.** `agent/` is Agent 0.2.0 — the store over the engine, the
   belief, sensing, prediction, planning and execution packages and the MQTT transport — and
   is what `pytest` runs and, since 2026-09-25, what `orexis-agent` and the image run; `agent_old/`
   is the 0.1.0 container this section describes and the loader's kernel (`assembly/loader.py`
   names it by path); it is not started any more, its
   suite in `tests/` is switched off in the gates, and its packages are amended into 0.2.0's
   domains rather than copied. Every `agent_old/<file>`
   below is that container's; the two trees meet only through the packages' ontologies,
   which both read.

   **`agent/` is the kernel that loads them, not their home.** Capability Python used to live
   under it, so the tree itself showed which of it a runtime loads — it does not show that now.
   `packages/orexis-capability-market/` and `packages/orexis-part-dht11/` look identical, so the CONTRACTS
   carry the boundary alone: `lint-imports` holds `packages` away from `onboarding`, and the
   `Containerfile` decides what reaches an image by naming two trees and not a third. Both were
   always the real enforcement; the layout was a reminder, and the reminder is gone.
3. **Nothing in `infra/` is world-specific.** It holds the services and what is true of the
   installation: the broker image, the installation CA, Grafana's material, the admin token. A
   world's broker config, its ACL, its certificates and its device credentials live with the
   world. Also: **no `.env` at the repo root, because nothing there is true of every world at
   once.** `infra/.env` says where the shared series store is — the URL and the org, and nothing
   secret, because that file is handed to every agent container. What an agent may *do* with
   the store and the bus arrives as its own credentials, minted per agent into
   `world/<name>/secrets/` and mounted into that container alone. The admin token lives apart
   from both, in `infra/secrets/`, and no agent ever holds it. See
   [series-and-bus-isolation](knowledge/decisions/series-and-bus-isolation.md).
4. **There is no shared store.** The world is TTL files; each agent builds its own belief base
   at boot and holds it in a volume of its own, so isolation is structural rather than
   enforced. An agent is told its id and given one world, mounted — it never learns that other
   worlds exist. See [where-the-belief-base-lives](knowledge/decisions/where-the-belief-base-lives.md).
5. **There is no config file for the model.** Topology lives in the world graph, desire and
   limits in each agent's own beliefs, both authored in `world/<world>/`. Deployment facts
   (service URLs) are environment, because they are not beliefs anyone holds. See
   [world-graph](knowledge/decisions/world-graph.md).

**What an agent BELIEVES about all of that is settled by one test: model it only if a belief
about it would change which plan gets selected.** Everything else is telemetry — logged and
reported, never believed. Infrastructure reaches belief only through a named projection; anything
the interpreter already knows is COMPUTED (what stands, what I can do, how stale this is) and
never asserted; what comes from outside is stored; self-telemetry gets bands, not raw values;
reflection caps at one level; and beliefs about other agents stay first-order — what they DID,
never what they believe. See
[model-it-only-if-a-plan-would-branch-on-it](knowledge/decisions/model-it-only-if-a-plan-would-branch-on-it.md).

**And a SECOND axis, orthogonal to that one: the agent stack** — network, transport,
translation, the belief-revision seam, mind — sliced by representation rather than by timescale.
The transport has no position on the cognitive axis at all; an infrastructure failure becomes a
belief only by explicit modelling; and a peer's message is a speech act, not an observation, so
it takes a different path through translation. See
[the-agent-stack-is-a-second-axis](knowledge/decisions/the-agent-stack-is-a-second-axis.md).

**Three layers, split by how long a thing may take and whether it may be interrupted** —
reactive handlers (ms, atomic, no search: classify and write — `packages/orexis-agent-reactive/`,
a queue and the ONE executing thread that drains it), intention progression (seconds to
minutes, suspends rather than blocks, searches nothing — `packages/orexis-agent-progression/`,
the ledger, the patience, the scheduler thread that keeps time and runs nothing, and a timer
whose landing is an enqueue), deliberation (the search — `packages/orexis-agent-deliberation/`,
on a worker thread of its own, only its result crossing onto the loop). The rule:
**anything that blocks belongs in progression, anything that searches belongs in deliberation,
anything that must never block belongs in a handler** — and the belief base is the INTERFACE
between them, which is why staleness, a dead sensor and event thinning all settled there rather
than in either neighbour. See
[layered-by-timescale-and-interruptibility](knowledge/decisions/layered-by-timescale-and-interruptibility.md).

**One principle explains most of the shapes above: control the derivative, not the value.**
Nothing here dictates an act — a cadence not a reading, a region not an aim, a mandate not a
belief, what is available not the act taken. When a change you are making reaches DOWN a level (a
deliberator setting a price, a world file pinning an aim, a model emitting an action), stop:
that is the one move this architecture refuses everywhere. See
[control-the-derivative-not-the-value](knowledge/decisions/control-the-derivative-not-the-value.md).

And two that catch people out. **There is no default world** — every command takes one as a
required argument and `current_world()` refuses rather than guessing, because a fallback puts a
misconfigured agent on the same topics as the real one. Also: **capabilities are worked out at
genesis, never hand-declared.** `world.ttl` must not contain `orexis:hasCapability`.

**Wiring is one input, not the definition.** Sensing's are a strict function of the hardware —
a board that keeps an interval gives its agent `sensing:Subscribing`, and nothing could have decided
otherwise. Others have no wiring to follow and are *deduced*: someone at genesis judged that this
agent should have them, and could have judged differently. Both end up in the world graph and
neither is hand-written, but they are not the same kind of fact — the first is `derived`, the
second `deduced`, and since the provenance split they are distinguishable rather than merely
distinct. So "deduced at genesis" is the rule; "computed from the wiring" is how it happens to
work for the one family whose hardware forces the answer.

**Each capability is granted by whatever fact makes it meaningful, and that fact is its own.** The
premise lives in the capability's `rules.ru`, and there is no pattern to fit a new one into. What
is left after the mind came home is two kinds of premise and no third. **Equipment or a position
in a market**: `actuation:hasActuator`, `market:bidsIn`/`market:hosts`, `sensing:polls` and a
sense mode. **Latitude**: `review:Reckoning`, because revising your own settings means nothing
without settings you are permitted to move, so an `review:commits` mandate whose ends differ is
its premise. When you add one, ask what makes *yours* meaningful rather than which of these it
resembles.

**A region want is NOT a premise for a capability, and neither is one with a lever beside it.** Three
capabilities were granted that way — wanting, committing, deciding — and all three are gone:
they were the mind, every agent has one, and the STORES they read were already built for every
agent unconditionally. A modality nobody may write is not a modality. What a region want still decides
is which SHAPES apply — `orexis:KeeperShape` targets a want that is not merely about knowing, and
sensing's region want shapes target `orexis:actsFor` a subject that states what it needs — so
`world/sensing`'s agent still holds no region and states no patience, by the fact rather than
by a grant. See
[the-mind-is-not-a-package](knowledge/decisions/the-mind-is-not-a-package.md),
[self-review-is-a-capability](knowledge/decisions/self-review-is-a-capability.md),
[desire-is-deduced-from-the-ranges-the-world-states](knowledge/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
and [an-intention-is-an-amortised-deliberation](knowledge/decisions/an-intention-is-an-amortised-deliberation.md).

**What the prohibition is actually against** is a capability nobody is answerable for. That was
unenforceable while a declared one and a derived one looked identical in the graph — which is why
the rule had to be absolute. It no longer is: a derivation writes to `graph/world/derived`, the
ratified graph is exactly what the files say, and every graph says who put it there. See
[who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).

## Start by reading the open issues

`gh issue list`. What is known to be wrong is tracked there, and several of the sharper questions
about this project are already answered in one. Re-deriving a known defect is waste; discovering
that your question is a recorded seam is a real answer.

Two roles are defined in `.claude/agents/` — `deliberate` for thinking a question through and
writing down the outcome, `implement` for carrying out something already decided. They say what a
role does; this file says what is true of the project, and it wins wherever they seem to disagree.

## Unfinished work: an issue is a debt, a seam is a decision

Three places can describe work that is not done, and they must not overlap.

- **GitHub issues** — actionable debt, with a definition of done. Something is *wrong* or
  *missing* and someone could close it. File one.
- **"Seams left open"** in a decision record — things deliberately NOT done, and why. A seam is
  a decision, not a to-do; it never becomes an issue and never gets closed.
- **`decisions/roadmap.md`** — direction. It points at issues rather than restating them.

The failure mode this avoids: a seams list quietly accumulating real defects, which nothing ever
closes, until it is a graveyard nobody reads. "Nothing aggregates two sensors on one property" is
a seam — it is a choice. "An observation is keyed by subject alone" is a debt — it is a bug.

**The reasoning stays in the bundle; the issue says what is left.** Do not duplicate the analysis
into an issue, and do not turn a decision record into a task list — link them instead.

### Telling an issue from a decision

A **decision record** explains why the code is as it is. An **issue** says the code is not yet as
it should be. Three checks, in order of how quickly they settle it:

| | issue | decision |
|---|---|---|
| can it be **closed**? | yes, by doing something | never — only superseded or amended |
| what changes when it is resolved? | the **code** | what someone **believes** about the code |
| how does the title read? | an imperative — *"key observations by subject and property"* | a claim — *"an observation is keyed by its subject alone, and that was wrong"* |

**A record earns its place by refusing something, and most changes do not need one** — a line in
*Principles* above and a good commit message is the ordinary ending. The test is not *did we
decide* — every commit decides. It is whether a real alternative was available and turned down: two mechanisms
and one chosen, a rule accepted here and refused there, a thing retired where rewiring was live.
**"We could have not done it" is not an alternative**, and a record whose only argument is that
the change was a good idea is a commit message with frontmatter — written twice, kept true
twice, and read where nobody was looking for it. The commit messages here are long and precise
on purpose; that is where *what we did and why* belongs. Measured 2026-08-29: 137 records, 15
with a section weighing an alternative, and `knowledge/` running 1.75 lines to every line of
code.

They compose in both directions, which is the part worth internalising. Fixing an issue usually
*produces* a decision worth recording. Writing a decision usually *emits* issues — the seams it
leaves that someone could close. `decisions/one-agent-many-sensors.md` did exactly that: the record
came first, and two issues fell out of it.

**The tell that you have misfiled something: an issue that argues both sides is not an issue.** If
it needs a section weighing alternatives, a choice has not been made yet, and the place for that is
a decision record — with the trigger for revisiting written down, so the next person knows when it
stops being theoretical.

## Commands

```bash
source .venv/bin/activate
pip install -e . $(ls -d packages/*/)   # 25 distributions; or `uv sync --all-packages`

orexis-validate <world> # build the world from its files and hold it to every package's shapes
orexis-onboard <world>       # ONBOARDING: validate, then grant everything below. One command.
  orexis-influx <world>      #   a bucket per agent, and a token that opens only it
  orexis-mqtt <world>        #   a credential per principal, and the broker ACL, derived
  orexis-compose <world>     #   generate world/<world>/compose.yaml from that world's roster
  orexis-dashboards <world>  #   a Grafana folder per world, from what its agents observe
orexis-firmware <world>      # a board's config.h, from the world it belongs to
orexis-wokwi <world>         # world/<world>/wokwi/ — its hardware as a wokwi.com project, which RUNS
orexis-wokwi <world> --import d.json  # the other way: DRAFT a hardware.ttl from a drawing
orexis-wireviz <world>       # world/<world>/wiring.yaml — the wiring as a WireViz harness
orexis-wireviz <world> --import w.yaml   # and the same, drafted back from one
orexis-keygen <world>        # once per world, before it is onboarded
orexis-ask <world> <agent> <modality> 'SPARQL'  # the sovereign asks a RUNNING agent — naming
                       # WHICH of its mind's stores (beliefs, desires; more as they land),
                       # required like the world is: no default modality. Read-only by
                       # construction. See decisions/the-sovereign-may-ask.md.
orexis-infra-certs           # INFRA, not onboarding — the services' certs and whom they trust
cd world/<world> && podman compose up -d      # one container per agent
podman build -t orexis:local .                 # only when a dependency changes
pytest -q              # what testpaths names: agent/, packages/ and world/. No infra needed.
                       # NOT `pytest tests` — that is the 0.1.0 suite, switched off in the gates
                       # since 2026-09-25; its four files that read the whole tree (knowledge,
                       # layout, store, projects) still gate.
pytest infra -q -n0    # 8 more, against the RUNNING broker and store — see below.
                       # -n0 is REQUIRED: they rewrite one acl.conf in place. It refuses without it.
lint-imports           # the layering: onboarding may import agent, never the reverse
```

`orexis-validate` and `pytest` are the two gates, and both must pass before a change is done.
`pytest infra` is a third thing, run deliberately, and it is not part of them — and it must
be run `-n0`, because `addopts` carries `-n auto` for everything else and those eight tests
cannot share a broker. They refuse rather than letting you find out: see
`infra/tests/conftest.py`.

**`infra/tests/` is a contract with the infrastructure, not with the code.** It holds mosquitto
and InfluxDB to the behaviour the isolation design leans on — that a revoked grant stops delivery
to an already-connected client, that a rotated credential is refused at once, that one agent's
token cannot reach another's bucket. None of that is guaranteed by MQTT or computed by anything
here; it is how those two services happen to behave, so it is worth re-proving whenever they
change. Both files report the version they ran against and assert nothing about it: bump
`MOSQUITTO_VERSION` in `infra/mosquitto/Containerfile` or the Influx image in
`infra/compose.yaml`, rebuild, and re-run `pytest infra -q -n0`.

**Onboarding is the phase between a ratified world and a running society** — see
[onboarding](knowledge/domain/onboarding.md). Its three generators all read the same `world.ttl`
and grant exactly what its wiring implies, so adding an agent and re-running `orexis-onboard` is
the whole of deploying one. They stay separately callable because rotating one service's
credentials should not touch the other's.

**Its code is in `onboarding/`, beside `agent/` and outside it.** The line is drawn by **who
calls a function**, not by file: `validate_agent` stays in `agent` because an agent checks
itself at boot, while `validate_world` moved because only the sovereign asks it; `sign` and
`verify_command` stay because an actuator co-signs, while `create_keypair` moved — an agent that
could mint a society's keys could sign for it. `orexis-influx` reads the admin token, which opens
every bucket and which no agent may ever hold, so the surest guarantee is that the code using it
is absent from the image.

**That absence is asserted, not implied.** There is ONE distribution now. What keeps onboarding
out of an agent image is the `Containerfile` not naming it — `tests/test_layout.py` fails if a
`COPY onboarding/` appears — and `lint-imports` holds the direction: onboarding may import
agent, agent may never import onboarding. Two pyprojects used to look like that boundary while
enforcing none of it. `orexis-influx` and `orexis-mqtt`
need infra up; `orexis-mqtt` must run before the broker will start at all, since its ACL is
generated and mosquitto now refuses anonymous clients. It then **reloads** the broker itself
(SIGHUP, not a restart — connected agents keep their sessions), so adding an agent or a world
still interrupts nothing.

Beliefs are the agent's: **authored** once at birth, never touched by start or stop — and so are
its ROOT desires, authored at birth into a graph with no period by the packages' desire rules
and projected, never rebuilt (#644). Anything
that would reset them on a restart is a bug, not a convenience. One addition is not a reset:
an amendment that grants a capability may author terms an existing volume has NEVER held, and
boot **endows** those — never-held terms arrive with their structures, held terms stay the
agent's whatever their value. `rebirth` remains the explicit discard. See
[an-amendment-endows-what-it-grants](knowledge/decisions/an-amendment-endows-what-it-grants.md).

But a belief is a **point chosen inside a range**, not a constant, and what genesis wrote is the
first pick rather than a bound. An agent whose **world gives it room to move** — `review:commits`, in
`world.ttl` — re-picks on its own clock inside that room, so the author's job is to constrain
well, not to guess well. **The mandate is also the grant**: `packages/orexis-capability-review/` derives its
capability from exactly those triples, so an agent given no room has no review module, keeps no
summaries and never arises. Which terms may move is one triple in the owning package's
`ontology.ttl`; a review rule is `packages/orexis-capability-<name>/review.rq`, SPARQL and never Python; and a
revision is legitimate exactly when `validate_agent` still passes, which is the same call the
agent makes at boot. **Compaction is not part of this** — it is not a choice, so it stayed in the
kernel on a clock of its own. See
[self-review-is-a-capability](knowledge/decisions/self-review-is-a-capability.md).

## Traps worth knowing, and one that is closed

**Closed: the two engines used to disagree about what the vocabulary says.** Shapes ran with RDFS
inference and the runtime ran none, so a world could validate against a relationship the code
would never observe — and six queries carried `rdfs:subClassOf*` by hand to compensate, for
twenty-five declared axioms. The entailments are now materialised into the store at genesis, and
validation runs with inference off against that same graph. **Ask what a thing IS; do not walk a
subclass path.** If the closure does not cover your case, widen `agent_old/inference.py` rather than
working around it — `tests/test_inference.py` refuses a seventh hand-rolled walk, and separately
fails if pyshacl ever entails something the closure does not. See
[one-graph-both-engines-read](knowledge/decisions/one-graph-both-engines-read.md).

- **Name the graph CLASS, never an instance — and scope by MODALITY when you leave belief.**
  `?d a orexis:DesireGraph` unions every instance of that class, exactly as `store.graphs_of(PUBLIC)`
  does, so a scoped query keeps the property the rule below exists to protect. A MODALITY
  class is a legitimate thing to name; a graph instance never is. (This first carried a
  sharper warning — that a want and a fact would share their shape, so an unscoped query would
  return the wanted value beside the observed one. That hazard is gone: what an agent pursues
  is SHACL, not belief-shaped data, so the two cannot be confused. The rule survives its
  motivation because naming a class rather than an instance was always the right discipline.)
  See [a-desire-is-a-shape](knowledge/decisions/a-desire-is-a-shape.md).
- **Never wrap `GRAPH <…>` around a SELECT.** Public knowledge is SEVERAL graphs — asserted,
  derived and entailed, for the vocabulary and for the world, plus whichever a package owns —
  and a reader hands `store.query` the list `store.graphs_of(PUBLIC)` answers, merged as the default graph, so an ordinary pattern reads all of them.
  Never count them: `orexis:PublicGraph` is a class and `graphs_of` asks. A basic graph
  pattern inside one `GRAPH` clause must match entirely *within* that graph, so narrowing it
  returns **nothing** the moment a fact you wanted lives elsewhere, silently, because an empty
  result is not an error. Updates are the exception and must name their target; a `rules.ru`
  writes `$given` and `$derived`, or `$into(pkg:SomeGraphClass)` when its package owns a graph —
  a graph *class* is a T-Box term and genesis resolves it, so **no rule names a graph**.
  `tests/test_provenance.py` refuses a narrowed SELECT. See
  [who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).
- **An update's WHERE reads the unnamed default graph unless `USING` says otherwise**, and the
  engine's `query` the same unless `default_graph` is passed — so a rule text run raw against
  the engine binds nothing, silently, though every graph it names is there. `store.query` and
  `store.construct` are HANDED their graphs — the reader states the kinds it means and the
  instant it stands at, `graphs_of` answers with the list, and the store adds nothing to it
  (a-reader-states-the-kinds-it-reads); a text that reads one graph names its kinds in its
  own `GRAPH` clauses by joining the catalogue, and is handed no default at all.
- **A graph IRI is an instance, so rule 1 applies to it.** `orexis:WorldGraph` is the term code may
  name; `…/graph/world` is not, any more than a world's `:fern_agent` is. Ask `store.graphs_of(PUBLIC)`.
  Two things are still named and both are writes or the bootstrap root, never a reader
  enumerating what to read — adding a public graph is a vocabulary edit that touches no Python.
  **A PER-AGENT graph is asked for the same way**: `store.graphs_of(<kind>)` answers with every
  graph this agent owns of a kind — its records, its desires, its wants, whatever a package
  puts under a kernel kind — by reading the classification each
  graph's OWNER wrote when it created the graph (`Store.classify`): the ledger its record, the
  keeper its promises, review its three, the derivation each want, sensing each prediction, genesis
  the pick record and the roots. A graph that does not exist until its agent does cannot be
  declared in a T-Box, and boot used to type them by matching names against a prefix each
  class declared — the one reader that depended on a name. A kind no runner asks for —
  review's three, the scopes — is read by its package alone, and no class
  hides anything from anyone. And a reader that means its OWN gets
  its own: the belief base tells the store whose it is, the classification says whose each
  graph is, and every list of the agent's graphs is kept to that owner — a graph saying no
  owner is anyone's. A graph's NAME is for eyes: the helpers
  spell a readable convention for writers, and `tests/test_layout.py` refuses a reader that
  imports one — a reader asks the class. Every one of those answers comes from ONE graph, the
  catalogue, which describes itself and is asked for from the store (`store.catalogue`) by a
  reader that must name it in a `GRAPH` clause — never spelled, since genesis alone creates it.
  Every row carries every kind its class is beneath, so a text asks `?g a orexis:WantGraph`
  and walks no path.
- **SPARQL prefixes.** Only what `store.NAMESPACES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `tests/test_store.py` checks this by scanning the source text — and asserts each
  source tree is still *found*, because moving files has twice emptied one of its globs and taken
  cases off the guard without failing anything. **A `sh:select` inside a shape is the same
  query** (#508): it uses the same names, says `sh:prefixes orexis:` on the node that carries
  it, and the store's `DECLARATION` — the dictionary in SHACL's words, assembled and never
  authored — travels with every shapes graph either engine is handed. A select spelling an
  IRI in full that the store has a name for fails the same test. **A select speaking words the
  store never loaded declares them itself**, `PREFIX name: <iri>` above its `SELECT` as SPARQL
  says it, and the compiler writes them at the head of the query it produces; a name the store
  already spells differently, or two selects spelling one name two ways, is refused. No shape
  shipped here needs one — a package's namespace is one the store discovered from that
  package's own ontology — and a test case speaking its own words does.
- **A test that asserts inside a loop can assert nothing.** An empty result set is not an error,
  so the body never runs and the test is green. The repo-root `conftest.py` traces the at-risk
  tests — an `assert` inside a loop over something that could be empty — and fails the run if a
  test function executed no assertion in any of its cases. It does NOT catch a parametrisation
  that generated zero cases, nor a glob that still matches but no longer covers what it is named
  for; both have happened, and both are still found by hand. See
  [a-test-that-asserted-nothing](knowledge/decisions/a-test-that-asserted-nothing.md).
- **A premise may not rest on another package's CONCLUSIONS.** Derivations run once, in
  package-directory order, so a rule in `desire/` cannot see what `market/` derives — the
  pattern matches nothing, the grant does not happen, and nothing says so. Premises use
  AUTHORED or ENTAILED facts, which every cross-package grant here already does: entailment is
  materialised before any rule runs, so `market:offeredBy` is available where `market:hosts`
  is not.
- **The engine's own query parameters reach only a variable the query PROJECTS at its top
  level.** pyoxigraph's `substitutions=` (SEP-0007) was measured refusing a subquery that does
  not project the variable and every aggregate that does not group it — which is the shape of
  every estimate — so the kernel's own simple queries bind that way and a rule text takes its
  parameters as `$tokens` through ONE binder, `store.bind`: whole-token match, values
  rendered as the terms they are, and a token nobody bound REFUSES. A chain of `.replace`
  left `$about` in the dosing rule to parse as a free variable, and the prediction matched
  an observation of any property (#500).
- **A property path whose end is bound by a `VALUES` inside a `FILTER NOT EXISTS` is
  evaluated per candidate, not once** — folding a second excluded class into the own-graphs
  query that way took it from 2 ms to 600 ms at the start of every pass, and two plain
  filters cost what one did. Measure a query you reshape, not only one you write.
- **A pattern under `FILTER NOT EXISTS` is left untranslated by rdflib's algebra** — it sits
  in the parse tree as a triples block, not a BGP, so a walk that reads BGPs alone reads
  nothing from a want that says "unmet while this fact is absent"; `relevance.py` reads both.
- **A `BIND` inside a `UNION` branch cannot see a variable bound outside the union.** The
  branches are evaluated on their own and joined with the surrounding pattern afterwards, so
  the tidy form — state the preamble once, then `{ … } UNION { … }` — leaves every outer
  variable unbound where the arithmetic runs. Measured on the courier's distance heuristic: it
  returned 0 for every world, no error and no empty result, which reads as "already arrived".
  Repeat the preamble inside each branch.
- **An operation this engine lacks binds NOTHING — it does not fail.** `duration / duration`
  and `duration * number` return unbound in pyoxigraph, and so does every cast of a duration
  to a number (`xsd:decimal(?a - ?b)`, measured on 0.5.9: only a dateTime's `HOURS`, `MINUTES`
  and `SECONDS` bind, so no rule can measure the stretch between two instants, which is why a
  drift counts the `$elapsed` sensing hands it when it writes a prediction), and so does a decimal division whose
  dividend is an exact zero (`0.0 / 0.25`; cast the dividend to `xsd:double`), and so does a
  decimal PRODUCT past the engine's eighteen fractional digits (`0.5 * (0.02 / 0.375)`; round
  the repeating operand to six places first, as every derived number here is written), and so
  does an exact-zero decimal PRODUCT by a decimal (`0.0 * 0.5` bound nothing where `0.0 * 1`
  bound zero, measured in #642 — cast a factor that may be zero to `xsd:double`), so a
  column computed that way reads empty for every row and no query errors, no test goes red.
  And `a / b * c` is evaluated as `a / (b * c)` — measured, `0.02 / 0.375 * 1000000` gave
  five hundred-millionths — so parenthesise every chain of two operators. And `GROUP_CONCAT`
  over an IRI binds nothing — no column at all, measured — where `GROUP_CONCAT(STR(?x))`
  binds; `find_wants` reads a want's several abouts that way and `test_wants.py` pins it. It is the
  same family as the empty-result trap above, arriving through arithmetic and aggregation: measure an unfamiliar operation on a
  literal before building a column on it, and pin what you measured — `tests/test_desires.py`
  does, so the day the engine grows the operation the guard says so.
- **`build_agent` does not run the boot gate.** The fixture patches `validate_agent` out of
  the boot unless a test passes `validating=True`: the gate raises or passes and changes
  nothing else, it cost two seconds of every boot, and it was paid about 250 times a run to
  say the same thing about a store built from the ratified files. A test that expects
  `BeliefsInvalid` from a built agent gets none — say `validating=True`, or build the
  `Agent` yourself as `test_shapes` and `test_hanoi` do.
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.

1. **Code may reference T-Box terms; never an instance.** `term("Subscribing")` is fine;
   `"supplier"`, `"sensors/fern/moisture"`, a world's `:world` node are not. The single exception is the one
   identifier a process is handed at boot: its own agent id. Everything else is discovered from
   the graph. See [capability-packages](knowledge/decisions/capability-packages.md).
2. **A capability is a named ability with interchangeable implementations. A DIRECTORY IS A
   PACKAGE, and a package may hold several.** The ability is a **family** — the slot; the
   implementations are its members. `sensing:SensingCapability` is a family and `sensing:Subscribing`
   and `sensing:Listening` are two ways of having it, chosen by what the hardware can do. That is the
   shape to reach for: a capability worth naming is one where the *how* could differ. Reviewing
   your own settings by strict rules or by asking a model is one ability with two
   implementations; pay-as-bid and uniform-price are one auction with two. Where nothing could
   differ, you have a function, not a capability.

   The two are not the same axis, and saying "a capability is a directory" hid that.
   `packages/orexis-capability-market/` provides three — bidding, hosting, and the matching family — and it is
   one package. **What isolates a capability is `PROVIDES` and its term, never the directory
   boundary**: `hosting.py` asks `agent.provider(BID_MATCHING)` and never learns which member
   answered, so uniform price landed without touching a line of it. A directory is how a package
   is FOUND and how one is deleted. See
   [a-package-owns-its-namespace](knowledge/decisions/a-package-owns-its-namespace.md).

   **There is ONE package tree and one mechanic.** `packages/orexis-<family>-<name>/` holds whichever
   of `ontology.ttl`, `shapes.ttl`, `rules.ru`, `actions.ttl`, `review.rq` and Python it wants — every one
   optional, and an omission is a statement. Two files are NOT optional: a `pyproject.toml`,
   because **every package is its own distribution with its own dependencies**
   (`orexis-<family>-<name>`), and the `__init__.py` manifest. A dependency is declared by
   whoever imports it and `tests/test_projects.py` holds each list to the imports in both
   directions — a missing one and an unused one both fail. `packages/` and `packages/<family>/`
   are PEP 420 namespace portions belonging to no distribution, which is what lets a package
   from another repository join the same import root. See
   [every-package-is-a-project](knowledge/decisions/every-package-is-a-project.md). `packages/orexis-part-esp32/` is an ontology and nothing
   else because a board has no behaviour a runtime could load; `packages/orexis-capability-market/` has
   all of it. Neither is more of a package than the other, and that is the point: a plant, a
   part and a capability are the same kind of thing to the loader.

   A package may declare **its own namespace**, in its `ontology.ttl` and mirrored in
   `terms.py`. `agent.loader` reads every project namespace off the ontology that declares it,
   so `market:` reaches a query without `store.PREFIXES` learning the package exists. Nothing
   lists them — `agent.loader` finds them one level down, and the FAMILY is the second segment of
   the package's own NAME — which is also its distribution name and, with underscores, its
   module — so `kind` distinguishes a plant from a part without a registry and without a second
   place to state it. `PROVIDES` in `__init__.py` is how an implementation registers, and its absence
   is what makes a package knowledge-only. A package implements the terms IT declares —
   which is what lets imports follow grants: a runtime imports only the packages its own
   capabilities name (#216) — and, beneath the grants, a REQUIRED injection pulls the package
   providing its key into the load set, needs after needs, while a soft one (`X | None`)
   injects only what is already there and loads nothing (#455). Adding one is adding a directory. Packages never
   import each other's Python ACROSS a layer: ask `agent.provider(family)` or contribute via
   the choir's extension points (`desires`, every ACTION, `notices`, `series`, `quiet` — and, in sensing's
   words through `agent.ask`, `annotate`, `bounds`).
   The one ordinary import is DOWNWARD, of the contract of the layer beneath: a family's plug-ins
   import the family's contract — `packages/orexis-codec-*`, `packages/orexis-scaling-*` and
   `packages/orexis-transport-*` import sensing's `Codec`, `Scaling` and `pointer`, because those
   are the contracts they exist to implement (see
   [sensing-owns-the-reading-pipeline](knowledge/decisions/sensing-owns-the-reading-pipeline.md))
   — and THE KERNEL IS THREE LAYER PACKAGES in the same tree, each importing only the layers
   beneath it: the reactive loop (`packages/orexis-agent-reactive/`, importing nothing of
   ours), progression (`packages/orexis-agent-progression/`, the ledger and the store
   engine, the lowest layer that persists) and deliberation
   (`packages/orexis-agent-deliberation/`, the belief base, the desires and the search). There
   is no floor beneath them: what a lower layer has to say upward it says as an EVENT through
   the choir. `agent/` is the CONTAINER that assembles them and may import all three; nothing
   imports it from below, and a capability may import any layer's contract (see
   [a-layer-is-a-package-and-need-loads-it](knowledge/decisions/a-layer-is-a-package-and-need-loads-it.md)).
   The order is spelled once, `LAYERS` in `tests/test_projects.py`, and `tests/test_layering.py`
   holds every arrow, finding each layer by its family.
   **A layer with words of its own owns a namespace** (#529) — `progression:` for the ledger,
   `deliberation:` for the trace and the budget, each declared in the layer package's own
   `ontology.ttl`; the reactive layer has no vocabulary — and a term one layer reads and writes
   carries its prefix, so a query says which layer it speaks for. What every layer and every
   package writes in — `orexis:Agent`, `orexis:Action`, a want's grammar, the choir's extension
   points — stays `orexis:`, and a file naming a HIGHER layer's prefix fails
   `tests/test_layering.py` as an upward import would.
   A transport is also a capability the fact of its bus grants — how the agent reaches its
   society, connection, delivery loop and watchdog in the transport's module, reached through
   the choir (`subscriptions`, `handle`, `send`) — and the kernel has no mailbox (see
   [the-kernel-has-no-mailbox](knowledge/decisions/the-kernel-has-no-mailbox.md)).

   **`agent/` is the kernel that loads them, not their home.** Capability Python used to live
   under it, so the tree itself showed which of it a runtime loads — it does not show that now.
   `packages/orexis-capability-market/` and `packages/orexis-part-dht11/` look identical, so the CONTRACTS
   carry the boundary alone: `lint-imports` holds `packages` away from `onboarding`, and the
   `Containerfile` decides what reaches an image by naming two trees and not a third. Both were
   always the real enforcement; the layout was a reminder, and the reminder is gone.
3. **Nothing in `infra/` is world-specific.** It holds the services and what is true of the
   installation: the broker image, the installation CA, Grafana's material, the admin token. A
   world's broker config, its ACL, its certificates and its device credentials live with the
   world. Also: **no `.env` at the repo root, because nothing there is true of every world at
   once.** `infra/.env` says where the shared series store is — the URL and the org, and nothing
   secret, because that file is handed to every agent container. What an agent may *do* with
   the store and the bus arrives as its own credentials, minted per agent into
   `world/<name>/secrets/` and mounted into that container alone. The admin token lives apart
   from both, in `infra/secrets/`, and no agent ever holds it. See
   [series-and-bus-isolation](knowledge/decisions/series-and-bus-isolation.md).
4. **There is no shared store.** The world is TTL files; each agent builds its own belief base
   at boot and holds it in a volume of its own, so isolation is structural rather than
   enforced. An agent is told its id and given one world, mounted — it never learns that other
   worlds exist. See [where-the-belief-base-lives](knowledge/decisions/where-the-belief-base-lives.md).
5. **There is no config file for the model.** Topology lives in the world graph, desire and
   limits in each agent's own beliefs, both authored in `world/<world>/`. Deployment facts
   (service URLs) are environment, because they are not beliefs anyone holds. See
   [world-graph](knowledge/decisions/world-graph.md).

**What an agent BELIEVES about all of that is settled by one test: model it only if a belief
about it would change which plan gets selected.** Everything else is telemetry — logged and
reported, never believed. Infrastructure reaches belief only through a named projection; anything
the interpreter already knows is COMPUTED (what stands, what I can do, how stale this is) and
never asserted; what comes from outside is stored; self-telemetry gets bands, not raw values;
reflection caps at one level; and beliefs about other agents stay first-order — what they DID,
never what they believe. See
[model-it-only-if-a-plan-would-branch-on-it](knowledge/decisions/model-it-only-if-a-plan-would-branch-on-it.md).

**And a SECOND axis, orthogonal to that one: the agent stack** — network, transport,
translation, the belief-revision seam, mind — sliced by representation rather than by timescale.
The transport has no position on the cognitive axis at all; an infrastructure failure becomes a
belief only by explicit modelling; and a peer's message is a speech act, not an observation, so
it takes a different path through translation. See
[the-agent-stack-is-a-second-axis](knowledge/decisions/the-agent-stack-is-a-second-axis.md).

**Three layers, split by how long a thing may take and whether it may be interrupted** —
reactive handlers (ms, atomic, no search: classify and write — `packages/orexis-agent-reactive/`,
a queue and the ONE executing thread that drains it), intention progression (seconds to
minutes, suspends rather than blocks, searches nothing — `packages/orexis-agent-progression/`,
the ledger, the patience, the scheduler thread that keeps time and runs nothing, and a timer
whose landing is an enqueue), deliberation (the search — `packages/orexis-agent-deliberation/`,
on a worker thread of its own, only its result crossing onto the loop). The rule:
**anything that blocks belongs in progression, anything that searches belongs in deliberation,
anything that must never block belongs in a handler** — and the belief base is the INTERFACE
between them, which is why staleness, a dead sensor and event thinning all settled there rather
than in either neighbour. See
[layered-by-timescale-and-interruptibility](knowledge/decisions/layered-by-timescale-and-interruptibility.md).

**One principle explains most of the shapes above: control the derivative, not the value.**
Nothing here dictates an act — a cadence not a reading, a region not an aim, a mandate not a
belief, what is available not the act taken. When a change you are making reaches DOWN a level (a
deliberator setting a price, a world file pinning an aim, a model emitting an action), stop:
that is the one move this architecture refuses everywhere. See
[control-the-derivative-not-the-value](knowledge/decisions/control-the-derivative-not-the-value.md).

And two that catch people out. **There is no default world** — every command takes one as a
required argument and `current_world()` refuses rather than guessing, because a fallback puts a
misconfigured agent on the same topics as the real one. Also: **capabilities are worked out at
genesis, never hand-declared.** `world.ttl` must not contain `orexis:hasCapability`.

**Wiring is one input, not the definition.** Sensing's are a strict function of the hardware —
a board that keeps an interval gives its agent `sensing:Subscribing`, and nothing could have decided
otherwise. Others have no wiring to follow and are *deduced*: someone at genesis judged that this
agent should have them, and could have judged differently. Both end up in the world graph and
neither is hand-written, but they are not the same kind of fact — the first is `derived`, the
second `deduced`, and since the provenance split they are distinguishable rather than merely
distinct. So "deduced at genesis" is the rule; "computed from the wiring" is how it happens to
work for the one family whose hardware forces the answer.

**Each capability is granted by whatever fact makes it meaningful, and that fact is its own.** The
premise lives in the capability's `rules.ru`, and there is no pattern to fit a new one into. What
is left after the mind came home is two kinds of premise and no third. **Equipment or a position
in a market**: `actuation:hasActuator`, `market:bidsIn`/`market:hosts`, `sensing:polls` and a
sense mode. **Latitude**: `review:Reckoning`, because revising your own settings means nothing
without settings you are permitted to move, so an `review:commits` mandate whose ends differ is
its premise. When you add one, ask what makes *yours* meaningful rather than which of these it
resembles.

**A region want is NOT a premise for a capability, and neither is one with a lever beside it.** Three
capabilities were granted that way — wanting, committing, deciding — and all three are gone:
they were the mind, every agent has one, and the STORES they read were already built for every
agent unconditionally. A modality nobody may write is not a modality. What a region want still decides
is which SHAPES apply — `orexis:KeeperShape` targets a want that is not merely about knowing, and
sensing's region want shapes target `orexis:actsFor` a subject that states what it needs — so
`world/sensing`'s agent still holds no region and states no patience, by the fact rather than
by a grant. See
[the-mind-is-not-a-package](knowledge/decisions/the-mind-is-not-a-package.md),
[self-review-is-a-capability](knowledge/decisions/self-review-is-a-capability.md),
[desire-is-deduced-from-the-ranges-the-world-states](knowledge/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
and [an-intention-is-an-amortised-deliberation](knowledge/decisions/an-intention-is-an-amortised-deliberation.md).

**What the prohibition is actually against** is a capability nobody is answerable for. That was
unenforceable while a declared one and a derived one looked identical in the graph — which is why
the rule had to be absolute. It no longer is: a derivation writes to `graph/world/derived`, the
ratified graph is exactly what the files say, and every graph says who put it there. See
[who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).

## Start by reading the open issues

`gh issue list`. What is known to be wrong is tracked there, and several of the sharper questions
about this project are already answered in one. Re-deriving a known defect is waste; discovering
that your question is a recorded seam is a real answer.

Two roles are defined in `.claude/agents/` — `deliberate` for thinking a question through and
writing down the outcome, `implement` for carrying out something already decided. They say what a
role does; this file says what is true of the project, and it wins wherever they seem to disagree.

## Unfinished work: an issue is a debt, a seam is a decision

Three places can describe work that is not done, and they must not overlap.

- **GitHub issues** — actionable debt, with a definition of done. Something is *wrong* or
  *missing* and someone could close it. File one.
- **"Seams left open"** in a decision record — things deliberately NOT done, and why. A seam is
  a decision, not a to-do; it never becomes an issue and never gets closed.
- **`decisions/roadmap.md`** — direction. It points at issues rather than restating them.

The failure mode this avoids: a seams list quietly accumulating real defects, which nothing ever
closes, until it is a graveyard nobody reads. "Nothing aggregates two sensors on one property" is
a seam — it is a choice. "An observation is keyed by subject alone" is a debt — it is a bug.

**The reasoning stays in the bundle; the issue says what is left.** Do not duplicate the analysis
into an issue, and do not turn a decision record into a task list — link them instead.

### Telling an issue from a decision

A **decision record** explains why the code is as it is. An **issue** says the code is not yet as
it should be. Three checks, in order of how quickly they settle it:

| | issue | decision |
|---|---|---|
| can it be **closed**? | yes, by doing something | never — only superseded or amended |
| what changes when it is resolved? | the **code** | what someone **believes** about the code |
| how does the title read? | an imperative — *"key observations by subject and property"* | a claim — *"an observation is keyed by its subject alone, and that was wrong"* |

**A record earns its place by refusing something, and most changes do not need one** — a line in
*Principles* above and a good commit message is the ordinary ending. The test is not *did we
decide* — every commit decides. It is whether a real alternative was available and turned down: two mechanisms
and one chosen, a rule accepted here and refused there, a thing retired where rewiring was live.
**"We could have not done it" is not an alternative**, and a record whose only argument is that
the change was a good idea is a commit message with frontmatter — written twice, kept true
twice, and read where nobody was looking for it. The commit messages here are long and precise
on purpose; that is where *what we did and why* belongs. Measured 2026-08-29: 137 records, 15
with a section weighing an alternative, and `knowledge/` running 1.75 lines to every line of
code.

They compose in both directions, which is the part worth internalising. Fixing an issue usually
*produces* a decision worth recording. Writing a decision usually *emits* issues — the seams it
leaves that someone could close. `decisions/one-agent-many-sensors.md` did exactly that: the record
came first, and two issues fell out of it.

**The tell that you have misfiled something: an issue that argues both sides is not an issue.** If
it needs a section weighing alternatives, a choice has not been made yet, and the place for that is
a decision record — with the trigger for revisiting written down, so the next person knows when it
stops being theoretical.

## Commands

```bash
source .venv/bin/activate
pip install -e . $(ls -d packages/*/)   # 25 distributions; or `uv sync --all-packages`

orexis-validate <world> # build the world from its files and hold it to every package's shapes
orexis-onboard <world>       # ONBOARDING: validate, then grant everything below. One command.
  orexis-influx <world>      #   a bucket per agent, and a token that opens only it
  orexis-mqtt <world>        #   a credential per principal, and the broker ACL, derived
  orexis-compose <world>     #   generate world/<world>/compose.yaml from that world's roster
  orexis-dashboards <world>  #   a Grafana folder per world, from what its agents observe
orexis-firmware <world>      # a board's config.h, from the world it belongs to
orexis-wokwi <world>         # world/<world>/wokwi/ — its hardware as a wokwi.com project, which RUNS
orexis-wokwi <world> --import d.json  # the other way: DRAFT a hardware.ttl from a drawing
orexis-wireviz <world>       # world/<world>/wiring.yaml — the wiring as a WireViz harness
orexis-wireviz <world> --import w.yaml   # and the same, drafted back from one
orexis-keygen <world>        # once per world, before it is onboarded
orexis-ask <world> <agent> <modality> 'SPARQL'  # the sovereign asks a RUNNING agent — naming
                       # WHICH of its mind's stores (beliefs, desires; more as they land),
                       # required like the world is: no default modality. Read-only by
                       # construction. See decisions/the-sovereign-may-ask.md.
orexis-infra-certs           # INFRA, not onboarding — the services' certs and whom they trust
cd world/<world> && podman compose up -d      # one container per agent
podman build -t orexis:local .                 # only when a dependency changes
pytest -q              # what testpaths names: agent/, packages/ and world/. No infra needed.
                       # NOT `pytest tests` — that is the 0.1.0 suite, switched off in the gates
                       # since 2026-09-25; its four files that read the whole tree (knowledge,
                       # layout, store, projects) still gate.
pytest infra -q -n0    # 8 more, against the RUNNING broker and store — see below.
                       # -n0 is REQUIRED: they rewrite one acl.conf in place. It refuses without it.
lint-imports           # the layering: onboarding may import agent, never the reverse
```

`orexis-validate` and `pytest` are the two gates, and both must pass before a change is done.
`pytest infra` is a third thing, run deliberately, and it is not part of them — and it must
be run `-n0`, because `addopts` carries `-n auto` for everything else and those eight tests
cannot share a broker. They refuse rather than letting you find out: see
`infra/tests/conftest.py`.

**`infra/tests/` is a contract with the infrastructure, not with the code.** It holds mosquitto
and InfluxDB to the behaviour the isolation design leans on — that a revoked grant stops delivery
to an already-connected client, that a rotated credential is refused at once, that one agent's
token cannot reach another's bucket. None of that is guaranteed by MQTT or computed by anything
here; it is how those two services happen to behave, so it is worth re-proving whenever they
change. Both files report the version they ran against and assert nothing about it: bump
`MOSQUITTO_VERSION` in `infra/mosquitto/Containerfile` or the Influx image in
`infra/compose.yaml`, rebuild, and re-run `pytest infra -q -n0`.

**Onboarding is the phase between a ratified world and a running society** — see
[onboarding](knowledge/domain/onboarding.md). Its three generators all read the same `world.ttl`
and grant exactly what its wiring implies, so adding an agent and re-running `orexis-onboard` is
the whole of deploying one. They stay separately callable because rotating one service's
credentials should not touch the other's.

**Its code is in `onboarding/`, beside `agent/` and outside it.** The line is drawn by **who
calls a function**, not by file: `validate_agent` stays in `agent` because an agent checks
itself at boot, while `validate_world` moved because only the sovereign asks it; `sign` and
`verify_command` stay because an actuator co-signs, while `create_keypair` moved — an agent that
could mint a society's keys could sign for it. `orexis-influx` reads the admin token, which opens
every bucket and which no agent may ever hold, so the surest guarantee is that the code using it
is absent from the image.

**That absence is asserted, not implied.** There is ONE distribution now. What keeps onboarding
out of an agent image is the `Containerfile` not naming it — `tests/test_layout.py` fails if a
`COPY onboarding/` appears — and `lint-imports` holds the direction: onboarding may import
agent, agent may never import onboarding. Two pyprojects used to look like that boundary while
enforcing none of it. `orexis-influx` and `orexis-mqtt`
need infra up; `orexis-mqtt` must run before the broker will start at all, since its ACL is
generated and mosquitto now refuses anonymous clients. It then **reloads** the broker itself
(SIGHUP, not a restart — connected agents keep their sessions), so adding an agent or a world
still interrupts nothing.

Beliefs are the agent's: **authored** once at birth, never touched by start or stop — and so are
its ROOT desires, authored at birth into a graph with no period by the packages' desire rules
and projected, never rebuilt (#644). Anything
that would reset them on a restart is a bug, not a convenience. One addition is not a reset:
an amendment that grants a capability may author terms an existing volume has NEVER held, and
boot **endows** those — never-held terms arrive with their structures, held terms stay the
agent's whatever their value. `rebirth` remains the explicit discard. See
[an-amendment-endows-what-it-grants](knowledge/decisions/an-amendment-endows-what-it-grants.md).

But a belief is a **point chosen inside a range**, not a constant, and what genesis wrote is the
first pick rather than a bound. An agent whose **world gives it room to move** — `review:commits`, in
`world.ttl` — re-picks on its own clock inside that room, so the author's job is to constrain
well, not to guess well. **The mandate is also the grant**: `packages/orexis-capability-review/` derives its
capability from exactly those triples, so an agent given no room has no review module, keeps no
summaries and never arises. Which terms may move is one triple in the owning package's
`ontology.ttl`; a review rule is `packages/orexis-capability-<name>/review.rq`, SPARQL and never Python; and a
revision is legitimate exactly when `validate_agent` still passes, which is the same call the
agent makes at boot. **Compaction is not part of this** — it is not a choice, so it stayed in the
kernel on a clock of its own. See
[self-review-is-a-capability](knowledge/decisions/self-review-is-a-capability.md).

## Traps worth knowing, and one that is closed

**Closed: the two engines used to disagree about what the vocabulary says.** Shapes ran with RDFS
inference and the runtime ran none, so a world could validate against a relationship the code
would never observe — and six queries carried `rdfs:subClassOf*` by hand to compensate, for
twenty-five declared axioms. The entailments are now materialised into the store at genesis, and
validation runs with inference off against that same graph. **Ask what a thing IS; do not walk a
subclass path.** If the closure does not cover your case, widen `agent_old/inference.py` rather than
working around it — `tests/test_inference.py` refuses a seventh hand-rolled walk, and separately
fails if pyshacl ever entails something the closure does not. See
[one-graph-both-engines-read](knowledge/decisions/one-graph-both-engines-read.md).

- **Name the graph CLASS, never an instance — and scope by MODALITY when you leave belief.**
  `?d a orexis:DesireGraph` unions every instance of that class, exactly as `store.graphs_of(PUBLIC)`
  does, so a scoped query keeps the property the rule below exists to protect. A MODALITY
  class is a legitimate thing to name; a graph instance never is. (This first carried a
  sharper warning — that a want and a fact would share their shape, so an unscoped query would
  return the wanted value beside the observed one. That hazard is gone: what an agent pursues
  is SHACL, not belief-shaped data, so the two cannot be confused. The rule survives its
  motivation because naming a class rather than an instance was always the right discipline.)
  See [a-desire-is-a-shape](knowledge/decisions/a-desire-is-a-shape.md).
- **Never wrap `GRAPH <…>` around a SELECT.** Public knowledge is SEVERAL graphs — asserted,
  derived and entailed, for the vocabulary and for the world, plus whichever a package owns —
  and a reader hands `store.query` the list `store.graphs_of(PUBLIC)` answers, merged as the default graph, so an ordinary pattern reads all of them.
  Never count them: `orexis:PublicGraph` is a class and `graphs_of` asks. A basic graph
  pattern inside one `GRAPH` clause must match entirely *within* that graph, so narrowing it
  returns **nothing** the moment a fact you wanted lives elsewhere, silently, because an empty
  result is not an error. Updates are the exception and must name their target; a `rules.ru`
  writes `$given` and `$derived`, or `$into(pkg:SomeGraphClass)` when its package owns a graph —
  a graph *class* is a T-Box term and genesis resolves it, so **no rule names a graph**.
  `tests/test_provenance.py` refuses a narrowed SELECT. See
  [who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).
- **An update's WHERE reads the unnamed default graph unless `USING` says otherwise**, and the
  engine's `query` the same unless `default_graph` is passed — so a rule text run raw against
  the engine binds nothing, silently, though every graph it names is there. `store.query` and
  `store.construct` are HANDED their graphs — the reader states the kinds it means and the
  instant it stands at, `graphs_of` answers with the list, and the store adds nothing to it
  (a-reader-states-the-kinds-it-reads); a text that reads one graph names its kinds in its
  own `GRAPH` clauses by joining the catalogue, and is handed no default at all.
- **A graph IRI is an instance, so rule 1 applies to it.** `orexis:WorldGraph` is the term code may
  name; `…/graph/world` is not, any more than a world's `:fern_agent` is. Ask `store.graphs_of(PUBLIC)`.
  Two things are still named and both are writes or the bootstrap root, never a reader
  enumerating what to read — adding a public graph is a vocabulary edit that touches no Python.
  **A PER-AGENT graph is asked for the same way**: `store.graphs_of(<kind>)` answers with every
  graph this agent owns of a kind — its records, its desires, its wants, whatever a package
  puts under a kernel kind — by reading the classification each
  graph's OWNER wrote when it created the graph (`Store.classify`): the ledger its record, the
  keeper its promises, review its three, the derivation each want, sensing each prediction, genesis
  the pick record and the roots. A graph that does not exist until its agent does cannot be
  declared in a T-Box, and boot used to type them by matching names against a prefix each
  class declared — the one reader that depended on a name. A kind no runner asks for —
  review's three, the scopes — is read by its package alone, and no class
  hides anything from anyone. And a reader that means its OWN gets
  its own: the belief base tells the store whose it is, the classification says whose each
  graph is, and every list of the agent's graphs is kept to that owner — a graph saying no
  owner is anyone's. A graph's NAME is for eyes: the helpers
  spell a readable convention for writers, and `tests/test_layout.py` refuses a reader that
  imports one — a reader asks the class. Every one of those answers comes from ONE graph, the
  catalogue, which describes itself and is asked for from the store (`store.catalogue`) by a
  reader that must name it in a `GRAPH` clause — never spelled, since genesis alone creates it.
  Every row carries every kind its class is beneath, so a text asks `?g a orexis:WantGraph`
  and walks no path.
- **SPARQL prefixes.** Only what `store.NAMESPACES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `tests/test_store.py` checks this by scanning the source text — and asserts each
  source tree is still *found*, because moving files has twice emptied one of its globs and taken
  cases off the guard without failing anything. **A `sh:select` inside a shape is the same
  query** (#508): it uses the same names, says `sh:prefixes orexis:` on the node that carries
  it, and the store's `DECLARATION` — the dictionary in SHACL's words, assembled and never
  authored — travels with every shapes graph either engine is handed. A select spelling an
  IRI in full that the store has a name for fails the same test. **A select speaking words the
  store never loaded declares them itself**, `PREFIX name: <iri>` above its `SELECT` as SPARQL
  says it, and the compiler writes them at the head of the query it produces; a name the store
  already spells differently, or two selects spelling one name two ways, is refused. No shape
  shipped here needs one — a package's namespace is one the store discovered from that
  package's own ontology — and a test case speaking its own words does.
- **A test that asserts inside a loop can assert nothing.** An empty result set is not an error,
  so the body never runs and the test is green. The repo-root `conftest.py` traces the at-risk
  tests — an `assert` inside a loop over something that could be empty — and fails the run if a
  test function executed no assertion in any of its cases. It does NOT catch a parametrisation
  that generated zero cases, nor a glob that still matches but no longer covers what it is named
  for; both have happened, and both are still found by hand. See
  [a-test-that-asserted-nothing](knowledge/decisions/a-test-that-asserted-nothing.md).
- **A premise may not rest on another package's CONCLUSIONS.** Derivations run once, in
  package-directory order, so a rule in `desire/` cannot see what `market/` derives — the
  pattern matches nothing, the grant does not happen, and nothing says so. Premises use
  AUTHORED or ENTAILED facts, which every cross-package grant here already does: entailment is
  materialised before any rule runs, so `market:offeredBy` is available where `market:hosts`
  is not.
- **The engine's own query parameters reach only a variable the query PROJECTS at its top
  level.** pyoxigraph's `substitutions=` (SEP-0007) was measured refusing a subquery that does
  not project the variable and every aggregate that does not group it — which is the shape of
  every estimate — so the kernel's own simple queries bind that way and a rule text takes its
  parameters as `$tokens` through ONE binder, `store.bind`: whole-token match, values
  rendered as the terms they are, and a token nobody bound REFUSES. A chain of `.replace`
  left `$about` in the dosing rule to parse as a free variable, and the prediction matched
  an observation of any property (#500).
- **A property path whose end is bound by a `VALUES` inside a `FILTER NOT EXISTS` is
  evaluated per candidate, not once** — folding a second excluded class into the own-graphs
  query that way took it from 2 ms to 600 ms at the start of every pass, and two plain
  filters cost what one did. Measure a query you reshape, not only one you write.
- **A pattern under `FILTER NOT EXISTS` is left untranslated by rdflib's algebra** — it sits
  in the parse tree as a triples block, not a BGP, so a walk that reads BGPs alone reads
  nothing from a want that says "unmet while this fact is absent"; `relevance.py` reads both.
- **A `BIND` inside a `UNION` branch cannot see a variable bound outside the union.** The
  branches are evaluated on their own and joined with the surrounding pattern afterwards, so
  the tidy form — state the preamble once, then `{ … } UNION { … }` — leaves every outer
  variable unbound where the arithmetic runs. Measured on the courier's distance heuristic: it
  returned 0 for every world, no error and no empty result, which reads as "already arrived".
  Repeat the preamble inside each branch.
- **An operation this engine lacks binds NOTHING — it does not fail.** `duration / duration`
  and `duration * number` return unbound in pyoxigraph, and so does every cast of a duration
  to a number (`xsd:decimal(?a - ?b)`, measured on 0.5.9: only a dateTime's `HOURS`, `MINUTES`
  and `SECONDS` bind, so no rule can measure the stretch between two instants, which is why a
  drift counts the `$elapsed` sensing hands it when it writes a prediction), and so does a decimal division whose
  dividend is an exact zero (`0.0 / 0.25`; cast the dividend to `xsd:double`), and so does a
  decimal PRODUCT past the engine's eighteen fractional digits (`0.5 * (0.02 / 0.375)`; round
  the repeating operand to six places first, as every derived number here is written), and so
  does an exact-zero decimal PRODUCT by a decimal (`0.0 * 0.5` bound nothing where `0.0 * 1`
  bound zero, measured in #642 — cast a factor that may be zero to `xsd:double`), so a
  column computed that way reads empty for every row and no query errors, no test goes red.
  And `a / b * c` is evaluated as `a / (b * c)` — measured, `0.02 / 0.375 * 1000000` gave
  five hundred-millionths — so parenthesise every chain of two operators. And `GROUP_CONCAT`
  over an IRI binds nothing — no column at all, measured — where `GROUP_CONCAT(STR(?x))`
  binds; `find_wants` reads a want's several abouts that way and `test_wants.py` pins it. It is the
  same family as the empty-result trap above, arriving through arithmetic and aggregation: measure an unfamiliar operation on a
  literal before building a column on it, and pin what you measured — `tests/test_desires.py`
  does, so the day the engine grows the operation the guard says so.
- **`build_agent` does not run the boot gate.** The fixture patches `validate_agent` out of
  the boot unless a test passes `validating=True`: the gate raises or passes and changes
  nothing else, it cost two seconds of every boot, and it was paid about 250 times a run to
  say the same thing about a store built from the ratified files. A test that expects
  `BeliefsInvalid` from a built agent gets none — say `validating=True`, or build the
  `Agent` yourself as `test_shapes` and `test_hanoi` do.
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.
