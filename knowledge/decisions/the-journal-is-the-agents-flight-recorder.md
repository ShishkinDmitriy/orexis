---
type: Decision
title: The journal is the agent's flight recorder - its events in RDF and its log for the last minutes, in a store of its own
status: accepted
timestamp: 2026-10-26T12:00:00Z
description: >-
  The sovereign's ruling of 2026-10-25, asking to watch a running agent with some time back, as a dash cam keeps the
  last minutes and saves them when something happens, with the events in RDF and the replay on a triplestore. Each
  agent keeps a journal, a pyoxigraph store in a volume of its own beside its beliefs - every event its packages say,
  in their words, kept for good, and its log, kept for a window unless an incident keeps the minutes before it - and
  serves it read-only over the SPARQL protocol on the host's loopback. InfluxDB keeps the observations and the
  metrics. The history view runs each drawing's selects over the journals, the observations and the world, after a
  run or live, and speech journals every statement said and heard. Refused - events
  in InfluxDB, a central store, journal files, every event journaled under words of its own, and a reader opening a
  live journal.
---

# What was true

History was points in an InfluxDB bucket of each agent's own
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)), and the replay
drew them ([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)).
A plan was a point per step and a set of holdings a point per member, each tagged by local names, since a series store
has tags and fields and nothing else: a plan's steps were told apart by an `order` tag, a holding by an `n` tag, and
the IRIs behind every name were gone. A replay was a page built after the run, and nothing kept what the agent said in
its log beyond the container's own output. The sovereign asked for the run as it goes, *with some time back, as a dash
cam holds the last N minutes and saves them if something happens*, and then: *I would make events in RDF; can the
replay be fully on top of a triplestore — but no central store, and keep Influx for the observations and metrics.*

# The claim

**Each agent keeps a journal: a triplestore of its own, beside its beliefs and apart from them**
([journal](/domain/kernel/journal.md)). It is a pyoxigraph store in a volume of its own (`--journal`), so a reader of
the journal is handed no belief, and nothing in it reaches a plan: no part reads it. Each entry is a named graph
holding one node, named by a UUID's URN so two agents' journals merge without renaming.

**An event is history in its package's words** ([event](/domain/kernel/event.md)). An event class that is history
answers `statements(node)`: its class beneath `orexis:Event` in the package's ontology — `planning:PlanPublished`,
`execution:StepTaken`, `coordination:Foreseen` — and what the agent held of what it is about, copied as it stands:
the plan graph whole, the act and its step as the plan states it, every value it takes in the domain's words, the
holdings in the words a question carries them in, a conflict under its own name. The history part writes it, the
journal stamps its `prov:atTime`. So a plan's steps are read back in their chain and a step by its own IRI, which is
what planning and execution meet at.

**What two agents said to each other is history too.** Speech journals each statement the agent said, with every
agent it was told to (`speech:Said`), and each a peer said to it (`speech:Heard`), the statement carried whole and the
kind it says it is beside it — a question, an answer, a commitment, in the words of whoever spoke it. Coordination
journals what it held and concluded, and what it asked and answered is speech's to say; a commitment and a reveal are
steps, which execution journals.

**The log is the dash cam.** Every record the agent's process logs is an `orexis:LogRecord` in the journal, kept for
the window (`JOURNAL_WINDOW_S`, ten minutes where nothing says) and swept after — unless an INCIDENT keeps it: an
event of a class beneath `orexis:Incident` — `execution:StepFailed`, `execution:IntentionFailed`,
`planning:WantUnreachable` — or a record at WARNING or above, which is how a present that violates a constraint, a
sensor gone silent and an exception escaping a pass are said. **What an incident is, is the vocabulary's, and which
count, the deployment's**: a package puts the classes of its events that are incidents beneath `orexis:Incident`, the
history part reads them off the agent's T-Box, and a world's deployment graph may add classes (`onboarding:incident`)
and raise or lower the level (`onboarding:incidentLevel`), told to the agent as environment. Keeping a journal is
every agent's, and needs no role. An incident keeps every record of the window before it for good (`orexis:keptBy`). The history is
the flight data, kept for good; the log the cockpit's voice, kept when something happened.

**The journal is served read-only, on the host's loopback.** An agent runs on the host's network, so it serves its
journal at `http://127.0.0.1:<port>/sparql`, a query endpoint over the journal alone that refuses an update by not
parsing one. The port is allocated by the installation from a pool of its own, as a broker's is, and kept in
`infra/installation.derived.ttl` (`onboarding:journal`); `orexis-compose` tells the container `JOURNAL_PORT`. A stopped
agent's journal is read off its volume, opened read-only, which is safe once nothing writes it.

