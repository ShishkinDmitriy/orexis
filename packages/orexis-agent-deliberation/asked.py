"""Asking a rule about a world that is held as a diff — the patterns, rewritten.

A rule says what it needs to be true and names no graph (#666). Where the world it is asked
about is the belief base, that is already what an unqualified pattern reads. Where it is a
node of a search, the world is that node's ADDS and RETRACTS over the one the pass began in,
and a pattern has to read the adds first — which SPARQL has no operator for, so each pattern
is rewritten into the two cases:

    { GRAPH <adds> { ?s ?p ?o } }
    UNION
    { ?s ?p ?o  FILTER NOT EXISTS { GRAPH <retracts> { ?s ?p ?gone } } }

Both halves of the test are BOUND by the pattern itself, so the second case is an index lookup
rather than a scan; measured at 1.08–1.22x a read against the materialised world it replaces,
falling as worlds grow, and against no copy per node at all.

**Only the patterns that need it.** A pattern whose predicate no action writes cannot differ
between the base and any world under it, so rewriting it buys nothing and costs a union —
measured, rewriting everything runs 1.32–1.72x where rewriting what moves runs 1.08–1.22x.
Which predicates move is read off the actions' own constructs and retractions, the same parse
`relevance` already does, and the direction of error is safe: a predicate wrongly included is
slower, never wrong.

**It may refuse, and refusing is not failing.** A rule this cannot normalise — a shape the
scanner does not recognise — is answered the old way, against a world the imaginarium
materialises for it. That is the behaviour this file replaces, so refusing costs what today
costs and nothing is ever answered from half a world. `relevance` refuses in the same
direction and for the same reason.

**A property path is refused too**, and not for want of trying: a closure cannot alternate
between two graphs, and no rewriting of the pattern gives it one. What the imaginarium does
instead is materialise that predicate alone — see `Imaginarium.extension`.

See knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md, whose claim this
completes: a rule was already asked about a world rather than a store, and still had to be
told which graph the world was in.
"""

from __future__ import annotations

import re

#  A pattern's predicate is a path, not an IRI, where it carries any of these.
_PATH = re.compile(r"[/|*+?^!()]")
#  The IRIs inside a path, so a path over predicates nothing writes is left alone rather than
#  refused: `ssn-system:hasOperatingRange/ssn-system:inCondition/ssn:forProperty` walks public
#  vocabulary and no step can move any of it.
_STEPS = re.compile(r"[/|*+?^!()]+")
#  `<` opens an IRI only when an IRI is what follows. Otherwise it is less-than, which is how
#  `FILTER(?ss < ?ds)` read as an unterminated IRI and took hanoi's own Move off the fast path.
_IRI = re.compile(r"<[^\s<>\"{}|^`\\]*>")
#  What separates one statement from the next, at depth zero.
_KEYWORDS = ("OPTIONAL", "FILTER", "BIND", "VALUES", "GRAPH", "UNION", "MINUS", "SELECT",
             "SERVICE", "EXISTS")


class Refused(Exception):
    """This text is not one the scanner can normalise. The caller materialises instead."""


def resolved(body: str, adds: str, retracts: str, moves) -> str:
    """`body` — a WHERE clause's inside — with every pattern whose predicate MOVES rewritten to
    read the node's adds before the world it stands in. Raises `Refused` where it cannot say.

    `moves` is the predicates some action writes, as IRIs in the text's own spelling — full
    `<iri>` or a prefixed name, since a rule writes either and this never resolves a prefix.
    """
    body = _uncommented(body)
    out = []
    for kind, text in _scan(body):
        if kind == "triples":
            out.append(" ".join(_rewrite(t, adds, retracts, moves) for t in _triples(text)))
        else:
            out.append(_block(text, adds, retracts, moves))
    return "\n".join(out)


