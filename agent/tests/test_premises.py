"""A package beyond the mind is loaded where its premise, read off the world, holds (#824): its
documents put in the store and its modules imported, and neither where it does not.

Each premise is held both ways, on a world written for the case: one where it holds, which runs
the deferred import it guards — a deferred import is code no test runs otherwise, which 0.1.0
learned by every agent crash-looping at boot — and one where it does not, which puts none of the
package's documents in the store. That no module is IMPORTED where no premise holds is a question
about a whole process, so it is asked of one: a fresh interpreter boots a world and says what of
`agent.` it holds, and the case where every premise holds shows the probe can see them at all.
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

from agent.runtime import EVERY, WATCHERS, HTTP, KERNEL, MIND, MQTT, PREDICTION, PREMISES, SENSING, SPEECH, Runtime, _documents_of, \
    boot, packages_of

ROOT = Path(__file__).resolve().parents[2]
ME = "http://example.org/test#me"

_HEAD = """@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#> .
@prefix prediction: <http://example.org/orexis/prediction#> .
@prefix execution: <http://example.org/orexis/execution#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix td: <https://www.w3.org/2019/wot/td#> .
@prefix schema: <https://schema.org/> .
"""
_AGENT = ':me a orexis:Agent ; orexis:localId "me" ; orexis:actsFor :pot .\n'
_PROBE = ":probe a sosa:Sensor ; sosa:isHostedBy :pot .\n"
_DRIFT = ':Drying a prediction:Drift ; prediction:moves :moisture ; prediction:rate "SELECT ?rate WHERE {}" .\n'
_SAYING = (':Telling a orexis:Action ; execution:implementation [ a execution:Implementation ;\n'
           '    execution:operation [ a execution:Saying ; sh:construct "CONSTRUCT {} WHERE {}" ] ] .\n')

#  EACH CASE: what the world states besides the agent, where its drift and its action are, and
#  the packages beyond the mind it loads.
CASES = {
    "nothing":                   ("", "", "", ()),
    "a sensor of mine":          (_PROBE, "", "", (SENSING,)),
    "a sensor in a sample":      (":sample sosa:isSampleOf :pot . :probe a sosa:Sensor ; sosa:isHostedBy :sample .\n",
                                  "", "", (SENSING,)),
    "a sensor of somebody's":    (":probe a sosa:Sensor ; sosa:isHostedBy :elsewhere .\n", "", "", ()),
    "a drift and a sensor":      (_PROBE, _DRIFT, "", (SENSING, PREDICTION)),
    "a drift and no sensor":     ("", _DRIFT, "", ()),
    "a topic I listen to":       (":me mqtt4ssn:listensToTopic :inbox .\n", "", "", (SPEECH, MQTT)),
    "an action that says":       ("", "", _SAYING, (SPEECH,)),
    "a sensor on a topic":       (_PROBE + ":probe mqtt4ssn:observesTopic :readings .\n", "", "", (SENSING, MQTT)),
    "a sensor of the place":     (":pot schema:containedInPlace :balcony . :gauge a sosa:Sensor ; sosa:isHostedBy :balcony .\n",
                                  "", "", (SENSING,)),
    "a service with a form":     (":pot schema:containedInPlace :balcony . :weather a sosa:Sensor ; sosa:isHostedBy :balcony ; "
                                  "td:hasForm [] .\n", "", "", (SENSING, HTTP)),
}


def _world(tmp_path: Path, facts: str, drift: str, action: str) -> Path:
    (tmp_path / "world.ttl").write_text(_HEAD + "<> a orexis:WorldGraph .\n" + _AGENT + facts)
    if drift:
        (tmp_path / "drifts.ttl").write_text(_HEAD + "<> a orexis:PublicGraph .\n" + drift)
    if action:
        (tmp_path / "actions.ttl").write_text(_HEAD + "<> a orexis:ActionGraph .\n" + action)
    return tmp_path


def _held(store: ox.Store, package: str) -> list[bool]:
    """For each document of `package`, whether the catalogue says its graph is in the store."""
    return [bool(list(store.quads_for_pattern(ox.NamedNode(path.as_uri()), None, None)))
            for path in _documents_of([package])]


@pytest.mark.parametrize("case", CASES, ids=str)
def test_a_package_is_loaded_where_its_premise_holds_and_nowhere_else(tmp_path, case):
    facts, drift, action, expected = CASES[case]
    store = boot(_world(tmp_path, facts, drift, action), "me")
    assert packages_of(store) == (*MIND, *expected)
    for package in EVERY:
        documents = _held(store, package)
        if package in (*MIND, *expected):
            assert all(documents), f"{package} is loaded and its documents are not all in the store"
        else:
            assert not any(documents), f"{package}'s documents are in the store, and nothing asked for them"
    runtime = Runtime(store, "me")
    assert runtime.packages == packages_of(store)
    #  WHAT HAS A PART: the mind, and every loaded package with a `create` module but a transport,
    #  which is created only where the runtime is told to connect; a transport package has its `create`
    #  all the same.
    assert list(runtime.parts) == [p for p in (*MIND, *expected) if not p.startswith("transport/")]
    for package in (MQTT, HTTP):
        assert (package in expected) <= (importlib.util.find_spec("agent." + package.replace("/", ".") + ".create") is not None)


@pytest.mark.parametrize("facts, read", [(_PROBE, True), ("", False)], ids=["sensing loaded", "sensing not loaded"])
def test_a_world_graph_of_a_kind_a_loaded_package_declares_is_read_after_it(tmp_path, facts, read):
    """THE ORDER PROBLEM. A graph the world states as a `sensing:ObservationGraph` is of no kind the
    mind declares, so the first half of the boot passes it over; where sensing's premise holds, its
    vocabulary goes in after, and the graph is looked at again and read, as the agent's own since
    an observation is state. Where sensing is not loaded, nothing says what the kind is, and it
    stays passed over."""
    world = _world(tmp_path, facts, "", "")
    (world / "reading.ttl").write_text(_HEAD + "@prefix sensing: <http://example.org/orexis/sensing#> .\n"
                                       "<> a sensing:ObservationGraph .\n"
                                       ":reading a sosa:Observation ; sosa:hasFeatureOfInterest :pot .\n")
    store = boot(world, "me")
    name = ox.NamedNode((world / "reading.ttl").resolve().as_uri())
    assert bool(list(store.quads_for_pattern(None, None, None, name))) is read
    if read:
        owner = ox.NamedNode("http://example.org/orexis#beliefsOf")
        assert [q.object.value for q in store.quads_for_pattern(name, owner, None)] == [ME], "the agent's own"


def test_every_case_is_a_case_of_some_premise_both_ways():
    """Every premise holds in some case and fails in another, so none is held one way only."""
    for package in PREMISES:
        assert any(package in c[3] for c in CASES.values()), f"no case where {package}'s premise holds"
        assert any(package not in c[3] for c in CASES.values()), f"no case where {package}'s premise fails"


def test_every_document_the_agent_ships_is_the_kernels_or_a_packages_it_names():
    """A package is loaded because it is the mind or because it has a premise; a document under
    `agent/` in a directory that is neither would never be read by any agent, silently. And every
    package directory — one with an `__init__.py` — is one or the other, or watches the agent where
    the environment names a store for it."""
    ships = sorted(p for p in KERNEL.rglob("*") if p.suffix in (".ttl", ".trig")
                   and "tests" not in p.relative_to(KERNEL).parts)
    named = {KERNEL / "ontology.ttl", *_documents_of(EVERY)}
    assert ships and set(ships) <= named, f"shipped and read by nobody: {sorted(set(ships) - named)}"
    packages = sorted(p.parent.relative_to(KERNEL).as_posix() for p in KERNEL.rglob("__init__.py")
                      if "tests" not in p.relative_to(KERNEL).parts)
    assert packages and set(packages) == {*EVERY, *WATCHERS}, f"packages {packages} against the mind, the premises and the watchers"


#  WHAT A PROCESS HOLDS: a fresh interpreter, the tree under test first on its path, boots a world,
#  builds the runtime, imports its transport packages' `create` and runs `passes`; what of `agent.` it then
#  holds, by the package beneath `agent`.
_PROBE_SCRIPT = """
import json, sys
from pathlib import Path
import importlib
from agent.runtime import Runtime, boot
world, agent, passes = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
runtime = Runtime(boot(world, agent), agent, budget=64)
for package in runtime.packages:
    if package.startswith('transport/'):
        importlib.import_module('agent.' + package.replace('/', '.') + '.create')
