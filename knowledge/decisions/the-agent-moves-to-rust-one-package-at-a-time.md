---
type: Decision
title: The agent moves to Rust one package at a time, and the documents do not change
status: accepted
timestamp: 2026-11-04T22:00:00Z
description: >-
  The sovereign's ruling of 2026-11-04, with 0.2.0 tagged, that the agent moves to Rust - for speed on the
  Pi, a typed SPARQL algebra, deployment to smaller hardware, and an image holding the bare minimum.
  Decided - one Rust binary per agent, each package a Cargo feature, held alone by its snapshot cases as it
  is ported, an agent running in Rust once its roles' packages all are, world by world, a society mixing the
  two in between, a ported package frozen until its last Python user moves and the Python agent retired whole
  at the end, every text parsed once, and the documents unchanged since the engine is the same. Refused - a Rust core under Python, staying Python, and the reasoning as Rust code.
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

Parsing alone was then measured in Rust with the same parser, over the statements those passes ran: 40 µs a
statement on the Pi, 66 ms of the greenhouse's pass and 84 ms of four disks', about 13%. Parsed once a process,
as the kernel crate's store parses, the same statements' 1,454 and 1,510 distinct texts take 68 ms in all. The
rest of the replay's upper bound is the engine planning each query as it runs it.

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
features its roles load, from `binary/Containerfile`, for every agent whose packages are all crates (`compose.ported`), as it builds an image with the extras today
([a-package-brings-its-own-dependencies](/decisions/a-package-brings-its-own-dependencies.md)). A package
an agent does not run is then compiled out rather than merely left uninstalled. The image holds the
binary and the CA certificates, and the world is mounted read-only. That leaves no interpreter, no
package manager and no shell. The binary is its own crate, `binary/`, beside `agent/` and not in it: every entry of `agent/` that is no
package is kept in each Python agent's image (`agent/tree.py`). Its volume is RocksDB, as pyoxigraph keeps one, so an
agent moving to the binary keeps the beliefs it has lived in.

**Each package is a crate of its own, in its own directory, and the features are the binary's.** The kernel
is `agent/Cargo.toml` and planning `agent/planning/Cargo.toml`, beside the package's ontology and its Python,
and a package's crate depends on the crates beneath it alone. So the compiler holds the rule that a package
imports what lies beneath it and never above, as `lint-imports` and the layout test hold it in Python. Features
in one crate were refused: a module of sensing calling planning would compile in every build with both on
and break only in the build without planning. A package's own dependencies are its crate's, so a binary built
without a feature links none of them.

**The documents do not change.** The ontologies, the actions, the rules, the shapes, the desires and the
worlds are read as they are, by the same engine, so the engine's traps that AGENTS.md lists stay true.
A domain stays documents and no code an agent runs.

**Every text is parsed once.** A rule, a met-test, an estimate or an action's text is parsed when it is read,
at boot or when it arrives, with spargebra, and kept parsed. A value is bound into the parsed query, never
by substituting `$tokens` into text. Speech, onboarding and the footprint all read the same typed algebra
in place of rdflib's parse tree, so the traps that parse tree had go with it.

**A package is held alone the day it is ported.** A snapshot case holds a function to the whole store it
leaves: a store in, the function run, the store out. A ported function runs the same case with no agent
around it and no Python beside it, and leaves the same store, so `revise`, `take` and `weigh` are each
checked as they land, not at the end.

**The diff is Python's to write and the crate's to read.** `agent/src/snapshots.rs` loads a case as
`agent/conftest.py` does, applies its diff by line number and compares every quad, blank nodes by their
shape, and regenerates nothing: two writers of one canonical form would drift. So what a diff records, the
Rust copy reproduces exactly, and the graph hash shows what that costs: a digest is Python's `repr` of the
canonical facts, hashed, and `agent/src/hash.rs` spells each tuple, string and float as `repr` does, so the
four `hash_named_graph` cases pass on both. The same holds for every literal a ported act writes, since a
case compares terms and not values: an instant is spelled as Python's `isoformat` spells it, `+00:00` and not
`Z`, and a parameter's value reaches a rule text as Python's binder hands it. And so does an ORDER no document
states: a met-test numbers its constraints in the order the shapes come back from the engine, the number is part
of a violation row and of a want's key, and the engine hands quads back in no order a document says, reversed by
each store they are copied through. So a case is loaded as `put_graph` loads it, through a store of its own, and
the shapes are merged as rdflib's `Graph` merges them, each subject's predicates in the order first met. A filling is
asked as a chain of OPTIONALs in the order rdflib's algebra holds a precondition's patterns, each block reordered by
`reorderTriples`, and the chain's order decides which rows bind, so `agent/planning/src/footprint/patterns.rs` orders
them as rdflib does; read in the order written, seven of the eleven shipped agents' scopes came out otherwise. The
spelling and the order are free to change once the Python agent is retired and the diffs are the crate's to
write. What the two parsers READ differs in one place, and no shipped text meets it: the engine's parser
translates a sequence or an inverse of plain predicates into triples, as SPARQL's algebra says, where rdflib
keeps the path, so `?x :p/a :C` reads the class in the crate and every type in Python. And a parser may refuse
what the other lets pass: `$tank` and `?tank` are one variable to SPARQL, so an effect's `BIND($tank AS ?tank)`
is refused by the engine's and passed by rdflib's, and `agent/planning/src/footprint.rs` reads a token as a
variable of its own name.

**An agent runs in Rust once every package its roles load is ported.** Inside one agent the packages share
one store in one process, and a Rust runtime hosting a Python package would need the interpreter in the
image, the bridge refused below. So the order is the order in which the worlds' agents become wholly
ported, each world's walks and benches passing on the binary as it does:

