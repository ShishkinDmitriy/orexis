"""The HTTP transport of Agent 0.2.0: how an agent reaches a service over the web, in the words of
the W3C Web of Things Thing Description.

**THE VOCABULARY IS THE THING DESCRIPTION'S, ADOPTED AS IT STANDS.** A sensor reached over HTTP is
also a `td:Thing`, and its `td:hasForm` is an `hctl:Form` whose `hctl:hasTarget` is where it is
read — a URI template whose variables are filled from the `schema:geo` of what the sensor is
hosted by, variable by local name, so `{latitude}` is the place's `schema:latitude`. This package
declares no word of its own; its ontology names the two namespaces and says which terms the code
reads.

**WHAT IS DERIVED, NOT AUTHORED.** Which services the agent reads follows from what it acts for:
its sensors are those `sosa:isHostedBy` the subject it `orexis:actsFor`, a sample of it or a place
containing it, and a sensor with a form is this member's.

**ONE CLASS, AND THE THREAD IS ITS OWN.** `Http` answers the family's `Transport` contract. It
keeps no timer: sensing's `missed` says when a sensor is due and the container nudges, and
`sense_now` fetches on a thread of its own, once at a time and not again within `RETRY_S` of the
last attempt, handing the response to the container's `deliver`, which enqueues it for the one
executing thread to hand to `handle` and so to sensing's `received`. A public service needs no
credential, so nothing is read from the environment.
"""
