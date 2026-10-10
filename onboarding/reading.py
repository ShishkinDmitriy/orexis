"""The world as onboarding reads it: what an agent reads of it, and then the kinds no agent does.

**A document's kind says who reads it, and every reader loads only the kinds it reads**
(knowledge/decisions/a-documents-kind-says-who-reads-it.md). An agent's boot passes over a graph
whose kind its T-Box does not declare. Onboarding's own kinds — the hardware `orexis-firmware`
interpolates into a board's config.h, and the deployment — are declared in `ontology.ttl` beside
this module and outside `agent/`, so no agent's vocabulary can say what they are and the import
direction holds: onboarding may import the agent, never the reverse.

So onboarding does not borrow the agent's boot whole, which is what once made the hardware public
to every agent: `world` reads the world as an agent does (`agent.runtime.world_of`), then its own
vocabulary, then every graph in the world's directory of a kind that vocabulary declares.

**A kind no reader declares is refused here, because nowhere else can.** Passing over an unknown
kind makes a misspelled one silent in every reader; onboarding knows every reader's vocabulary, so
`unread` names the graphs none of them reads, and `orexis-onboard` refuses a world that has any.

**A margin its range cannot hold is refused here, for the same reason** (`unholdable`,
knowledge/domain/sensing/margin.md): a domain's transition judging an observation into a subject
belief takes `sensing:margin` as stated, so one that is no number, negative, or of half its range's
width or more is caught here or nowhere.

**A step runs where the world has what it serves.** `premises` answers which of `PREMISES` hold of
a world (#824): the broker's credentials and its ACL, the agents' certificates and the broker in a
compose file are granted to a world whose society names a broker, and a world naming none is
onboarded without them.

**What an agent runs is declared, and held to its world both ways here** (knowledge/decisions/
a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md). `refused` boots every agent as
its container boots it and says each way its roles and its world disagree: an agent declaring no
role, which would run nothing; a declared role whose needs the world lacks, each need a shape the
package or domain owning its words ships, `sh:targetClass` the role and a `sh:sparql` select whose
every row is a violation; a sensor reporting to an agent that is no observer; a topic an agent
listens to with no speaker to hear it; and a graph the agent would read of a kind none of the
packages it loads declares — the refusal `unread` makes of the world, narrowed to the agent. It does
NOT refuse a drift with no predictor, foresight being the author's to decline, nor an action whose
saying an agent is in no role to take, which is the search's to say and not onboarding's.

**Whether an agent lasts is read off the agent, as its boot reads it.** `lasts` boots the agent
from the world's documents and asks the two things the runtime's own stop rule asks
(`Runtime._pass`): a desire it holds, which asks at every instant, and a transport, whose
readings go on arriving. Holding neither, it exits once every want is reached — or planned, where
it is no executor — or as unreachable, and its compose service is not restarted — a restart would only boot, find nothing
to pursue and exit again. Per agent and not per world, since a desire is in an agent's own graphs.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pyoxigraph as ox

from agent.planning.planner import Planner
from agent.runtime import (MINE, MQTT, OBSERVER, PLANNING, SPEAKER, boot, documents, known, packages_of,
                           read_with_imports, roles_of, selves, world_of)
from agent.store import (answer, catalogue_of, close_catalogue, closed, document, graphs_of, kinds_in, put_document,
                         rows, whose)

from .worlds import DOCUMENTS

VOCABULARY = Path(__file__).resolve().parent / "ontology.ttl"
ONBOARDING = "http://example.org/orexis/onboarding#"
HARDWARE = ONBOARDING + "HardwareGraph"
DEPLOYMENT = ONBOARDING + "DeploymentGraph"
PUBLIC = "http://example.org/orexis#PublicGraph"
GRAPH = "http://example.org/orexis#Graph"
SELF_GRAPH = "http://example.org/orexis#SelfGraph"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"

_CLASS = ox.NamedNode("http://www.w3.org/2002/07/owl#Class")
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  WHAT A STEP OF ONBOARDING SERVES, AS A PREMISE READ OFF THE WORLD (#824): an ASK per premise over
#  the world's public graphs, in T-Box terms alone. Onboarding's own, and the one kind of premise
#  left: what an AGENT runs is declared in its roles, never derived (#927). A
#  step runs where its premise holds and says it was skipped where it does not, so a world is
#  granted what it has and nothing it lacks. The BUS is a broker the world's society names: the
#  broker's credentials, its ACL, the agents' certificates and the broker in the compose file all
#  serve one, and a world with none — a puzzle, a courier's map — has nothing for them to serve.
#  History has no premise, since every agent writes it; metrics' is the world's deployment saying
#  `onboarding:monitored`, which `installation.purposes` asks.
BUS = "bus"
PREMISES = {BUS: f"ASK {{ ?broker a <{MQTT4SSN}Broker> }}"}


@cache
def ours() -> frozenset[str]:
    """Every class onboarding's vocabulary declares — the kinds only onboarding reads."""
    return frozenset(q.subject.value for q in document(VOCABULARY).quads_for_pattern(None, _TYPE, _CLASS, None))


