---
type: Decision
title: The agent's lifecycle and each package's are activities, heard on the events as any other
status: accepted
timestamp: 2026-11-17T13:42:55Z
description: >-
  The sovereign's ruling of 2026-11-17, from an event storm. The agent boots, runs and stops as three activities of the
  kernel's, AgentBooting, AgentRunning and AgentStopping, each holding the PackageBooting, PackageRunning and
  PackageStopping of every package in it; each is said by one start and one end, and a package waits on another, and on
  the agent, by hearing those ends on the events. A package brings its own documents in its booting, named in the order
  it wants. Refused - the kernel's private barriers, a gate counting the cores made, a flag for the boot finished and a
  wait on the cores a package's roles depend on; and a package's documents listed in its registration for the kernel to
  bring.
---

# What was decided

The agent's life is three activities of the kernel's, and each package's is up to three inside them, all beneath
`prov:Activity` and each said, as every [activity](/domain/kernel/activity.md) is, by one `prov:Start` and one
`prov:End`:

| the agent's | holds, for each package | ends when |
|---|---|---|
| `orexis:AgentBooting` | `orexis:PackageBooting`: the package decides whether it runs, joins bringing its documents (`orexis:PackageJoined`), waits for what its roles depend on, makes its core | every package's booting has ended, the boot finished there or refused |
| `orexis:AgentRunning` | `orexis:PackageRunning`: its loop | every running package's running has ended |
| `orexis:AgentStopping` | `orexis:PackageStopping`, where a package has work left once the others are done | the last task does |

A booting that declines ends having made no core, so the journal shows which packages did not run (`orexis:runs`).
A booting ends saying the role classes its package serves (`orexis:serves`), and a package whose role depends on
another role (`orexis:dependsOn`) waits to hear the end of a booting serving it. Since a dependency may be stated in
another package's documents - `execution:Executor orexis:dependsOn planning:Planner` is planning's - a package reads
what it waits for only once every package has joined or ended its booting, so the vocabulary is whole. A check is the
agent's booting alone, and a package told it does not run (`Handed::booted` false) ends there.

**A package brings its own documents** in its booting, `handed.joins(&DOCUMENTS)`, the files of its crate in the
order it names them (`orexis::documents!`); its registration is a name and a start. The prefixes the registration's
documents were read for went in #1211, every text declaring its own.

# Why

Packages already meet by events: a policy hears an event beneath its trigger and starts an activity whose start and
end are events another may hear ([packages-meet-by-events-policies-and-activities](/decisions/packages-meet-by-events-policies-and-activities.md)).
The lifecycle was the one place they met otherwise: a gate in the kernel counted the cores being made, a flag said the
boot was finished, a set of cores made was waited on by the roles each package depends on, and two events of the
kernel's own, a package starting and a package started, were said after the fact, for the journal. Each was a
second mechanism beside the events for one thing the events already say, and the journal could not see what caused a
package to go on. As activities, the boot is in the journal as what it is: the agent's booting, each package's inside
it, and how long each took.

# What was refused

- **The kernel's barriers**, the state above. They gave the two guarantees this keeps: that every package has made its
  core before any speaks - now the agent's booting ending before any running begins - and that waiters wake in the
  order they began to wait, which the events keep because each hearer is a channel of its own sent to in the order it
  subscribed, where a Tokio `watch` had picked notifiers at random.
- **A package's documents in its registration**, for the kernel to bring: it was the kernel loading on the package's
  behalf, and with the prefix table gone nothing else read them.
- **The archive's last take as a callback the kernel ran after every task**: it is the archiver's stopping,
  begun once the agent's running has ended.

# Seams left open

- **What the lifecycle hears is asked before any task runs** (`task::spawn`): the events keep nothing, so an end said
  before its hearer subscribed is lost. A package subscribing to the lifecycle late would wait for ever, and none can,
  since the kernel subscribes for it.
- **A test that calls a core itself boots by the agent's booting alone** (`Booted::without_starting`): the store holds
  the documents of the packages the agent runs and of no other, where it had held every linked package's; a test
  wanting another package's words boots an agent that runs it.
