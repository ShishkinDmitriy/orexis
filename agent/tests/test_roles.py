"""A package is loaded only for a role the agent is declared in (#927,
knowledge/decisions/a-package-is-loaded-only-for-a-role-the-agent-is-declared-in.md): its documents
put in the store and its part created, and neither where no declared role calls for it.

Every role a package declares is held both ways, on a world written for the case and FOUND by
looking at the packages' ontologies, as the boot finds them: declared, the package's documents are in
the store and its deferred import runs — a deferred import is code no test runs otherwise, which
0.1.0 learned by every agent crash-looping at boot — and declared NOT, beside every role that does
not call for it, the package's documents are absent and it has no part. That no module of a package
is imported where no role calls for it is a question about a whole process, so it is asked of one:
a fresh interpreter boots a world and says what of `agent.` it holds, telling a package's PART from
an import of its term module — planning imports `agent.execution.ontology` for the words a plan is
written in, and a planner that is no executor still may.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pyoxigraph as ox
import pytest

from agent.runtime import (HTTP, KERNEL, MQTT, OBSERVER, SPEAKER, VOCABULARY, WATCHERS, Runtime, _documents_of,
                           _vocabularies, boot, every_package, packages_of, roles_of)

ROOT = Path(__file__).resolve().parents[2]
ME = "http://example.org/test#me"
ROLE = "http://example.org/orexis#Role"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#> .
@prefix td: <https://www.w3.org/2019/wot/td#> .
@prefix schema: <https://schema.org/> .
"""
_AGENT = ':me a orexis:Agent ; orexis:localId "me" ; orexis:actsFor :pot .\n'
_PROBE = ":probe a sosa:Sensor ; sosa:isHostedBy :pot .\n"

#  EVERY ROLE A PACKAGE DECLARES, and the package — read off the packages' ontologies as the boot
#  reads them, so a role added to a package is a case here without a line of this file changing.
ROLES, _ = _vocabularies()


def _world(tmp_path: Path, roles=(), facts: str = "") -> Path:
    """A world of one agent, `me`, declared in `roles` in its self graph, beside `facts`."""
    (tmp_path / "world.ttl").write_text(_HEAD + "<> a orexis:WorldGraph .\n" + _AGENT + facts)
    (tmp_path / "beliefs").mkdir(exist_ok=True)
    declared = "".join(f" , <{role}>" for role in roles)
    (tmp_path / "beliefs" / "me.self.ttl").write_text(_HEAD + "<> a orexis:SelfGraph .\n" f":me a orexis:Self{declared} .\n")
    return tmp_path


def _held(store: ox.Store, package: str) -> list[bool]:
    """For each document of `package`, whether its graph is in the store."""
    return [bool(list(store.quads_for_pattern(ox.NamedNode(path.as_uri()), None, None)))
            for path in _documents_of([package])]


def _creates(package: str) -> bool:
    return importlib.util.find_spec("agent." + package.replace("/", ".") + ".create") is not None


def _calls_for(role: str) -> set[str]:
    """The packages a world declaring `role` alone loads."""
    return {package for r, package in ROLES.items() if r == role or r in _supers(role)}


def _supers(role: str) -> set[str]:
    _, steps = _vocabularies()
    out, frontier = set(), {role}
    while frontier:
        for s in steps.get(frontier.pop(), ()):
            if s not in out:
                out.add(s)
                frontier.add(s)
    return out


def test_every_package_but_a_transport_declares_a_role_and_every_role_is_found():
    """A package is loaded for a role it serves, so one that serves none would be read by no agent,
    silently; a transport is the one exception, loaded where a role needs bytes. And the roles found
    are the ones the dictionary names."""
    serving = set(ROLES.values())
    assert set(every_package()) - serving == {MQTT, HTTP}, sorted(serving)
    local = {role.rsplit("#", 1)[-1] for role in ROLES}
    assert local == {"Deliberator", "Observer", "Predictor", "Planner", "Executor", "Speaker"}, sorted(local)


@pytest.mark.parametrize("role", sorted(ROLES), ids=lambda r: r.rsplit("#", 1)[-1])
def test_a_declared_role_loads_its_package_and_runs_its_part(tmp_path, role):
    package = ROLES[role]
    store = boot(_world(tmp_path, [role]), "me")
    assert role in roles_of(store)
    assert set(packages_of(store)) == _calls_for(role), "the role and the roles it is beneath, and nothing else"
    assert all(_held(store, package)), f"{package} is loaded and its documents are not all in the store"
    runtime = Runtime(store, "me")
    assert package in runtime.parts or not _creates(package), f"{package} has a create module and no part was made"


@pytest.mark.parametrize("role", sorted(ROLES), ids=lambda r: r.rsplit("#", 1)[-1])
def test_an_undeclared_role_loads_nothing_of_its_package_beside_every_role_that_does_not_call_for_it(tmp_path, role):
    package = ROLES[role]
    others = [r for r in ROLES if package not in _calls_for(r)]
    store = boot(_world(tmp_path, others, _PROBE), "me")
    assert others and package not in packages_of(store)
    assert not any(_held(store, package)), f"{package}'s documents are in the store, and no role asked for them"
    assert package not in Runtime(store, "me").parts