def _uncommented(text: str) -> str:
    """`text` with its comments gone, blind inside IRIs and quoted strings.

    Done once, at the top, because a rule's comments are long and carry apostrophes — one in
    `climate:Venting` read as a literal's opening quote and took the whole construct off the
    fast path. Nothing downstream needs them: what is rewritten is run, never read.
    """
    out, i = "", 0
    while i < len(text):
        if _opens(text, i):
            end = _closing(text, i); out += text[i:end]; i = end; continue
        if text[i] == "#":
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        out += text[i]; i += 1
    return out


def _block(text: str, adds: str, retracts: str, moves) -> str:
    """Anything that is not a run of patterns — a group, an OPTIONAL, a FILTER NOT EXISTS, a
    UNION branch — with whatever it encloses resolved in turn.

    A block is where the patterns actually live in most rules, so leaving one alone reads the
    world the pass began in and answers about a node's world with the root's facts — which the
    gate caught on its first run, as hanoi's Move offering a disk a move had already taken.

    `GRAPH` is the one that decides something. A rule naming a graph of its OWN — the agent's
    settings, `GRAPH $beliefs` — means that graph and is left whole. A rule naming the world it
    stands in is the thing this issue removes: the wrapper is dropped and its patterns take
    their place in the surrounding group, which is what a migrated package ships.
    """
    prefix, inner, suffix = _split_block(text)
    if inner is None:
        return text
    head = prefix.strip().upper()
    if head.startswith(("VALUES", "SERVICE")):
        return text                           # data, or somebody else's endpoint: not patterns
    if head.startswith("GRAPH"):
        named = prefix.strip()[5:].strip()
        if not named.startswith(("$state", "?state")):
            return text                       # a graph the author means: left whole
        prefix = ""                           # the world it stands in: the wrapper comes off
        return resolved(inner, adds, retracts, moves)
    return f"{prefix}{{{resolved(inner, adds, retracts, moves)}}}{suffix}"


def _split_block(text: str):
    """`text` as (what comes before its first group, that group's inside, what comes after),
    or (text, None, "") where it opens no group."""
    start = None
    depth = 0
    i = 0
    while i < len(text):
        if _opens(text, i):
            i = _closing(text, i); continue
        if text[i] == "{":
            if depth == 0:
                start = i
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[:start], text[start + 1:i], text[i + 1:]
        i += 1
    return text, None, ""


def _rewrite(triple: tuple, adds: str, retracts: str, moves) -> str:
    """One pattern: left alone where its predicate cannot move, both cases where it can."""
    s, p, o = triple
    #  A VARIABLE predicate moves, whatever `moves` holds: it binds whichever predicate the
    #  world offers, so one of them may be a predicate an action writes. The retraction half
    #  of every upsert in the tree is this shape — `?obs ?p ?o`, anchored on a subject — and
    #  read as immovable it would take the node's own reading out of the base and leave the
    #  replacement standing beside it.
    if not _moves(p, moves):
        return f"{s} {p} {o} ."
    if not p.startswith(("?", "$")) and _PATH.search(p):
        raise Refused(f"a property path over a predicate a step moves: {p}")
    return (f"{{ {{ GRAPH <{adds}> {{ {s} {p} {o} }} }} UNION "
            f"{{ {s} {p} {o} "
            f"FILTER NOT EXISTS {{ GRAPH <{retracts}> {{ {s} {p} ?_gone{abs(hash(triple)) % 10**6} }} }} }} }}")


def _moves(predicate: str, moves) -> bool:
    """Whether this pattern's predicate could name a fact a step changes.

    A VARIABLE could name anything, so it says yes — over-including is slower and never wrong,
    and the retraction half of every upsert in the tree is that shape. A PATH says yes only
    where one of the IRIs it walks moves: a path through public vocabulary cannot reach a fact
    a step changes, and refusing it would take a rule off the fast path for nothing.
    """
    if predicate.startswith(("?", "$")):
        return True
    if _PATH.search(predicate):
        return any(step in moves for step in _STEPS.split(predicate) if step)
    return predicate in moves


