---
type: Decision
title: Series and bus isolation — a bucket each, and an ACL derived from the wiring
description: The belief base was isolated structurally, but history and channels stayed shared - one Influx bucket behind an admin token every agent held, and a broker with no ACLs at all. Decision, one per backing service, both derived from the world - a bucket and a scoped token per agent, and per-principal broker credentials whose permitted topics come from the same connections that derive capability.
status: accepted
timestamp: 2026-08-05T00:00:00Z
---

# Context

[where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) made isolation
*structural*: an agent's beliefs are a store inside its own container, so there is nothing to
enforce. It then named two holes it deliberately did not close, and this decision closes both.

**The series.** Every agent held the same admin token and wrote to one bucket, `sensors`. So
`fern` could not read `tomato`'s beliefs but could read its complete moisture history — exactly
the raw state that the band-only disclosure on the bus exists to withhold. Worse, the token was
in `infra/.env`, which the generated compose files hand to every agent container as an
`env_file`; any scoped token added beside it would have been theatre.

**The bus.** `allow_anonymous true`, no ACL file, one open listener. Any process on the LAN
could subscribe `#` and watch every reading, every bid and every claim, or publish a forged
offer as the supplier. The [capability-modules](/decisions/capability-modules.md) note admitting
this was accurate: *"the bus has no ACLs at all."*

# Decision

**One bucket per agent, and one broker principal per agent and per device**, both provisioned by
tools that read the ratified world and grant exactly what its wiring implies.

Two tools, not one, because they are two backing services and either could be replaced:

    agora-influx <world>    a bucket per agent, and a token that opens only it
    agora-mqtt <world>      a credential per principal, and the broker ACL, derived

## The ACL is the wiring

Nothing is listed by hand. The connections that give an agent a capability give it exactly the
topics that capability needs:

| wiring | granted |
|---|---|
| `sensing:polls S` | read S's `readingTopic`, write S's `commandTopic` |
| `ag:simulatedBy` on a device | that DEVICE reads the `commandTopic` of whatever actuates its subject |
| `market:bidsIn M` | read M's `offerTopic` and `claimTopic/<me>`, write `bidTopic/<me>` |
| `market:hosts M` | write `offerTopic` and `claimTopic/+`, read `bidTopic/+` and each bidder's `eventTopic` |
| `actuation:hasActuator V` | write V's `commandTopic` |
| `mqtt:eventTopic E` | write E |

Read that against `packages/capability/market/bidding.py` and `hosting.py` and it is the same set of
topics they subscribe and publish. This is the same move `agora-compose` makes for the roster:
derived, never hand-maintained, because a second list is a second thing to drift.

The simulated-device row is the one that had to be *found* rather than reasoned out. A real
plant gets wet because water physically arrives; nothing arrives to a stand-in, so it learns it
was watered by reading the **valve's** command topic. No other wiring implies that grant, and
`tests/test_isolation.py` holds every module's `subscriptions()` to the derived grants,
which is the check that caught it.

It used to be granted to the *agent*, because the agent held the model. It is granted to the
**device** now: the stand-in holds the model, and an agent in a simulated world has no more
business reading a valve command than an agent anywhere else.

## What goes in the world, and what does not

A **topic is a rendezvous**: two parties must name the same string or they never meet. So topics
and the broker are ratified in `world.ttl`, as [world-graph](/decisions/world-graph.md) already
had them.

A **bucket has exactly one writer and nobody to agree with**. That makes it deployment, like the
store's URL — so it gets no ontology term. It is named `<world>-<agent>` by convention, and the
convention lives in one function in `influx_admin.py`. The agent is never told it: it reads the
name out of the credential file mounted for it, so no process builds a destination from a naming
rule, and the [three rules the code lives by](/decisions/capability-packages.md) hold unchanged.

Qualifying by world is not cosmetic. Bucket names are org-global, so two worlds each holding a
`fern` would otherwise share one history and a simulation would write into the record of a real
plant. **No world can detect that for itself** — a world is not allowed to know the others exist
— so the convention has to make the collision impossible rather than detectable.

## Where credentials live

Following the pattern the signing keys already set: named by world and agent on the host, mounted
at a fixed path in the container, so the agent reads a path and never constructs a name.

| | where | why |
|---|---|---|
| admin token | `infra/secrets/admin.env` | opens every bucket; no agent may hold it |
| agent's bucket + token | `world/<w>/secrets/influx-<agent>.env` | mounted into that one container |
| agent's broker credential | `world/<w>/secrets/mqtt-<agent>.env` | same |
| device's broker credential | `world/<w>/secrets/mqtt-<id>.env` | world-scoped, since a broker is — see below |
| `infra/.env` | committed template | now only `INFLUX_URL` and `INFLUX_ORG` |

