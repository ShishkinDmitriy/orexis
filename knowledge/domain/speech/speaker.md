---
type: Role
title: Speaker
term: http://example.org/orexis/speech#Speaker
description: >-
  An agent that hears its peers' documents and says its own - the role whose part is speech's,
  and the one word speech's vocabulary declares. It needs a topic the agent listens to, a shape the
  MQTT transport ships since a topic is the transport's word; a topic no speaker hears is refused.
---

# Who is one

An agent stated `speech:Speaker` beside its self, or in a role beneath it: the market's
[host](/domain/market/host.md) and [bidder](/domain/market/bidder.md) are both, so every allotment agent
is one. Declaring it loads [speech](/domain/speech/speech.md), whose part believes what the agent
says when a step says it, and whose `heard` believes a peer's document when the transport hands one
in. Before roles, speech had no vocabulary at all; this is the first word in it.

# What it needs

A topic the agent listens to, `mqtt4ssn:listensToTopic`, where a peer's document arrives. That is
the MQTT transport's word, which speech beneath the transport does not speak, so the shape stating
the need ships in the transport's ontology rather than speech's. The MQTT member is loaded for a
speaker that listens, and `orexis-onboard` refuses both a speaker listening to nothing and a topic
listened to by an agent that is no speaker.

An action whose implementation says a document is not held to the speaker role at all; why
[onboarding](/domain/onboarding/onboarding.md) leaves it alone is that page's to say
([role](/domain/kernel/role.md)).
