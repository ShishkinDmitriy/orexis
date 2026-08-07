---
type: Decision
title: One convention, and a boundary that is checked rather than implied
description: Why the repository is flat, why it ships one distribution instead of two, why capabilities and transports live inside the agent while the vocabulary does not, and why the packaging boundary was replaced with a test and an import contract.
tags: [layout, packaging, boundaries, enforcement, seams]
timestamp: 2026-08-07T00:00:00Z
---

# What it looks like

```
pyproject.toml   Containerfile
agent/                       the runtime, and the model it reads
agent/capabilities/<name>/   what an agent can DO — discovered
agent/transports/<name>/     how a device is REACHED — discovered
onboarding/                  the sovereign's tools
vocabulary/agora/            the society kernel everything layers on
vocabulary/stand/            boards, peripherals, pins, wires
vocabulary/<part>/           one concrete part, or one protocol — dht11, onewire, rgb-led
vocabulary/water/            what this society is about
tests/  firmware/  infra/  world/  knowledge/
```

Six Python trees, one convention. It used to be two: `capabilities/`, `transports/` and `domain/`
were flat packages imported from the repo root, while `backend/src/agora/` and
`onboarding/src/onboarding/` used a `src` layout and were pip-installed separately.

# Why flat, when `src/` is the recommendation

The `src` layout exists for one reason: the package is not importable from the repo root, so tests
can only import the *installed* code. That guarantee was already void here. `loader` appends the
repo root to `sys.path` so the discovered trees can be found, which means most of this repository
was imported from the checkout regardless.

Keeping `src/` for two trees out of six bought nothing and cost a repeated word —
`onboarding/src/onboarding`. **Half a convention is worse than either whole one**, because a reader
cannot tell which rule is in force without checking.

# Why one distribution, when the boundary is real

The boundary is real: **an agent image must not contain credential-minting code.** `agora-influx`
reads an admin token that opens every bucket, and no agent may hold it.

But two distributions were not what enforced it. The agent never installs from an index and never
runs `pip install ./onboarding`; the image copies directories. **The `COPY` line was the
enforcement, and the packaging split only described the intent** — which is worse than describing
nothing, because it invites trust it cannot honour.

So the split went, and the intent became two things that fail when violated:

- `tests/test_layout.py` reads the `Containerfile` and asserts no operator code is among the copied
  paths. It runs in CI without building anything.
- an `import-linter` contract: `onboarding` may import `agent`, `agent` may never import
  `onboarding`, and no capability or transport may import `onboarding` at all.

**Both were verified by breaking them**, which is the only way to know a guard works: adding
`import onboarding.mqtt` to `agent/runtime.py` turns the contract BROKEN, and adding
`COPY onboarding/` fails two tests. A guard never seen to fail is a guard nobody has tested.

The image is now two directories — `agent/` and `vocabulary/` — and neither is onboarding. Measured
on the built image: `/app/onboarding` does not exist and `import onboarding` raises
`ModuleNotFoundError`.

# Why capabilities live inside the agent and the vocabulary does not

The line is whether **Python** is shared.

A capability's code is loaded only by an agent runtime. Onboarding reads its `ontology.ttl`,
`shapes.ttl` and `rules.ru` — to validate a world and to derive what an agent can do — but never
imports its Python. So the tree belongs to the thing that runs it, and `agent/capabilities/` says
so. Transports are the same kind of thing and moved for the same reason; nothing outside `agent/`
imports either tree's code.

The vocabulary is genuinely shared: onboarding validates worlds against it and derives from it. It
stays at the root.

A pleasant consequence: because capabilities and transports travel inside `agent/`, the image's
copy list collapsed to two directories, which is what made the boundary test almost trivial to
write.

# Why there is no `agent/kernel/`

Symmetry was proposed — `agent/{kernel,capabilities,transports}`, three peer trees — and refused,
because the symmetry would be false. `capabilities/` and `transports/` are **discovered**: the
loader globs them, anything dropped in is found, nothing lists them. A kernel is what those
discovered trees **import**. One is a trunk, the others are places to graft onto, and presenting
them as peers would suggest the trunk is replaceable.

It would also have cost every capability, every transport and all of onboarding an extra level —
`from agent.kernel.ontology import term` against `from agent.ontology import term` — and
reintroduced the word `kernel` with a new meaning days after `vocabulary/agora` freed it, making
every older reference ambiguous about which kernel it meant.

# Naming

`backend` described nothing — and by the time it was renamed it was actively wrong, since the
onboarding tools had already moved out and what remained was precisely what an agent runs.

`agent` rather than `agora` because the whole project is agora; a component inside it called agora
is the same redundancy as `onboarding/src/onboarding`. The known cost is that onboarding imports
`from agent.ontology import …`, which reads like a layering smell even though the direction is
correct. The import contract states the rule explicitly, so the name surprises and the contract
does not.

`vocabulary/agora` and `vocabulary/water` rather than `kernel/` and `domain/water/`: those two were
the only trees with no Python at all, which is exactly what they have in common. There are now
more of them than two — the stand, a package per protocol, a package per part — and that is the
same rule applied further: see [pins-and-wires](/decisions/pins-and-wires.md).

# Seams left open

- **One image for every agent.** Everything else an agent gets is derived from its wiring — bucket,
  token, credential, certificate, belief base, mounted files, signing keys. The image is handed to
  all identically, though `agora-compose` already computes each agent's capability set. This costs
  nothing today: capabilities are a few KB, and the trees are mounted read-only over the image so
  adding one needs a restart rather than a build. **The trigger is the first capability that
  declares its own dependency** — a library installed at build time lands in every agent's image,
  including agents that never load it, and mounting cannot help. The alternative is equally
  respectable: rule that a capability may use only what the runtime already has. Either is fine;
  drifting into one by accident is not.
- **The agent image is not Alpine.** Measured: musl wheels exist for `pyoxigraph` and
  `cryptography`, and a RocksDB belief base writes, reads and survives a reopen on musl — about
  85 MB of the 230 is the glibc base. Not taken, because `pyshacl` and `rdflib` recurse over graphs
  and musl gives threads a much smaller default stack, and that risk is untested for a saving that
  does not matter on a machine with 10 GB free.
- **The model is not a third package.** `agent` holds both the runtime and the model onboarding
  reads. Extracting a shared core was proposed twice and declined twice: the dependency is already
  one-way and acyclic, the shared surface is seven modules, and a third distribution would buy a
  boundary the import contract already states.