**Both are world-scoped, though devices were not at first.** An agent runs in a container
belonging to one world, so its credential obviously belongs to that world. A board was argued to
be different: flashed once, the same physical thing whichever world is loaded, so one credential
per device — and `world/sensing` was device-for-device identical to `world/society` precisely so
one ESP32 works in either. (`society` has since been removed and `simulation` took its place in
that pair; see [two-worlds-were-one](two-worlds-were-one.md).)

That argument died with the shared broker. A board is flashed with one host and **one port**, and
each world's broker now listens on its own — so a board already reaches exactly one world, and
sharing its password across worlds meant every world's broker holding a secret the others' boards
also used. It was the last thing spanning worlds, and it bought nothing: moving a board between
worlds requires reflashing the port regardless, so it may as well carry that world's credential
with it. The two worlds remain device-for-device identical; what differs is which broker the
board is pointed at.

# Why not InfluxDB 3

Checked, because the store was going to be touched anyway. **InfluxDB 3 Core has admin tokens
only** — fine-grained per-database tokens are an Enterprise feature, so on Core every agent
holding a token holds a token to everything, which is this decision's problem with a new version
number. Enterprise's free At-Home license never expires but caps the node at 2 CPU cores, forbids
commercial use, and requires email registration at server startup — a hard dependency to put in
front of anyone cloning this repo, and half a Raspberry Pi.

Influx 2.x is not end-of-life, and its per-bucket tokens do the job — verified: a scoped token
wrote and read its own bucket, and was refused its neighbour's with 403 on write and 404 on read.
The 404 is the better answer: the token cannot establish that the other bucket exists.

So the version pin in `infra/compose.yaml` is now **load-bearing**, not tidiness. Docker's
`latest` tag points at InfluxDB 3 Core, and drifting onto it would remove the mechanism this
decision is built on.

# Consequences

- **The society is down until every board is reflashed.** `allow_anonymous false` lands in one
  commit rather than two. A staged flip was available and was declined: a half-secured window is
  a window.
- **Grafana keeps the admin token**, and legitimately — with a bucket per agent, the only reader
  that still spans the whole society is the operator's dashboard, which is not a member's view of
  its neighbours. Its Flux panels name `sensors` and are **broken on landing**; fixing them is
  deferred and tracked, not done.
- **`world/simulation` had to be re-authored.** It published on byte-identical topics to
  `world/society` **while both shared one broker**, so running both cross-fed them, and its
  channels were given a `sim/` prefix. That prefix is gone again: each world now runs its own
  broker on its own port, so two worlds naming one topic are two channels and cannot meet. The
  sentence this replaced — *two worlds meet wherever they name the same topic* — was true of a
  shared bus and is not true of separate ones. See
  [two-worlds-were-one](two-worlds-were-one.md).
- **A missed grant is silent.** Mosquitto accepts a SUBSCRIBE it will not honour and simply never
  delivers, so an under-derived ACL looks like an agent that has gone quiet rather than an error.
  Hence the test, rather than trust — and hence `agora-mqtt` reloading the broker itself rather
  than leaving it as a step to forget.
- **The tests split by what they are a contract with.** `tests/test_isolation.py` is a
  unit test of what the tools *derive* from a world, needs nothing running, and stays in the gate
  (`pytest tests -q`). `infra/tests/` is a contract with mosquitto and InfluxDB themselves —
  meaningless without them running, and about behaviour neither we nor any specification
  guarantees. It is run deliberately with `pytest infra -q` and is not part of the gate, so the
  fast suite stays fast and honest about needing no infrastructure.
- **The broker version is pinned, and upgrading it is a tested change.** Everything below is
  mosquitto's behaviour rather than anything MQTT guarantees, so `infra/mosquitto/Containerfile`
  pins `MOSQUITTO_VERSION` and `infra/tests/` reports the version it ran against
  and asserts nothing about it — a test that had to be edited to match the compose file would
  fail for a version change rather than a behaviour change. A bump means rebuilding and re-running
  `pytest infra -q`, and those eight tests are what it has to survive. The cost is that Debian removing a superseded package
  breaks the build — which is the bump announcing itself rather than a mystery.
- **A changed grant reaches a connected agent immediately, and a changed password evicts it.**
  Both were measured rather than assumed, and both are pinned by `infra/tests/test_bus_acl_runtime.py`:
  mosquitto checks the ACL on every *delivery*, so revoking a grant stops the traffic at once
  without the client reconnecting, and granting one reaches a client that subscribed before the
  grant existed. Rotating a password is stronger than expected — on reload the broker re-checks
  connected clients and disconnects those that no longer match, so `--rotate` really does take an
  agent off the bus rather than merely barring its return. That weakens the case for the dynamic
  security plugin considerably: eviction was the one thing it was wanted for.