def _files(world: Path) -> list[Path]:
    return sorted(p for p in world.iterdir() if p.is_file() and p.suffix in DOCUMENTS)


def world(here: Path) -> ox.Store:
    """The world in `here` as onboarding reads it: its public graphs as an agent reads them, and
    every graph in its directory whose kind onboarding's vocabulary declares, closed. The first
    half passes over onboarding's kinds, and says so only at DEBUG, since the second half reads
    them."""
    here = Path(here).resolve()
    store = world_of(here, others=ours())
    put_document(store, document(VOCABULARY))
    for path in _files(here):
        doc = document(path)
        graphs = {g for g, kinds in kinds_in(doc).items() if any(ours() & set(closed(store, k)) for k in kinds)}
        if graphs:
            put_document(store, doc, graphs=graphs)
    close_catalogue(store)
    return store


def premises(here: Path) -> frozenset[str]:
    """Every premise in `PREMISES` that holds of the world in `here`, read as onboarding reads it."""
    store = world(here)
    public = graphs_of(store, PUBLIC)
    return frozenset(premise for premise, ask in PREMISES.items() if answer(store, ask, public)["boolean"])


def lasts(here: Path, agent_id: str) -> bool:
    """Whether the agent `agent_id` of the world in `here` runs for as long as its process does —
    booted from the documents as its container boots it, into a store of its own in memory: it
    holds a desire, or the MQTT transport is among the packages it loads, which is what brings a
    transport up (`_transport_of`). False for an agent holding wants alone and reached by no
    transport, which the runtime lets finish."""
    beliefs = boot(Path(here).resolve(), agent_id, others=ours())
    loaded = packages_of(beliefs)
    return (PLANNING in loaded and Planner(beliefs, agent_id).holds_a_desire()) or MQTT in loaded


def contradicted(here: Path, agent_id: str) -> list[str]:
    """Every constraint the agent `agent_id` of the world in `here` holds that the world AS POSED
    violates, as `constraint: (instance, constraint, offending), …` — asked of the agent as its boot
    reads it, by the Planner's own judge. A constraint is what the world says is possible, so a
    world whose asserted state violates its own word is a contradiction and not a want anyone could
    repair: `orexis-onboard` refuses it before anything is granted, as it refuses a world that will
    not load, since a society started that way would say the contradiction in every pass and mend
    nothing (knowledge/domain/planning/constraint.md). Empty for a world posed as it says it can be,
    and for an agent that is no planner, which weighs no constraint."""
    beliefs = boot(Path(here).resolve(), agent_id, others=ours())
    if PLANNING not in packages_of(beliefs):
        return []
    planner = Planner(beliefs, agent_id)
    return [f"{constraint.rsplit('#', 1)[-1]}: " + ", ".join(
                f"({str(i).rsplit('#', 1)[-1]}, {c}, {str(o).rsplit('#', 1)[-1]})" for i, c, _, o in sorted(broken, key=str))
            for constraint, broken in planner.contradictions()]


def unread(here: Path) -> list[str]:
    """Every graph the world in `here` holds — in its directory, in every agent's own documents
    under `beliefs/`, and in whatever they import — whose kind no reader declares, as
    `document: graph (kinds)`. Empty for a world every one of whose graphs somebody reads."""
    here = Path(here).resolve()
    store = world(here)
    out = []
    for path, doc in read_with_imports(documents(here)):
        for graph, kinds in sorted(kinds_in(doc).items()):
            if not known(store, kinds):
                out.append(f"{path.name}: {graph} ({', '.join(sorted(kinds))})")
    return out


#  EVERY MARGIN A RANGE CANNOT HOLD (knowledge/domain/sensing/margin.md), with its range's name where it
#  has one — a blank range is said as one with no name, and judged like any other — and the bounds it
#  widens: one that is no number, which a transition's sum binds nothing with, so a subject held below
#  or above would be judged in no state at all; a negative one, which widens nothing, so a transition
#  would read as nought a figure the world stated; and one of half its range's width or more, since every act
#  here aims at a range's middle and a subject a step brought there would still be believed in the
#  state it came from.
_MARGINS_Q = """
SELECT ?named ?margin ?low ?high WHERE {
  ?range ssn-system:inCondition ?condition . ?condition sensing:margin ?margin .
  OPTIONAL { ?condition schema:minValue ?low } OPTIONAL { ?condition schema:maxValue ?high }
  BIND(IF(isIRI(?range), STR(?range), "") AS ?named)
  FILTER(!isNumeric(?margin) || ?margin < 0
         || (BOUND(?low) && BOUND(?high) && 2 * ?margin >= ?high - ?low)) }
ORDER BY ?named ?margin"""


