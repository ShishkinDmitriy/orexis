---
type: Decision
title: The self is a class held to one instance, authored in the agent's self graph and checked by the boot, and a text asks for it
status: accepted
timestamp: 2026-10-08
description: >-
  Every text about the agent was handed `$me`, because nothing in the store said who the agent
  was. The world now authors `<agent> a orexis:Self` in a self graph of the agent's own, the boot
  checks it against the id the process was told, and a text asks `?me a orexis:Self`. Whose a
  graph of an agent's own is, its document says, never its file's name. Refused - the boot minting
  the self, a file's name saying whose, a singleton IRI, a public self graph, a guard in each text.
  The first half of #876.
---

# What was true (measured 2026-10-08, on main at e99731d0)

**The one identifier a process is told was threaded by hand into every text that mentioned the
agent.** 37 `$me` tokens in 14 files under `agent/`, `domains/` and `world/` — 27 of them in 21
query texts, the rest in the prose describing them: the five premises, the three readings of the
agent's sensors (the premises', the MQTT driver's, the HTTP driver's), sensing's limits, the
planner's subject, and every precondition, effect, command and saying of the actuation, climate
and market domains. 15 Python sites bound it (`me=` and a `"me"` token), and `take`, `admit`,
`command`, `says`, `limit_of`, `packages_of` and couplings' helpers took the agent as an argument
for that alone.

**Nothing in the store could have answered for it.** One agent, one volume (rule 4) makes every
agent's store hold exactly one agent that is THIS one, but no fact said which: the boot found the
agent by its `orexis:localId` and kept the IRI in Python.

**And an agent's own documents were found by their file's name** — the one place the boot relied
on a name. `documents()` globbed `beliefs/<id>.*`, `orexis-compose` mounted `beliefs/<id>.*` into
the agent's container, and every other document of a kind that is not public was the booting
agent's because it sat beside the world. The loader refused a document stating `orexis:beliefsOf`
as "what only the loader says", so no document could say whose it was, and the boot owned what it
read by where it found it: 14 private documents across 9 worlds, 3 of them under `beliefs/`.

# The decision

**The world authors the self, and the boot checks it.** Each agent has a private document of kind
`orexis:SelfGraph` that says who it is — `<> a orexis:SelfGraph . :rose_grower a orexis:Self .` —
written by the sovereign under `beliefs/`, as the agent's desires are: a belief given at birth. The
boot keeps exactly the private documents whose content says they are the agent it was told to be
(found by `orexis:localId`, as before), finds exactly one self graph among them, puts it in owned
and asserted, and counts every self in every graph: anything but that one agent does not boot. A
text asks `?me a orexis:Self` and is bound nothing; `store.bind` still refuses a token nobody
binds when a text runs, and `tests/test_store.py` refuses a `$me` written anywhere in the trees a
text lives in ([self](/domain/kernel/self.md)). All ten shipped agents, across nine worlds, have one.

**Whose a graph of an agent's own is, its document says: `<> orexis:beliefsOf :rose_grower`,**
beside `<> a planning:DesireGraph`, the way it says what the graph is (`store.whose`). A self graph
needs no such row: it is its self's by the self it states, and a row stated beside it must name
the same agent or the file is refused — one fact, one source, and two that disagree are not
picked between. The boot passes over another agent's graph rather than refusing it: a world read
from a checkout, as every test and onboarding's `lasts` read it, holds every agent's, and in a
container only the agent's own are mounted; which files happen to be present is exactly the thing
the boot is not to rely on. `orexis-compose` mounts each document into the container of the agent
its content names, and the simulator, which is no agent, the public documents alone.

**The loader's refusal is relaxed for what the WORLD authors, and only there.** It refused a stated
owner because the catalogue's provenance rows are the loader's to write — `orexis:arrivedBy` still
is, from every document. But the boot was already writing `orexis:beliefsOf` on every private file
it read, and choosing the owner by the file's location: the owner was a guess, and the document is
where the sovereign can say it. A FILE (`store.document`) may now state an owner, one per graph,
naming an agent the world states; a graph naming nobody, or nobody the world states, is refused,
since kept by its owner it would be in no agent's store, silently. A PUBLIC graph stating one is
refused, since a lived-in volume reads again only what nobody owns and an owned public graph would
never be refreshed. A PEER's document (`heard`) and the agent's own SAYING (`said`) state neither an
owner nor a self (`store.refuse_the_sovereigns`): the hearer and the sayer are the owner of what
they put in, and no peer tells an agent who it is.

**The self has one home.** A file states a self only in a graph that says it is a self graph and
nothing else, exactly once there; a self in a world graph, a desire graph or a document's rows is
refused at the loader. Asked by the kinds the document states, the check needs no vocabulary,
which the loader does not have.

