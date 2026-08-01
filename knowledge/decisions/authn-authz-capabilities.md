---
type: Decision
title: Identity, authorization, and settlement as self-verifying artifacts
description: Certificates for who-you-are, signed capability grants (JWT) for what-you-may-do-now; revoke only on provable violation.
status: accepted
stage: v1
tags: [security, identity, authorization, jwt, capabilities, pki]
timestamp: 2026-08-01T00:00:00Z
---

# Context

Agents are self-interested and may lie or be injected, yet the system must stay correct
([trust-boundary](/decisions/trust-boundary.md)). We want the honesty guarantees without
leaning on mandatory, always-on central infrastructure. The unlock: express both *who an
agent is* and *what it may do* as **signed artifacts an agent carries**, so verification is
local and needs no hot-path lookup.

# Decision — two self-verifying layers

Split authentication from authorization; make each a signed artifact verifiable against a
public key alone.

- **AuthN — certificate = *who you are*.** Durable identity. Sovereign-issued. Answers "is
  this really Fern, and is that identity still valid."
- **AuthZ — capability grant = *what you may do now*.** Ephemeral, scoped, expiring.
  Issued per round by [clearing](/domain/clearing.md) after the
  [constitution](/domain/constitution.md) check. Answers "may Fern receive 2 L this round."

Both are checked *locally* by any verifier holding the issuer's public key. No registry is
consulted on the hot path — the artifact carries its own proof. This is what keeps identity
and authorization off the list of mandatory always-on services.

# Certificates (identity)

- **Provisioned before, in v1.** The system is closed — three sovereign-chartered agents.
  The certificate is part of the [charter](/domain/agent.md): creating an agent atomically
  issues its cert (signs its public key + plant URI) and its endowment. There is no open
  registration desk in v1.
- **Registry tracks existence + validity, never liveness.** Two states only: *issued* and
  *revoked*. "Who is online right now" is **not** the registry's job — presence is emergent
  from the MQTT bus (a round broadcasts; live, solvent agents answer; a dead agent simply
  doesn't bid). Fusing identity with presence would turn the identity anchor into a
  stateful, always-on service — the very thing we avoid.
- **Sybil resistance is the point (v2 seam).** Open self-registration is a v2 concern and is
  *gated issuance*, not free: a newcomer gets a cert **plus a broke endowment** and accrues
  reputation. The cost of joining is what defeats whitewashing (a revoked agent re-joining as
  someone new). See the Sybil item in [roadmap](/decisions/roadmap.md).

# Revocation

- **Only on mechanically-provable violations** — forged provenance, citing a triple not in
  `:attested`, bidding above wallet, flooding the bus. Never on *judged intent*: bluffing and
  aggressive-but-legal strategy are undecidable to tell from malice, and a judge that revokes
  on them reintroduces the adjudicator [trust-boundary](/decisions/trust-boundary.md)
  forbids.
- **You already have two judge-free revocations.** The *leash* revokes a specific claim
  per-message (uncitable → rejected; see [belief-base](/domain/belief-base.md)); *insolvency*
  revokes an agent economically (broke → can't bid; see [wallet](/domain/wallet.md)). Both
  are per-action and preventive, strictly better than reactive cert-revocation for the powers
  that matter.
- **Grants self-expire; only certs need a list.** Round-scoped grants die at round end, so
  grant "revocation" is free. Only the durable cert needs an explicit, published, signed
  **revocation list**.

# Capability grants (authorization) as the auction result

The output of [clearing](/domain/clearing.md) is modeled explicitly as a signed capability —
concretely a **JWT (JWS)**:

```json
{
  "iss": "clearing",                 // issuer (after constitution check)
  "sub": "tomato",                   // who won
  "aud": "trusted-executor",         // who honors it
  "scope": "actuate:valve/tomato",   // what
  "amount_l": 2,                     // water leg
  "debit": 38,                       // credit leg
  "round": "R-2026-08-01T10:00",     // binds to this round
  "jti": "a3f…",                     // anti-replay id
  "exp": 1754040300                  // end of round R
}
```

- **Who bears the token matters.** For the **irreversible** water leg the grant flows
  **clearing → trusted executor** internally; the agent gets a *copy as a receipt* — proof of
  allocation, **not** a valve-trigger it redeems. Agent-borne tokens are only for
  **reversible** scopes (e.g. auction participation, premium-API access) and must be
  **bound to the agent's cert** (sender-constrained) so a bearer token can't be stolen and
  replayed on the shared bus.
- **Settlement authorizes; the trusted core performs.** The JWT *represents* the trade;
  clearing debits the wallet (credit leg) and the executor opens the valve (water leg). A
  settlement token **must be single-use** — plain JWTs are replayable bearer tokens, so the
  executor tracks `jti` (per round, bounded) and checks `round`, or the same win settles
  twice (double-spend).
- **The settlement token is a signature chain, not one signature.** The host runs the
  auction but does not get to conjure obligations. So the token carries: each participant's
  **order_sig** (a bid or ask = consent + solvency/availability), the host's **match_sig**
  (the scarce side proposing the trade), and clearing's **val_sig** (integrity notarization).
  The executor honors only a fully-signed token. This is what stops a host fabricating a
  counterparty's obligation or shill-bidding — it can neither sign as another agent nor
  out-mint its wallet. See [clearing-as-validator](/decisions/clearing-as-validator.md).

# Cryptographic stance (this *is* the trust boundary)

- **Asymmetric signing** (ES256 / EdDSA): clearing holds the private key, everyone verifies
  with the public key. Nobody but clearing can mint a grant — so **clearing's private key is
  the mint authority**, which is exactly why it stays in trusted infrastructure.
- **Never `alg: none`, never HMAC/shared-secret** — with a shared secret, any verifier could
  forge grants, handing every agent the mint. The classic JWT footgun.
- Public keys (CA + clearing) live as constants alongside the threshold in the T-Box; the
  cert revocation list is small and published. Neither sits on the hot path.

# Why this fits the whole design

- **AuthN/AuthZ = durable/ephemeral = the powers-vs-social line.** A valid cert **never**
  unlocks attest/mint/actuate; those stay structurally denied. The cert governs the social
  (reversible) layer; grants govern per-round authorization; the three powers stay in
  infrastructure regardless.
- **Self-verifying artifacts = no mandatory hot-path infra**, which is the property we've
  been optimizing toward: authority travels in the token, not in a service you must keep up.

# Seam for v2

Open, gated registration (naturalize + broke endowment); reputation attached to the durable
cert identity. See [roadmap](/decisions/roadmap.md).