def test_a_domain_role_loads_every_package_role_it_is_beneath(tmp_path):
    """The market's host is beneath the planner, the executor, the speaker and the deliberator, in the
    market's own ontology; declared in the domain's word, the boot's closure loads all four and nothing
    an author listed."""
    market = (ROOT / "domains" / "market" / "ontology.ttl").as_uri()
    world = _world(tmp_path, ["http://example.org/orexis/market#Host"])
    text = (world / "world.ttl").read_text().replace("<> a orexis:WorldGraph .", f"<> a orexis:WorldGraph ; <http://www.w3.org/2002/07/owl#imports> <{market}> .")
    (world / "world.ttl").write_text(text)
    store = boot(world, "me")
    assert packages_of(store) == ("belief", "planning", "execution", "speech")


def test_an_agent_declaring_no_role_loads_nothing_and_runs_nothing(tmp_path, caplog):
    store = boot(_world(tmp_path, [], _PROBE), "me")
    assert roles_of(store) == frozenset() and packages_of(store) == ()
    assert not any(_held(store, package)[0] for package in every_package())
    assert Runtime(store, "me").parts == {}
    assert "declared in no role" in caplog.text


#  WHAT BRINGS A TRANSPORT: a role that needs bytes and the wiring of a bus — and either alone, none.
_ON_A_TOPIC = _PROBE + ":probe mqtt4ssn:observesTopic :readings .\n"
_LISTENS = ":me mqtt4ssn:listensToTopic :inbox .\n"
_A_FORM = ":pot schema:containedInPlace :balcony . :weather a sosa:Sensor ; sosa:isHostedBy :balcony ; td:hasForm [] .\n"
TRANSPORTS = {
    "an observer's sensor on a topic": ([OBSERVER], _ON_A_TOPIC, {MQTT}),
    "a speaker listening to a topic": ([SPEAKER], _LISTENS, {MQTT}),
    "an observer's sensor with a form": ([OBSERVER], _A_FORM, {HTTP}),
    "an observer's sensor on no bus": ([OBSERVER], _PROBE, set()),
    "a sensor on a topic, and no observer": ([SPEAKER], _ON_A_TOPIC, set()),
    "a topic listened to, and no speaker": ([OBSERVER], _PROBE + _LISTENS, set()),
    "a sensor with a form, and no observer": ([SPEAKER], _A_FORM, set()),
}


@pytest.mark.parametrize("case", TRANSPORTS, ids=str)
def test_a_transport_is_loaded_where_a_loaded_role_needs_bytes_and_the_society_wires_a_bus(tmp_path, case):
    roles, facts, expected = TRANSPORTS[case]
    store = boot(_world(tmp_path, roles, facts), "me")
    assert set(packages_of(store)) & {MQTT, HTTP} == expected
    for transport in (MQTT, HTTP):
        assert all(_held(store, transport)) if transport in expected else not any(_held(store, transport))
    for transport in expected:
        assert _creates(transport), f"{transport} is loaded and has no create module to make its member"
    #  A TRANSPORT'S PART IS MADE ONLY WHERE THE RUNTIME IS TOLD TO CONNECT, which `main` is.
    assert not set(Runtime(store, "me").parts) & {MQTT, HTTP}


@pytest.mark.parametrize("roles, read", [([OBSERVER], True), ([SPEAKER], False)], ids=["an observer", "no observer"])
def test_a_world_graph_of_a_kind_a_loaded_package_declares_is_read_after_it(tmp_path, roles, read):
    """THE ORDER PROBLEM. A graph the world states as a `sensing:ObservationGraph` is of no kind the
    kernel declares, so the first half of the boot passes it over; where the agent is an observer,
    sensing's vocabulary goes in after, and the graph is looked at again and read, as the agent's own
    since an observation is state. Where it is not, nothing says what the kind is, and it stays
    passed over."""
    world = _world(tmp_path, roles, _PROBE)
    (world / "reading.ttl").write_text(_HEAD + "@prefix sensing: <http://example.org/orexis/sensing#> .\n"
                                       "<> a sensing:ObservationGraph ; orexis:beliefsOf :me .\n"
                                       ":reading a sosa:Observation ; sosa:hasFeatureOfInterest :pot .\n")
    store = boot(world, "me")
    name = ox.NamedNode((world / "reading.ttl").resolve().as_uri())
    assert bool(list(store.quads_for_pattern(None, None, None, name))) is read
    if read:
        owner = ox.NamedNode("http://example.org/orexis#beliefsOf")
        assert [q.object.value for q in store.quads_for_pattern(name, owner, None)] == [ME], "the agent's own"


def test_a_role_is_read_off_the_self_graph_alone(tmp_path):
    """What an agent runs is its own word about itself: a role a public graph states of it is no role
    of its, as a stance stated there is no stance."""
    store = boot(_world(tmp_path, [], f":me a <{SPEAKER}> .\n"), "me")
    assert roles_of(store) == frozenset() and packages_of(store) == ()


