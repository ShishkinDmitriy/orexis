---
type: Decision
title: Clearing is a standalone function
description: The supplier calls clearing; it is not welded into the supplier.
status: accepted
stage: v1
tags: [seam, clearing, market-topology]
timestamp: 2026-08-01T00:00:00Z
---

# Context

"Who hosts the auction" turns out to be relative to market shape: the *scarce side* hosts.
Supplier hosts one-to-many; a consumer hosts many-to-one (reverse auction); N-to-N has no
host and needs a stake-free exchange. The invariant across all of them is the *clearing
logic* — the host is just where it temporarily lives.

# Decision

Write **clearing as a standalone, stake-free function**. In v1 the
[supplier](/domain/supplier.md) *calls* it rather than *being* it.

# Why (the seam)

The same clearing serves every topology as a change of *caller*, not a rewrite:
- one-to-many → supplier invokes it (v1)
- many-to-one → consumer invokes it (reverse auction)
- N-to-N → a standalone exchange invokes it

This is the one place worth spending extra effort up front, because we already know all
three callers are coming. See [roadmap](/decisions/roadmap.md) and [clearing](/domain/clearing.md).
