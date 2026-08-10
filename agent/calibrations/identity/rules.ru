# Derivation: which calibration serves each sensor, from the curve its device follows.
#
# The premise is `calibration:curve` and the conclusion is `calibration:calibratedBy`. Two
# predicates rather than one, deliberately: a world states what is TRUE of a probe, and genesis
# writes down what SERVES it. Collapsing them would let a world state the conclusion, which is
# the one thing no world may do.
#
# The default is `calibration:Identity`, and it is the honest answer rather than a stand-in.
# `firmware/moisture-sensor` maps its ADC counts to a fraction before it publishes, so what
# reaches an agent has already been through a curve — one that lives in C, on the board, where
# changing it means reflashing. From the agent's side the remaining calibration genuinely is the
# identity function. Issue #26 is the proposal to move that work here, and the moment it lands a
# curve stops being a compiled constant and becomes a belief.
#
# What is NOT consulted: the unit. `calibration:quantityUnit` says what the resulting quantity
# IS, which no derivation could work out — a fraction and a temperature are both bare decimals,
# and only the world can say which this one is.

PREFIX ag:          <http://example.org/agora#>
PREFIX calibration: <http://example.org/agora/calibration#>

#  Follows a stated curve -> that member calibrates it.
INSERT { GRAPH $derived {
    ?sensor calibration:calibratedBy ?curve } }
$given
WHERE  { ?sensor a ag:Sensor ; calibration:curve ?curve .
         ?curve a calibration:Calibration } ;

#  States no curve -> identity, because the board already scaled.
INSERT { GRAPH $derived {
    ?sensor calibration:calibratedBy calibration:Identity } }
$given
WHERE  { ?sensor a ag:Sensor . FILTER NOT EXISTS { ?sensor calibration:curve ?stated } }
