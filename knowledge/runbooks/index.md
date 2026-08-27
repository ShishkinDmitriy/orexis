# Runbooks

How to actually operate a society: bring one into existence, run it, and take it apart. The
[domain](/domain/) says what things are; these say what to type.

# Lifecycle

* [genesis-a-world](/runbooks/genesis-a-world.md) - Author a new world and seed it: what to write, what genesis derives, and the four checks.
* [run-a-world](/runbooks/run-a-world.md) - Deploy, up, down, logs, and what to do after a code change. One container per agent, generated from the world.
* [add-a-package](/runbooks/add-a-package.md) - Create one: what is mandatory and which gate refuses you, what is merely recommended, and what an omission states.
* [tear-down](/runbooks/tear-down.md) - Stopping a society is not one command. What survives `down`, why each survives on purpose, and how to remove it.

# A note on commands

There is no `orexis-up`, no `orexis-down`, no `orexis-restart`. Running a society is
`podman compose` (or `docker compose`) — a tool you already know, with verbs you already know,
that behaves the same here as everywhere else.

The only orexis-specific commands are the ones that **produce** something from the world:
`orexis-onboard`, and `orexis-validate` to check the result. Once they have run, you are holding
an ordinary compose project. There is still nothing to **seed** — an agent builds its own belief
base at boot — but there is something to **provision**, and that is what onboarding is: a bucket
and a token per agent, a bus credential and an ACL per principal, every one of them derived from
the world's wiring rather than decided. See [onboarding](/domain/onboarding.md). That line is
deliberate: a wrapper
would be one more thing to learn, one more thing to document, and one more place for the truth
about what is running to diverge from what compose thinks is running.
