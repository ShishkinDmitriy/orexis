# Derivation: which codec serves each sensor, from what its device SENDS.
#
# The premise is `codec:encoding` — a fact about the board's firmware, the same kind of fact as
# `ag:senseMode`. Nobody's opinion, and nothing an agent decides. The conclusion is
# `codec:decodedBy`, and like every other conclusion here it lands in the derived graph and is
# never written by hand.
#
# Why derive it at all when the premise names the member directly: because the DEFAULT has to
# exist somewhere, and a default computed in Python is a fact nothing can read. Before this,
# every sensor in every world was decoded as JSON by a `DEFAULT = True` on a class — true, load-
# bearing, and absent from the graph. Now genesis writes it down, so a sensor's pipeline is
# something you can query rather than something you infer from which classes a build imported.
#
# The two rules are DISJOINT by `FILTER NOT EXISTS`, which is what makes an explicit statement
# beat the default structurally. It used to be a Python claim test that had to be written
# carefully, ordered against a `PROVIDES` tuple that guarantees no order at all; here the
# premises cannot both hold, so there is no order to get wrong.
#
# A second codec package declaring itself the default as well would produce TWO conclusions for
# one sensor, and `codec:SensorIsDecodedByExactlyOneShape` refuses that at validation — before
# a society starts, rather than at the first message.

PREFIX ag:    <http://example.org/agora#>
PREFIX codec: <http://example.org/agora/codec#>

#  Says what it sends -> that member decodes it.
INSERT { GRAPH $derived {
    ?sensor codec:decodedBy ?encoding } }
$given
WHERE  { ?sensor a ag:Sensor ; codec:encoding ?encoding . ?encoding a codec:Encoding } ;

#  Says nothing -> JSON, which is what every board in every shipped world sends. The default
#  belongs to THIS package rather than to the kernel: it is a claim about what the fleet does,
#  and a society whose boards all spoke CBOR would move it by adding a directory.
INSERT { GRAPH $derived {
    ?sensor codec:decodedBy codec:Json } }
$given
WHERE  { ?sensor a ag:Sensor . FILTER NOT EXISTS { ?sensor codec:encoding ?stated } }
