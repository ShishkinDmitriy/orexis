# Derivation: one node per distinct topic, and who sends or receives on it.
#
# The premise is what a device already states — `mqtt:readingTopic`, `mqtt:commandTopic`,
# `mqtt:statusTopic` — so an author restates nothing. The conclusion is the node, and the node's
# IRI is a FUNCTION of the topic string. That is the load-bearing choice here, for a reason that
# is not aesthetic: `$given` is public MINUS the derived graph, so a rule may never read another
# rule's conclusions. A minted IRI computed the same way in two packages is therefore the only
# join key available — `codecs/json/rules.ru` computes this same expression to hang an encoding
# on the channel, and the two agree because arithmetic agrees, not because one ran first.
#
# A blank node cannot do this: two solutions would produce two nodes and the sensors sharing a
# stream would stop sharing it. A counter cannot either — nothing here is ordered.
#
# ENCODE_FOR_URI rather than a prettier substitution, because a slug that replaced `/` with `.`
# would collide with a topic containing a literal `.` and the collision would silently MERGE two
# streams. A derived node has to be stable and distinct; nothing looks one up by name.

PREFIX mqtt: <http://example.org/orexis/mqtt#>
PREFIX ag: <http://example.org/orexis#>

#  Where a device SENDS: what it read, or what it did.
INSERT { GRAPH $derived {
    ?channel a mqtt:Channel ; mqtt:channelTopic ?topic .
    ?device mqtt:publishesOn ?channel } }
$given
WHERE  {
    { ?device mqtt:readingTopic ?topic } UNION { ?device mqtt:statusTopic ?topic }
    BIND(IRI(CONCAT("http://example.org/orexis#channel.", ENCODE_FOR_URI(?topic))) AS ?channel)
} ;

#  Where a device RECEIVES: a cadence for a sensor, a dose for a valve.
INSERT { GRAPH $derived {
    ?channel a mqtt:Channel ; mqtt:channelTopic ?topic .
    ?device mqtt:listensOn ?channel } }
$given
WHERE  {
    ?device mqtt:commandTopic ?topic .
    BIND(IRI(CONCAT("http://example.org/orexis#channel.", ENCODE_FOR_URI(?topic))) AS ?channel)
}
