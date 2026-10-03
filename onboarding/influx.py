"""orexis-influx — give each agent a bucket of its own per purpose, and a token that opens only it.

  orexis-influx society        -> per agent in world/society, a history bucket, a metrics bucket where
                                  the world is monitored, and a token scoped to each

The operator's half of the series store; `agent/series.py`, the sink, is the agent's half. They
are separate modules because they are separate privileges: a sink holds one token for one
bucket, this holds the admin token that opens every bucket, and nothing that runs inside an
agent may import this.

**Per purpose** (knowledge/domain/kernel/series.md). A series store is told to an agent for a
purpose — history and metrics — in the store the installation says `onboarding:serves` it, so the
credential file names its purpose, `secrets/influx-<purpose>-<agent>.env`, and says
`INFLUX_<PURPOSE>_BUCKET` and `INFLUX_<PURPOSE>_TOKEN`; `orexis-compose` adds where the store is
under the same purpose. The history bucket keeps the name the one bucket had, `<world>-<agent>`, so
a history begun before purposes continues in it. A grant made before purposes — its authorization
described without one, its file `influx-<agent>.env` — is replaced by the history grant and its
file removed, since its token opens the same bucket and an orphaned token is a grant nobody holds
on purpose.

**Metrics are a bucket of their own, `<world>-<agent>-metrics`**, and not a measurement in the
history bucket. Three things differ, each by the bucket: how long a point is kept — history is the
record and keeps everything, while metrics are the admins' figures, read over hours and days, and
the installation lets them go after `onboarding:retentionDays`; what the agent may do there — it
reads its own past and never its metrics, so the metrics token writes and nothing else; and the
measurement names, which are a property's local name in history and a metric's in metrics, and
could not collide once they were in two buckets.

**Metrics are minted only where the world is monitored** (`installation.purposes`): its own
deployment graph says `onboarding:monitored true`. A world that stops saying it has its agents'
metrics grants revoked and their credential files removed on the next run, since a grant nobody is
told of is a grant nobody holds on purpose; the bucket is left for its retention to empty.

**Why per agent.** Before this, one bucket and one admin token were handed to every container,
so `fern` could not read `tomato`'s beliefs but could read its entire moisture history — the
raw state that the band-only disclosure on the bus exists to withhold. Influx 2.x permissions
are per bucket, not per tag, so isolation means a bucket each. See
knowledge/decisions/series-and-bus-isolation.md.

**Why every agent, and not only the ones that observe.** Deciding here which capabilities write
history would put that knowledge in a second place, beside the world that already implies it,
and the two would drift. A bucket nobody writes to grants nobody anything, so uniform is both
simpler and safer than clever.

**Why the name is not in the world.** A topic is a rendezvous — two parties must name the same
string or they never meet — so topics are ratified in the world's society graph. A bucket has exactly one
writer and nobody to agree with, which makes it deployment, like the store's URL. The agent is
never told the convention: it reads the name out of the credential file mounted for it, so no
process builds a destination from a naming rule.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import dotenv_values
from influxdb_client import Authorization, BucketRetentionRules, InfluxDBClient, Permission, \
    PermissionResource

from agent.series import HISTORY, METRICS, PURPOSES

from . import compose, installation
from .worlds import REPO_ROOT
from .worlds import shown, world_dir, worlds

log = logging.getLogger("influx")

ADMIN_ENV = REPO_ROOT / "infra" / "secrets" / "admin.env"


class AdminError(RuntimeError):
    """The operator's environment is not set up. Not an agent's problem — nothing is running."""


class StoreUnreachable(RuntimeError):
    """A store the installation names did not answer a ping. Raised by the report alone, which must
    go on without it; a grant refuses through the client's own errors, as it did."""


