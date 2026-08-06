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
existing READMEs (root, `firmware/*/`) are operational entry points and stay, but do
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

And two that catch people out. **There is no default world** — every command takes one as a
required argument and `current_world()` refuses rather than guessing, because a fallback puts a
misconfigured agent on the same topics as the real one. Also: **capabilities are derived, never
declared.** `world.ttl` must
not contain `ag:hasCapability` — seeding computes it from the wiring.

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

## Commands

```bash
source .venv/bin/activate

agora-validate <world> # build the world from its files and hold it to every package's shapes
agora-onboard <world>       # ONBOARDING: validate, then grant everything below. One command.
  agora-influx <world>      #   a bucket per agent, and a token that opens only it
  agora-mqtt <world>        #   a credential per principal, and the broker ACL, derived
  agora-compose <world>     #   generate world/<world>/compose.yaml from that world's roster
agora-broker-cert           # INFRA, not onboarding — the broker's own cert and whom it trusts
cd world/<world> && podman compose up -d               # one container per agent
podman build -t agora:local -f backend/Containerfile .   # only when a dependency changes
pytest backend -q      # 199 tests, no infra needed
pytest infra -q        # 8 more, against the RUNNING broker and store — see below
```

`agora-validate` and `pytest backend` are the two gates. `pytest infra` is a third thing, run
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

**Its code is in `onboarding/`, not `backend/`, and is installed separately** (`pip install -e
./onboarding`). The line is drawn by **who calls a function**, not by file: `validate_agent`
stays in `agora` because an agent checks itself at boot, while `validate_world` moved because
only the sovereign asks it; `sign` and `verify_command` stay because an actuator co-signs, while
`create_keypair` moved — an agent that could mint a society's keys could sign for it. `agora-influx` reads the admin token, which opens every bucket and which no agent
may ever hold — and an agent image copies `backend/` wholesale, so the surest way to guarantee
that is for the code to be absent. `agora-influx` and `agora-mqtt`
need infra up; `agora-mqtt` must run before the broker will start at all, since its ACL is
generated and mosquitto now refuses anonymous clients. It then **reloads** the broker itself
(SIGHUP, not a restart — connected agents keep their sessions), so adding an agent or a world
still interrupts nothing.

`agora-validate` and `pytest backend` are the two gates. Both must pass before a change is done.

Beliefs are the agent's: written once at birth, never touched by start or stop. Anything that
would reset them on a restart is a bug, not a convenience.

## Two traps worth knowing

- **SPARQL prefixes.** Only what `store.PREFIXES` declares may be used. rdflib silently
  pre-binds common prefixes and Fuseki does not, so a query can pass every test and 400 in
  production. `backend/tests/test_store.py` checks this by scanning the source text.
- **Stray host processes are the usual cause of doubled data.** A leaked publisher from an
  earlier run keeps writing to the same topic, and both readings get ingested. `podman compose
  down` removes a society deterministically, which is half of why deployment is containers.
  Simulated devices are containers too, and belong to their world's compose project — the
  world knows they exist, so nothing is told by hand which subjects to pretend to be.
