# orexis-sensing-influxdb

The housekeeper of `orexis-sensing/`: it alone writes a reading to the agent's series store, and has sensing
forget the past readings the store took.

- **Loaded for:** no role of its own. It is started wherever the binary holds sensing, and has a task only where the deployment hands it a series store.
- **Words:** none. It asks sensing for a reading's point (`past::point`) and has sensing remove (`past::forget`).

## What starts it

| Woken by | Does |
|---|---|
| the clock, every `ARCHIVE_INTERVAL_S` of the agent's time (10 s) | writes every reading the store has not taken, then has sensing forget the past ones the store holds |

It hears no event and starts no activity. A stretch in which sensing observed nothing asks the beliefs nothing.
A store that refuses leaves everything where it lies for the next time.