def bucket_name(world: str, agent_id: str, purpose: str = HISTORY) -> str:
    """The convention, and the only place it is written down.

    Qualified by world because bucket names are org-global: two worlds each holding a `fern`
    would otherwise share one history, and a simulation would write into the record of a real
    plant. A world cannot check this for itself — it is not allowed to know other worlds exist
    — so the convention has to make the collision impossible rather than detectable.

    History keeps the name the one bucket had, so a record begun before purposes goes on in it;
    every other purpose is suffixed with its own name.
    """
    return f"{world}-{agent_id}" if purpose == HISTORY else f"{world}-{agent_id}-{purpose.lower()}"


def credential_file(world: str, agent_id: str, purpose: str = HISTORY) -> Path:
    """Where the agent's credential for `purpose` is minted: its own, named for what it is for, by
    the name `orexis-compose` mounts."""
    return world_dir(world) / "secrets" / compose.series_credential(agent_id, purpose)


def _unpurposed_file(world: str, agent_id: str) -> Path:
    """Where a grant made before purposes was written — removed when the history grant replaces it."""
    return world_dir(world) / "secrets" / f"influx-{agent_id}.env"


def _description(world: str, agent_id: str, purpose: str | None) -> str:
    """How a grant is described in the store — the one place its principal is written down there,
    since a token's own text says nothing of whose it is."""
    return f"orexis {world}/{agent_id}" + (f" {purpose.lower()}" if purpose else "")


def _principal_of(description: str, world: str) -> str | None:
    """The agent a grant's description names, where it is one of this world's; the metrics grant
    says `orexis <world>/<agent> metrics`, and one made before purposes `orexis <world>/<agent>`."""
    head = f"orexis {world}/"
    if not description.startswith(head):
        return None
    return description[len(head):].split(" ", 1)[0]


def _admin_token() -> str:
    """The one credential that opens every bucket, read from its own file.

    Deliberately not from any document, nor from anything handed to every agent container: a
    token held by every agent would make scoped tokens theatre, and one in a graph would persist
    wherever the graph is copied.
    """
    if not ADMIN_ENV.exists():
        raise AdminError(
            f"{ADMIN_ENV.relative_to(REPO_ROOT)} does not exist — copy infra/admin.env.example "
            "to it and fill it in. It holds the admin token, which no agent may ever hold."
        )
    token = dotenv_values(ADMIN_ENV).get("INFLUX_ADMIN_TOKEN")
    if not token:
        raise AdminError(f"{ADMIN_ENV.relative_to(REPO_ROOT)} declares no INFLUX_ADMIN_TOKEN")
    return token