**InfluxDB keeps what it is built for**: the observations, a number at an instant on a few tags, which the dashboards
draw, and the metrics.

**The history view is SPARQL** ([history view](/domain/onboarding/history-view.md)). `orexis-history` loads the journals, the
observations — each point made a `sosa:Observation` again, its sensor, feature and property found by local name in the
world — and the world's documents into one store in memory, and runs every drawing's selects (`ui/<Query>.rq`
beside its `ui/index.tsx`) once per agent: its observations and the world as the default graph, its journal's entries
named, so a select reads an event within its own graph. The rows go into the page; a drawing reads them by query.
What the world states of a thing is joined in the select, so the scenes are handed nothing else. `--live` serves the
page on the loopback and asks the endpoints again every few seconds for the last `--window`, following the latest
instant. `orexis-explain` reads its steps from the journal the same way.

# What was refused

- **Events in InfluxDB.** A series store indexes its tags, and an event's identities — a want, a plan, a step, each
  its own IRI — are tags of unbounded values, which break that index; and it has no structure, so a plan's steps were
  an `order` tag and a contact's van a lookup the page made. It keeps the numbers.
- **A central store**, every agent's journal in one triplestore the operator runs. Refused by the sovereign: an agent's
  isolation is structural, its store in a volume of its own
  ([where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md)), and a journal is the same.
- **Journal files**, TriG segments in a bind-mounted directory, an hour's history a file and a minute's log another,
  the dash cam copying segments aside. Proposed and refused by the sovereign for a triplestore: a file is not queried,
  and the history view would have loaded every segment to ask one question.
- **Every event journaled under words of its own**, the metrics' events — a search ended, a pass, a re-root — each a
  class and every field a property: some hundred terms nobody would read but the dash cam, which the log already says
  at the grain a person reads it. What only metrics hear stays theirs, aggregated.
- **A reader opening a live journal.** pyoxigraph 0.5.11 opens a store read-only, and doing so while another process
  writes it is undefined behaviour, with no follower mode; so a running agent's journal is reached through its endpoint
  and never its volume.
- **A logger role**, an agent keeping a journal only where its self graph says it plays one. Whether an agent keeps a
  journal changes no plan, so it is no belief, and a role is one; and a world forgetting to declare it would leave an
  agent with no recorder on the day it was wanted. Every agent keeps one, as every agent writes its history.
- **An incident typed by code**, a step's event typed `orexis:Incident` where it did not land. What an incident is
  became a question nothing could ask; a class beneath `orexis:Incident` is one the T-Box answers, and the deployment
  can name another.
- **Recording the belief base** stays refused
  ([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)):
  the journal holds what the packages said, copied, and never the store.

# What it amends

- **Reflection reads the journal too, and never a belief volume**
  ([reflection-is-genesis-run-again-over-the-series](/decisions/reflection-is-genesis-run-again-over-the-series.md)):
  the journal is the agent's word about what it did, watched as the series is.
- **History is two stores** ([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)):
  an observation is a point, and every other event that is history is triples.
- **The history view reads rows and not points**, and is named for what it shows: the sovereign's *replay is a side
  effect, if we have history* renamed `orexis-replay` to `orexis-history` and put each drawing in a `ui/` folder of its
  package, its components and its selects together
  ([a-replay-is-the-history-drawn-by-the-package-that-decides-it](/decisions/a-replay-is-the-history-drawn-by-the-package-that-decides-it.md)):
  a drawing ships its selects, and `things` is gone into them.

# Seams left open

- **An endpoint is open to anyone on the host.** It is bound to the loopback and carries no credential, as the
  sovereign chose; a host shared with someone who may not read an agent's journal is the trigger for a token minted
  per agent, as the series store's are.
- **A series store refusing writes keeps the log for good** where the world leaves the level at WARNING: each refusal
  is a warning, and every warning an incident. A world raises it with `onboarding:incidentLevel`; the trigger for more
  is a journal that grows through an outage at ERROR.
- **A deployment adds incidents and never takes one away.** A class the vocabulary counts is counted everywhere; the
  trigger for an exclusion is a world whose incidents of one class keep more log than anyone reads.
- **The log of one process is one agent's.** A test walking two agents in one interpreter keeps no log in either
  journal, since a handler would hear both; only `orexis-agent` installs one.
- **The live page asks for the whole window each time.** A season of dozens of agents shown live is the trigger for
  asking only what came since the last answer.
- **What only metrics hear is in no journal.** A search's figures, a pass's laps: the trigger is an incident the log
  does not explain.