| ported | the first world wholly in Rust |
|---|---|
| the kernel and planning | `hanoi`, a planner alone |
| execution | `courier`, `driver` |
| belief | `tower` |
| sensing, prediction and the MQTT transport | `greenhouse`, its day bench sending the same commands, `layby` and `sensing` |
| speech and coordination | `lane` |
| the market, documents over speech that bring no code | `allotment` |
| the journal, the series, history and metrics; translation, the Telegram and HTTP members | `terrace` |

The kernel is the store, the catalogue, the binder, the lifecycle and the runtime. Belief's transition
machine landed with planning, before the rest of belief, because an action's effect is a transition and `take`
applies it; it says a rule's scope on the parsed update, its templates the world's and its dataset the graphs
read, where the Python copy reprints the text around rdflib's parse.

**A world may mix the two.** Agents share no store and meet only by the documents on the bus, so a Rust
courier can drive beside a Python one in the lane. A mixed society is what holds the two to one wire, where
a case holds each to itself.

**A ported package is frozen until its last Python user moves.** A package ported early is still loaded in
Python by every agent whose other packages are not yet ported, so both copies live for a while. While they
do, a fix lands in both, and a new behaviour waits, or lands in Rust alone once no Python agent loads the
package. So the two copies never drift apart, and nobody pays for a feature twice. The cases are TriG files
that both runners read, so they hold either copy to the same store.

**When the last world runs on the binary, the Python agent is retired whole.** The commit before its deletion
is tagged as the last Python release, as 0.1.0's tree was retired, and `agent/` holds the Rust agent alone. Done on 2026-11-09: what the operator's tools and the simulator still read a world with
is `documents/`, a package of its own since the simulator's image may hold no onboarding code.
The snapshot cases outlive it, being files and not Python.

**What is no agent's stays Python.** Onboarding stays Python, with pyshacl, and keeps the admin token out of
every image. It reads a world as an agent boots it by running the agent's binary to boot and check that
world, rather than by importing its code — `orexis-agent --check --boot FILE`, which `orexis-onboard` runs for
every agent, reading back the store it wrote to hold the requirements to and to derive what it derives, so a
world is booted once, by the agent that will run it. The simulator,
the operator's tools and the history view stay as they are.

**What waits is a task, and the mind is one thread.** Today the runtime polls: a pass that moved
nothing sleeps a second and looks again, so a reading waits up to that second and an idle agent wakes every
one. Each transport, the model's call and the journal's server has a thread of its own, and so does the
executor, twice. In Rust, everything that waits on the network or the clock is a Tokio task:

- the MQTT, HTTP, Telegram and email members;
- the model's call, the series' writes and the journal's server;
- every timer, the executor's landings and patience among them.

Each task hands the mind what arrived over a channel. The mind is one thread that owns every write to the
store and runs the passes, woken by its channel or the next timer due, so a reading starts a pass at once and
an idle agent sleeps. Its jobs run in the order they came, which is what lets a snapshot case and the day
bench's digest hold the binary to one result. A pass blocks on the engine and a search can run for seconds,
so the mind is a thread of its own and never one of Tokio's workers, whose transports it would stall.

**The binary links the parts.** A Python part links to the others by connecting signals. In the mind's one thread,
the binary shares a part's own object instead. The executor asks the shared Planner about a head it is about to
take, and planning tells the shared executor, after its pass and before it decides what holds the agent, what the
pass published, reached and reconsidered, in the order the Python signals fire. The executor tells the shared
deliberator each graph it writes as the world, as it writes it, so what the rules conclude of it stands before the
walk goes on, and a revision pass that changed the present queues a walk. Sensing hands the shared deliberator every
percept it writes, with its own kind for the revision. The executor hands the shared transport member each command a
step's implementation sends, and what the member's thread receives waits in its inbox until the pass takes it as a
job. Speech keeps each document a step says and tells it through the member, and coordination says what it asks
and answers through speech, and asks the shared Planner to reopen the plans a draw it has won decides. The planner is handed the predictor's foresight, which it
advances as it lays each ground, through a trait the kernel keeps because the two packages meet at it, as they meet
at `orexis:FlowGraph`. What a part answers it wrote, the runtime
hands to each part listening for a kind the catalogue says it is, as the Python runtime's `on` does. What WATCHES the
agent is one watch per agent, handed to every part: history and metrics heard every Python signal, so a Python
signal's `connected` was always the question whether anybody watches, and an event is made exactly where it was. No
crate names another's, since the binary is the container that assembles them all.

**What cannot change the result runs in parallel.** Each scope's imaginarium is a store of its own, so the
scopes are searched at once and their plans taken in scope order. Laying grounds is per scope and about
two-thirds of the greenhouse's planning. A reader of the store, a chat's query or the journal's server, reads
a snapshot of it, beside a pass and without waiting for one.

**The clock is handed in.** A walk or a bench runs in the world's time, so the binary reads time through
one clock it is handed: the wall in a container, a simulated one in a test, which a day runs through as fast
as the machine allows.

# What was refused

**A Rust core under Python.** Moving the hot kernel into a crate that Python calls through PyO3 would have
given most of the speed soonest. But every image would keep the interpreter, the package manager and every
package's Python, which is the opposite of the image the sovereign asked for. It would also mean two
languages in one agent for good, and a boundary between them crossed per statement.

**Staying Python.** Parsing, rdflib and conversions are most of a shipped world's pass, and are what the
language costs. The image cannot be made minimal around an interpreter.

**A store shared under locks.** Every task could write the store itself, behind a lock. Then the order of
two writes would be the scheduler's, and a case or a digest could not hold the binary to one result.

**Async into the mind.** The mind's functions could be async too. The engine is synchronous, so nothing
would be gained, and every function would take on async to call one that has it.

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
