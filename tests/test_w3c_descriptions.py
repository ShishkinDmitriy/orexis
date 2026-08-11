"""The W3C's own SSN descriptions, dropped into a world and held to our shapes.

These are not our files. `tests/fixtures/w3c-ssn/` holds two documents from `w3c/sdw` — the
repository behind the 2017 SSN Recommendation — describing a DHT22, which is the KY-015's
sibling and the part `vocabulary/dht11/` was modelled against. They are byte-identical to
upstream; see the README beside them.

They are here to answer one question that reasoning could not: **can a description written by
the people who wrote the vocabulary be deployed in a world without editing it?**

The answer turns out to be *yes for the description, no for the illustration*, and the boundary
is worth pinning:

- a vendor describes a PART — what it is, what its channels can do, how accurate they are. That
  is theirs and it is complete.
- a world adds the DEPLOYMENT — a name on our wire, who drives it, whose plant it watches, which
  topic it publishes on. A vendor cannot know any of that, and its absence from their file is
  correct rather than a gap.

The first test is the deliverable. The rest say what breaks when it stops being true.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import rdflib
from pyshacl import validate as shacl_validate

from agent import genesis
from agent.ontology import PROVENANCE_GRAPH, beliefs_graph
from agent.store import Store
from agent.validate import _shapes_and_vocabulary, conforms, graph_from

from conftest import WORLDS_ROOT

FIXTURES = Path(__file__).parent / "fixtures" / "w3c-ssn"

#  THEIR FILE DOES NOT PARSE, and this is the one character we change.
#
#  `<observation/1087>` ends with `;` and never receives its `.`, so the next subject begins
#  mid-statement. Every Turtle parser rejects it; ours is not being strict. The fixture stays
#  byte-identical to upstream and the repair lives here, in code, where it is reviewable —
#  rather than being edited into the file where it would read as theirs.
#
#  Asserted rather than applied blindly: if W3C ever fixes it, `_repaired` fails and tells us,
#  instead of a silent no-op leaving a patch nobody needs.
_MALFORMED = "  ssn-system:qualityOfObservation <observation/1087#quality> ;\n"
_REPAIRED = "  ssn-system:qualityOfObservation <observation/1087#quality> .\n"


def _repaired(name: str) -> str:
    src = (FIXTURES / name).read_text()
    assert _MALFORMED in src, (
        f"{name} no longer carries the malformed statement this repair exists for — upstream "
        f"has probably fixed it, and this patch should go with it"
    )
    return src.replace(_MALFORMED, _REPAIRED, 1)


def _world_with(tmp_path, **files: str):
    """`world/sensing` plus some extra Turtle, built the way `agora-validate` builds a world.

    Through the real path on purpose. The derivation runs, so a sensor gets its codec and its
    scaling, and `agent/inference.py`'s closure runs, so the legacy schema.org bridge takes
    effect — validating the fixture as a bare graph would measure neither and report violations
    no deployment would ever see.
    """
    world = tmp_path / "probe"
    shutil.copytree(WORLDS_ROOT / "sensing", world)
    for name, ttl in files.items():
        (world / f"{name}.ttl").write_text(ttl)

    st = Store()
    genesis.refresh_public(st, world)
    everyone = [genesis.agent_id_of(p) for p in sorted(world.glob(genesis.BELIEFS_GLOB))]
    for agent_id in everyone:
        genesis.birth(st, world, agent_id)
    return graph_from(st, *st.public_graphs(), PROVENANCE_GRAPH,
                      *(beliefs_graph(a) for a in everyone))


_SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")


def _by_severity(data: rdflib.Graph) -> dict[str, set[str]]:
    """Focus nodes that drew a result, split by severity.

    `conforms` returns one verdict and the report as text; this test needs to say WHICH nodes
    and how badly, because the whole point is that the residue is one specific node.
    """
    ontology, shapes = _shapes_and_vocabulary()
    data = data + ontology
    _, results, _ = shacl_validate(data, shacl_graph=shapes, ont_graph=ontology,
                                   inference="none", advanced=True)
    out: dict[str, set[str]] = {"Violation": set(), "Warning": set()}
    for result in results.subjects(rdflib.RDF.type, _SH.ValidationResult):
        severity = str(results.value(result, _SH.resultSeverity)).rsplit("#", 1)[-1]
        out.setdefault(severity, set()).add(str(results.value(result, _SH.focusNode)))
    return out


# --- the deliverable -------------------------------------------------------------------------

def test_a_standard_deployment_description_needs_no_editing_at_all(tmp_path):
    """`dht22-deployment.ttl` is dropped into a world verbatim and the world still conforms.

    Rooms, walls, boards and deployments, written by the SSN authors — and every shape this
    project owns is satisfied by it untouched. Nothing was relaxed to get here and no overlay
    supplies anything.

    It works because that file describes PLATFORMS and SYSTEMS and declares no `sosa:Sensor`:
    our sensor shapes ask for deployment facts, and there is no sensor to ask about. Which is
    the boundary this whole fixture set exists to draw — a description of where things are
    mounted is complete on its own; a description of a sensor is not, and should not be.
    """
    data = _world_with(tmp_path, vendor=(FIXTURES / "dht22-deployment.ttl").read_text())
    ok, report = conforms(data)
    assert ok, report


def test_their_device_description_deploys_once_our_half_is_supplied(tmp_path):
    """Their two DHT22 channels, plus `deploy-dht22.ttl`, satisfy every shape that targets them.

    Focused on their nodes, because that is the claim: a part described by a vendor becomes a
    sensor this society can drive, once the society says the things only it knows. Their file
    supplies the frequency floor, the accuracy and the operating range; ours supplies the name,
    the clock, the subject and the topic. Neither restates the other.
    """
    data = _world_with(tmp_path,
                       a_vendor=_repaired("dht22.ttl"),
                       b_deploy=(FIXTURES / "deploy-dht22.ttl").read_text())
    for channel in ("TemperatureSensor", "HumiditySensor"):
        iri = f"http://example.org/data/DHT22/4578#{channel}"
        ok, report = conforms(data, focus=iri)
        assert ok, f"{channel} did not conform:\n{report}"


# --- what is left, and why it is right to be left ---------------------------------------------

def test_the_only_thing_left_refusing_is_their_illustrative_reading(tmp_path):
    """One violating node in the whole world: `<observation/1087>`, and it SHOULD be refused.

    Their file bundles a device description with a sample observation, included to illustrate
    `ssn-system:qualityOfObservation`. It states a sensor and a procedure and nothing else — no
    result, no time, no feature of interest, no author.

    A reading here carries all of those, and the shape is right to refuse one that does not.
    Completing it in the overlay would have made this test green by **fabricating provenance for
    a reading nobody took**, which is precisely what `prov:wasGeneratedBy` is on a reading to
    prevent. So it stays refused, and this test names it so the residue can never grow quietly.

    The warnings are a different matter and are correct: deploying a second DHT22 beside the
    board's own puts two sensors on one property of one subject, which is the legitimate rig
    `perception:DuplicateSensorShape` warns about rather than forbids.
    """
    data = _world_with(tmp_path,
                       a_vendor=_repaired("dht22.ttl"),
                       b_deploy=(FIXTURES / "deploy-dht22.ttl").read_text())
    found = _by_severity(data)

    assert found["Violation"] == {"http://example.org/data/observation/1087"}, (
        "the residue moved: something other than their illustrative observation is now refused"
    )
    assert any("DHT22" in n for n in found["Warning"]), (
        "the duplicate-rig warning stopped firing — two sensors on one property of one subject "
        "is exactly what it is for"
    )


def test_a_vendor_description_alone_is_missing_only_deployment_facts(tmp_path):
    """Without our overlay, their sensors fail for four reasons and all four are ours to supply.

    This is the characterisation: it says what a standard description does NOT contain, so that
    a future change adding a fifth requirement has to come past this test and say so. Every one
    of these is a fact about *this* deployment that no vendor could know.
    """
    data = _world_with(tmp_path, vendor=_repaired("dht22.ttl"))
    ok, report = conforms(data)
    assert not ok

    for expected in ("perception:monitors", "sosa:observes",
                     "a sensor must say how it is driven"):
        assert expected in report, f"{expected} stopped being required of a deployed sensor"

    #  And NOT for anything about the datasheet. Their frequency is stated in the legacy
    #  schema.org namespace and in QUDT 1.1, and both are understood — see the bridge in
    #  `capabilities/perception/ontology.ttl` and `sh:in` in its shapes.
    assert "frequency" not in report, (
        "a datasheet figure stopped being readable — the legacy schema.org bridge or the QUDT "
        "1.1 unit is no longer accepted, and a vendor's file now fails for a fact it DOES state"
    )


def test_the_legacy_schema_org_spelling_is_what_their_frequency_uses(tmp_path):
    """The bridge earns its place, and this is the evidence.

    schema.org's canonical namespace is `https:`; the W3C's example is written in `http:`. They
    are two IRIs, so without the bridge their `schema:value` and `schema:unitCode` are simply
    absent and the shape reports the node as missing figures it plainly states.

    Asserted against their file rather than a mock, so it stops being true the day they migrate.
    """
    src = (FIXTURES / "dht22.ttl").read_text()
    assert "@prefix schema: <http://schema.org/>" in src
    assert "https://schema.org/" not in src
