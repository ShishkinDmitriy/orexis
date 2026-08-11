# Derivation: which codec serves each CHANNEL, from what the devices on it send.
#
# The premise is `codec:encoding` — a fact about a board's firmware, the same kind of fact as
# `ag:senseMode`. The conclusion moved: it used to land on the sensor and now lands on the
# stream, because an encoding is a property of a stream and never was one of a sensor. Three
# sensors sharing one topic are three copies of one fact the moment it sits on them, and nothing
# stops the copies disagreeing — which is exactly what validated clean before this.
#
# A channel also outlives the sensor case. A command channel has no sensor at all, so a
# sensor-borne encoding could never describe what an agent PUBLISHES to a board. That is the
# path `codec:Json.encode()` was written for and nothing has ever reached.
#
# The channel IRI is recomputed here rather than read, and that is forced rather than chosen:
# `$given` is public MINUS the derived graph, so this rule cannot see the node
# `transports/mqtt/rules.ru` mints. Both compute the same expression from the same topic, so
# both name the same node without either depending on the other having run. The duplicated
# CONCAT is the price of a rule never reading a conclusion, and it is the right price.
#
# Silence is an assertion, not an absence. A device that states nothing is saying JSON, which is
# what every board here sends — so a stream carrying one device that says CBOR and another that
# says nothing has two claims on it and `codec:ChannelIsDecodedByExactlyOneShape` refuses the
# world. That is the intended reading: two devices disagreeing about the format of one stream is
# the error, however quietly one of them disagrees.

PREFIX mqtt: <http://example.org/agora/mqtt#>
PREFIX ag:    <http://example.org/agora#>
PREFIX codec: <http://example.org/agora/codec#>

#  Says what it sends -> that member decodes every stream it is on.
INSERT { GRAPH $derived {
    ?channel codec:decodedBy ?encoding } }
$given
WHERE  {
    ?device codec:encoding ?encoding . ?encoding a codec:Encoding .
    { ?device mqtt:readingTopic ?topic } UNION { ?device mqtt:commandTopic ?topic }
    UNION { ?device mqtt:statusTopic ?topic }
    BIND(IRI(CONCAT("http://example.org/agora#channel.", ENCODE_FOR_URI(?topic))) AS ?channel)
} ;

#  Says nothing -> JSON, which is what every board in every shipped world sends. The default
#  belongs to THIS package rather than to the kernel: it is a claim about what the fleet does,
#  and a society whose boards all spoke CBOR would move it by adding a directory.
INSERT { GRAPH $derived {
    ?channel codec:decodedBy codec:Json } }
$given
WHERE  {
    { ?device mqtt:readingTopic ?topic } UNION { ?device mqtt:commandTopic ?topic }
    UNION { ?device mqtt:statusTopic ?topic }
    FILTER NOT EXISTS { ?device codec:encoding ?stated }
    BIND(IRI(CONCAT("http://example.org/agora#channel.", ENCODE_FOR_URI(?topic))) AS ?channel)
}