def _scan(body: str):
    """A WHERE clause's inside, as a list of `(kind, text)` in order — `triples` for a run of
    triple patterns, `other` for everything else, whose insides are scanned in turn.

    Depth-aware over `{}` and `()`, and blind inside `<…>` and quoted strings, which is the
    whole of what makes this a scanner rather than a chain of replacements (#500).
    """
    out, buf, depth, i = [], "", 0, 0
    while i < len(body):
        c = body[i]
        if _opens(body, i):
            end = _closing(body, i)
            buf += body[i:end]
            i = end
            continue
        if c in "{(":
            depth += 1
        elif c in "})":
            depth -= 1
            if depth < 0:
                raise Refused("unbalanced")
        buf += c
        if depth == 0 and c == "}":
            out.append(("other", buf)); buf = ""
        elif depth == 0 and c == ".":
            out.append(("triples", buf)); buf = ""
        i += 1
    if buf.strip():
        out.append(("triples" if not _starts_with_keyword(buf) else "other", buf))
    #  A run that opened a block is that block's, not a pattern's.
    return [("other", t) if k == "triples" and _starts_with_keyword(t) else (k, t) for k, t in out]


def _starts_with_keyword(text: str) -> bool:
    stripped = re.sub(r"^\s*(#[^\n]*\n\s*)*", "", text)
    return stripped.upper().startswith(_KEYWORDS) or stripped.startswith("{")


def _triples(text: str) -> list[tuple]:
    """A statement's patterns, with `;` and `,` expanded — one `(s, p, o)` each.

    Refused where a term this does not understand appears: a blank-node property list `[…]`,
    a collection `(…)`, or anything that leaves the arity wrong. The caller materialises.
    """
    body = text.strip().rstrip(".").strip()
    if not body:
        return []
    if "[" in body or "]" in body:
        raise Refused("a blank node property list is not normalised")
    out, subject, predicate = [], None, None
    for clause in _split(body, ";"):
        parts = _terms(clause)
        if subject is None:
            if len(parts) < 3:
                raise Refused(f"not a triple: {clause.strip()!r}")
            subject, parts = parts[0], parts[1:]
        if len(parts) < 2:
            raise Refused(f"not a predicate-object pair: {clause.strip()!r}")
        predicate = parts[0]
        for obj in _split(" ".join(parts[1:]), ","):
            terms = _terms(obj)
            if len(terms) != 1:
                raise Refused(f"not one object: {obj.strip()!r}")
            out.append((subject, predicate, terms[0]))
    return out


def _split(text: str, sep: str) -> list[str]:
    """`text` split on `sep` at depth zero, blind inside `<…>` and quoted strings."""
    out, buf, depth, i = [], "", 0, 0
    while i < len(text):
        c = text[i]
        if _opens(text, i):
            end = _closing(text, i); buf += text[i:end]; i = end; continue
        if c in "{(":
            depth += 1
        elif c in "})":
            depth -= 1
        if c == sep and depth == 0:
            out.append(buf); buf = ""
        else:
            buf += c
        i += 1
    out.append(buf)
    return [b for b in out if b.strip()]


def _terms(text: str) -> list[str]:
    """A clause's terms — whitespace-separated, except inside `<…>` and quoted strings."""
    out, buf, i = [], "", 0
    while i < len(text):
        c = text[i]
        if _opens(text, i):
            end = _closing(text, i); buf += text[i:end]; i = end; continue
        if c.isspace():
            if buf:
                out.append(buf); buf = ""
        else:
            buf += c
        i += 1
    if buf:
        out.append(buf)
    return out


def _opens(text: str, i: int) -> bool:
    """Whether a term this must read whole starts here — a quoted string, or an IRI rather than
    a less-than."""
    return text[i] in "\"'" or (text[i] == "<" and bool(_IRI.match(text, i)))


def _closing(text: str, start: int) -> int:
    """One past the end of the `<…>` or quoted string opening at `start`."""
    opener = text[start]
    if opener == "<":
        end = text.find(">", start)
        if end < 0:
            raise Refused("unterminated IRI")
        return end + 1
    i = start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == opener:
            return i + 1
        i += 1
    raise Refused("unterminated literal")
