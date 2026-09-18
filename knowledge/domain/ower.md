---
type: Service
title: Ower
description: >-
  The service that keeps what this agent owes — one row per claim the society issued against it,
  with the counterparty, the amount and the window. It is the only writer of the obligations
  graph, and its rows become obligations the search ranges over rather than facts anyone may retract.
---

# What it runs

**Debt keeping.** `owe` raises a row when a claim is issued; `demanded` marks it presented;
`discharge` closes it. Each row is an [obligation](/domain/obligation.md) — a want this agent did
not source — so a debt is pursued through the same road as anything else it wants.

# What it reads and writes

![ower — what it reads and writes](../diagrams/service-ower.svg)

**Durable on purpose.** A host's in-memory record of what it issued dies with the process; the
ledger is what survives a restart, which is why a claim raises a row whether or not the holder
ever presents it.

# What it is not

**It is [hosting](/domain/market.md)'s, and the modality is the kernel's.** Only a host owes,
because a debt arises from a claim this agent ISSUED — so the ledger lives in the market package
and `HostingModule` holds it. What stays the mind's is the
want under *no overdue debts* — minted by the pursuit road about the
[obligation](/domain/obligation.md), holding at its deadline — the modality that projects the
record, and the branches that rank a debt beside a stake. The words written in the record —
the counterparty, the claim, the amount, the window, the discharge — and the record's class
are the market's (#635), and so is the desire's met-test, authored by the ledger's own
`desires.ru`; the planner judges the road's want as it judges any shaped want and names no
word of the ledger.

**Which needed no new mechanism**, and that is the point worth keeping. A package declaring a
per-agent graph of its own is what [review](/domain/review.md) already does with its summaries —
so the ledger declares `market:ObligationsGraph` with its prefix and how it arrives, boot
classifies it as it classifies every such graph, and nothing in the kernel learns that market
exists. The one thing the kernel keeps is the prefix, because the desire modality projects
the record and may not import the package to learn its name.

**Not a capability of its own.** Keeping a record cannot be done two ways, and rule 2 reserves a
capability for an ability whose *how* could differ. It is a thing hosting holds, and what it
contributes to the choir — the debts among what this agent pursues, and the figures beneath
them — arrives through the module that holds it.
