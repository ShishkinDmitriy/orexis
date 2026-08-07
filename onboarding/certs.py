"""A certificate authority per world, and a client certificate per agent.

**Why a CA per world, and not one for the installation.** The same argument that gives each world
its own signing keys: two worlds are two societies, and a certificate issued by one must not
authenticate into the other. A single installation CA would make `society-fern` and
`sensing-fern` mutually impersonable the moment both existed, which is exactly what the
world-qualified username already prevents.

**Why the CN is the username, exactly.** Mosquitto's `use_identity_as_username true` takes the
certificate's CN and uses it as the username for authorisation — so the ACL `agora-mqtt` already
derives from the wiring keeps working untouched, and there is no second mapping to drift. A
certificate is a *different way of proving who you are*, not a different notion of who you are.

**Agents only, deliberately.** A board deep-sleeps between readings and wakes for seconds; a full
TLS handshake on every wake costs radio time and battery on the most constrained thing in the
system. Boards keep their password on the plaintext listener, and the broker enforces the same
ACL for both — one authorisation model, two ways of authenticating. See
knowledge/domain/onboarding.md.

**The broker's certificate IS issued here, from this world's authority.** One broker per world
means the broker belongs to the world, so the world vouches for it — and an agent verifies its
broker with the same `ca.crt` that vouches for the agent itself. Nothing installation-wide is
involved in reaching the bus at all, which is what makes a world self-contained: its authority
signs both ends of every connection its members make.

**What is NOT issued here** is any *shared* service's certificate — Grafana's, and anything else
in `infra/`. Clients verify the broker, and the broker
serves every world — so its identity belongs to the *installation*, not to any world, and its
Those serve every world at once, so their identity belongs to the installation and their
lifecycle is the infrastructure's — possibly another host, certainly another schedule. See
`onboarding/infra_certs.py` (`agora-infra-certs`).

Nothing crosses between the two any more. When the broker was shared it needed a bundle of every
world's authority, rebuilt and reloaded whenever a world appeared; a broker that belongs to one
world trusts exactly one authority and never learns the others exist.

Certificates expire, which passwords did not. That is a real gain — it is the first thing here
that can be revoked — and a real new failure mode: an agent whose certificate lapsed stops
connecting and looks exactly like a process that went quiet. Re-running `agora-onboard` reissues
anything within `RENEW_BEFORE_DAYS` of expiry, so the routine cure is the routine command.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from agent.config import REPO_ROOT
from agent.genesis import world_dir

log = logging.getLogger("certs")

CA_DAYS = 3650          # a world outlives its agents; reissuing the CA re-enrols everyone
LEAF_DAYS = 397         # the CA/Browser Forum's cap, and a habit worth keeping
RENEW_BEFORE_DAYS = 30  # reissue this far ahead, so a routine re-run is the cure


def _new_key(browser_facing: bool):
    """Ed25519 between our own processes; ECDSA P-256 for anything a BROWSER must verify.

    Ed25519 is the better key and every client here speaks it — mosquitto, paho and curl all
    verify it without complaint. Browsers do not support Ed25519 certificates at all, and the
    failure is opaque from the other end: Firefox reports SSL_ERROR_NO_CYPHER_OVERLAP, which
    reads like a ciphersuite misconfiguration rather than "your certificate uses an algorithm I
    will not accept".

    It applies to the whole chain, not just the leaf: an ECDSA certificate signed by an Ed25519
    authority still asks the browser to verify an Ed25519 signature.
    """
    return ec.generate_private_key(ec.SECP256R1()) if browser_facing else Ed25519PrivateKey.generate()


def _sign_with(key):
    """Ed25519 carries its own hash and rejects one; ECDSA requires it."""
    return None if isinstance(key, Ed25519PrivateKey) else hashes.SHA256()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _write(path: Path, data: bytes, private: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600 if private else 0o644)


def _load_ca(cert_path: Path, key_path: Path):
    return (
        x509.load_pem_x509_certificate(cert_path.read_bytes()),
        serialization.load_pem_private_key(key_path.read_bytes(), password=None),
    )


def _expiring(cert_path: Path) -> bool:
    """True if it is absent, unreadable, or close enough to expiry to reissue now."""
    if not cert_path.exists():
        return True
    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    except ValueError:
        return True  # unreadable is indistinguishable from absent, and reissuing is safe
    return cert.not_valid_after_utc - _now() < dt.timedelta(days=RENEW_BEFORE_DAYS)


def _ca(dir_: Path, common_name: str, rotate: bool,
        browser_facing: bool = False) -> tuple[Path, Path]:
    """This authority's cert and key, created if absent. Rotating one re-enrols everyone it
    signed for, so it is never done as a side effect."""
    cert_path, key_path = dir_ / "ca.crt", dir_ / "ca.key"
    if cert_path.exists() and key_path.exists() and not rotate and not _expiring(cert_path):
        return cert_path, key_path

    key = _new_key(browser_facing)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(_now() - dt.timedelta(minutes=5))  # tolerate a little clock skew
        .not_valid_after(_now() + dt.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, _sign_with(key))
    )
    _write(key_path, key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), private=True)
    _write(cert_path, cert.public_bytes(serialization.Encoding.PEM), private=False)
    log.info("  authority %s", common_name)
    return cert_path, key_path


def _leaf(dir_: Path, stem: str, common_name: str, ca: tuple[Path, Path],
          server: bool, rotate: bool, browser_facing: bool = False) -> bool:
    """Issue `<stem>.crt`/`.key` for this identity. Returns whether it wrote anything."""
    cert_path, key_path = dir_ / f"{stem}.crt", dir_ / f"{stem}.key"
    if not rotate and key_path.exists() and not _expiring(cert_path):
        return False

    ca_cert, ca_key = _load_ca(*ca)
    key = _new_key(browser_facing)
    usage = x509.ExtendedKeyUsage(
        [x509.oid.ExtendedKeyUsageOID.SERVER_AUTH] if server
        else [x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]
    )
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(_now() - dt.timedelta(minutes=5))
        .not_valid_after(_now() + dt.timedelta(days=LEAF_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(usage, critical=False)
    )
    if server:
        # Agents reach the broker by the name the WORLD states, so that name must be in the
        # certificate or every client rejects it. localhost covers the host-networked case.
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name), x509.DNSName("localhost")]),
            critical=False,
        )
    cert = builder.sign(ca_key, _sign_with(ca_key))
    _write(key_path, key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), private=True)
    _write(cert_path, cert.public_bytes(serialization.Encoding.PEM), private=False)
    return True


def agent_cert_files(world: str, agent_id: str) -> tuple[Path, Path]:
    d = world_dir(world) / "secrets"
    return d / f"{agent_id}.crt", d / f"{agent_id}.key"


def world_ca(world: str) -> Path:
    return world_dir(world) / "secrets" / "ca.crt"


def issue_for_world(world: str, agent_ids, rotate: bool = False,
                    broker_host: str | None = None) -> None:
    """This world's authority, its broker's certificate, and one per agent.

    The CN is the agent's world-qualified username, so the broker maps it straight onto the ACL
    that is already derived from the wiring.
    """
    from .mqtt import agent_username

    secrets = world_dir(world) / "secrets"
    ca = _ca(secrets, f"agora {world} CA", rotate)
    if broker_host and _leaf(secrets, "broker", broker_host, ca, server=True, rotate=rotate):
        # Signed by the world, for the world. An agent verifies its broker with the same
        # authority that vouches for the agent — one trust root per society, both directions.
        log.info("  cert   broker         CN=%s", broker_host)
    for agent_id in sorted(agent_ids):
        if _leaf(secrets, agent_id, agent_username(world, agent_id), ca,
                 server=False, rotate=rotate):
            log.info("  cert   %-14s CN=%s", agent_id, agent_username(world, agent_id))