outcome = runtime.run(passes=passes, poll_s=0) if passes else None
print(json.dumps({"outcome": outcome, "held": sorted({m.split('.')[1] for m in sys.modules if m.startswith('agent.')})}))
"""


OPTIONAL = {"sensing", "prediction", "speech", "transport"}


@pytest.mark.parametrize("world, agent, passes, imported, outcome", [
    ("hanoi", "hanoi", 20, set(), "met"),
    ("allotment", "fern_grower", 0, OPTIONAL, None),
], ids=["hanoi's mover, run to met, imports none", "allotment's fern grower imports all four"])
def test_a_process_imports_the_packages_its_world_needs_and_no_other(world, agent, passes, imported, outcome):
    """Hanoi's mover senses nothing, predicts nothing and has no bus: booted and run until its tower
    stands, it has imported nothing of sensing, prediction, speech or any transport. The allotment's
    fern grower senses, predicts, listens and says, and has imported all four — which is what makes
    the mover's absence a measurement and not a probe that sees nothing."""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")])}
    done = subprocess.run([sys.executable, "-c", _PROBE_SCRIPT, str(ROOT / "world" / world), agent, str(passes)],
                          capture_output=True, text=True, env=env, cwd=ROOT, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    said = json.loads(done.stdout.strip().splitlines()[-1])
    assert said["outcome"] == outcome
    assert set(said["held"]) & OPTIONAL == imported, said["held"]
    assert set(said["held"]) >= set(MIND), "the mind is imported whatever the world"