def unholdable(here: Path) -> list[str]:
    """Every margin the world in `here` states that its range cannot hold, as `range: why`. Empty for a
    world each of whose margins is a number from nought to less than half its range's width — every
    world stating none among them."""
    store = world(here)
    out = []
    for r in rows(store, _MARGINS_Q, graphs_of(store, PUBLIC)):
        said = f"a margin of {r['margin']}"
        named = r["named"] or "a range with no name"
        try:
            margin = float(r["margin"])
        except ValueError:
            out.append(f"{named}: {said}, which is no number")
            continue
        out.append(f"{named}: {said}, which is negative and widens nothing" if margin < 0 else
                   f"{named}: {said}, half the width of [{r['low']}, {r['high']}] or more — a subject a step "
                   f"brought to its middle would still be believed in the state it came from")
    return out


#  EVERY AGENT THE WORLD STATES, by the id its process is told.
_AGENTS_Q = "SELECT ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id } ORDER BY ?id"

#  WHAT A ROLE NEEDS OF THE WORLD: every shape the vocabularies ship targeting a class, with the
#  select its `sh:sparql` constraint carries and what it says when a row comes back — read off every
#  package's ontology and every domain's, the world's store holding them all, since a need is the
#  shape of the package or domain owning its words and not always of the role's declarer.
_NEEDS_Q = """
SELECT ?role ?select ?message WHERE {
  ?shape a sh:NodeShape ; sh:targetClass ?role ; sh:sparql ?constraint .
  ?constraint sh:select ?select OPTIONAL { ?constraint sh:message ?message } }"""

#  WHETHER THE SELF IS READ BY A PACKAGE IT DOES NOT LOAD, off the public graphs and the self.
_SENSOR_Q = f"ASK {{ ?me a orexis:Self . {MINE} }}"
_LISTENS_Q = "ASK { ?me a orexis:Self ; mqtt4ssn:listensToTopic ?topic }"


def agents(here: Path) -> list[str]:
    """Every agent the world in `here` states, by id, sorted."""
    store = world(here)
    return [r["id"] for r in rows(store, _AGENTS_Q, graphs_of(store, PUBLIC))]


def loaded(here: Path) -> frozenset[str]:
    """Every package SOME agent of the world in `here` loads: each agent booted as its container
    boots it, since what an agent runs is its roles', declared in its own self graph, which a store
    of the whole world does not hold."""
    here = Path(here).resolve()
    return frozenset(p for agent_id in agents(here) for p in packages_of(boot(here, agent_id, others=ours())))


def refused(here: Path) -> list[str]:
    """Every way an agent of the world in `here` is declared that its world does not bear out, as
    `agent: why` — each agent booted from the documents as its container boots it. Empty for a world
    whose every agent runs what it is declared to and is read by what it runs."""
    here = Path(here).resolve()
    store = world(here)
    needs = rows(store, _NEEDS_Q, graphs_of(store, PUBLIC))
    return [f"{agent_id}: {why}" for agent_id in agents(here)
            for why in _refusals(here, boot(here, agent_id, others=ours()), needs)]


def _refusals(here: Path, beliefs: ox.Store, needs: list[dict]) -> list[str]:
    roles = roles_of(beliefs)
    if not roles:
        return ["declares no role in its self graph, so it would load no package and run nothing — "
                "`<agent> a orexis:Self , <role>` says what it runs"]
    cat = catalogue_of(beliefs)
    held = [g for g in graphs_of(beliefs, GRAPH) if g != cat]
    out = [need.get("message") or f"its world lacks what {need['role']} needs" for need in needs
           if need["role"] in roles and rows(beliefs, need["select"], held)]
    public = graphs_of(beliefs, PUBLIC, SELF_GRAPH)
    if OBSERVER not in roles and answer(beliefs, _SENSOR_Q, public)["boolean"]:
        out.append("a sensor reports to it, and it is no observer: no package it loads would read the sensor")
    if SPEAKER not in roles and answer(beliefs, _LISTENS_Q, public)["boolean"]:
        out.append("it listens to a topic, and it is no speaker: no package it loads would hear what arrives there")
    (me,) = selves(beliefs)
    for path, doc in read_with_imports(documents(here, packages_of(beliefs))):
        for graph, kinds in sorted(kinds_in(doc).items()):
            if known(beliefs, kinds) or ours() & kinds or whose(doc, graph) not in (None, me):
                continue
            out.append(f"{path.name}: {graph} is of a kind none of the packages it loads declares "
                       f"({', '.join(sorted(kinds))})")
    return out
