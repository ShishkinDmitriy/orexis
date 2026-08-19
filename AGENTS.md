# Working on Agora

A society of self-interested agents that bid for a scarce resource. The v1 domain is plant
watering, but the domain is a plug-in — plant/water language is the example, not the
architecture.

Read [`knowledge/index.md`](knowledge/index.md) before changing anything structural. It is the
durable "what and why"; the code follows it, not the other way round.

## Use the OKF skill for anything under `knowledge/`

`knowledge/` is an **Open Knowledge Format v0.1 bundle** (https://okf.md), not a docs folder.
Invoke the `okf-open-knowledge-format` skill when adding, editing or checking documents there.
If it is unavailable, the rules are short enough to follow by hand:

- every concept `.md` has YAML frontmatter with a non-empty `type` (`Decision`, `Domain
  Concept`, `Component`), plus `title` and `description`;
- `index.md` carries **no** frontmatter — it is navigation, and its title is its heading. Only
  `knowledge/index.md` may declare `okf_version`;
- validate with `./tools/validate-okf.sh knowledge` — vendored from the skill, because a gate
  that only runs from one person's home directory cannot be run by a fresh clone or by CI.

**Durable knowledge goes in the bundle, never in a new README.** `domain/` says what a thing is
and how to use it; `decisions/` says why a choice was made and which seams it leaves open. The
existing READMEs (root, `firmware/*/`) are operational entry points and stay, but do
not add more for design knowledge.

**Reconciling the bundle is part of the change, not follow-up.** After changing behaviour, grep
`knowledge/` for claims the change made false and fix them in the same commit. A stale decision
record is worse than none, because it is still cited.

## The three rules the code lives by

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
   `capabilities/market/` provides three — bidding, hosting, and the matching family — and it is
   one package. **What isolates a capability is `PROVIDES` and its term, never the directory
   boundary**: `hosting.py` asks `agent.provider(BID_MATCHING)` and never learns which member
   answered, so uniform price landed without touching a line of it. A directory is how a package
   is FOUND and how one is deleted. See
   [a-package-owns-its-namespace](knowledge/decisions/a-package-owns-its-namespace.md).

   **There is ONE package tree and one mechanic.** `packages/<family>/<name>/` holds whichever
   of `ontology.ttl`, `shapes.ttl`, `rules.ru`, `review.rq` and Python it wants — every one
   optional, and an omission is a statement. `packages/part/esp32/` is an ontology and nothing
   else because a board has no behaviour a runtime could load; `packages/capability/market/` has
   all of it. Neither is more of a package than the other, and that is the point: a plant, a
   part and a capability are the same kind of thing to the loader.

   A package may declare **its own namespace**, in its `ontology.ttl` and mirrored in
   `terms.py`. `agent.loader` reads every project namespace off the ontology that declares it,
   so `market:` reaches a query without `store.PREFIXES` learning the package exists. Nothing
   lists them — `agent.loader` finds them two levels down, and the FAMILY is the parent
   directory rather than anything declared, so `kind` distinguishes a plant from a part without
   a registry. `PROVIDES` in `__init__.py` is how an implementation registers, and its absence
   is what makes a package knowledge-only. A package implements the terms IT declares —
   which is what lets imports follow grants: a runtime imports only the packages its own
   capabilities name (#216). Adding one is adding a directory. Packages never
   import each other's Python: ask `agent.provider(family)` or contribute via
   the choir hooks (`annotate`, `urgency`, `notices`, `series`, `quiet`).

   **`agent/` is the kernel that loads them, not their home.** Capability Python used to live
   under it, so the tree itself showed which of it a runtime loads — it does not show that now.
   `packages/capability/market/` and `packages/part/dht11/` look identical, so the CONTRACTS
   carry the boundary alone: `lint-imports` holds `packages` away from `onboarding`, and the
   `Containerfile` decides what reaches an image by naming two trees and not a third. Both were
   always the real enforcement; the layout was a reminder, and the reminder is gone.
3. **Nothing in `infra/` is world-specific.** It holds the services and what is true of the
installation: the broker image, the installation CA, Grafana's material, the admin token. A
world's broker config, its ACL, its certificates and its device credentials live with the world.
Also: **no `.env` at the repo root, because nothing there is true of every world at once.**
   `infra/.env` says where the shared series store is — the URL and the org, and nothing
   secret, because that file is handed to every agent container. What an agent may *do* with
   the store and the bus arrives as its own credentials, minted per agent into
   `world/<name>/secrets/` and mounted into that container alone. The admin token lives apart
   from both, in `infra/secrets/`, and no agent ever holds it. See
   [series-and-bus-isolation](knowledge/decisions/series-and-bus-isolation.md).
4. **There is no shared store.** The world is TTL files; each agent builds its own belief base
   at boot and holds it in a volume of its own, so isolation is structural rather than
   enforced. An agent is told its id and given one world, mounted — it never learns that other
   worlds exist. See [where-the-belief-base-lives](knowledge/decisions/where-the-belief-base-lives.md).
5. **There is no config file for the model.** Topology lives in the world graph, desire and limits in each
   service URLs) are environment, because they are not beliefs anyone holds. See
   [world-graph](knowledge/decisions/world-graph.md).

**One principle explains most of the shapes above: control the derivative, not the value.**
Nothing here controls a step — a cadence not a reading, a region not an aim, a mandate not a
belief, an affordance not an action. When a change you are making reaches DOWN a level (a
deliberator setting a price, a world file pinning an aim, a model emitting an action), stop:
that is the one move this architecture refuses everywhere. See
[control-the-derivative-not-the-value](knowledge/decisions/control-the-derivative-not-the-value.md).

And two that catch people out. **There is no default world** — every command takes one as a
required argument and `current_world()` refuses rather than guessing, because a fallback puts a
misconfigured agent on the same topics as the real one. Also: **capabilities are worked out at
genesis, never hand-declared.** `world.ttl` must not contain `ag:hasCapability`.

**Wiring is one input, not the definition.** Sensing's are a strict function of the hardware —
a board that keeps an interval gives its agent `sensing:Subscribing`, and nothing could have decided
otherwise. Others have no wiring to follow and are *deduced*: someone at genesis judged that this
agent should have them, and could have judged differently. Both end up in the world graph and
neither is hand-written, but they are not the same kind of fact — the first is `derived`, the
second `deduced`, and since the provenance split they are distinguishable rather than merely
distinct. So "deduced at genesis" is the rule; "computed from the wiring" is how it happens to
work for the one family whose hardware forces the answer.

**Each capability is granted by whatever fact makes it meaningful, and that fact is its own.** The
premise lives in the capability's `rules.ru`, and there is no pattern to fit a new one into. Three
are granted by wiring — `actuation:hasActuator`, `market:bidsIn`/`market:hosts`, `sensing:polls` and a sense mode —
because they are about equipment or a position in a market. `review:Reckoning` is granted by
**latitude**: revising your own settings means nothing without settings you are permitted to move,
so an `review:commits` mandate whose ends differ is its premise. `desire:Deducing` is granted by
a **stake**: `ag:actsFor` a subject that states what it needs — an agent advancing nobody's
interest wants nothing, which is why `world/sensing`'s agent has three sensors and records.
`intention:Keeping` and `deliberation:Reflex` are granted by a **stake AND a lever** — wanting
without means is a wish, means without wants have nothing to decide — and they share that premise
while staying two capabilities, because how commitments are kept and how decisions are reached
are separately replaceable. When you add one, ask what makes *yours* meaningful rather than which
of these it resembles. See
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

agora-validate <world> # build the world from its files and hold it to every package's shapes
agora-onboard <world>       # ONBOARDING: validate, then grant everything below. One command.
  agora-influx <world>      #   a bucket per agent, and a token that opens only it
  agora-mqtt <world>        #   a credential per principal, and the broker ACL, derived
  agora-compose <world>     #   generate world/<world>/compose.yaml from that world's roster
  agora-dashboards <world>  #   a Grafana folder per world, from what its agents observe
agora-firmware <world>      # a board's config.h, from the world it belongs to
agora-wokwi <world>         # world/<world>/wokwi/ — its hardware as a wokwi.com project, which RUNS
agora-wokwi <world> --import d.json  # the other way: DRAFT a hardware.ttl from a drawing
agora-wireviz <world>       # world/<world>/wiring.yaml — the wiring as a WireViz harness
agora-wireviz <world> --import w.yaml   # and the same, drafted back from one
agora-keygen <world>        # once per world, before it is onboarded
agora-ask <world> <agent> 'SPARQL'   # the sovereign asks a RUNNING agent about itself — see
                       # decisions/the-sovereign-may-ask.md. Read-only by construction.
agora-infra-certs           # INFRA, not onboarding — the services' certs and whom they trust
cd world/<world> && podman compose up -d      # one container per agent
podman build -t agora:local .                 # only when a dependency changes
pytest -q              # BOTH roots: tests/ and any a package carries. No infra needed.
                       # NOT `pytest tests` — a package's own tests are invisible to that,
                       # and to a bare `pytest` if testpaths does not name packages.
pytest infra -q        # 8 more, against the RUNNING broker and store — see below
lint-imports           # the layering: onboarding may import agent, never the reverse
```

`agora-validate` and `pytest` are the two gates. `pytest infra` is a third thing, run
deliberately, and it is not part of them.

**`infra/tests/` is a contract with the infrastructure, not with the code.** It holds mosquitto
and InfluxDB to the behaviour the isolation design leans on — that a revoked grant stops delivery
to an already-connected client, that a rotated credential is refused at once, that one agent's
token cannot reach another's bucket. None of that is guaranteed by MQTT or computed by anything
here; it is how those two services happen to behave, so it is worth re-proving whenever they
change. Both files report the version they ran against and assert nothing about it: bump
`MOSQUITTO_VERSION` in `infra/mosquitto/Containerfile` or the Influx image in
`infra/compose.yaml`, rebuild, and re-run `pytest infra`.

**Onboarding is the phase between a ratified world and a running society** — see
[onboarding](knowledge/domain/onboarding.md). Its three generators all read the same `world.ttl`
and grant exactly what its wiring implies, so adding an agent and re-running `agora-onboard` is
the whole of deploying one. They stay separately callable because rotating one service's
credentials should not touch the other's.

**Its code is in `onboarding/`, beside `agent/` and outside it.** The line is drawn by **who
calls a function**, not by file: `validate_agent` stays in `agent` because an agent checks
itself at boot, while `validate_world` moved because only the sovereign asks it; `sign` and
`verify_command` stay because an actuator co-signs, while `create_keypair` moved — an agent that
could mint a society's keys could sign for it. `agora-influx` reads the admin token, which opens
every bucket and which no agent may ever hold, so the surest guarantee is that the code using it
is absent from the image.

**That absence is asserted, not implied.** There is ONE distribution now. What keeps onboarding
out of an agent image is the `Containerfile` not naming it — `tests/test_layout.py` fails if a
`COPY onboarding/` appears — and `lint-imports` holds the direction: onboarding may import
agent, agent may never import onboarding. Two pyprojects used to look like that boundary while
enforcing none of it. `agora-influx` and `agora-mqtt`
need infra up; `agora-mqtt` must run before the broker will start at all, since its ACL is
generated and mosquitto now refuses anonymous clients. It then **reloads** the broker itself
(SIGHUP, not a restart — connected agents keep their sessions), so adding an agent or a world
still interrupts nothing.

`agora-validate` and `pytest` are the two gates. Both must pass before a change is done.

Beliefs are the agent's: **authored** once at birth, never touched by start or stop. Anything
that would reset them on a restart is a bug, not a convenience. One addition is not a reset:
an amendment that grants a capability may author terms an existing volume has NEVER held, and
boot **endows** those — never-held terms arrive with their structures, held terms stay the
agent's whatever their value. `rebirth` remains the explicit discard. See
[an-amendment-endows-what-it-grants](knowledge/decisions/an-amendment-endows-what-it-grants.md).

But a belief is a **point chosen inside a range**, not a constant, and what genesis wrote is the
first pick rather than a bound. An agent whose **world gives it room to move** — `review:commits`, in
`world.ttl` — re-picks on its own clock inside that room, so the author's job is to constrain
well, not to guess well. **The mandate is also the grant**: `capabilities/review/` derives its
capability from exactly those triples, so an agent given no room has no review module, keeps no
summaries and never arises. Which terms may move is one triple in the owning package's
`ontology.ttl`; a review rule is `capabilities/<name>/review.rq`, SPARQL and never Python; and a
revision is legitimate exactly when `validate_agent` still passes, which is the same call the
agent makes at boot. **Compaction is not part of this** — it is not a choice, so it stayed in the
kernel on a clock of its own. See
[self-review-is-a-capability](knowledge/decisions/self-review-is-a-capability.md).

## Three traps worth knowing, and one that is closed

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
  `?d a ag:DesireGraph` unions every instance of that class, exactly as `store.public_graphs()`
  does, so a scoped query keeps the property the rule below exists to protect. What it buys is
  the other direction of wrongness: desires and beliefs share their SHAPE, so an unscoped query
  for a reading returns the wanted value beside the observed one — an extra result, which looks
  like an answer. See [the-mind-is-six-graphs](knowledge/decisions/the-mind-is-six-graphs.md).
- **Never wrap `GRAPH <…>` around a SELECT.** Public knowledge is SEVERAL graphs — asserted,
  derived and entailed, for the vocabulary and for the world, plus whichever a package owns —
  and `store.query` merges them as the default graph, so an ordinary pattern reads all of them.
  Never count them: `ag:PublicGraph` is a class and `store.public_graphs()` asks. A basic graph
  pattern inside one `GRAPH` clause must match entirely *within* that graph, so narrowing it
  returns **nothing** the moment a fact you wanted lives elsewhere, silently, because an empty
  result is not an error. Updates are the exception and must name their target; a `rules.ru`
  writes `$given` and `$derived`, or `$into(pkg:SomeGraphClass)` when its package owns a graph —
  a graph *class* is a T-Box term and genesis resolves it, so **no rule names a graph**.
  `tests/test_provenance.py` refuses a narrowed SELECT. See
  [who-put-the-fact-there](knowledge/decisions/who-put-the-fact-there.md).
- **A graph IRI is an instance, so rule 1 applies to it.** `ag:WorldGraph` is the term code may
  name; `…/graph/world` is not, any more than a world's `:fern_agent` is. Ask `store.public_graphs()`.
  Two things are still named and both are writes or the bootstrap root, never a reader
  enumerating what to read — adding a public graph is a vocabulary edit that touches no Python.
- **SPARQL prefixes.** Only what `store.PREFIXES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `tests/test_store.py` checks this by scanning the source text — and asserts each
  source tree is still *found*, because moving files has twice emptied one of its globs and taken
  cases off the guard without failing anything.
- - **A test that asserts inside a loop can assert nothing.** An empty result set is not an error,
  so the body never runs and the test is green. The repo-root `conftest.py` traces the at-risk
  tests — an `assert` inside a loop over something that could be empty — and fails the run if a
  test function executed no assertion in any of its cases. It does NOT catch a parametrisation
  that generated zero cases, nor a glob that still matches but no longer covers what it is named
  for; both have happened, and both are still found by hand. See
  [a-test-that-asserted-nothing](knowledge/decisions/a-test-that-asserted-nothing.md).
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.