def test_every_document_the_agent_ships_is_the_kernels_or_a_packages():
    """A document under `agent/` in a directory that is no package would be read by no agent,
    silently; and every package directory — one with an `__init__.py` — has a vocabulary, which is
    what makes it a package, or watches the agent where the environment names a store for it."""
    ships = sorted(p for p in KERNEL.rglob("*") if p.suffix in (".ttl", ".trig")
                   and "tests" not in p.relative_to(KERNEL).parts)
    named = {KERNEL / VOCABULARY, *_documents_of(every_package())}
    assert ships and set(ships) <= named, f"shipped and read by nobody: {sorted(set(ships) - named)}"
    packages = sorted(p.parent.relative_to(KERNEL).as_posix() for p in KERNEL.rglob("__init__.py")
                      if "tests" not in p.relative_to(KERNEL).parts)
    assert packages and set(packages) == {*every_package(), *WATCHERS}, f"packages {packages} against the vocabularies and the watchers"


#  WHAT A PROCESS HOLDS: a fresh interpreter, the tree under test first on its path, boots a world,
#  builds the runtime, imports its transport packages' `create` and runs `passes`; what of `agent.` it
#  then holds, by the package — every module beneath it, so a part can be told from a term module.
_PROBE_SCRIPT = """
import json, sys
from pathlib import Path
import importlib
from agent.runtime import Runtime, boot, every_package
world, agent, passes = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
runtime = Runtime(boot(world, agent), agent, budget=64)
for package in runtime.packages:
    if package.startswith('transport/'):
        importlib.import_module('agent.' + package.replace('/', '.') + '.create')
outcome = runtime.run(passes=passes, poll_s=0) if passes else None
held = {p: sorted(m for m in sys.modules if m == 'agent.' + p.replace('/', '.') or m.startswith('agent.' + p.replace('/', '.') + '.'))
        for p in every_package()}
print(json.dumps({"outcome": outcome, "loaded": list(runtime.packages), "held": held}))
"""


def _planner_alone(tmp_path: Path) -> Path:
    """Hanoi's world with its mover declared a planner and nothing else — what #928 will ship, here
    run no pass, so the question is only what such a process imports."""
    world = tmp_path / "hanoi"
    world.mkdir()
    hanoi = ROOT / "world" / "hanoi"
    domain = (ROOT / "domains" / "hanoi" / "ontology.ttl").as_uri()
    (world / "world.ttl").write_text((hanoi / "world.ttl").read_text().replace("<../../domains/hanoi/ontology.ttl>", f"<{domain}>"))
    for name in ("state.ttl", "wants.ttl"):
        (world / name).write_text((hanoi / name).read_text())
    (world / "beliefs").mkdir()
    (world / "beliefs" / "hanoi.self.ttl").write_text((hanoi / "beliefs" / "hanoi.self.ttl").read_text()
                                                      .replace(" , execution:Executor", ""))
    return world


#  A TERM MODULE: the words a package declares, which a package above it may import for them.
_TERMS = {"ontology"}


@pytest.mark.parametrize("world, agent, passes, loaded, outcome", [
    ("hanoi", "hanoi", 20, {"planning", "execution"}, "met"),
    ("terrace", "terrace", 0, {"belief", "sensing", "prediction", MQTT, HTTP}, None),
    ("allotment", "fern_grower", 0, {"belief", "planning", "execution", "sensing", "prediction", "speech", MQTT}, None),
    (None, "hanoi", 0, {"planning"}, None),
], ids=["hanoi's planner and executor, run to met", "the terrace's observer and predictor",
        "the allotment's fern grower, everything", "a planner that is no executor"])
def test_a_process_runs_the_parts_its_roles_call_for_and_no_other(tmp_path, world, agent, passes, loaded, outcome):
    """Each process boots and runs as its container would. A package its roles call for has its part
    imported; one they do not has none — at most its term module, imported by a package above it for
    the words it declares, as planning imports execution's. The fern grower loading everything is what
    makes the others' absences a measurement and not a probe that sees nothing."""
    where = _planner_alone(tmp_path) if world is None else ROOT / "world" / world
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")])}
    done = subprocess.run([sys.executable, "-c", _PROBE_SCRIPT, str(where), agent, str(passes)],
                          capture_output=True, text=True, env=env, cwd=ROOT, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    said = json.loads(done.stdout.strip().splitlines()[-1])
    assert said["outcome"] == outcome
    assert set(said["loaded"]) == loaded
    for package, modules in said["held"].items():
        base = "agent." + package.replace("/", ".")
        beyond = {m.removeprefix(base + ".") for m in modules if m != base}
        if package in loaded:
            assert "create" in beyond or not _creates(package), f"{package} is loaded and its part was never imported"
        else:
            assert beyond <= _TERMS, f"{package} is called for by no role, and the process imported {sorted(beyond)}"
    if "planning" in loaded and "execution" not in loaded:
        assert "agent.execution.ontology" in said["held"]["execution"], \
            "planning imports execution's term module — the probe must see it, or this case measures nothing"
