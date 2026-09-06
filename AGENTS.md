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
  | `Domain Concept` | a **thing** in the model — a claim, a good, an affordance, a world |
  | `Process` | something that **happens**, with phases and an end — an auction, a round, onboarding |
  | `Capability` | a named ability with **interchangeable implementations**, granted by its own premise and provided by a package — rule 2's unit |
  | `Role` | a kind of **principal** that holds a stake — an agent, a supplier, a dealer |
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
pages there fix what our words MEAN — affordance, gap, imaginarium, capability, action, lot, venue
— and a discussion, a commit message, a docstring or an issue that uses one of them uses it the
way its page does. **If a change needs a word the bundle does not have, write the page in the SAME
change, first.** A word used before it is defined is a word everyone defines differently, and the
definitions never meet. This is the discipline
`tests/test_knowledge.py::test_no_two_domain_pages_state_the_same_claim` already enforces between
pages — one claim, one owner — applied to the vocabulary itself.

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
  `means` and `lever` split because each had content of its own — a means was the joint three
  subsystems met at; a lever is an instance whose absence removes a row. And when the three
  subsystems became one node, `means` folded into `action`, because a joint between one thing
  and itself is nothing (the-action-is-the-kind).
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
- **Desire is bouletic, obligation deontic, affordance alethic, freshness epistemic** — different
  logics rather than strengths of one, which is why an unmet want is a gap and an unpaid debt is
  a breach.
- **A repository holds data and a service holds logic**, and a thing that decides nothing is a
  repository's support function rather than a service.
- **Deciding nothing is the finding** — writing no graph is only the hint, since three services
  write none and stay services.
- **Verify a claim in the bundle against the code before repeating it**; nothing gates prose
  against the thing it describes.
- **A rename is done when the suite says so**, not when the thing you grepped for is gone.
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
  was "a lever the reflex may take" to one road and "passed over, plan partial" to another,
  until the gate held every action to both texts or neither, and a class for the second kind
  was weighed and dropped as a term nobody would read.
- **A lever that touches nothing the want reads is never simulated, and the closure is what
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
- **An action is a point its taker contributes to** — `@contributes(<action>)` on a module says who
  and how in one place, a triple restating who was retired as a duplicate, and a gate in the
  repo, at onboarding and at boot holds a family to its actions, because a taker missing at
  runtime looked exactly like an actor that was busy.
- **An effect is one declaration** — the diff the search planned on rides on the step and is
  what the world is held to, so no actor sizes an expectation of its own; the one thing an
  actor adds is how close, and that is a bounded pick rather than a kernel constant.
- **The desire owns the term and the package owns the measure** — a want says `unmetWhen`
  and `estimates`; what the pattern means and that the estimate never overstates are promises
  about the package's own actions and costs, which a world file cannot keep.
- **A ceiling on compute is stated in the unit the search spends** — depth was that unit
  under breadth-first and stopped being it under best-first, and a budget of worlds is what a
  sovereign can size from a measured cost per fork.
