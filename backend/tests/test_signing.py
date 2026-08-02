"""Tests for Ed25519 signing + the co-signed valve-command verification."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agora import signing
from agora.clearing import Grant
from agora.executor import Executor, verify_command


def test_sign_verify_roundtrip():
    key = Ed25519PrivateKey.generate()
    data = b"hello"
    sig = signing.sign(key, data)
    assert signing.verify(key.public_key(), data, sig)


def test_wrong_key_fails():
    key = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    sig = signing.sign(key, b"hello")
    assert not signing.verify(other.public_key(), b"hello", sig)


def test_tampered_data_fails():
    key = Ed25519PrivateKey.generate()
    sig = signing.sign(key, b"hello")
    assert not signing.verify(key.public_key(), b"hello!", sig)


# --- the actuate boundary: pump verifies host + clearing ---------------------

def _signing_executor():
    host = Ed25519PrivateKey.generate()
    clearing = Ed25519PrivateKey.generate()
    captured = []
    exe = Executor(lambda t, p: captured.append((t, p)), host_key=host, clearing_key=clearing)
    return exe, captured, host.public_key(), clearing.public_key()


def _grant(jti="j1"):
    return Grant(sub="fern", scope="actuate:valve/fern", amount_l=0.4, debit=0.2, round_id="R-1", jti=jti)


def test_settled_command_is_co_signed_and_verifies():
    exe, captured, host_pub, clearing_pub = _signing_executor()
    exe.settle(_grant())
    _, payload = captured[0]
    assert "match_sig" in payload and "val_sig" in payload
    assert verify_command(payload, host_pub, clearing_pub)


def test_unsigned_command_is_rejected():
    exe = Executor(lambda t, p: None)  # no keys -> no signatures
    cmd = exe.command_for(_grant())
    from dataclasses import asdict
    host = Ed25519PrivateKey.generate().public_key()
    clearing = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(asdict(cmd), host, clearing)


def test_tampered_dose_is_rejected():
    exe, captured, host_pub, clearing_pub = _signing_executor()
    exe.settle(_grant())
    _, payload = captured[0]
    payload["ml"] = payload["ml"] + 500  # attacker bumps the dose
    assert not verify_command(payload, host_pub, clearing_pub)


def test_wrong_signer_is_rejected():
    exe, captured, host_pub, _ = _signing_executor()
    exe.settle(_grant())
    _, payload = captured[0]
    impostor = Ed25519PrivateKey.generate().public_key()
    assert not verify_command(payload, host_pub, impostor)  # clearing key is not the real one
