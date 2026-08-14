# Derivation: which calibration serves each sensor, from the curve its device follows.
#
# The premise is `scaling:curve` and the conclusion is `scaling:scaledBy`. Two
# predicates rather than one, deliberately: a world states what is TRUE of a probe, and genesis
# writes down what SERVES it. Collapsing them would let a world state the conclusion, which is
# the one thing no world may do.
#
# The default is `scaling:Identity`, and it is the honest answer rather than a stand-in.
# `firmware/moisture-sensor` maps its ADC counts to a fraction before it publishes, so what
# reaches an agent has already been through a curve — one that lives in C, on the board, where
# changing it means reflashing. From the agent's side the remaining calibration genuinely is the
# identity function. Issue #26 is the proposal to move that work here, and the moment it lands a
# curve stops being a compiled constant and becomes a belief.
#
# What is NOT consulted: the unit. `scaling:quantityUnit` says what the resulting quantity
# IS, which no derivation could work out — a fraction and a temperature are both bare decimals,
# and only the world can say which this one is.

PREFIX sensing: <http://example.org/agora/sensing#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX ag:          <http://example.org/agora#>
PREFIX scaling: <http://example.org/agora/scaling#>

#  Follows a stated curve -> that member calibrates it.
INSERT { GRAPH $derived {
    ?sensor scaling:scaledBy ?curve } }
$given
WHERE  { ?sensor a sosa:Sensor ; scaling:curve ?curve .
         ?curve a scaling:Scaling } ;

#  States no curve -> identity, because the board already scaled.
INSERT { GRAPH $derived {
    ?sensor scaling:scaledBy scaling:Identity } }
$given
WHERE  { ?sensor a sosa:Sensor . FILTER NOT EXISTS { ?sensor scaling:curve ?stated } }