- **A base class is an import and an annotation is not** — a layer contract named in a
  signature costs nothing at assembly; subclassed, it loads the layer, which is why sensing's
  row types live behind the touch (#455).
- **A verdict the search reads is a query, and the judge stays at the gates** — a shape
  compiled to the select whose rows are its violations costs a millisecond where the judge's
  reader floors at tens, and holding the two to one answer by parity is what makes that safe.
- **The present is identified among the root's children, never asserted from one** — a child is
  a prediction and the present is observed, so what execution decides is which imagined world
  the real one landed in, and the cone under the match survives while its siblings die.
- **A predicted number is an interval, and a plan that cannot be certainly met has a look in it** —
  a point with a tolerance applied at verification can neither find the look that narrows the
  width nor refuse the step whose uncertainty crosses the law.

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
   the choir's extension points (`desires`, `size`, every ACTION, `notices`, `series`, `quiet` — and, in sensing's
   words through `agent.ask`, `annotate`, `urgency`, `bounds`).
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
Nothing here controls a step — a cadence not a reading, a region not an aim, a mandate not a
belief, an affordance not an action. When a change you are making reaches DOWN a level (a
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

**A stake is NOT a premise for a capability, and neither is a stake and a lever.** Three
capabilities were granted that way — wanting, committing, deciding — and all three are gone:
they were the mind, every agent has one, and the STORES they read were already built for every
agent unconditionally. A modality nobody may write is not a modality. What a stake still decides
is which SHAPES apply — `orexis:KeeperShape` targets a want that is not merely about knowing, and
sensing's stake shapes target `orexis:actsFor` a subject that states what it needs — so
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
pytest -q              # BOTH roots: tests/ and any a package carries. No infra needed.
                       # NOT `pytest tests` — a package's own tests are invisible to that,
                       # and to a bare `pytest` if testpaths does not name packages.
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

Beliefs are the agent's: **authored** once at birth, never touched by start or stop. Anything
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
subclass path.** If the closure does not cover your case, widen `agent/inference.py` rather than
working around it — `tests/test_inference.py` refuses a seventh hand-rolled walk, and separately
fails if pyshacl ever entails something the closure does not. See
[one-graph-both-engines-read](knowledge/decisions/one-graph-both-engines-read.md).

- **Name the graph CLASS, never an instance — and scope by MODALITY when you leave belief.**
  `?d a orexis:DesireGraph` unions every instance of that class, exactly as `store.public_graphs()`
  does, so a scoped query keeps the property the rule below exists to protect. A MODALITY
  class is a legitimate thing to name; a graph instance never is. (This first carried a
  sharper warning — that a want and a fact would share their shape, so an unscoped query would
  return the wanted value beside the observed one. That hazard is gone: what an agent pursues
  is SHACL, not belief-shaped data, so the two cannot be confused. The rule survives its
  motivation because naming a class rather than an instance was always the right discipline.)
  See [a-desire-is-a-shape](knowledge/decisions/a-desire-is-a-shape.md).
- **Never wrap `GRAPH <…>` around a SELECT.** Public knowledge is SEVERAL graphs — asserted,
  derived and entailed, for the vocabulary and for the world, plus whichever a package owns —
  and `store.query` merges them as the default graph, so an ordinary pattern reads all of them.
  Never count them: `orexis:PublicGraph` is a class and `store.public_graphs()` asks. A basic graph
  pattern inside one `GRAPH` clause must match entirely *within* that graph, so narrowing it
  returns **nothing** the moment a fact you wanted lives elsewhere, silently, because an empty
  result is not an error. Updates are the exception and must name their target; a `rules.ru`
  writes `$given` and `$derived`, or `$into(pkg:SomeGraphClass)` when its package owns a graph —
  a graph *class* is a T-Box term and genesis resolves it, so **no rule names a graph**.
  `tests/test_provenance.py` refuses a narrowed SELECT. See
  [who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).
- **A graph IRI is an instance, so rule 1 applies to it.** `orexis:WorldGraph` is the term code may
  name; `…/graph/world` is not, any more than a world's `:fern_agent` is. Ask `store.public_graphs()`.
  Two things are still named and both are writes or the bootstrap root, never a reader
  enumerating what to read — adding a public graph is a vocabulary edit that touches no Python.
  **A PER-AGENT graph is asked for the same way**: `store.recorded_graphs()` answers with every
  graph this agent owns — its picks, its debts, whatever a package records — by reading the
  classification the agent wrote about itself at boot, since a graph that does not exist until
  its agent does cannot be declared in a T-Box. What boot types is ASKED of the vocabulary
  (#448): a class saying `orexis:graphPrefix` and `orexis:arrivesBy` is a per-agent graph class
  whichever package declares it, and `orexis:WorkingGraph` is how a package says its graph is
  its own and not carried. Naming one is still legitimate to SUBTRACT it
  (`validate_agent` takes the pick record out where the desires modality already carries it),
  which is saying which road a fact came by rather than enumerating what to read.
- **SPARQL prefixes.** Only what `store.NAMESPACES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `tests/test_store.py` checks this by scanning the source text — and asserts each
  source tree is still *found*, because moving files has twice emptied one of its globs and taken
  cases off the guard without failing anything. **A `sh:select` inside a shape is the same
  query** (#508): it uses the same names, says `sh:prefixes orexis:` on the node that carries
  it, and the store's `DECLARATION` — the dictionary in SHACL's words, assembled and never
  authored — travels with every shapes graph either engine is handed. A select spelling an
  IRI in full that the store has a name for fails the same test.
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
  and `duration * number` return unbound in pyoxigraph, and so does a decimal division whose
  dividend is an exact zero (`0.0 / 0.25`; cast the dividend to `xsd:double`), so a column
  computed that way reads empty for every row and no query errors, no test goes red. It is the same family as the
  empty-result trap above, arriving through arithmetic: measure an unfamiliar operation on a
  literal before building a column on it, and pin what you measured — `tests/test_desires.py`
  does, so the day the engine grows the operation the guard says so.
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.
