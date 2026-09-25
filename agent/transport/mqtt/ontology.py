"""The words the MQTT transport reads — every one MQTT4SSN's, none its own."""

from __future__ import annotations

MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"

#  READ BY THIS PACKAGE, in its queries by the prefix and here for a test that asks by term.
OBSERVES_TOPIC = MQTT4SSN + "observesTopic"
LISTENS_TO_TOPIC = MQTT4SSN + "listensToTopic"
MATCHES_TOPIC = MQTT4SSN + "matchesTopic"
HAS_FILTER_PATTERN = MQTT4SSN + "hasFilterPattern"
