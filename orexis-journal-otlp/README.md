# orexis-journal-otlp

A housekeeper of `orexis-journal/`: it ships the activities the journal holds to a tracer, as spans, over OTLP's
JSON on HTTP.

- **Loaded for:** `journal:Recorder`, where the world names a tracer: it asks the world's deployment graph for a
  `journal:Tracer` as it starts, and ends its start where there is none.
- **Words:** none. It marks what the tracer accepted `orexis:shippedTo`.

## What starts it

| Woken by | Does |
|---|---|
| the clock, every 10 s of the agent's time | POSTs every activity not yet shipped to `/v1/traces` beneath the tracer's url, off the agent's own threads |

It hears no event and starts no activity.

## What a span is

| In the journal | In the trace |
|---|---|
| an activity, by its class | a span, named for the class |
| an activity begun inside another (`dcterms:isPartOf`) | a child span |
| an event said inside it | a span event, carrying `prov.entity` |
| what started it | the attribute `orexis.trigger`, and a link to the span that generated it |
| `orexis:tookS` | the span's length |

A tracer that refuses is said in the log once; what it was not told stays in the journal until the window sweeps it.