def _write_credential(path: Path, agent_id: str, purpose: str, bucket: str, token: str) -> None:
    """One agent's whole relationship with the series store for one purpose, in two lines.

    Mounted into that container and no other. The sink reads these two out of its environment
    beside the url and the organisation `orexis-compose` writes under the same purpose.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# GENERATED by `orexis-influx` — this agent's {purpose.lower()} bucket, and a token that opens only it.\n"
        f"# Mounted into agent-{agent_id} alone. Never commit.\n"
        f"INFLUX_{purpose}_BUCKET={bucket}\n"
        f"INFLUX_{purpose}_TOKEN={token}\n"
    )
    path.chmod(0o600)


#  WHAT AN AGENT MAY DO WITH EACH PURPOSE'S BUCKET. History is read as well as written: an agent that
#  forecasts reads its OWN past, and it is the neighbour's past this exists to deny, which the
#  resource id does. Metrics are written and never read by the agent — Grafana reads them with a
#  token of its own — so their grant is write alone.
ACTIONS = {HISTORY: ("read", "write"), METRICS: ("write",)}


def provision(world: str, rotate: bool = False) -> None:
    """Bring the store into line with the world: for every purpose its agents are told of, a bucket
    and a scoped token per agent, in the series store the installation says serves it
    (`infra/installation.ttl`); and for a purpose they are not told of, no grant left standing."""
    agents = compose.agent_ids(world)
    if not agents:
        raise SystemExit(f"orexis-influx: world {world!r} declares no agents")
    told = installation.purposes(world)
    for purpose in PURPOSES:
        if purpose in told:
            _provision(world, agents, purpose, rotate)
        else:
            _withdraw(world, agents, purpose)


def _withdraw(world: str, agents: list[str], purpose: str) -> None:
    """No grant for `purpose` to any of `agents`: each credential file removed, and each token revoked
    in the store serving the purpose, where one does. The buckets stay, for their retention to empty."""
    for agent_id in agents:
        path = credential_file(world, agent_id, purpose)
        if path.exists():
            path.unlink()
            log.info("  %s credential of agent-%s removed — the world is told of no %s store",
                     purpose.lower(), agent_id, purpose.lower())
    if (where := installation.served(purpose)) is None:
        return
    url, org = where
    with InfluxDBClient(url=url, token=_admin_token(), org=org) as client:
        auth_api = client.authorizations_api()
        existing = {a.description: a for a in auth_api.find_authorizations() or [] if a.description}
        for agent_id in agents:
            held = existing.get(_description(world, agent_id, purpose))
            if held:
                auth_api.delete_authorization(held)
                log.info("  bucket %-32s grant revoked — the world is not %s", bucket_name(world, agent_id, purpose),
                         "monitored" if purpose == METRICS else f"told of {purpose.lower()}")


def _provision(world: str, agents: list[str], purpose: str, rotate: bool) -> None:
    url, org = installation.series(purpose)
    days = installation.retention(purpose)
    with InfluxDBClient(url=url, token=_admin_token(), org=org) as client:
        organisation = next(
            (o for o in client.organizations_api().find_organizations() if o.name == org), None)
        if organisation is None:
            raise AdminError(
                f"no organization {org!r} at {url} — is `cd infra && podman compose up -d` done?")

        buckets_api = client.buckets_api()
        auth_api = client.authorizations_api()
        existing = {a.description: a for a in auth_api.find_authorizations() or []
                    if a.description}
        #  KEPT AS LONG AS THE INSTALLATION SAYS for the purpose, and for ever where it says nothing:
        #  history is the record, and retention is an operator's decision, not a default.
        kept = BucketRetentionRules(type="expire", every_seconds=(days or 0) * 86400)

        for agent_id in agents:
            name = bucket_name(world, agent_id, purpose)
            bucket = buckets_api.find_bucket_by_name(name)
            if bucket is None:
                bucket = buckets_api.create_bucket(bucket_name=name, org_id=organisation.id,
                                                   retention_rules=kept)
                log.info("  bucket %-32s created", name)
            elif days is not None and [r.every_seconds for r in bucket.retention_rules or []] != [kept.every_seconds]:
                bucket.retention_rules = [kept]
                buckets_api.update_bucket(bucket=bucket)
                log.info("  bucket %-32s kept %d days, as the installation says", name, days)

            path = credential_file(world, agent_id, purpose)
            description = _description(world, agent_id, purpose)
            held = existing.get(description)
            #  A GRANT MADE BEFORE PURPOSES opens the history bucket under a description naming
            #  none; the history grant replaces it, and its file goes with its token.
            unpurposed = existing.get(_description(world, agent_id, None)) if purpose == HISTORY else None
            if unpurposed:
                auth_api.delete_authorization(unpurposed)
                _unpurposed_file(world, agent_id).unlink(missing_ok=True)
                log.info("  bucket %-32s the grant naming no purpose is replaced by history's", name)

            if held and path.exists() and not rotate:
                log.info("  bucket %-32s already granted", name)
                continue
            if held:
                # Influx returns a token's secret only when it is created, so an authorization
                # whose credential file has gone is unrecoverable rather than re-readable. The
                # honest repair is to replace it.
                auth_api.delete_authorization(held)
                log.info("  bucket %-32s token %s", name,
                         "rotated" if rotate else "replaced (credential file was missing)")

            resource = PermissionResource(id=bucket.id, org_id=organisation.id, type="buckets")
            auth = auth_api.create_authorization(authorization=Authorization(
                org_id=organisation.id, description=description,
                permissions=[Permission(action=action, resource=resource) for action in ACTIONS[purpose]]))
            _write_credential(path, agent_id, purpose, name, auth.token)
            if not held:
                log.info("  bucket %-32s granted to agent-%s (%s)", name, agent_id, ", ".join(ACTIONS[purpose]))

        #  GRAFANA'S TOKEN is org-wide, so it is minted once, in the store history is written to.
        if purpose == HISTORY:
            _grafana_token(auth_api, organisation, existing, rotate)


# ---------------------------------------------------------------- revocation and the report


def _revoke_grants(auth_api, world: str, principal: str) -> list[str]:
    """Delete every token the store holds for `principal` in this world, whatever its purpose, and
    answer the descriptions of those deleted. Buckets are not touched here or anywhere."""
    gone = []
    for auth in auth_api.find_authorizations() or []:
        if auth.description and _principal_of(auth.description, world) == principal:
            auth_api.delete_authorization(auth)
            gone.append(auth.description)
    return gone


def revoke(world: str, principal: str) -> None:
    """Take one agent's access to the series store away, by name, and KEEP its buckets.

    The token is the grant and it goes: deleted in every store the installation serves a purpose
    from, refused on the agent's very next request, and its credential files removed so no
    container is handed it again. The bucket is history — the record of what that agent observed
    and did while it was here — and history that was true stays true after the agent is gone;
    deleting it would be editing the record because its author left. A bucket nobody writes to
    costs nothing and grants nobody anything, which is also why a withdrawn metrics bucket is left
    for its retention to empty. Deleting one is the admin's act, with the admin's token, by hand.

    Explicit, never implicit: `orexis-onboard` reports a grant the wiring no longer implies and
    leaves it, since an agent absent from a world today may be back tomorrow, and re-granted it
    writes on in the bucket it had.
    """
    removed = []
    for path in [*(credential_file(world, principal, p) for p in PURPOSES), _unpurposed_file(world, principal)]:
        if path.exists():
            path.unlink()
            removed.append(path)
            log.info("  %-14s %s removed", principal, shown(path))
    gone: list[str] = []
    asked: set[tuple[str, str]] = set()
    for purpose in PURPOSES:
        where = installation.served(purpose)
        if where is None or where in asked:
            continue
        asked.add(where)
        url, org = where
        with InfluxDBClient(url=url, token=_admin_token(), org=org) as client:
            gone += _revoke_grants(client.authorizations_api(), world, principal)
    for description in gone:
        log.info("  %-14s token revoked (%s) — refused on its next request", principal, description)
    if not removed and not gone:
        raise SystemExit(f"orexis-influx: nothing to revoke — world {world!r} holds no credential file for "
                         f"{principal!r} and no store holds a grant described as {_description(world, principal, None)!r}")
    log.info("  %-14s bucket %s kept — history that was true stays; deleting it is the admin's act, by hand",
             principal, bucket_name(world, principal))


def stale_files(world: str) -> list[str]:
    """Credential files under this world's `secrets/` for the series store whose agent the world no
    longer states. Report only."""
    roster = set(compose.agent_ids(world))
    secrets = world_dir(world) / "secrets"
    if not secrets.is_dir():
        return []
    found = []
    for path in sorted(secrets.glob("influx-*.env")):
        who = path.name[len("influx-"):-len(".env")]
        for purpose in PURPOSES:
            who = who.removeprefix(f"{purpose.lower()}-")
        if who not in roster:
            found.append(f"secrets/{path.name} — no agent {who!r} in the world; "
                         f"`orexis-influx {world} --revoke {who}` takes it back and keeps the bucket")
    return found


def stale_grants(world: str) -> list[str]:
    """What the series stores hold for this world that its roster no longer implies: a token
    described as an agent's the world does not state, and a bucket named for one. Asks every store
    the installation serves a purpose from, with the admin token, which is why `orexis-onboard`
    runs this where it can and says so where it cannot. Report only: a token here is taken back by
    `--revoke`, and a bucket by nobody but the admin, by hand."""
    roster = set(compose.agent_ids(world))
    implied = {bucket_name(world, a, p) for a in roster for p in PURPOSES}
    found = []
    asked: set[tuple[str, str]] = set()
    for purpose in PURPOSES:
        where = installation.served(purpose)
        if where is None or where in asked:
            continue
        asked.add(where)
        url, org = where
        with InfluxDBClient(url=url, token=_admin_token(), org=org) as client:
            #  PINGED FIRST: the client's ping answers False on a store that is down, where every
            #  other call raises the transport's own error, which this tree does not import.
            if not client.ping():
                raise StoreUnreachable(f"{url} did not answer")
            for auth in client.authorizations_api().find_authorizations() or []:
                who = _principal_of(auth.description or "", world)
                if who is not None and who not in roster:
                    found.append(f"token {auth.description!r} at {url} — no agent {who!r} in the world; "
                                 f"`orexis-influx {world} --revoke {who}` deletes it")
            #  A BUCKET IS THIS WORLD'S BY ITS PREFIX, which is the convention `bucket_name` writes
            #  and the only mark a bucket carries; a world whose name is another's prefix would be
            #  read as owning the other's buckets, and no shipped world is.
            for bucket in client.buckets_api().find_buckets_iter():
                if bucket.name.startswith(f"{world}-") and bucket.name not in implied:
                    found.append(f"bucket {bucket.name} at {url} — named for no agent in the world; kept, since "
                                 "history that was true stays — delete it with the admin token, by hand, if you mean to")
    return found


GRAFANA_ENV = REPO_ROOT / "infra" / "secrets" / "grafana.env"
GRAFANA_DESC = "orexis grafana (read-only, all buckets)"


def _grafana_token(auth_api, organisation, existing, rotate: bool) -> None:
    """The dashboard's own credential: read, every bucket, nothing else.

    Grafana is the one reader that legitimately spans the whole society — it is the operator's
    view, not a member's view of its neighbours — so this is deliberately NOT scoped to one
    bucket. What it does remove is everything else the admin token could do: writing points,
    deleting buckets, and minting further tokens. A dashboard reachable from the network should
    not be able to hand out credentials.

    Org-scoped rather than a list of bucket ids, so a world onboarded tomorrow is visible without
    re-running this. That is the one place where "all buckets" is the right grant.
    """
    held = existing.get(GRAFANA_DESC)
    if held and GRAFANA_ENV.exists() and not rotate:
        log.info("  grafana%-23s already granted", "")
        return
    if held:
        auth_api.delete_authorization(held)

    auth = auth_api.create_authorization(authorization=Authorization(
        org_id=organisation.id,
        description=GRAFANA_DESC,
        permissions=[Permission(action="read",
                                resource=PermissionResource(org_id=organisation.id,
                                                            type="buckets"))]))
    GRAFANA_ENV.parent.mkdir(parents=True, exist_ok=True)
    GRAFANA_ENV.write_text(
        "# GENERATED by `orexis-influx` — Grafana's datasource credential.\n"
        "# Read-only across every bucket. NOT the admin token: a dashboard on the network must\n"
        "# not be able to write series or mint credentials.\n"
        f"INFLUX_GRAFANA_TOKEN={auth.token}\n")
    GRAFANA_ENV.chmod(0o600)
    log.info("  grafana%-23s read-only token %s", "", "rotated" if held else "granted")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-influx",
        description="Give each of a world's agents its own bucket and a token scoped to it.")
    p.add_argument("world",
                   help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--rotate", action="store_true",
                   help="replace every token even if one is already held")
    p.add_argument("--revoke", metavar="PRINCIPAL",
                   help="delete ONE agent's tokens, by its id, remove its credential files, and grant "
                        "nothing else. Its buckets are KEPT: they are history. Never implicit — "
                        "`orexis-onboard` only reports a grant the wiring no longer implies.")
    args = p.parse_args()
    log.info("world %s", args.world)
    try:
        if args.revoke:
            revoke(args.world, args.revoke)
        else:
            provision(args.world, rotate=args.rotate)
    except AdminError as exc:
        raise SystemExit(f"orexis-influx: {exc}")


if __name__ == "__main__":
    main()
