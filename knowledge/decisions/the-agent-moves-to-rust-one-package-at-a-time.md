---
type: Decision
title: The agent moves to Rust one package at a time, and the documents do not change
status: accepted
timestamp: 2026-11-04T22:00:00Z
description: >-
  The sovereign's ruling of 2026-11-04, with 0.2.0 tagged, that the agent moves to Rust - for speed on the
  Pi, a typed SPARQL algebra, deployment to smaller hardware, and an image holding the bare minimum.
  Decided - one Rust binary per agent, each package a Cargo feature, ported one at a time with the
  snapshot cases as the conformance suite, every text parsed once, and the documents unchanged since the
  engine is the same. Refused - a Rust core under Python, staying Python, and the reasoning as Rust code.
---

# The question

With 0.2.0 tagged, the sovereign asked about moving the agent to Rust. Their reasons were speed on the
Pi, a typed algebra in place of rdflib's parse tree, deployment, smaller hardware, and an image that
holds the bare minimum, since an agent's container is safer the less there is in it to run.

The engine is Rust already: pyoxigraph is Oxigraph, and every query, update and rule runs in it. What a
move would change is everything around the engine. The agent is about 21,000 lines of Python with 12,000
of tests, over 7,000 lines of Turtle and SPARQL that are the agent's actual program.

# What was measured

The time was split by category on the bench Pi, using timers around `Planner.plan` and `Runtime.run`.
cProfile could not split it, because it charges pyoxigraph's time to whoever called it. Statement
parsing is an upper bound: every statement replayed on an empty store. The greenhouse figures are after
#1071, which did not move them.

| case | pass | evaluation | parsing statements | rdflib and pyparsing | our Python and JSON |
|---|---|---|---|---|---|
| greenhouse, cold dry bed | 460 ms | ~30% | ~35% | ~19% | ~19% |
| greenhouse, comfortable bed | 353 ms | ~20% | ~31% | ~31% | ~18% |
| hanoi, four disks, after #1071 | 669 ms | ~85% | ~8% | ~3%, once per process | ~7% |

Two findings decided the shape of the move.

**A pass on a shipped world is mostly not evaluation.** The greenhouse runs about 1,650 statements a pass,
each over a store of fewer than 2,000 quads. Parsing each statement every time, rdflib's grammar and the
conversions in Python come to about 70% of the pass, and the engine's own evaluation to the rest.

**The search grew with the cone because of query shape, which a port would have kept.** Five disks took
72 s, 99% of it in the engine, because two reads joined an `OPTIONAL`'s group and a subselect in a way the
engine evaluates whole. Fixing three texts took it to 3.3 s
([measure-the-search](/runbooks/measure-the-search.md), #1071). That is Oxigraph's behaviour, the same
in either language.

# What was decided

**One binary per agent, each package a Cargo feature.** `orexis-compose` builds an agent's binary with the
features its roles load, as it builds an image with the extras today
([a-package-brings-its-own-dependencies](/decisions/a-package-brings-its-own-dependencies.md)). A package
an agent does not run is then compiled out rather than merely left uninstalled. The image holds the
binary and the CA certificates, and the world is mounted read-only. That leaves no interpreter, no
package manager and no shell.

**The documents do not change.** The ontologies, the actions, the rules, the shapes, the desires and the
worlds are read as they are, by the same engine, so the engine's traps that AGENTS.md lists stay true.
A domain stays documents and no code an agent runs.

**Every text is parsed once.** A rule, a met-test, an estimate or an action's text is parsed when it is read,
at boot or when it arrives, with spargebra, and kept parsed. A value is bound into the parsed query, never
by substituting `$tokens` into text. Speech, onboarding and the footprint all read the same typed algebra
in place of rdflib's parse tree, so the traps that parse tree had go with it.

**The snapshot cases are the conformance suite.** A case is held to the whole store it leaves. A package is
ported when its cases leave the same store run by the Rust binary as run by Python, and its walks pass.
Until the last package moves, the Python tree stays the reference, and main keeps moving under it.

**The order goes up the stack.** First the kernel: the store, the catalogue, the binder, the lifecycle and
the runtime. Then belief, sensing, prediction, planning, execution, speech, coordination and the
transports, then the journal, the series and the metrics, and translation last.

**What is no agent's stays Python.** Onboarding stays Python, with pyshacl, and keeps the admin token out of
every image. It reads a world as an agent boots it by running the agent's binary to boot and check that
world, rather than by importing its code. The simulator, the operator's tools and the history view stay as
they are.

# What was refused

**A Rust core under Python.** Moving the hot kernel into a crate that Python calls through PyO3 would have
given most of the speed soonest. But every image would keep the interpreter, the package manager and every
package's Python, which is the opposite of the image the sovereign asked for. It would also mean two
languages in one agent for good, and a boundary between them crossed per statement.

**Staying Python.** Parsing, rdflib and conversions are most of a shipped world's pass, and are what the
language costs. The image cannot be made minimal around an interpreter.

**The reasoning as Rust code.** A port could replace the SPARQL texts with Rust: a transition as a function,
a met-test as a match. It would be faster, and it would end what the architecture rests on: a domain is
documents, an action is a node in `actions.ttl`, and adding a way of acting touches no code. The texts
stay, and Rust only reads them better.

# Seams left open

- **SHACL in the agent.** Desires and constraints are shapes compiled to SPARQL by the kernel, which reads
  them with rdflib today. The port compiles the subset the kernel uses. rudof is there if a world needs
  more of SHACL than the kernel compiles.
- **The model's client.** No official Rust SDK exists, so retries and the names of failures become plain
  HTTP, to the same API.
- **The ground.** Laying grounds is about two-thirds of the greenhouse's `plan`, and it is a cost of
  copying per scope that a port carries over unchanged. It is the next thing to measure, in either
  language.
