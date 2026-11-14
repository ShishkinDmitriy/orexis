# orexis-sensing-influxdb

The housekeeper of `orexis-sensing/`: it alone writes a reading to the agent's series store, and has sensing
forget the past readings the store took.

- **Loaded for:** `sensing:Observer`, where the role names a series store (`sensing:archivedIn`): it makes its own
  sink from that store, as the world's deployment states it, and the agent's history credential, where the agent
  is deployed. An observer whose role names none keeps its readings in its beliefs.
- **Words:** none. It asks sensing for a reading's point (`past::point`) and has sensing remove (`past::forget`).

## What starts it

| Woken by | Does |
|---|---|
| the clock, as often as the observer's role says (`sensing:archivedEveryS`), every 10 s of the agent's time where it says nothing | writes every reading the store has not taken, then has sensing forget the past ones the store holds |

It hears no event and starts no activity. A stretch in which sensing observed nothing asks the beliefs nothing.
A store that refuses leaves everything where it lies for the next time.
