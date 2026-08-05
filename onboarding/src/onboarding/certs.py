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

**The broker's own certificate is NOT issued here.** Clients verify the broker, and the broker
serves every world — so its identity belongs to the *installation*, not to any world, and its
lifecycle is the infrastructure's: it may be deployed at a different time, on a different host,
by someone who has no copy of these worlds at all. Mixing the two would make onboarding a world
require write access to wherever the broker runs. See `onboarding/broker.py` (`agora-broker-cert`).

What crosses that boundary is one public file: this world's `ca.crt`, which the broker must be
given so it will trust the certificates issued below. Onboarding produces it; the infra side
consumes it. On a single host that is a file copy, and it is still two steps.

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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from agora.config import PROJECT_ROOT
from agora.genesis import world_dir

log = logging.getLogger("certs")

REPO_ROOT = PROJECT_ROOT.parent
CA_DAYS = 3650          # a world outlives its agents; reissuing the CA re-enrols everyone
LEAF_DAYS = 397         # the CA/Browser Forum's cap, and a habit worth keeping
RENEW_BEFORE_DAYS = 30  # reissue this far ahead, so a routine re-run is the cure


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


def _ca(dir_: Path, common_name: str, rotate: bool) -> tuple[Path, Path]:
    """This authority's cert and key, created if absent. Rotating one re-enrols everyone it
    signed for, so it is never done as a side effect."""
    cert_path, key_path = dir_ / "ca.crt", dir_ / "ca.key"
    if cert_path.exists() and key_path.exists() and not rotate and not _expiring(cert_path):
        return cert_path, key_path

    key = Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(_now() - dt.timedelta(minutes=5))  # tolerate a little clock skew
        .not_valid_after(_now() + dt.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, None)  # Ed25519 carries its own hash; passing one is an error
    )
    _write(key_path, key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), private=True)
    _write(cert_path, cert.public_bytes(serialization.Encoding.PEM), private=False)
    log.info("  authority %s", common_name)
    return cert_path, key_path


def _leaf(dir_: Path, stem: str, common_name: str, ca: tuple[Path, Path],
          server: bool, rotate: bool) -> bool:
    """Issue `<stem>.crt`/`.key` for this identity. Returns whether it wrote anything."""
    cert_path, key_path = dir_ / f"{stem}.crt", dir_ / f"{stem}.key"
    if not rotate and key_path.exists() and not _expiring(cert_path):
        return False

    ca_cert, ca_key = _load_ca(*ca)
    key = Ed25519PrivateKey.generate()
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
    cert = builder.sign(ca_key, None)
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


def issue_for_world(world: str, agent_ids, rotate: bool = False) -> None:
    """This world's authority, and a client certificate for each of its agents.

    The CN is the agent's world-qualified username, so the broker maps it straight onto the ACL
    that is already derived from the wiring.
    """
    from .mqtt import agent_username

    secrets = world_dir(world) / "secrets"
    ca = _ca(secrets, f"agora {world} CA", rotate)
    for agent_id in sorted(agent_ids):
        if _leaf(secrets, agent_id, agent_username(world, agent_id), ca,
                 server=False, rotate=rotate):
            log.info("  cert   %-14s CN=%s", agent_id, agent_username(world, agent_id))
