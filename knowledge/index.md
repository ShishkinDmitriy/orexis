---
okf_version: "0.1"
---

# Orexis — Agent Society

Self-interested agents that plan for what they want and trade for what they lack, on real
sensors on a Raspberry Pi. Each agent is Agent 0.2.0: one process, one store, one world. Bytes
from its instruments become observations, rules revise them, the future is predicted, wants are
derived from its desires and searched over possible worlds, and the plans are carried out and
held to what they predicted. The domain is a plug-in: plant watering is the example — a grower
buying water on a supplier's venue — and hanoi, a courier grid and a tower of the two are the
others. This bundle is the durable what and why; the live state is in each agent's store.

# Domain

* [domain/](domain/) - The dictionary, filed by the package that owns each word, in the order a pass runs: kernel, sensing, belief, prediction, planning, execution.

# Decisions

* [decisions/](decisions/) - Why the code is as it is, and the seams left open; 0.1.0's records are filed apart.

# Runbooks

* [runbooks/](runbooks/) - Author a world, add a domain, run it, measure the search, and take it apart.

# How to use this bundle

* **What is a word?** Its page in [domain](/domain/index.md), in the folder of the package that
  owns it. A domain page is the current statement, and the gates hold it to live terms.
* **Why is it so?** The [decision](/decisions/index.md) a domain page links. A record argues and
  refuses; several may amend one another, and a superseded one says what superseded it.
* **Operating one?** Start at [runbooks](runbooks/).
* **Changing something?** Check whether a record pins it — its seams are what you are checking for.
* **Adding a document?** Frontmatter with a `type` — `Decision`, `Domain Concept`, `Process`,
  `Capability`, `Role`, `Service`, `Repository` or `Runbook` — a `title` and a `description`; a
  decision adds `status` and `timestamp`; a domain page whose word the T-Box carries binds it with
  `term:`. An `index.md` carries none; only this file declares `okf_version`.
