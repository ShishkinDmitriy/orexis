# orexis-journal-otlp

A housekeeper of `orexis-journal/`: it ships the activities the journal holds to a tracer, as spans, over OTLP's
JSON on HTTP.

- **Loaded for:** `journal:Recorder`, where the role names a tracer (`journal:tracedBy`): it asks the world's
  deployment graph where that `journal:Tracer` answers as it starts, and ends its start where the role names none.
- **Words:** none. It marks what the tracer accepted `orexis:shippedTo`.

## What starts it

| Woken by | Does |
|---|---|
| the clock, as often as the recorder's role says (`journal:tracedEveryS`), every 10 s of the agent's time where it says nothing | POSTs every activity not yet shipped to `/v1/traces` beneath the tracer's url, off the agent's own threads |

It hears no event and starts no activity.

## What a span is

| In the journal | In the trace |
|---|---|
| an activity, by its class | a span, named for the class |
| an activity begun inside another (`dcterms:isPartOf`) | a child span |
| a turn's activity inside one that lasts, a listening or a running | no child of it: a link to it carrying `orexis.partOf` |
| an event said inside it | a span event, carrying `prov.entity` |
| what started it | the attribute `orexis.trigger` |
| the turn's activity that generated what started it, where it is inside no other of its turn | its parent span, so what caused what is one trace; a second cause, or one that lasts, is a link |
| `orexis:tookS` | the span's length |

A tracer that refuses is said in the log once; what it was not told stays in the journal until the window sweeps it.
