# Runbooks

How to actually operate a society: bring one into existence, run it, and take it apart. The
[domain](/domain/) says what things are; these say what to type.

# Lifecycle

* [author-a-world](/runbooks/author-a-world.md) - The documents a world is, each saying which graph it is, and the test beside it that proves it.
* [run-a-world](/runbooks/run-a-world.md) - Deploy, up, down, logs, and what to do after a code change. One container per agent, generated from the world.
* [add-a-domain](/runbooks/add-a-domain.md) - A directory of documents under `domains/`: its words, actions, shapes and rules, each text declaring its prefixes.
* [measure-the-search](/runbooks/measure-the-search.md) - Time the planner on its bench, record a row in the ledger, and alternate A/B in one session.
* [measure-a-pass](/runbooks/measure-a-pass.md) - Time a whole agent's pass on the greenhouse by its own laps, held to what the pass did, and record it in the pass ledger.
* [reflect](/runbooks/reflect.md) - Ask one agent's series what a season says: `orexis-explain` over its two buckets, or over a run's points, never its beliefs.
* [move-a-world-to-agent-0-2-0](/runbooks/move-a-world-to-agent-0-2-0.md) - Take a running 0.1.0 world onto the 0.2.0 image: rebuild, clear 0.1.0's leftovers, replace the belief volume. The board is untouched.
* [calibrate-a-probe](/runbooks/calibrate-a-probe.md) - Move the probe off the battery pin, flash raw counts, then tell the agent what it reads dry and wet; no reflash again.
* [tear-down](/runbooks/tear-down.md) - Stopping a society is not one command. What survives `down`, why each survives on purpose, and how to remove it.

# A note on commands

There is no `orexis-up`, no `orexis-down`, no `orexis-restart`. Running a society is
`podman compose` (or `docker compose`) — a tool you already know, with verbs you already know,
that behaves the same here as everywhere else.

The only orexis-specific commands are the ones that **produce** something from the world:
`orexis-onboard` and `orexis-firmware`. Once they have run, you are holding
an ordinary compose project. There is still nothing to **seed** — an agent builds its own belief
base at boot — but there is something to **provision**, and that is what onboarding is: a bucket
and a token per agent, a bus credential and an ACL per principal, every one of them derived from
the world's wiring rather than decided. See [onboarding](/domain/onboarding/onboarding.md). That line is
deliberate: a wrapper
would be one more thing to learn, one more thing to document, and one more place for the truth
about what is running to diverge from what compose thinks is running.
