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

**A world is held to the shapes its vocabularies ship, here and nowhere else** (#838). The package
or domain owning a word ships the shape a document using it is held to, in a requirement graph
beside its ontology, of onboarding's kind, which no agent loads: a
sensor observes a property and is mounted on something, a range's floor is below its ceiling and
its margin a number it can hold, a desire is judged by one test. pyshacl judges each agent's boot, which is what it
will believe, so an agent's own documents may complete what the world's leave out; `invalid` says
once what the common beliefs break and every agent's boot breaks too, and `refused` the rest, per
agent. What the world states
is accepted and revised once it runs; a document the sovereign authored may be garbage, and this is
the last reader before it is believed.

**A step runs where the world has what it serves.** `premises` answers which of `PREMISES` hold of
a world (#824): the broker's credentials and its ACL, the agents' certificates and the broker in a
compose file are granted to a world whose society names a broker, and a world naming none is
onboarded without them.

**What an agent runs is declared, and held to its world both ways here** (knowledge/decisions/
a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md, a-role-is-an-instance-an-agent-plays.md).
`refused` boots every agent as its container boots it and says each way its roles and its world
disagree: an agent playing no role, which would run nothing; a declared role whose needs the world lacks, each need a shape the
package or domain owning its words ships, `sh:targetClass` the role and a `sh:sparql` select of
`$this`, the role, for every way it is unmet; a shape its own documents break, as a desire
judged by both tests; a sensor reporting to an agent that no observer role of its reads; a topic an agent
listens to with no speaker to hear it; and a graph the agent would read of a kind none of the
packages it loads declares — the refusal `unread` makes of the world, narrowed to the agent. It does
NOT refuse a flow with no predictor, foresight being the author's to decline, nor an action whose
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
import pyshacl
import rdflib

from agent.planning.planner import Planner
from agent.ontology import local_of
from agent.runtime import (MQTT, ONTOLOGY, PLANNING, SPEAKER, boot, documents, known, packages_of, read_with_imports,
                           roles_of, selves, world_of)
from agent.store import (NAMESPACES, DocumentRefused, answer, catalogue_of, close_catalogue, closed, document, graphs_of, kinds_in, put_document,
                         rdflib_view, rows, whose)

from .worlds import DOCUMENTS

REQUIREMENT = "http://example.org/orexis/onboarding#RequirementGraph"
_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

VOCABULARY = Path(__file__).resolve().parent / "ontology.ttl"
REQUIREMENTS = Path(__file__).resolve().parent / "requirements.ttl"
INSTALLATION_REQUIREMENTS = Path(__file__).resolve().parent.parent / "infra" / "requirements.ttl"
ONBOARDING = "http://example.org/orexis/onboarding#"
HARDWARE = ONBOARDING + "HardwareGraph"
DEPLOYMENT = ONBOARDING + "DeploymentGraph"
BELIEF = "http://example.org/orexis#BeliefGraph"
GRAPH = "http://example.org/orexis#Graph"
SELF_GRAPH = "http://example.org/orexis#SelfGraph"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"

_CLASS = ox.NamedNode("http://www.w3.org/2002/07/owl#Class")
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  WHAT A STEP OF ONBOARDING SERVES, AS A PREMISE READ OFF THE WORLD (#824): an ASK per premise over
#  the world's common beliefs, in T-Box terms alone. Onboarding's own, and the one kind of premise
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
    """The world in `here` as onboarding reads it: its common beliefs as an agent reads them, and
    every graph whose kind onboarding's vocabulary declares, closed — in its directory, its hardware
    and its deployment, and beside every package's and imported domain's ontology, their requirement
    graphs. The first half passes over onboarding's kinds, and says so only at DEBUG, since the
    second half reads them."""
    here = Path(here).resolve()
    store = world_of(here, others=ours())
    put_document(store, document(VOCABULARY))
    put_document(store, document(REQUIREMENTS))
    for _, doc in read_with_imports(documents(here)):
        graphs = {g for g, kinds in kinds_in(doc).items() if any(ours() & set(closed(store, k)) for k in kinds)}
        if graphs:
            put_document(store, doc, graphs=graphs)
    close_catalogue(store)
    return store


def premises(here: Path) -> frozenset[str]:
    """Every premise in `PREMISES` that holds of the world in `here`, read as onboarding reads it."""
    store = world(here)
    stated = graphs_of(store, BELIEF, common=True)
    return frozenset(premise for premise, ask in PREMISES.items() if answer(store, ask, stated)["boolean"])


def lasts(here: Path, agent_id: str) -> bool:
    """Whether the agent `agent_id` of the world in `here` runs for as long as its process does —
    booted from the documents as its container boots it, into a store of its own in memory: it
    holds a desire, or the MQTT transport is among the packages it loads, which is what brings a
    transport up (`_transport_of`). False for an agent holding wants alone and reached by no
    transport, which the runtime lets finish."""
    beliefs = boot(Path(here).resolve(), agent_id, others=ours())
    loaded = packages_of(beliefs)
    return (PLANNING in loaded and Planner(beliefs, agent_id).holds_a_desire()) or MQTT in loaded


def check(here: Path) -> None:
    """Refuse the world in `here`, naming every way, where its documents fail what onboarding holds
    them to; nothing where they hold. `orexis-onboard` asks it first, and so does every tool it
    runs that is called alone, so a renderer only ever reads a world that holds (#838) and formats
    what it reads, judging nothing. Refused in that order, each said whole before the next is asked:

    a world that will not load, or a graph of a kind no reader declares — every reader passes over
    such a graph in silence, so a misspelled kind is caught here or nowhere; a requirement the
    world breaks; an agent whose roles its world does not bear out, an agent declaring no role among
    them, which would boot and run nothing (a-package-is-loaded-only-for-a-role-the-agent-is-declared-in);
    and a world posed in a state its own constraints say is impossible, which no agent repairs — it
    would say so in every pass and mend nothing (constraint.md)."""
    here = Path(here).resolve()
    name = here.name
    try:
        found = unread(here)
    except DocumentRefused as why:
        raise SystemExit(f"world {name!r} does not load — {why}; nothing granted")
    if found:
        raise SystemExit(f"world {name!r} holds graphs of a kind no reader declares — {'; '.join(found)}; nothing granted")
    found = invalid(here)
    if found:
        raise SystemExit(f"world {name!r} states what its requirements refuse — {'; '.join(found)}; nothing granted")
    found = refused(here)
    if found:
        raise SystemExit(f"world {name!r} declares its agents' roles in a way it does not bear out — "
                         f"{'; '.join(found)}; nothing granted")
    found = [f"{a} holds {c}" for a in agents(here) for c in contradicted(here, a)]
    if found:
        raise SystemExit(f"world {name!r} is posed in a state its own constraints say is impossible — "
                         f"{'; '.join(found)}; nothing granted")


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


def invalid(here: Path) -> list[str]:
    """Every way the world in `here` breaks a requirement its vocabularies ship that no agent's own
    documents complete, as `focus: why`, or `why` alone where the focus has no name: what the common
    beliefs break and every agent's boot breaks too, said once as the world's. Empty for a world whose
    common beliefs conform, or are completed in every agent. What an agent's boot breaks and the
    others' do not is `refused`'s, per agent."""
    of_world, _ = _judged(Path(here).resolve())
    return sorted(of_world.values())


def _judged(here: Path) -> tuple[dict[tuple, str], dict[str, list[str]]]:
    """What the requirements report of the world in `here`: what is the world's, and what is each
    agent's alone, by its id.

    WHAT IS JUDGED IS WHAT AN AGENT WILL BELIEVE — its boot, the common beliefs with its own documents
    beside them — so a world's document may leave a fact about a shared thing to the agents' own, and
    an agent whose own documents complete it is not refused. The common beliefs are judged alone only
    to say a fault once: one they break that every agent's boot breaks too is the world's, and the rest
    each agent's that reports it. The world's deployment is judged beside either, being no belief and
    the world's alone: what it says of the broker the society names is what the broker is told."""
    store = world(here)
    shapes = shapes_of(store)
    deployed = rdflib_view(store, *graphs_of(store, DEPLOYMENT))
    common = _held_to(shapes, store, graphs_of(store, BELIEF, common=True), deployed)
    each = {}
    for agent_id in agents(here):
        beliefs = boot(here, agent_id, others=ours())
        cat = catalogue_of(beliefs)
        each[agent_id] = _held_to(shapes, beliefs, [g for g in graphs_of(beliefs, GRAPH) if g != cat], deployed)
    of_world = {key: why for key, why in common.items() if all(key in found for found in each.values())}
    return of_world, {agent_id: sorted(why for key, why in found.items() if key not in of_world)
                      for agent_id, found in each.items()}


def shapes_of(store: ox.Store) -> tuple[rdflib.Graph, rdflib.Graph]:
    """Every requirement the world in `store` holds, and the vocabulary its shapes target through.

    A requirement is a package's or a domain's word about its own terms, shipped beside its ontology
    in a graph of onboarding's kind, which no agent loads (requirement.md, #838). Both are read off
    the WORLD, which knows every package's vocabulary, and never off an agent's boot, which loads
    only what its roles do: an agent playing an executor alone loads no planning, and the shape
    refusing it is planning's."""
    return rdflib_view(store, *graphs_of(store, REQUIREMENT)), rdflib_view(store, *graphs_of(store, ONTOLOGY))


def _held_to(shapes: tuple[rdflib.Graph, rdflib.Graph], store: ox.Store, held: list[str],
             beside: rdflib.Graph) -> dict[tuple, str]:
    """What the requirements in `shapes` report of the graphs `held` in `store`, keyed by the message and the focus where
    that has a name — which is what tells a report about the world from one about an agent's own
    documents in an agent's boot. The graphs cross into rdflib for pyshacl with the store's namespaces
    bound on what is held, since pyshacl reads a constraint's select against the graph it asks, and
    the world's vocabulary mixed in, so a role is targeted through the class it is beneath. What is
    judged `beside` them is in no agent's store, and crosses as it is."""
    data = rdflib_view(store, *held)
    data += beside
    return reported(data, *shapes)


@cache
def own() -> rdflib.Graph:
    """What the installation is held to: onboarding's own requirements, which a world is held to as
    well — the port one listener holds, the credential no url carries — and the installation's own,
    beside its document, which no world is, since a world states no store (`INSTALLATION_REQUIREMENTS`)."""
    return rdflib.Graph().parse(REQUIREMENTS) + rdflib.Graph().parse(INSTALLATION_REQUIREMENTS)


def reported(data: rdflib.Graph, requirements: rdflib.Graph, vocabulary: rdflib.Graph | None = None) -> dict[tuple, str]:
    """What `requirements` report of `data`, keyed by the message and the focus where that has a
    name, and said as `focus: why` with the focus's local name, or `why` alone. The store's
    namespaces are bound on `data`, since pyshacl reads a constraint's select against the graph it asks."""
    for label, iri in NAMESPACES.items():
        data.bind(label, iri, override=True, replace=True)
    _, report, _ = pyshacl.validate(data, shacl_graph=requirements, ont_graph=vocabulary)
    out = {}
    for result in report.subjects(_SH.resultMessage, None):
        focus, message = report.value(result, _SH.focusNode), str(report.value(result, _SH.resultMessage))
        named = isinstance(focus, rdflib.URIRef)
        out[(message, str(focus) if named else None)] = f"{local_of(str(focus))}: {message}" if named else message
    return out


#  EVERY AGENT THE WORLD STATES, by the id its process is told.
_AGENTS_Q = "SELECT ?id WHERE { ?a a orexis:Agent ; orexis:localId ?id } ORDER BY ?id"

#  EVERY SENSOR THAT REPORTS TO THE SELF AND NO OBSERVER ROLE OF ITS READS, off the common beliefs and
#  the self: mounted on what it acts for, a sample of it, a sample it carries (a contact, #1003), or a
#  place containing it. The converse of the observer shape (agent/sensing/requirements.ttl), which refuses
#  a sensor a role reads that does not report to it; between them a declaration and the world it is made
#  in say one thing. A SENSOR, typed: a contact a van carries is hosted by it too, and is no sensor.
_UNREAD_Q = """
SELECT DISTINCT ?sensor WHERE {
  ?me a orexis:Self ; orexis:actsFor ?subject . ?subject schema:containedInPlace* ?host .
  ?sensor a sosa:Sensor ; sosa:isHostedBy/(sosa:isSampleOf|sosa:isHostedBy)? ?host
  FILTER NOT EXISTS { ?me orexis:plays/sensing:sensor ?sensor } }
ORDER BY ?sensor"""
#  WHETHER THE SELF IS READ BY A PACKAGE IT DOES NOT LOAD, off the common beliefs and the self.
_LISTENS_Q = "ASK { ?me a orexis:Self ; mqtt4ssn:listensToTopic ?topic }"


def agents(here: Path) -> list[str]:
    """Every agent the world in `here` states, by id, sorted."""
    store = world(here)
    return [r["id"] for r in rows(store, _AGENTS_Q, graphs_of(store, BELIEF, common=True))]


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
    _, broken = _judged(here)
    return [f"{agent_id}: {why}" for agent_id in agents(here)
            for why in _refusals(here, boot(here, agent_id, others=ours()), broken[agent_id])]


def _refusals(here: Path, beliefs: ox.Store, broken: list[str]) -> list[str]:
    roles = roles_of(beliefs)
    if not roles:
        return ["plays no role in its self graph, so it would load no package and run nothing — "
                "`<agent> orexis:plays [ a <role> ]` says what it runs"]
    out = list(broken)
    stated = [*graphs_of(beliefs, BELIEF, common=True), *graphs_of(beliefs, SELF_GRAPH)]
    out += [f"{local_of(r['sensor'])} reports to it, and no observer role it plays reads it: no package it "
            f"loads would read the sensor — `orexis:plays [ a sensing:Observer ; sensing:sensor <sensor> ]` says one does"
            for r in rows(beliefs, _UNREAD_Q, stated)]
    if SPEAKER not in roles and answer(beliefs, _LISTENS_Q, stated)["boolean"]:
        out.append("it listens to a topic, and it is no speaker: no package it loads would hear what arrives there")
    (me,) = selves(beliefs)
    for path, doc in read_with_imports(documents(here, packages_of(beliefs))):
        for graph, kinds in sorted(kinds_in(doc).items()):
            if known(beliefs, kinds) or ours() & kinds or whose(doc, graph) not in (None, me):
                continue
            out.append(f"{path.name}: {graph} is of a kind none of the packages it loads declares "
                       f"({', '.join(sorted(kinds))})")
    return out
