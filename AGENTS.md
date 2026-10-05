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
  `tests/fixtures/vocabularies/` for the external ones) actually declare. **Seven types, and the one to reach for is the one that answers what KIND of
  thing the page is:**

  | | |
  |---|---|
  | `Decision` | why the code is as it is. Closed by nothing; superseded or amended |
  | `Domain Concept` | a **thing** in the model — a claim, a good, a step, a world |
  | `Process` | something that **happens**, with phases and an end — an auction, a round, onboarding |
  | `Role` | a kind of **principal** with something at stake — an agent, a supplier, a dealer |
  | `Service` | a part of the implementation that **holds logic** — the deliberator, the revision seam |
  | `Repository` | a part that **passively holds data**, scoped to one agent — the belief base, the imaginarium |
  | `Runbook` | how to **operate** it |

  The split was asked for by the pages: `auction` opened "an auction is a PROCESS", `bid-matching`
  called itself "the STEP that…", `onboarding` "the PHASE between…" — three pages naming their own
  type in prose because the field could not hold it. **A type that falls to one member is a type
  to fold back**, not to defend: `Capability`, rule 2's unit, fell to none once the dictionary was
  filed by package, and folded (#828); the rest stand at 41 / 8 / 7 / 4 / 3 / 3, concept to repository;
- a **decision** additionally carries `status` (`accepted`, `superseded`, `superseded-in-part`)
  and `timestamp`, and a superseded one carries `superseded-by`. **No other type carries any of
  those**: a concept, a process, a role, a service and a repository have no state to be in,
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

**`knowledge/domain/` is the shared dictionary, filed by the package that owns each word** —
`kernel/`, `sensing/`, `transport/`, `belief/`, `prediction/`, `planning/`, `execution/`,
`speech/`, `market/`, `actuation/`, `onboarding/` — and `tests/test_knowledge.py` holds a page to
live terms in its folder's namespace, so retiring a term fails until its page follows. A record
stays in `knowledge/decisions/` while something current cites it; 0.1.0's are filed under
`decisions/0.1.0/`. **And a term is defined before it is used.** The
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
it is a record wearing a bullet. The commit messages carry what each change did and why, at
length; a line here carries only the rule, and names the record or the issue where the argument
lives. The file was 18,000 words once, and every coding session paid for all of it.

### Words, records and the bundle

- **An RDF URI beats a homemade id for referring to an agent**; the one short string left is the
  one that must also be a broker principal, a bucket, a container and a directory — and a sensor
  or a subject goes by the local name of its IRI in the series, since a stated id equalled it in
  every world and was missing in the one that mattered, which got no readings dashboard (#885).
- **A term nobody reads is annotation**, however many instances state it.
- **A word used before it is defined is a word everyone defines differently** — `duty` ran to 64
  code sites and 13 pages, meaning `obligation` all along.
- **Desire is bouletic, obligation deontic, availability alethic, freshness epistemic** — different
  logics rather than strengths of one, so an unmet want is a gap and an unpaid debt is a breach.
- **A repository holds data and a service holds logic**, and a thing that decides nothing is a
  repository's support function; deciding nothing is the finding, writing no graph only the hint.
- **A repository is a collection of domain objects, not a store, and nothing here is one any
  more** — `Wants` and `Desires` became functions over a store; `Store` is infrastructure.
- **Verify a claim in the bundle against the code before repeating it**; nothing gates prose
  against the thing it describes, and a dictionary nothing holds to the code rots in the present
  tense (the-knowledge-is-filed-like-the-code).
- **A rename is done when the suite says so**, not when the thing you grepped for is gone.
- **A word-boundary sweep bites a hyphenated slug and a variable named after the word** — hold out
  the words that merely contain the letters first, and let the parser and the suite find the rest.
- **Search every tree that loads the vocabulary before calling a term dead.**
- **A record earns its place by refusing something**; "we could have not done it" is not an
  alternative, and a record is engaged by its premises, not cited by its conclusion.
- **A graph class is named for the rows it holds, may not say how a graph arrived, and a retired
  spelling may return with a different claim** — a second spelling for one thing is the synonym
  the dictionary refuses.
- **A package's words are the package's, however long the kernel spoke them** — `market:dischargedAt`
  is the market's, and the kernel names no word of it (#635).
- **A term belongs to the package that owns the concept, and the kernel keeps what packages meet
  at** — `orexis:Action`, `orexis:takes` and `orexis:PredictionGraph` are the kernel's; one word is
  one concept, so `planning:spent` and `planning:costs` are two.
- **The core's word has priority, and a package speaks around it** (#640).
- **"Ledger" is the market's word, for the book of what an agent owes; the intentions are called the
  intentions.**
- **Never count what a class answers for** — a test that asserted eight public graphs meant "as
  many as there are today" and went red over a change it was not about.

### Desires, wants and the derivation

- **A search is never handed a DESIRE** — what is pursued is a WANT derived from one, with a
  binding of its own; the desire is universal, the want existential and one-shot (#618).
- **Nothing stands between a desire and a want** — `derive_wants` judges every desire at the present
  and at each foreseen instant and mints a want per cluster of what the met-tests read unmet, in one
  function; `scope_actions` writes the scopes at boot.
- **A want exists because its desire read unmet, so the same rows withdraw it** — against the whole
  decomposition, present and foreseen; a want a plan is walking is kept whatever its desire reads.
- **A want is judged by its met-test, and nothing scores a world by degree** — the search sees no
  partial progress, and the met-test is the one judgment path.
- **A met-test asked by band says it once per way of failing, and tests no topology** — a reading is
  the band it is in; a test that walked the topology would be met by moving the sample off the
  subject.
- **A want is authored positive and the kernel writes the negation** — rows are existential and a
  want universal, so one compiler turns the shape inside out, held to the judge by parity.
- **The desire owns the term and the package owns the COST** — what the pattern means and that the
  estimate never overstates are promises about the package's own actions.
- **A want's estimate is the desire's with `$this` bound to its instance, and `$this` stands where a
  name and a variable are both legal** — a pattern's subject or a `BIND`'s argument, never a projection
  or a `GROUP BY`; the desire's sum over every parcel read six for a want about one, and the other
  van's drive tied the frontier (#893).
- **Nothing ranks a want before the search that could rank it** — `Planner.plan` searches every
  want it is handed, and what compares a thirsty fern to an overdue debt is what their plans cost.
- **A want states no time semantics of its own** — the KIND is its type, the INTERVAL its graph's
  period, the INSTANT `planning:holdsAt`, the FAMILY its graph's classification (#681).
- **A kind is a type, not a binding**, and **`planning:Want` is not a subclass of `planning:Desire`**
  — the closure is materialised at genesis, and the axis only made `?d a planning:Desire` match both.
- **Standing versus occasioned is the axis, and who wrote it is provenance** — three worlds ratify a
  WANT directly, and it is handed to a search like any other.
- **A want is one-shot and carries where it has got to; a desire has no stages** — each state
  written by whoever DECIDES it, never inferred, and a terminal state is an invariant (`Done` is
  never left) rather than an ordering rule.
- **Deciding a thing is finished and clearing it away are two acts** — `forget_wants` is garbage
  collection over whatever is `Done`, on the pass.
- **What was foreseen may arrive early, and the present outranks the instant** — a cluster unmet
  now whose want still names an instant is re-minted at none, same name.
- **A want is weighed in the ground holding at its instant, and a pass searches the wants holding
  at any instant it can see** — weighed in the present, a want minted for a foreseen crossing read
  met and was withdrawn in the pass that minted it, every pass, and the forecast never became a
  dose (#858).
- **A fallback is held to the case it was written for** — one want about everything a desire is
  about is for a desire UNMET NOW whose select yields no rows.
- **A want somebody else sourced is still an INSTANCE under a standing desire** — a host holds
  *no unanswered calls* over its venues, and the call is the row that desire is about.
- **A capability that asks for a derivation is not minting** — the ledger writes a debt and its
  prediction and calls `derive_wants`, so a claim arriving is a want arriving.
- **A desire is met when a shape holds or unmet when a select binds, one of the two, and `weigh`
  judges either** — `planning:unmetWhen` was declared, carried onto wants and compiled since #468
  and weighed by nothing, so the dispatcher's aversion shipped as a shape named for the good state
  wrapping the select of the bad one (#892).
- **A shape over instances says each block is about `sh:this`, or two instances are one want** — a
  witness about nothing joins every cluster, and the dispatcher's two parcels were one want searched
  over both vans' every move, 674 candidates where a want per parcel costs 90
  (a-parcel-astray-is-a-want-of-its-own).
- **One mind couples the wants a constraint can make collide, and searches them as one** — a
  constraint's footprint, read as a scope's is, says which wants' plans may interfere; those are one
  cluster, one want, one search, optimal for both by construction, and the invariant is weighed in
  every possible world to refuse one that newly enters it; a walking want is reconsidered when a want
  the footprint couples to it arrives; two minds optimize alone and meet through prediction, the
  market and execution; sequencing the elder plan as the younger's ground was refused as the two-minds
  tool used on one (#567, one-mind-couples-the-wants-a-constraint-can-make-collide).
- **A desire weighed in a ground and a want weighed in a possible world are one judgment at two
  grains**, and `planning:Weighing` carries the `planning:violation` rows for either.
- **A derivation asks nothing the met-tests do not answer** — how far ahead the agent sees is the
  horizons each drift predicts at.
- **Two readings of one met-test are not a duplicate when the compiler, the source and the cache
  all differ** — the derivation wants witnesses and caches nothing; the kernel lifting a ratified
  want wants a boolean and caches per want.
- **A criterion is an argument, never a name** — `find_wants(store, desire=…, derived=True)` says at
  the call site what five Spring-Data finders hid; the one distinction worth a name is the answer's
  SHAPE.
- **A model is a Python type only where something READS its fields**, and **gets its own file when
  it is cheaper alone** — `Want` is both; `Desire` was built from a query and discarded.
- **The function that decides a thing owns writing it, and a read only reads**; a read over stored
  rows is handed a store, a read over contributed answers the agent, and a read is handed a store
  and nothing else because an agent id is another aggregate root's identity.
- **A long-lived object and situational data about it is one shape three times, and only
  testimony is kept** — the observation is stored because it IS the premise; a judgment and a step
  are conclusions whose premises are stored.
- **A synchronous twin of a pass is a second pass, and it drifts** — one pass the runtime and a
  test both call (the executor's `tick` and `drain`) is what stops that.
- **A pass begins in one place, and judging happens once in it** — `Planner.plan` derives every
  pass, so no row goes stale for want of a re-judging.
- **The layer that waits does the waiting, and a package has ONE way in** — a module keeping its own
  timer has rebuilt the middle layer inside a capability (a-package-starts-itself).

### Planning: the search

- **A plan is placed at the instant of the root it was found from, never by subtraction from a
  deadline** (#625), and **what a search may see at a future instant is the instant's to say** —
  a round is a graph holding during its period (#620).
- **A round is the allocation under scarcity, and what makes buying available is a fact that holds
  at the instant the search stands at**; a plan waiting at its last step is in progress.
- **A ceiling on compute is stated in the unit the search spends** — a budget of worlds, sized from
  a measured cost per fork; a search the budget cuts short is finished by the passes after.
- **A prune is only as good as when its bound arrives** — an admissible estimate refused nothing
  under breadth-first and sixty percent of the courier's forks under best-first.
- **An estimate counts every step the want is certainly owed, not only the ones that move** — the
  courier's counted drives and not the pick or the drop, admissible and loose by two at the root,
  where fourteen of the twenty-four weighings laid at the one scope's door were its slack (#898).
- **The estimate rides on the weighing, and the frontier is A\* by reading it** — `planning:remaining`
  is written where the world is weighed; a want with no estimate is uniform-cost.
- **An action that touches nothing the want reads is never simulated, and the closure is what makes
  that safe** — closing backward through preconditions keeps the bid that makes the dose possible.
- **A scope's worlds admit the scope's actions alone**, a want is placed by what it reads that some
  action can CHANGE, **a type pattern reads its CLASS**, and **a partition of the vocabulary belongs
  to the store, not to an agent**.
- **A scope is a predicate on a KEY, read per filling off what the world alone binds** — a pump and a
  heater writing one predicate on two readings are two scopes by the property each is keyed by, one
  again where a lever reaches into the other's; a term places a want only where its predicates place
  it nowhere, since the puzzle's peg is a cell the van drives to (a-scope-is-a-predicate-on-a-key).
- **A scope admits a FILLING, not an action, and a scope's imaginarium holds the scope's readings** — a
  lamp's heating is admitted in the light's search alone though the action is the air's too, a due
  head is judged where its filling was admitted, and a reading keyed by another scope's term crosses
  into no imaginarium but its own, so a world is one percent of the present and a sensor added
  elsewhere adds nothing to it (`world/greenhouse/tests/test_scaling.py`).
- **A member is in every scope it falls in, and a reading, a witness and a want are placed where
  the scopes of what they name MEET; a member of every scope tells nothing** — the bed is the pump's
  and the heater's, the soil both pumps', a reading naming both the one pump's; so two beds each
  with a pump are two wants under the grower's one desire, each keyed by its bed off the violation's
  offending value, since the shape cannot say which bed came down its path
  (a-scope-is-a-predicate-on-a-key, `world/greenhouse/tests/test_two_beds.py`).
- **A variable in predicate position writes what a `VALUES` block in its own text binds it to, and
  anything only where nothing bounds it** — the one range the scopes honour is SPARQL's own.
- **What a fork may skip is bounded by what a rule may READ, never by what a step changed** —
  narrowing was measured and not taken, since a real pass forks for 0.1% of itself (#662).
- **A rule does not say which world it reads; the list the runner builds says it instead** —
  `GRAPH $state` was one package claiming what every other package's actions can change (#666).
- **A/B on this bench is alternated within one session or it is not a measurement** — the Pi drifts
  twofold between invocations (#666).
- **A level is a vocabulary, and the hierarchy is found in the rules a world combines** — a step
  whose predicted fact a bridge concludes is refined, and nothing marks an action abstract
  (the-hierarchy-is-found-in-the-rules); **a step is refined only where it would be fictive**, and
  **a refined step's goal below is the world it lands in, not its diff**.
- **A method is walked, never searched**, and **a plan that worked is kept, and the world verifies
  it, not a search** — every step is checked when it is taken.
- **A step is an action PICKED for execution** — a world merely ADMITS one per action per legal
  filling and the search picks (a-row-is-a-step); **an action declares what it is filled with, and
  the kernel names no column** (an-action-takes-parameters).
- **An action is a precondition, an effect and an implementation, and the effect is rules** — the
  effect deletes because a possible world is where taking something away is the point; the
  never-delete rule is belief revision's.
- **An effect is one declaration** — the diff the search planned on rides on the step and is what
  the world is held to; **a kind said by absence is a kind two readers disagree about**.
- **Deliberation is on triples, and a number is not special** — the core compares triples and
  interprets no literal; **an interval is how this project says it does not know, and membership
  in one is CRISP**.
- **A step is sized when it is taken, from the present, and the search only says the side it
  reaches** — the `execution:Command` runs over the beliefs as they stand.
- **A step lands when the world can SHOW its effect, and a landing is a BAND** — the least and the
  most, so a dose lands within a cadence of the step, a market act when its round's window closes,
  both ends agreeing; declared as nothing, a step landed the instant it was taken and failed a
  patience later. **A `landsAfter` text that will not parse is read as nought**, so probe a
  declared figure on the plan it places, never only on the outcome.
- **A possible world holds over the period its path's bands sum to, and a step carries both ends**
  — the executor looks from `landsAt` and gives up a patience past `notAfter`
  (a-landing-is-a-band-and-a-world-holds-over-a-period).
- **A world is forked from the ground holding at its earliest landing, with the path replayed
  there** — forked from its parent, a fill landing after a predicted drain read eleven where the
  world would read nine; a landing straddling a boundary is judged at its earliest alone, which is
  what #596 still asks.
- **A step lands as long after it is taken as its plan placed it after its opening.**
- **A want's view is parsed off its met-test, never declared beside it**, and a want spanning
  scopes is searched in the first of them.

### Planning: the imaginarium

- **What a pass worked out about a world for a want is a WEIGHING, and the frontier is a query** —
  a candidate passed over is weighed too, so a pass can be continued.
- **A pass weighs its grounds, and a candidate is weighed where it is taken** — weighed in the pass's
  own loop, the candidates a budget left untaken were never offered to the expansion.
- **A possible world is kept, and its diff was a memo** — a world's readings are a handful of quads
  against the thousands a pass copies once (#481).
- **The one function over TWO stores is the filling of a possible world** — narrowing what crosses
  fails silently, since a pattern reaching a graph nobody copied returns an EMPTY RESULT.
- **A function over the store is handed the engine and nothing else**, and **a function of the
  planning package starts in the store and ends in it, taking the names of what it is about** —
  `weigh(store, want, world)`, `take(store, candidate, me)`.
- **The planning package is a star, not a chain** — the `Planner` sequences the acts, an act calls
  no other act, and what one needs of another's work it reads off the rows the other wrote.
- **A module named for an act exports that act alone**, and **public means tested** — outside
  `agent/planning/` the one name imported is `Planner`.
- **The imaginarium outlives the pass, and the present is identified in it by hash** — `reroot`
  keeps the cone under the match and drops the rest; a surprise matches nothing; a name is never
  trusted (the-future-is-a-cone-and-the-present-is-identified-in-it).
- **What crosses into the imaginarium is taken back before it crosses again, and what the store
  made for itself stays.**
- **A possible world is named by a mint number and the path to it is rows** — a name that joined
  its path collided once, needed escaping, grew with depth and was read back by nothing; the
  counter is the store's, so a cone kept across passes is never named over (#486).
- **A want an intention is walking is neither searched nor handed down again**, and **a plan whose
  want is gone is nobody's**.
- **A prediction is a diff, and only a ground has applied it** — one reader answers the derivation
  and the search (`world_at`), and refuses a store with no ground.
- **A world speaks for its readings' revisions**, and **the search runs no rules, so a reading's
  revisions travel with it and an effect speaks the concept they conclude** — a revision is a belief
  and a drift's prediction is not, which keeps the foreseen reading out of the present.
- **A graph forgotten takes its revisions with it, and an orphan revision is a side with no
  reading** — one said `below` for a day in every possible world, and the dose read unmet in the
  world it made; `forget_graph` forgets `revisions_of` first.
- **What a plan changed is read off the signature, never off node identity** — a key is changed
  when its canonical facts are (#643); **a retraction is canonicalised like an addition** (#619).
- **A read that finds the catalogue by its row and then asks OPTIONALs inside that group is
  evaluated per named graph** — ask the catalogue's name once (`catalogue_of`) and splice it; and a
  read asked per iteration is sized by what the iteration opens.
- **A `NOT EXISTS` is evaluated per row from its FIRST pattern, so the bound variable goes first**;
  an act that admits a world it already admits is idempotent by FILLING, not by name.
- **A prologue goes at the head of a joined update, and the engine refuses one after `;`.**
- **A read of the clock is a tick in a test** — a pass hands its own instant down.

### Execution

- **The executor owns the intentions and alone writes them**, and its two doors are `tick` (the
  heads due) and `drain` (each step taken); **an intention's steps are its own**, tagged at adoption.
- **The world moves an intention, and the executor only says what happened** — a taken head waits
  at its `landsAt` for the present to hold what it predicted, fails a patience past it, and an
  action with nothing to answer with is FICTIVE and writes its own prediction.
- **A step whose command answers nothing is not taken** — recorded taken, it waited out its
  patience as though the pump had run (#869).
- **A fact stated and not asserted is a graph of a kind no reader of the present is handed, and a
  diff of two graphs is one `FILTER NOT EXISTS`** — a step predicts in `execution:adds` and
  `execution:retracts`, the engine fills them, compares the present to them and writes a fictive
  step from them; a JSON literal of triples in a triplestore could be queried, abbreviated and
  compared by nothing (#759, a-steps-prediction-is-two-graphs-it-names).
- **Planning and execution meet at the store and signal each other** — a plan is published once
  and an intention adopts it by reference; a plan begun is walked to its end
  (planning-and-execution-meet-at-the-store).
- **A committed step is a belief over its landing window, and a drift reads it there** — the
  executor writes each adopted step as an `execution:CommittedStepGraph` holding from its
  `notBefore` to its `landsAt` plus the patience, closes it when answered or ended, and prediction
  hears every belief and rewrites every key for one that is no observation; a later want is then
  searched against a future that contains the earlier plan (#849, committed-step).
- **The executor walks when the present changed, not when anything was revised** — a prediction or
  a committed step revised answers no step, and a walk on it read the clock for nothing, which on a
  test's clock is seconds the round could not spare.
- **A lap is from the last mark, so a part that marks one inside a drained job takes the drain with
  it** — the walk a revision queued read sensing's 52 ms as `execute` and the pass's `drain` as
  nought; only the walk a pass asks for marks the lap (measure-a-pass).
- **An action is a point its taker contributes to**, and a taker missing at runtime looks exactly
  like an actor that is busy, so a gate holds a family to its actions.

### Belief, sensing and prediction

- **A rule concludes and never deletes, and what replaces a revision is its source rewritten** —
  the revisions live in a graph derived from the source and go when it goes; the rules are SHACL's
  draft adopted as it stands (`agent/belief/revise.py`).
- **A graph is revised beside what the world states and nothing else** — revised beside everything
  believed, the first of two readings took the second's side.
- **Any belief is accepted, and revised** — dropping testimony over a shape is a gate wearing
  revision's name; **a state that served a gate goes with the gate**.
- **Revision's ceiling is a budget in rule executions, and a source the budget cuts short is
  continued by the next pass.**
- **A belief kind enters through `propose`, and a package's working graph is not a belief.**
- **Sensing observes and says when a sensor has gone silent, and prediction is a package of its
  own** — `received` writes one `sosa:Observation` per sensor holding until the next is due and a
  grace past it, `missed` says `sensing:silentSince`, the sides are revisions; `agent/prediction/`
  accumulates the drifts' rates and imports nothing of sensing.
- **A limit on how long a sensor may be silent or stuck is the agent's, stated of it by its world,
  and the figure in code is what holds where it states none** — `sensing:silentAfter` and
  `sensing:stuckAfter`, read as a cadence is; where an agent's word about itself lives is #876's.
- **A reading late is not a reading missing** — ended exactly at the next one's due, a late reading
  left no present, and a dose sized from it commanded nothing (#870,
  a-reading-late-is-not-a-reading-missing).
- **A sensor that keeps reporting one number is stuck, and age is not the only doubt about a
  reading** — each observation carries `sensing:unchangedSince`, the start of the unbroken run of
  its raw number, and `received` says `sensing:stuckSince` once the run has lasted `sensing:stuckAfter`
  cadences, in a state graph the first differing number takes back; identical is the raw number,
  since a clamp can make two counts one reading, and a count that creeps is the other two
  detectors' (#462).
- **Sensing speaks SOSA and SSN, and declares only what they lack** — the observation graph's kind,
  the silence, the sides and the pipeline's words; a transport hands `received` bytes and sensing
  knows no transport.
- **An observation is concluded from the number a sensor gave** — its quantity through the scaling,
  its reading through the calibration, then its sides
  (an-observation-is-concluded-from-the-number-a-sensor-gave).
- **A drift answers a rate, and a prediction accumulates them** — rates add, a happening is where
  one may change, a crossing is on a straight line (a-prediction-accumulates-rates-between-happenings);
  the observation in hand is read at every instant with its revisions, since a drift sized from a
  reading reads it past the stretch the observation holds for.
- **A prediction is bands, and the width never leaves the rule** (#642); **the mind wakes on
  contradiction, not on time** — a reading inside the bands leaves no mark (#632).
- **A step's band is the prediction from its landing, and a reading is compared once** (#639).
- **The claims a host issued are its demand** — a debt with a window is an occurrence about the
  window (#626).
- **A forecast is a series a sensor reads, and a public service's address is wiring** — one graph per
  stretch, the HTTP member polls, the location lives in `secrets/` (a-forecast-is-a-series-a-sensor-reads).
- **Several transport members are one to the container** — a message goes back to the member that
  queued it, a command to the member that `reaches` the device.
- **The transport speaks MQTT4SSN, and a topic is named by the filters that match it** — the agent
  subscribes by the pattern and publishes to one with no wildcard; the broker's address stays in the
  environment.
- **A peer's word is a document, believed as it stands where it is state**; **the market is files** —
  six actions whose `execution:Saying` operations make the documents at take time (`domains/market/`).
- **Signing is between agents, and an agent trusts itself** — the broker's ACL already admits only
  the holder to its devices' command topics.

### Graphs, the store and the runtime

- **A graph's name is for eyes, and code relies on its classification alone**; **a graph is
  classified per kind it HOLDS**, and a graph holding two kinds is two graphs.
- **One graph describes every graph and itself** — the catalogue, found by its own row, created by
  genesis alone.
- **A reader states the kinds it reads, and the store decides nothing** — a query is handed its
  graphs, `graphs_of` answers by kind and instant, and the union of everything was refused as the
  default.
- **An update takes no dataset** — what chooses which graphs are the world at an instant is Python
  or a materialised view.
- **What ends by the clock is a graph with a period, and one sweep drops it** — what the ending
  MEANS stays the owner's (#645); **a row whose presence is meant to BE a fact is named for the
  state, not for the instant it ends**.
- **A base class is an import and an annotation is not** (#455).
- **A verdict the search reads is a query, and the judge stays at the gates.**
- **The present is identified among the root's children, never asserted from one.**
- **The agent keeps one timeline, and its clock may run fast** — `clock.now()` is the only read,
  the pace is a deployment fact converted once where something sleeps (#646).
- **A document says which graph it is, and the file's name is for eyes**; **a document's kind says
  who reads it**, and `orexis-onboard` refuses a graph no reader declares
  (a-documents-kind-says-who-reads-it).
- **A world's words are its own or a domain's it imports** — `owl:imports` names the graph it
  brings; **a vocabulary two worlds speak is a domain**, and the shapes are `planning:ShapesGraph`.
- **A graph of actions is an `orexis:ActionGraph` and a graph of drifts an `orexis:DriftGraph`, and the
  planner and the predictor read each from those alone** — typed bare `orexis:PublicGraph`, every public
  graph was scanned for them; and the drifts' kind is the kernel's, not prediction's, because prediction's
  premise finds the drift rows before prediction is loaded, and a kind only it declared left it unloaded.
- **A package beyond the mind is loaded where its premise, read off the world, holds** (#824).
- **The runtime stops when no desire is held, no transport reaches it and every want is reached** —
  wants standing with nothing walking is `planning:Exhausted` or unreachable; a clock that does not
  tick is a test's mistake.
- **A package starts itself, and the runtime is a lifecycle container** — each part says what it
  does by jobs it submits, kinds it hears and timers it asks for (a-package-starts-itself).
- **A process is the AGENT with the id it was told, never whatever carries that id.**
- **The 0.2.0 kernel's T-Box is what the tree reads**; **0.1.0 was amended into 0.2.0, not copied,
  and then retired whole** (2026-09-26), its vocabulary kept under `tests/fixtures/retired/` for
  the bundle's history alone.
- **The plant's surroundings are one domain** (`climate:`), and actuation is the other.
- **A case is held to the whole store it leaves, never to a reading of it** — a behaviour change is
  a diff regenerated by a flag and reviewed by eyes.

### Deployment, onboarding and operating

- **A broker's address is the world's to assert or the installation's to allocate, and the agent's
  to be told** — asserted wins, derived completes, a collision is refused (#827, #823).
- **What the documents leave out is derived into a document, and a renderer only formats** —
  `infra/installation.derived.ttl` is committed and held to a fresh derivation (#827).
- **A world's wiring is its society, and its world graph speaks no MQTT4SSN** (#823).
- **An agent's own documents are under `beliefs/<id>`.**
- **A step of onboarding runs where the world has what it serves, and says so where it does not**
  (#824).
- **The simulator is a process of the world, not a pretend board** — it plays every system marked
  `sim:simulatedBy` from the world's own words, and sleeps until the next reading is due in the
  world's time (`simulation/`).
- **A simulated instrument keeps the premise its detector states** — the number published strays
  from the model's reading within the model's `sim:jitter` and is never the one before, since the
  physics moves only what something moves and sensing read a quiet thermometer as stuck (#879).
- **Hardware is the firmware generator's input, and no vocabulary types it** — `hardware.ttl` is an
  `onboarding:HardwareGraph`, a kind no agent loads (#820).
- **A series is watched and never believed, and the package that decides a thing shapes its
  history** (#822, #825); **metrics are the admins' instrumentation, so they are code and not
  model** (#826); **metrics and history are what events say, and no package imports either**
  (metrics-and-history-are-what-events-say); **a metric is optional at every level and aggregated
  where it happens**.
- **Reflection reads the series and never the beliefs, so a figure it lacks is a point the agent
  does not yet write** — the raw count rides beside every reading and `doubted` names the sensor
  where `silence` counted, and `orexis-explain` answers the fixed questions over the two buckets
  (#894, reflection-is-genesis-run-again-over-the-series).
- **A CRL is always written, empty where nobody is revoked, and its horizon is the authority's** —
  `crlfile` makes OpenSSL demand a CRL from the issuer on every handshake, so a config naming an
  absent file or a CRL past its `nextUpdate` refuses the whole society and not the one agent; and
  taking an agent away is not the mirror of adding one — a re-run reports what the wiring no
  longer implies and `--revoke` takes it, keeping the bucket, since history that was true stays
  (#28, #29).
- **A guard asked `in text` is answered by the comment that names the option** — the test for the
  `crlfile` line stayed green with the line struck out, because the config's own comment spelled
  it; a directive is held to by whole lines.

## The rules the code lives by

1. **Code may reference T-Box terms; never an instance.** `planning:Desire` is fine;
   `"supplier"`, `"sensors/fern/moisture"`, a world's `:world` node are not. The single exception
   is the one identifier a process is handed at boot: its own agent id. Everything else is
   discovered from the documents. See [capability-packages](knowledge/decisions/capability-packages.md).
2. **A package is a directory of `agent/`, and a term lives in the namespace of the package that
   owns the concept.** belief, sensing, prediction, planning, execution, speech and the MQTT
   transport each declare their words in their own `ontology.ttl`, beside the code that reads
   them; the kernel's `orexis:` keeps only what packages meet at. A package imports what lies
   beneath it and never above — the mind imports nothing of prediction, and outside planning the
   one name imported is `Planner` — and each package's layout test holds it to that.
   `agent/runtime.py` is the container that assembles them all. **A domain is documents and no
   code**: `domains/<name>/` holds a vocabulary, its actions and its rules, and a world imports it
   with `owl:imports`. Adding a way of acting is a node in a domain's `actions.ttl` — a
   precondition, an effect and an implementation — and nothing else.
3. **Nothing in `infra/` is world-specific.** It holds the services and what is true of the
   installation: the broker image, the installation CA, Grafana's material, the admin token. A
   world's broker config, its ACL, its certificates and its device credentials live with the
   world. Also: **no `.env` at the repo root, because nothing there is true of every world at
   once.** `infra/installation.ttl` says where the shared services are — the series store's URL
   and org, the images, and the pool a broker's ports are allocated from — and nothing secret;
   onboarding writes what an agent needs of it into that agent's environment, and derives
   `infra/compose.yaml` from it. What it allocated, `infra/installation.derived.ttl`, is the one
   document that names worlds, because a port is unique across the host and only the installation
   sees the host; a world names none of it and never learns what the others were given. What an agent may *do* with
   the store and the bus arrives as its own credentials, minted per agent into
   `world/<name>/secrets/` and mounted into that container alone. The admin token lives apart
   from both, in `infra/secrets/`, and no agent ever holds it. See
   [series-and-bus-isolation](knowledge/decisions/series-and-bus-isolation.md).
4. **There is no shared store.** A world is documents; each agent builds its own belief base
   from them at boot and holds it in a volume of its own, so isolation is structural rather than
   enforced. An agent is told its id and given one world, mounted — it never learns that other
   worlds exist. See [where-the-belief-base-lives](knowledge/decisions/where-the-belief-base-lives.md).
5. **There is no config file for the model.** Topology lives in the world's documents, desires
   in each agent's own `beliefs/<id>.ttl`, both authored in `world/<world>/`. Deployment facts
   (service URLs) are environment, because they are not beliefs anyone holds. See
   [world-graph](knowledge/decisions/world-graph.md).

**What an agent BELIEVES about all of that is settled by one test: model it only if a belief
about it would change which plan gets selected.** Everything else is telemetry — logged and
reported, never believed. Anything the interpreter already knows is COMPUTED and never
asserted; what comes from outside is stored; and beliefs about other agents stay first-order —
what they SAID, never what they believe. See
[model-it-only-if-a-plan-would-branch-on-it](knowledge/decisions/model-it-only-if-a-plan-would-branch-on-it.md).

**And a SECOND axis, orthogonal to that one: the agent stack** — network, transport,
translation, the belief-revision seam, mind — sliced by representation rather than by timescale.
The transport has no position on the cognitive axis at all; an infrastructure failure becomes a
belief only by explicit modelling; and a peer's message is a speech act, not an observation, so
it takes a different path through translation — sensing for an instrument's bytes, speech for a
peer's document. See
[the-agent-stack-is-a-second-axis](knowledge/decisions/the-agent-stack-is-a-second-axis.md).

**A package starts itself, and a pass drains, on one thread.** The runtime creates a part of every
loaded package that has a `create` module, the mind's three among them, links the parts, then starts
them, and knows no word of what they do:
belief revises what is written, planning plans every pass and publishes, execution adopts and walks,
a transport listens or polls, sensing asks after what has fallen due, prediction answers an
observation — each through jobs it submits, timers it asks for and the signals of the parts it
linked to (a-package-starts-itself, planning-and-execution-meet-at-the-store). A pass drains every job queued,
then what is due; the run ends when nothing holds the agent. A search is bounded by a budget in the
unit it spends and continued by the next pass. The executor's two doors, `tick` and `drain`, are
what its walk and a test call.

**One principle explains most of the shapes above: control the derivative, not the value.**
Nothing here dictates an act — a cadence not a reading, a range not an aim, what is available
not the act taken, the step's effect and not its size. When a change you are making reaches DOWN
a level (a search setting a price, a world file pinning an aim, a model emitting an action),
stop: that is the one move this architecture refuses everywhere. See
[control-the-derivative-not-the-value](knowledge/decisions/control-the-derivative-not-the-value.md).

And one that catches people out: **there is no default world** — every command takes one as a
required argument and refuses rather than guessing, because a fallback puts a misconfigured
agent on the same topics as the real one.

## Start by reading the open issues

`gh issue list`. What is known to be wrong is tracked there, and several of the sharper questions
about this project are already answered in one. Re-deriving a known defect is waste; discovering
that your question is a recorded seam is a real answer.

Two roles are defined in `.claude/agents/` — `deliberate` for thinking a question through and
writing down the outcome, `implement` for carrying out something already decided — and two skills
in `.claude/skills/`: `snapshot-tests`, for the case suites, and `author-a-world`, genesis as a
procedure. They say what a role does and what to run; this file says what is true of the project,
and it wins wherever they seem to disagree. **A skill or a role is a procedure, so it names no path
that is not there**: `tests/test_knowledge.py` reads them as it reads the bundle, with no exemption
for a retired tree, since the snapshot skill pointed at the retired `packages/` tree for a week.

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
pip install -e ".[dev]"

orexis-onboard <world>       # ONBOARDING: load the world as an agent boots it, derive what the documents
                             #   leave out (a broker's port, into infra/installation.derived.ttl),
                             #   then grant everything below the world has something for.
  orexis-influx <world>      #   a history bucket per agent, a metrics one where the world is monitored, each with a token that opens only it
  orexis-mqtt <world>        #   a credential per principal, and the broker ACL, derived — where its society names a broker
  orexis-compose <world>     #   generate world/<world>/compose.yaml from that world's roster, the broker only with a bus
  orexis-dashboards <world>  #   a Grafana folder per world: what its agents observe, and their health where monitored
orexis-explain <world> <agent>  # REFLECTION, not onboarding: one agent's season from its two buckets, the fixed
                             #   questions answered in the world's words, read with the admin token and never a volume
orexis-firmware <world>      # a board's config.h, from the world it belongs to
orexis-infra-certs           # INFRA, not onboarding — the services' certs and whom they trust
orexis-infra-compose         # INFRA — infra/compose.yaml, from infra/installation.ttl
cd world/<world> && podman compose up -d      # one container per agent
podman build -t orexis:local .                 # only when a dependency changes
pytest -q              # what testpaths names: agent/ and world/. No infra needed.
pytest -q tests        # the four files that read the whole tree: knowledge, layout, store, projects
pytest infra -q -n0    # 8 more, against the RUNNING broker and store — see below.
                       # -n0 is REQUIRED: they rewrite one acl.conf in place. It refuses without it.
lint-imports           # onboarding may import agent, never the reverse
```

`pytest`, `pytest tests` and `lint-imports` are the gates, and all must pass before a change is
done; a world is held to what it does by the tests beside it, and `orexis-onboard` refuses one
whose documents will not load. `pytest infra` is a third thing, run deliberately, and it is not
part of them — and it must be run `-n0`, because `addopts` carries `-n auto` for everything else
and those eight tests cannot share a broker. They refuse rather than letting you find out: see
`infra/tests/conftest.py`.

**`infra/tests/` is a contract with the infrastructure, not with the code.** It holds mosquitto
and InfluxDB to the behaviour the isolation design leans on — that a revoked grant stops delivery
to an already-connected client, that a rotated credential is refused at once, that one agent's
token cannot reach another's bucket. None of that is guaranteed by MQTT or computed by anything
here; it is how those two services happen to behave, so it is worth re-proving whenever they
change. Both files report the version they ran against and assert nothing about it: bump
`MOSQUITTO_VERSION` in `infra/mosquitto/Containerfile` or the Influx image in
`infra/installation.ttl` (then `orexis-infra-compose`), rebuild, and re-run `pytest infra -q -n0`.

**Onboarding is the phase between a ratified world and a running society** — see
[onboarding](knowledge/domain/onboarding/onboarding.md). Its generators all read the world as an agent boots
it and grant exactly what its wiring implies, so adding an agent and re-running `orexis-onboard`
is the whole of deploying one. They stay separately callable because rotating one service's
credentials should not touch the other's.

**Its code is in `onboarding/`, beside `agent/` and outside it, and that absence is asserted.**
`orexis-influx` reads the admin token, which opens every bucket and which no agent may ever hold,
so the surest guarantee is that the code using it is absent from the image. What keeps onboarding
out of an agent image is the `Containerfile` not naming it — `tests/test_layout.py` fails if a
`COPY onboarding/` appears — and `lint-imports` holds the direction: onboarding may import agent,
agent may never import onboarding. `orexis-influx` and `orexis-mqtt` need infra up;
`orexis-mqtt` must run before the broker will start at all, since its ACL is generated and
mosquitto refuses anonymous clients. It then **reloads** the broker itself (SIGHUP, not a
restart — connected agents keep their sessions), so adding an agent or a world still interrupts
nothing.

Beliefs are the agent's: **authored** once at birth from the world's documents, never touched by
start or stop. A volume lived in keeps the agent's own graphs and reads again only what a
document put in and nobody owns — the ontologies, the domains, the world's public graphs — which
is how an updated ontology reaches a running agent. Anything that would reset an agent's own beliefs on a
restart is a bug, not a convenience.

## Traps worth knowing, and one that is closed

**Ask what a thing IS; do not walk a subclass path.** The boot derives the `rdfs:subClassOf`
closure of every ontology graph into a graph of its own, and every catalogue row carries every
kind its class is beneath, so a text asks `?g a planning:WantGraph` and walks nothing. A seventh
hand-rolled walk was once refused for exactly that reason. See
[one-graph-both-engines-read](knowledge/decisions/one-graph-both-engines-read.md).

- **Name the graph CLASS, never an instance — and scope by MODALITY when you leave belief.**
  `?d a planning:DesireGraph` unions every instance of that class, exactly as `store.graphs_of(PUBLIC)`
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
  The 0.1.0 suite's provenance test refused a narrowed SELECT. See
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
  Every row carries every kind its class is beneath, so a text asks `?g a planning:WantGraph`
  and walks no path.
- **SPARQL prefixes.** Only what `store.NAMESPACES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `tests/test_store.py` checks this by scanning the source text of the agent, the
  operator's tools, the simulator, the domains and the worlds — and asserts each source tree is
  still *found*, because moving files has twice emptied one of its globs and taken cases off the
  guard without failing anything. **A text speaking words the store never loaded declares them
  itself**, `PREFIX name: <iri>` at its head as SPARQL says it: a domain's namespace is not the
  store's, so every action text, rule and desire select in `domains/` and `world/` carries its own.
- **A test that asserts inside a loop can assert nothing.** An empty result set is not an error,
  so the body never runs and the test is green. The repo-root `conftest.py` traces the at-risk
  tests — an `assert` inside a loop over something that could be empty — and fails the run if a
  test function executed no assertion in any of its cases. It does NOT catch a parametrisation
  that generated zero cases, nor a glob that still matches but no longer covers what it is named
  for; both have happened, and both are still found by hand. See
  [a-test-that-asserted-nothing](knowledge/decisions/a-test-that-asserted-nothing.md).
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
  nothing from a want that says "unmet while this fact is absent"; `footprint` reads both.
- **A `BIND` inside a `UNION` branch cannot see a variable bound outside the union.** The
  branches are evaluated on their own and joined with the surrounding pattern afterwards, so
  the tidy form — state the preamble once, then `{ … } UNION { … }` — leaves every outer
  variable unbound where the arithmetic runs. Measured on the courier's distance heuristic: it
  returned 0 for every world, no error and no empty result, which reads as "already arrived".
  Repeat the preamble inside each branch.
- **An operation this engine lacks binds NOTHING — it does not fail.** `duration / duration`
  and `duration * number` return unbound in pyoxigraph, and so does every cast of a duration
  to a number (`xsd:decimal(?a - ?b)`, measured on 0.5.9 and again on 0.5.11: only a dateTime's `HOURS`, `MINUTES`
  and `SECONDS` bind, so no rule can measure the stretch between two instants, which is why a
  committed step states its window's lengths in seconds beside the plan's instants), and so does
  `dateTime + dayTimeDuration` at about a third of the seconds of a minute — deterministic per
  instant, measured on 0.5.11, so a round said at an unlucky instant had no `closesAt` and its
  venue stayed open for ever — where `dateTime - dayTimeDuration` binds at every one, so an
  instant ahead is the instant LESS a negative duration (`- xsd:dayTimeDuration("-PT30S")`), and so does a decimal division whose
  dividend is an exact zero (`0.0 / 0.25`; cast the dividend to `xsd:double`), and so does a
  decimal PRODUCT past the engine's eighteen fractional digits (`0.5 * (0.02 / 0.375)`; round
  the repeating operand to six places first, as every derived number here is written), and so
  does an exact-zero decimal PRODUCT by a decimal (`0.0 * 0.5` bound nothing where `0.0 * 1`
  bound zero, measured in #642 — cast a factor that may be zero to `xsd:double`), so a
  column computed that way reads empty for every row and no query errors, no test goes red.
  And `a / b * c` is evaluated as `a / (b * c)` — measured, `0.02 / 0.375 * 1000000` gave
  five hundred-millionths — so parenthesise every chain of two operators. And `GROUP_CONCAT`
  over an IRI binds nothing — no column at all, measured — where `GROUP_CONCAT(STR(?x))`
  binds; `find_wants` reads a want's several abouts that way and `test_wants.py` pins it. And a
  `SUM(IF(?o = "failed", 1, 0))` over a row whose `?o` is unbound binds nothing for the WHOLE
  column, not nought for the row — coalesce first — while an `EXISTS` inside a projected aggregate
  is evaluated against the default graph, not the `GRAPH` block the rows came from; both measured
  on a metric's select (#826), and the planner's cone read still counts OPTIONAL rows for it. It is the
  same family as the empty-result trap above, arriving through arithmetic and aggregation: measure an unfamiliar operation on a
  literal before building a column on it, and pin what you measured, so the day the engine grows
  the operation the guard says so.
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.