**A graph kind of its own, beneath `orexis:BeliefGraph`.** A belief, so every text answered over
what is known reads it — a precondition in a possible world, a command over the present — and it
crosses into an imaginarium with the beliefs; not public, so the readers of the public graphs
alone that ask the self (the premises, the two drivers' sensors, the planner's subject) state its
kind beside `orexis:PublicGraph`. Sensing's limits were a fifth such reader until #876's second half
made them stances, read off the self graph alone
([a-stance-is-the-agents-word-about-itself](/decisions/a-stance-is-the-agents-word-about-itself.md));
#927's roles are to be stated in it too.

# What was refused

**The boot minting the self from the id it was told** — this record's first form, as 68e9e352
shipped it: `<agent> a orexis:Self` written into `graph/self/<id>`, recorded, wherever a store held
none. It made the self a conclusion of a deployment fact, when it is a belief the sovereign gives at
birth, as a desire is; it left the stances and roles #876 and #927 bring with no authored home
beside it; and it could not be wrong, so nothing checked it — a world whose author meant the agent
to be someone else had no way to say so. Authored, the told id is CHECKED against what the world
said, and the two refusals it opens (no self graph, two) are cases the boot reports.

**A file's name saying whose a document is** — `beliefs/<id>.ttl`, and a private document beside the
world being whoever's boot read it. A name is for eyes everywhere else in the tree (a document says
which graph it is); here it was the one premise the boot drew from one, and a world of one agent
was the only reason the second half held. Rewritten by content, `beliefs/` is where a world keeps
its agents' documents and nothing more.

**Reading ownership off a desire's `planning:holds`.** The desires already say `:rose_grower
planning:holds …`. It does not generalise: the courier's and Hanoi's state graphs name no agent at
all, a self graph names its agent by another word, and a graph of stances would by a third; and it
is planning's word read by the kernel's boot. `orexis:beliefsOf` is already the word for whose a
graph is, on every row the catalogue holds; a second word would be the synonym the dictionary
refuses.

**A directory per agent, `beliefs/<id>/`.** A path is a name; it moves the reliance, it does not end
it.

**A singleton IRI, `orexis:self`.** It was the first thought: one well-known node every text names.
It is an instance named in code, which rule 1 refuses; it is a second name for an agent the world
already names, the synonym the dictionary refuses; and it makes two instances impossible only by
making two agents indistinguishable — a test store holding three agents' documents would merge
whatever each said of itself into one node, without a word. The class is the project's own idiom:
ask what a thing IS.

**The self graph beneath `orexis:PublicGraph`**, which would have cost no reader anything, since
every reader of a text about the agent already reads the public graphs. Public means what every
agent of a world may read; the self is true of one store and of no other, and a graph typed public
is one whose content a reader may take for the world's.

**An existing per-agent kind.** A state graph is spoken for by the grounds — copied into every
world a search forks and into its hash; a record graph says how long what it states is worth
believing; a working graph is read by its own package alone and never crosses into a possible
world. The self is none of those.

**A guard in each text** — a `LIMIT 1`, a count beside the pattern. A text asking `?me a
orexis:Self` over two selves answers rows for both, the empty-result trap's twin; guarding every
text is the same rule written twenty times. The gate stands once, at the boot.

**Binding each agent in turn where a store holds a whole world.** The operator's dashboards asked
every package's premise once per agent, `$me` bound to each; a world's store holds no self — it
passes over every graph of an agent's own, the authored self graphs among them — so a premise there
is asked of every `orexis:Agent` at once (`packages_of(store, orexis:Agent)`), which is the union
the dashboards took.

**A footprint reading the self's pattern.** Kept in, `?me a orexis:Self` binds nothing over the
public graphs a filling is asked over, stands first in rdflib's order as the pattern with fewest
variables, and reorders the OPTIONAL chain: the greenhouse's dose came to be filled with the heater
and its scopes moved, measured. A footprint reads a text without it, since no public graph holds
the self and no action writes it.

# Seams left open

- **A volume lived in before its world authored a self graph** holds none, and the boot puts the
  authored one in; the wrong-volume refusal cannot fire on that one boot.
- **A store of several holders and no self** — a test's world — answers nothing to a text naming
  the agent, so couplings read over such a store admit nothing for those texts and couple less.
  The derivation's own `holder=` is untouched: it names whose desires and constraints a pass reads.
- **The agent's IRI still travels where a graph is WRITTEN** — the owner a write classifies with,
  the planner's and the executor's identity read by `orexis:localId`. A writer must say whose a
  graph is; that is a write target, not a text being handed the agent.
- **A document authored after birth is not read by a volume lived in**, the self graph's first
  arrival apart: the agent's own graphs are its beliefs from the first boot on
  (an-amendment-endows-what-it-grants), and a stance or a role added later reaches it on a fresh
  volume only.
- **The roles an agent holds** are #927's, to be stated in the self graph when they are built. Its
  stances are stated there already
  ([a-stance-is-the-agents-word-about-itself](/decisions/a-stance-is-the-agents-word-about-itself.md)).
