"""What a running series store does with a token scoped to one bucket.

The twin of `test_bus_acl_runtime.py`, for the other shared service.
`backend/tests/test_isolation.py` checks what `orexis-influx` *decides* — a bucket each, names
that cannot collide across worlds. This file checks what InfluxDB then *enforces*, which is the
part the whole design rests on and which no amount of reading the credential files can establish.
That split is why it lives here and not with the unit tests: it is a contract with this
infrastructure, and it says nothing at all without a store running.

The claim under test is the one in the decision record: an agent may read and write its own
history and is refused its neighbour's. That is a property of Influx's permission model, not of
anything Orexis computes, so it belongs here and it is worth re-proving whenever the store is
upgraded — change the image in `infra/compose.yaml`, re-run this file, and see.

Run it deliberately, with infra up:

    pytest infra -q

It **skips** rather than fails without a store or an admin token. Nothing here touches a real
agent's bucket: the tests mint their own throwaway buckets and tokens through the admin API and
remove them again, whatever the outcome.

See knowledge/decisions/series-and-bus-isolation.md.
"""

from __future__ import annotations

import uuid

import pytest

from onboarding import influx as influx_admin
from agent.config import env

influxdb_client = pytest.importorskip("influxdb_client")

from influxdb_client import Authorization, InfluxDBClient, Permission, PermissionResource, Point
from influxdb_client.client.write_api import SYNCHRONOUS


@pytest.fixture(scope="module")
def admin():
    """The operator's client. Everything a test needs to set up is created through this."""
    try:
        token = influx_admin._admin_token()
    except influx_admin.AdminError as exc:
        pytest.skip(str(exc))
    url, org = env("INFLUX_URL", "http://localhost:8086"), env("INFLUX_ORG", "orexis")
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        if not client.ping():
            pytest.skip(f"no series store at {url} — bring infra up to run these")
    except Exception:
        pytest.skip(f"no series store at {url} — bring infra up to run these")
    organisation = next(
        (o for o in client.organizations_api().find_organizations() if o.name == org), None)
    if organisation is None:
        pytest.skip(f"no organization {org!r} at {url}")
    yield client, organisation, org
    client.close()


class Grant:
    """One throwaway bucket and a token that opens only it — an agent's whole relationship
    with the store, in the shape `orexis-influx` creates it."""

    def __init__(self, bucket, token):
        self.bucket = bucket
        self.token = token


@pytest.fixture
def grants(admin):
    """Two of them, so 'its own' and 'a neighbour's' are both real and neither is an agent's."""
    client, organisation, org = admin
    buckets_api, auth_api = client.buckets_api(), client.authorizations_api()
    made, url = [], env("INFLUX_URL", "http://localhost:8086")

    def mint() -> Grant:
        name = f"orexis-test-{uuid.uuid4().hex[:10]}"
        bucket = buckets_api.create_bucket(bucket_name=name, org_id=organisation.id)
        resource = PermissionResource(id=bucket.id, org_id=organisation.id, type="buckets")
        auth = auth_api.create_authorization(authorization=Authorization(
            org_id=organisation.id, description=f"orexis test {name}",
            permissions=[Permission(action="read", resource=resource),
                         Permission(action="write", resource=resource)]))
        made.append((bucket, auth))
        return Grant(name, auth.token)

    mint.url, mint.org = url, org
    try:
        yield mint
    finally:
        for bucket, auth in made:
            try:
                auth_api.delete_authorization(auth)
            except Exception:
                pass  # a test may have revoked it already — that is one of the things tested
            buckets_api.delete_bucket(bucket)


def _as(grant: Grant, url: str, org: str) -> InfluxDBClient:
    return InfluxDBClient(url=url, token=grant.token, org=org)


def _write(client, bucket, value):
    client.write_api(write_options=SYNCHRONOUS).write(
        bucket=bucket, record=Point("soil_moisture").tag("plant", "probe").field("value", value))


def _read(client, bucket):
    rows = client.query_api().query(
        f'from(bucket:"{bucket}") |> range(start:-1h) '
        f'|> filter(fn:(r) => r._measurement == "soil_moisture") |> last()')
    return [r.records[0].get_value() for r in rows]


def test_reports_which_store_these_results_are_about(admin):
    """Says what was actually tested, and asserts nothing about which version that is.

    Same reasoning as the broker's: this file exists to be re-run after an upgrade, so the
    version is reported rather than pinned. A test that had to be edited to match
    `infra/compose.yaml` would fail for a version change instead of a behaviour change.
    """
    client, _, _ = admin
    print(f"\nseries store under test: InfluxDB {client.health().version}")


def test_an_agent_reads_and_writes_its_own_bucket(admin, grants):
    """Read as well as write: an agent that forecasts reads its own past. It is the neighbour's
    past this design withholds, never the agent's own."""
    _, _, org = admin
    mine = grants()
    with _as(mine, grants.url, org) as client:
        _write(client, mine.bucket, 0.42)
        assert _read(client, mine.bucket) == [0.42]


def test_an_agent_is_refused_its_neighbours_bucket(admin, grants):
    """The claim the whole feature rests on.

    Before this, one admin token was handed to every container, so `fern` could not read
    `tomato`'s beliefs but could read its entire moisture history — the raw state the band-only
    disclosure on the bus exists to withhold. Influx permissions are per bucket, not per tag,
    which is why isolation had to mean a bucket each.
    """
    _, _, org = admin
    mine, neighbour = grants(), grants()
    with _as(neighbour, grants.url, org) as owner:
        _write(owner, neighbour.bucket, 0.99)  # something worth stealing

    with _as(mine, grants.url, org) as client:
        with pytest.raises(Exception) as write_refused:
            _write(client, neighbour.bucket, 0.1)
        assert getattr(write_refused.value, "status", None) == 403, (
            f"writing a neighbour's bucket must be forbidden, got {write_refused.value!r}")

        with pytest.raises(Exception) as read_refused:
            _read(client, neighbour.bucket)
        # 404, not 403, and the difference is worth keeping: the token cannot even establish
        # that the other bucket exists.
        assert getattr(read_refused.value, "status", None) == 404, (
            f"reading a neighbour's bucket must be refused, got {read_refused.value!r}")


def test_revoking_a_token_takes_effect_at_once(admin, grants):
    """No reload, no restart, and no grace period — unlike the bus, which needs a SIGHUP.

    Influx checks the token on every request, so `orexis-influx --rotate` (which replaces the
    authorization) locks the old credential out immediately. What it does NOT do is re-key a
    running agent: the agent was handed its token in an env_file at container creation and holds
    it in memory, so a rotation takes that agent off the store until it is recreated. Rotation is
    a revocation, not a re-key. See knowledge/runbooks/run-a-world.md.
    """
    client, _, org = admin
    mine = grants()
    with _as(mine, grants.url, org) as agent:
        _write(agent, mine.bucket, 0.5)
        assert _read(agent, mine.bucket) == [0.5]

        held = next(a for a in client.authorizations_api().find_authorizations()
                    if a.description == f"orexis test {mine.bucket}")
        client.authorizations_api().delete_authorization(held)

        with pytest.raises(Exception) as refused:
            _write(agent, mine.bucket, 0.6)
        assert getattr(refused.value, "status", None) == 401, (
            f"a revoked token must be refused on the next request, got {refused.value!r}")
