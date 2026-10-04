"""What two of the greenhouse's suites share: the world with a light on the bed.

`test_scaling.py` holds the soil's search flat under the aspect added, and `test_bench.py` times the
pass with the third scope in it. A fixture is the one door pytest opens between two test modules —
under `--import-mode=importlib` a sibling module is not importable — so the copy lives here, and
each suite asks for it by name.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

WORLD = Path(__file__).resolve().parents[1]

LIGHT = '''
#  AN UNRELATED ASPECT: light on the bed, and a lamp that raises it.
:light_sensor a sosa:Sensor ; orexis:localId "light_sensor" ; sosa:observes climate:Light ; sosa:isHostedBy :bed ;
    ssn-system:hasSystemCapability [ ssn-system:hasSystemProperty
        [ a ssn-system:Frequency , schema:PropertyValue ; schema:value 10 ; schema:unitCode unit:MIN ] ] .
:bed_light_operating a ssn-system:OperatingRange ;
    ssn-system:inCondition [ a ssn-system:Condition , schema:PropertyValue ; ssn:forProperty climate:Light ;
                             schema:minValue 200 ; schema:maxValue 800 ; schema:unitCode unit:LUX ] .
:bed ssn-system:hasOperatingRange :bed_light_operating .
:lamp a climate:Heater ; orexis:localId "lamp" ; climate:warms :bed ; climate:warmsProperty climate:Light ;
    climate:degreesPerHour 400.0 ; climate:maxHeatS 3600 .
'''
WIRED = '''
:light_sensor mqtt4ssn:observesTopic :light_readings .
:light_readings a mqtt4ssn:Topic .
:light_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "sensors/light_sensor/reading" ; mqtt4ssn:matchesTopic :light_readings .
:lamp mqtt4ssn:listensToTopic :lamp_commands .
:lamp_commands a mqtt4ssn:Topic .
:lamp_filter a mqtt4ssn:TopicFilter ;
    mqtt4ssn:hasFilterPattern "actuators/lamp/command" ; mqtt4ssn:matchesTopic :lamp_commands .
'''
LIT = '''
:grower planning:holds :the_bed_is_lit .
:the_bed_is_lit a planning:Desire ; rdfs:label "the bed is lit" ; planning:metWhen :lit .
:lit a sh:NodeShape ;
    sh:targetNode :grower ;
    sh:property [
        sh:path ( orexis:actsFor [ sh:inversePath sosa:hasFeatureOfInterest ] ) ;
        planning:about climate:Light ;
        sh:qualifiedMaxCount 0 ;
        sh:qualifiedValueShape [
            sh:property [ sh:path sosa:observedProperty ; sh:hasValue climate:Light ] ;
            sh:property [ sh:path sensing:below ; sh:minCount 1 ] ] ;
        sh:message "the bed is dim" ] .
'''


@pytest.fixture
def lit_greenhouse(tmp_path):
    """The greenhouse with the light added — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / "world" / "greenhouse"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / "domains").symlink_to(WORLD.parents[1] / "domains")
    (world / "world.ttl").write_text((world / "world.ttl").read_text() + LIGHT)
    society = world / "society.ttl"
    society.write_text(society.read_text()
                       .replace("actuation:hasActuator :pump , :heater .", "actuation:hasActuator :pump , :heater , :lamp .")
                       .replace("mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater ;",
                                "mqtt4ssn:hosts :moisture_probe , :thermometer , :pump , :heater , :light_sensor , :lamp ;"))
    society.write_text(society.read_text() + WIRED)
    (world / "desires.ttl").write_text((world / "desires.ttl").read_text() + LIT)
    return world
