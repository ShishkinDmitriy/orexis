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
- validate with the skill's `scripts/validate.sh knowledge`, or `okflint`.

**Durable knowledge goes in the bundle, never in a new README.** `domain/` says what a thing is
and how to use it; `decisions/` says why a choice was made and which seams it leaves open. The
existing READMEs (root, `deploy/`, `firmware/*/`) are operational entry points and stay, but do
not add more for design knowledge.

**Reconciling the bundle is part of the change, not follow-up.** After changing behaviour, grep
`knowledge/` for claims the change made false and fix them in the same commit. A stale decision
record is worse than none, because it is still cited.

## The three rules the code lives by

1. **Code may reference T-Box terms; never an instance.** `term("Subscribing")` is fine;
   `"supplier"`, `"sensors/fern/moisture"`, `ag:world` are not. The single exception is the one
   identifier a process is handed at boot: its own agent id. Everything else is discovered from
   the graph. See [capability-packages](knowledge/decisions/capability-packages.md).
2. **A capability is a directory.** `capabilities/<name>/` holds its own `ontology.ttl`,
   `shapes.ttl`, `rules.ru`, `terms.py`, `beliefs.py` and code. Nothing lists them —
   `agora.loader` finds them. Adding one is adding a directory; no registry to edit. Capability
   packages never import each other's Python: ask `agent.provider(family)` or contribute via
   `annotate`/`urgency`.
3. **There is no config file.** Topology lives in the world graph, desire and limits in each
   agent's own beliefs, both authored in `genesis/<world>/`. Deployment facts (`AGORA_ACTUATE`,
   service URLs) are environment, because they are not beliefs anyone holds. See
   [world-graph](knowledge/decisions/world-graph.md).

And one that catches people out: **capabilities are derived, never declared.** `world.ttl` must
not contain `ag:hasCapability` — seeding computes it from the wiring.

## Commands

```bash
source .venv/bin/activate

agora-seed <world>     # load one ratified world from genesis/ (society | sensing)
agora-acl <world>      # per-agent store credentials + Fuseki access list
agora-validate         # SHACL over the live belief base; exits non-zero on violation
agora-up               # one process per agent the world declares
agora-sim              # virtual edge: subjects that dry, sense on cadence, get watered
pytest backend -q      # 176 tests, no infra needed
```

`agora-validate` and `pytest` are the two gates. Both must pass before a change is done.

## Two traps worth knowing

- **SPARQL prefixes.** Only what `store.PREFIXES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `backend/tests/test_store.py` checks this by scanning the source text.
- **`AGORA_SIM_PLANTS` empty means every subject in the world** — including ones a real board
  publishes for, on the same topic. With hardware connected, list only the virtual ones.
