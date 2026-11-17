# orexis-transport-http

The HTTP member of the transport family: it answers a request for what a web service a sensor reads says, in the
words of the W3C Web of Things Thing Description. A forecast is a series such a sensor reads.

- **Loaded for:** no role of its own. It is loaded where the agent reads a sensor over HTTP.
- **Words:** `ontology.ttl`. **Dictionary:** `knowledge/domain/transport/transport.md`.
- **Needs:** the service's address, in the agent's own `secrets/<agent>/`.

## What starts it

It adds its member to the agent's members (`orexis_transport::Members`) and runs no task. A request, sensing's at
the frequency each sensor states, is one fetch of the sensor's address, awaited as a Tokio task, its body left where
the requester asked.

It hears no event and starts no activity.
