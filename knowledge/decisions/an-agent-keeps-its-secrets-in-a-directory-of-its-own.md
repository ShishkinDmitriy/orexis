---
type: Decision
title: An agent keeps its secrets in a directory of its own, mounted whole, and shares none
status: accepted
timestamp: 2026-11-02T12:30:00Z
description: >-
  #860 - a world's private documents were mounted file by file where a checkout held them, so the
  committed compose file could be right on no machine. Decided by the sovereign - every agent has a
  directory of its own under the world's secrets, holding its credentials, its certificate and every
  document only it is handed, mounted whole into its container; nothing an agent holds is shared, so a
  group chat's id is stated in each member's. What is no agent's stays beside them. Refused - one
  directory of the world's private common documents, and a generated override.
---

# The question

A world kept everything git must not hold in one flat `secrets/`: every agent's credentials beside the
authority's key, the boards' passwords, and documents such as the terrace's place and its chat's id.
`orexis-compose` mounted each document there file by file, and only where the checkout held it, so the
committed `compose.yaml` was wrong wherever the documents were not, and dirty wherever they were (#860).

# What was decided

**An agent keeps its secrets in a directory of its own**, `secrets/<agent>/`, named by the one short
string the agent goes by: its broker credential (`mqtt.env`), its series tokens (`influx-<purpose>.env`),
its certificate (`agent.crt`, `agent.key`), its carriers' secrets (`telegram.env`, `mail.env`), and every
document only it is handed. Onboarding mints into it and creates it; the compose file mounts it whole into
the agent's container and no other; and the boot reads documents from the agent's own directory and from no
other's. The committed file names a directory, which every checkout has, so it is the same everywhere.

**Nothing an agent holds is shared.** A document two agents read - a group chat's id - is stated in each
member's directory. What is no agent's stays in `secrets/` itself: the world's authority, its broker's
certificate, and the boards' credentials, which the firmware generator reads on the host. An agent is handed
the authority's certificate, which is public, and nothing else of it.

# What was refused

- **One directory of the world's private common documents**, mounted whole into every agent. It mirrored how
  common documents already travel, and the sovereign refused it: a secret in it is every agent's, and
  isolation stays structural only where nothing private is shared.
- **A generated, gitignored override** carrying the private mounts beside the committed file. It answers #860
  and keeps the flat directory, where one agent's credentials sit beside another's.

# Seams left open

- **A document stated twice.** A group chat's id lies in each member's directory; nothing checks the copies
  agree, and an agent holding a stale one hears nothing in the group.
- **Moving an existing world.** The flat names were moved into each agent's directory by hand once, on the one
  host that held them; nothing in onboarding moves them.
