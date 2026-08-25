---
type: Domain Concept
title: Wallet
description: >-
  One budget per agent for both water and thinking. What is BUILT is a balance the bidder
  self-reports and clearing checks a line against; what is DESIGNED and not built is the
  ledger that would make that check mean something, the periodic allowance, and metering for
  thought. The three are marked apart here, because a reader who believes solvency is enforced
  would be wrong about the one thing in this project with real money-like consequences.
---

# What it is

One budget per agent, paying for **both** water and thinking. See
[single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md).

**Read the status column before building on any of it.** More of this concept is designed than
is built, and the gap is in the security-critical direction.

| | status |
|---|---|
| a balance exists and a bid carries it | **built** |
| clearing refuses a line the balance cannot pay | **built** — but see below |
| the balance is trustworthy | **not built** — it is self-reported |
| a periodic allowance is minted | **not built** |
| thinking is metered and debited | **not built** |

# Two conservation laws (deliberately different)

- **Water** — hard-conserved, zero-sum. One tank, fixed litres. The
  [constitution](/domain/constitution.md)'s physical law, and it *is* enforced: conservation is
  one of the five things [clearing](/domain/clearing.md) validates.
- **Credits** — NOT zero-sum by design. The intent is that they are minted fresh each window as
  a periodic **allowance**, spent-to-void rather than transferred, which is what would prevent
  permanent losers and kill Sybil swarms — newcomers join broke and accrue, nobody's credits are
  seized. **None of that is implemented.** There is no minting, no window, no allowance, and no
  ledger; an opening balance is authored at genesis and moves only as an agent's own belief.

# Solvency is checked, and the number it is checked against is untrusted

This is the one to understand, because half of it works.

`packages/capability/market/clearing.py` genuinely refuses a trade whose buyer cannot pay its line — solvency is one
of the five checks, beside identity, order-consistency, conservation and the constitution. What
it checks against is `MarketState.wallets`, and `packages/capability/market/hosting.py` fills
that from the `balance` field **the bidders themselves put in their bids**:

> Balances are SELF-REPORTED by the bidders and therefore untrusted. Clearing is supposed to
> check solvency against its own ledger; that ledger does not exist yet, and this is the honest
> stand-in until it does — recorded rather than hidden.

So an agent that overstates its balance is not caught by anything. The mechanism is sound and the
input is not, which is a different thing from either working or missing.

**The ledger is the piece that would close it**, and it is the one irreducible trusted thing this
architecture admits to needing — see
[thin-trusted-infra](/decisions/thin-trusted-infra.md), which thins the currency power as far as
it goes and stops exactly here, and
[agent-centric-epistemics](/decisions/agent-centric-epistemics.md), whose §4 records it as not
yet clearing-authored. `market:` states the intent on the term itself: the opening balance's
comment reads *"the authoritative running balance is the mint's, never a self-report"*, which is
a statement about where this is going rather than where it is.

# Bid

Deterministic willingness-to-pay from a value model over its **sensed** moisture, target,
evaporation and forecast — computed as a **function of unmet demand**. Priced in euros as a
*unit of account* (water has a real €/L cost); real money never moves. See
[deterministic-bid](/decisions/deterministic-bid.md) and
[bids-as-unmet-demand](/decisions/bids-as-unmet-demand.md).

# Metabolic cost — designed, not built

The design: every deliberation is metered (model tokens plus host electricity) as it happens and
settled against the same wallet **win or lose**, so thinking is paid for like metabolism. That is
what would make rounds self-limiting and bounded rationality economic, and it is the whole
argument of
[single-wallet-metabolic-cost](/decisions/single-wallet-metabolic-cost.md).

**Nothing meters anything today.** There is no token accounting, no per-call charge and no debit
for thought anywhere in `agent/` or `packages/`. It costs an agent nothing to deliberate, which
is worth knowing when reading any claim here about bounded rationality being priced in — and it
is why the Consulting seat's affordability argument rests on the keeper's patience bounding *how
often* a model is asked, rather than on a bill.

# What an agent commits to

An earlier version of this page carried an `Intention` sketch with `this_round`, `commitments`,
`horizon` and `valid_while`, and a `PROPOSE_COALITION` move. None of it was ever built and the
concept was settled differently: an intention is a commitment to reduce a named gap by a named
means, with an adoption, a resolution and a reason, kept in a private ledger. There is no
coalition move and no credit horizon.

See [intention](/domain/intention.md) for what an agent actually commits to, and
[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
for why it took that shape instead.