- **Adding an agent or a world restarts nothing.** The broker must *reread* its two files, which
  is a SIGHUP, not a restart: connected agents keep their sessions. `agora-mqtt` sends it. This
  preserves what [where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md) was
  built for — that adding the 21st world does not disturb the other 20.
- **The broker config path is constrained by the host**, in a way worth writing down because it
  cost an hour and the previous explanation in `infra/mosquitto/Containerfile` was wrong. See
  below.

# The AppArmor trap

The Containerfile blamed musl: the Alpine `eclipse-mosquitto` image *"cannot open ANY config file
on this host"* while a Debian build works. That was a real observation with the wrong cause.

The host **had** mosquitto installed as an apt package, which ships `/etc/apparmor.d/mosquitto`. An
AppArmor profile attaches to an **executable path**, and the container's broker is at
`/usr/sbin/mosquitto` like every other build — so the host's profile confines the container's
process too. The profile grants:

    file @{etc_ro}/mosquitto/* r,          # ONE level, and no deeper
    file @{etc_ro}/mosquitto/conf.d/** r,

Which explains everything that looked inexplicable: the baked `conf.d/agora.conf` works, a file
mosquitto writes itself in `/tmp` does not, and Alpine's `/mosquitto/config/` was outside the
profile by *any* means — bind mount, baked layer or otherwise. It was never the libc.

So the generated `passwd` and `acl.conf` are mounted **directly in `/etc/mosquitto/`** and not in
a subdirectory of it. `/etc/mosquitto/agora/passwd` is two levels deep and is refused however
correct its permissions are. Note also that `password_file` must be world-readable (0644): the
broker runs as an unprivileged user in a container that maps the host user to root. It holds
PBKDF2 hashes; the plaintext stays 0600 in the per-principal files.

The same profile mediated **signals**, which is why reloading took a second attempt. PID 1 in the
container is a root shell that starts the broker as a child (`infra/mosquitto/entrypoint.sh`),
because rootless podman cannot signal an unprivileged PID 1 — and dropping `USER` from the image
is not enough on its own, since mosquitto drops privileges itself. Even then the root PID 1 could
not forward the signal: under `abi <abi/4.0>` a profile that declares no `signal` rules denies
every signal sent to the process, and a root shell in that container was measured signalling an
unprivileged child fine and mosquitto with `EPERM`. From the host it worked, because a user
namespace's creator keeps `CAP_KILL` inside it. Hence `reload_broker()` signals the broker child
of the container's PID 1, from the host — a path that works whether or not a profile is loaded,
which is why it is still the one used.

# Resolved: the package is off the host

The broker no longer runs there, so the package that shipped the profile has no reason to be
installed. Removing it unloads the profile, and the difference is measured rather than assumed:

| | profile loaded | profile gone |
|---|---|---|
| broker's AppArmor label | `mosquitto (enforce)` | `crun (unconfined)` |
| signal from container PID 1 | `Permission denied` | `exit=0` |
| `podman stop` | 10s, then `SIGKILL`, exit 137 | **1s, exit 0** |

The last row is the one that mattered and was nearly missed: a `SIGKILL`ed broker never flushes
its persistence file, so every stop risked losing the retained cadences the volume exists to
keep. Two cautions for anyone reinstating it — `apt remove` unloads the profile but leaves the
conffile, so it can return on a rebuild, and `mosquitto-clients` is safe because the profile
ships with the **server** package.

The path constraints above are kept anyway. They cost nothing and hold if a profile ever returns.

Worth the trouble twice over: an unprivileged PID 1 could not receive `SIGTERM` either, so
`podman stop` timed out and left the container wedged in `Stopping`, needing `kill -9` on its
conmon before the name could be reused. That is gone.

# Seams

- **Two tools, because there could be other backing services.** When a second history store or a
  second transport appears, the admin half belongs beside its driver — `history/<name>/` mirroring
  `transports/<name>/`, discovered by `agora.loader` like everything else. Deliberately not built
  now: there is one of each, and a package tree with one member is a guess about the future.
- **A device's credential is minted here but flashed by hand.** `agora-mqtt` will not rotate a
  device password, because rotating it silently strands hardware that is not in front of you.
- **Nothing stops two worlds sharing a bus on purpose.** It means topic overlap can never be an
  error, only a choice; the operator is the only party who can see both worlds and judge. No
  shipped world does it any more — `sensing` and `simulation` each run their own broker, which is
  what made the `sim/` prefix removable.
- **The wire is still in the clear.** Credentials authenticate; they do not encrypt. TLS on the
  broker remains the next step, as [roadmap](/decisions/roadmap.md) has it.

# The dashboard was the hole in all of it

Worth recording because it survived every round of this design and was found only by looking at
what was left. While each agent got a bucket and a token that opens only it, Grafana sat on
`:3000` with:

    GF_AUTH_ANONYMOUS_ENABLED: "true"     no login, LAN-wide
    token: $INFLUX_ADMIN_TOKEN            opens every bucket, and mints more tokens

So anyone who could reach the port read every agent's history, through the one credential this
document says no agent may ever hold. The bus had per-principal ACLs and mTLS; the dashboard
beside it was an open door onto the same series. The intent was defensible — Grafana IS the
operator's view and legitimately spans every bucket — but *anonymous* and *admin* are both more
than that intent needs.

Now: its own **read-only** token, org-scoped so a world onboarded tomorrow is visible without
re-running anything; anonymous access off; and HTTPS with a certificate from the same
installation CA the broker uses. Measured after the change — read `200`, write `403`, and the
authorizations endpoint answers `200` with an **empty list**, so it cannot see another token's
secret.

Three things that cost time here, all of them the same shape — *a service cannot read its own
key*:

- Grafana runs as uid 472 and needs `userns_mode: keep-id:uid=472,gid=472`, exactly as the
  agents do, or its 0600 certificate key is unreadable and it silently falls back to plain HTTP.
- That mapping then collides with podman's default pod, so `infra/compose.yaml` needs the same
  `x-podman: in_pod: false` the generated world files already carry.
- Changing the mapping made the **existing** `grafana-data` volume unwritable, because it was
  owned under the old one. `podman unshare chown -R 0:0 <mountpoint>` — 0 in that view is your
  own uid.

And one that is not a permissions problem: **`GF_SECURITY_ADMIN_PASSWORD` applies only when the
database is first created.** Turning on login against an existing volume leaves the password as
whatever it already was, which reads as a wrong password in `admin.env`. `grafana cli --homepath
/usr/share/grafana admin reset-admin-password` is the repair.

## Ed25519 is fine between our processes, and invisible to a browser

The first cut used Ed25519 for every key. mosquitto verified it, paho verified it, `curl`
verified it — and Firefox answered `SSL_ERROR_NO_CYPHER_OVERLAP`, which reads like a
ciphersuite misconfiguration and is not one. **Browsers do not support Ed25519 certificates.**

It applies to the whole chain, not the leaf alone: an ECDSA certificate signed by an Ed25519
authority still asks the browser to verify an Ed25519 signature. So the *installation* CA and
both server certificates are ECDSA P-256, while the per-world CAs and the agents' client
certificates stay Ed25519 — nothing but our own code ever verifies those.

The rule worth keeping: **anything a browser terminates is ECDSA; anything only our processes
speak may be Ed25519.**

Rotating the installation CA to change this replaced the broker's certificate too, which every
agent verifies — so every agent had to be restarted to read the new `ca.crt`. That is the cost
recorded in `agora-infra-certs --rotate`, observed rather than predicted.

# The CA is files and a function, not a service

Nothing in `podman ps` is a certificate authority and nothing is meant to be. An authority here
is a private key on disk plus a function that signs — no issuing service, no ACME, no CRL, no
OCSP responder. For one Pi that is proportionate; step-ca or Vault would be the largest thing in
`infra/` and would bring its own availability and backup story.

Three consequences, and only the first is comfortable.

**Issuance is fine.** Re-running the command issues or renews, and anything within 30 days of
expiry is reissued, so the routine command is the routine cure.

**Revocation barely exists, and an earlier note here overstated it.** Certificates were described
as "the first thing that can genuinely be revoked". They are not: with no CRL the broker cannot
reject a certificate that is still inside its validity window. What revocation exists is coarse
and comes from an accident of the design — `clients-ca.crt` is a *concatenation*, so deleting a
world's authority from it and restarting the broker locks out that entire society. Per world,
never per agent, and it costs every connected client.

**The keys sit at rest** on whichever host runs each command, protected by file permissions and
nothing more — the same standing as the admin token beside them.

# Why the world authorities are not signed by the installation one

They are three independent self-signed roots, not a hierarchy. Signing each world's authority
with the installation one would be conventional, would let the broker trust a single root
forever, and would make adding a world cost no restart at all. It was rejected for two reasons.

The first is that the installation key would then be able to mint an identity in *any* world —
one key that can speak for every society, which is the same collapse the per-world signing keys
already refuse. The second is that creating a world's authority would need that key present, so
onboarding a world could no longer happen on a host that infra is not on. That is the separation
`agora-infra-certs` exists to keep.

The cost is honest and worth stating plainly: **a new world requires a broker restart**, because
the trust bundle changes and SIGHUP does not reload TLS material. Adding an *agent* to an
existing world still costs nothing, since the authority is unchanged. And the coarse revocation
above is only possible because the bundle is a list — a hierarchy would take that away too.
