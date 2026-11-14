# orexis-transport-http

The HTTP member of the transport family: it polls a web service a sensor reads, in the words of the W3C Web of
Things Thing Description. A forecast is a series such a sensor reads.

- **Loaded for:** no role of its own. It is loaded where the agent reads a sensor over HTTP.
- **Words:** `ontology.ttl`. **Dictionary:** `knowledge/domain/transport/transport.md`.
- **Needs:** the service's address, in the agent's own `secrets/<agent>/`.

## What starts it

| Woken by | Does |
|---|---|
| the clock: at start, then at the frequency each sensor states | fetches the sensor's address on a thread of its own |
| the body fetched (an arrival) | hands it to sensing (`received`) |

It hears no event and starts no activity. It holds the agent running.
