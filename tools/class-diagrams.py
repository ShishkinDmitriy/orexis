#!/usr/bin/env python3
"""Write one PlantUML class diagram per crate: every struct, enum and trait in its `src/`, grouped by module, and
what holds what.

A field, a variant's payload or a tuple member naming another type is drawn as an arrow labelled with the field and
its multiplicity — `*--` where the type is held by value, `o--` where it is shared (`Arc`, `Rc`, a reference) — and
`impl Trait for Type` as a realisation. A type of another crate this one names is drawn as a stub in that crate's
box. Tests (`#[cfg(test)]` modules, and `tests/`) are left out.

The diagrams are GENERATED, so nobody edits them: `tests/test_knowledge.py` regenerates each in memory and fails
where a committed one differs, which is what holds a picture of the code to the code. Run this, then
`tools/render-diagrams.sh`.

    tools/class-diagrams.py            # write knowledge/diagrams/package-<crate>.puml for every crate
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "knowledge" / "diagrams"

#  What wraps a type without being one: a collection reads as many, an Option as at most one, a pointer as shared.
MANY = {"Vec", "VecDeque", "HashMap", "BTreeMap", "HashSet", "BTreeSet", "IndexMap", "IndexSet", "SmallVec"}
SHARED = {"Arc", "Rc", "Weak"}


@dataclass
class Item:
    kind: str  # struct | enum | trait
    name: str
    module: str
    visibility: str
    members: list[tuple[str, str]] = field(default_factory=list)  # (name, type) — a variant's type is its payload


def crates() -> list[Path]:
    return sorted(p for p in REPO_ROOT.iterdir() if (p / "Cargo.toml").is_file() and p.name.split("-")[0] == "orexis")


def strip(source: str) -> str:
    """The source with its comments, strings, chars and test modules blanked, braces left balanced."""
    out, i, n = [], 0, len(source)
    while i < n:
        c = source[i]
        if source.startswith("//", i):
            j = source.find("\n", i)
            i = n if j < 0 else j
        elif source.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if source.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif source.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
        elif c == "r" and re.match(r'r#*"', source[i:]) and not (i and (source[i - 1].isalnum() or source[i - 1] == "_")):
            hashes = re.match(r'r(#*)"', source[i:]).group(1)
            end = source.find('"' + hashes, i + 2 + len(hashes))
            out.append('""')
            i = n if end < 0 else end + 1 + len(hashes)
        elif c == '"':
            i += 1
            while i < n and source[i] != '"':
                i += 2 if source[i] == "\\" else 1
            out.append('""')
            i += 1
        elif c == "'" and re.match(r"'(\\.[^']*|[^\\'])'", source[i:]):
            m = re.match(r"'(\\.[^']*|[^\\'])'", source[i:])
            out.append("' '")
            i += m.end()
        else:
            out.append(c)
            i += 1
    text = "".join(out)
    #  A test module goes whole: its attribute, its head and its block.
    while (m := re.search(r"#\[cfg\(test\)\]\s*(pub(\([^)]*\))?\s+)?mod\s+\w+\s*\{", text)):
        end = matching(text, m.end() - 1)
        text = text[:m.start()] + text[end + 1:]
    return text


def matching(text: str, open_at: int) -> int:
    pairs = {"{": "}", "(": ")", "[": "]", "<": ">"}
    opener, closer, depth = text[open_at], pairs[text[open_at]], 0
    for i in range(open_at, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == closer and not (closer == ">" and text[i - 1] == "-"):
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def split_top(text: str, sep: str = ",") -> list[str]:
    """`text` split at every `sep` outside brackets, a `->` not counted as one."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c in "([{<":
            depth += 1
        elif c in ")]}" or (c == ">" and text[i - 1] != "-"):
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def drop_attributes(text: str) -> str:
    while (m := re.search(r"#!?\[", text)):
        text = text[:m.start()] + text[matching(text, m.end() - 1) + 1:]
    return text


def normalise(t: str) -> str:
    return re.sub(r"\s+", " ", t).replace("< ", "<").replace(" >", ">").strip()


def items_of(path: Path, module: str) -> list[Item]:
    text = strip(path.read_text())
    found = []
    for m in re.finditer(r"(?m)^[ \t]*(pub(?:\([^)]*\))?\s+)?(struct|enum|trait)\s+([A-Z]\w*)", text):
        vis = "+" if m.group(1) and "(" not in m.group(1) else ("~" if m.group(1) else "-")
        kind, name, i = m.group(2), m.group(3), m.end()
        if i < len(text) and text[i] == "<":
            i = matching(text, i) + 1
        rest = text[i:].lstrip()
        offset = len(text) - len(rest)
        item = Item(kind, name, module, vis)
        if rest.startswith("("):
            end = matching(text, offset)
            item.members = [(str(k), normalise(re.sub(r"^pub(\([^)]*\))?\s+", "", t)))
                            for k, t in enumerate(split_top(drop_attributes(text[offset + 1:end])))]
        else:
            brace = text.find("{", offset)
            semi = text.find(";", offset)
            if brace < 0 or (0 <= semi < brace):
                found.append(item)
                continue
            body = drop_attributes(text[brace + 1:matching(text, brace)])
            if kind == "struct":
                for f in split_top(body):
                    fm = re.match(r"(pub(\([^)]*\))?\s+)?(\w+)\s*:\s*(.*)$", f, re.S)
                    if fm:
                        mark = "+" if fm.group(1) and not fm.group(2) else ("~" if fm.group(1) else "-")
                        item.members.append((mark + fm.group(3), normalise(fm.group(4))))
            elif kind == "enum":
                for v in split_top(body):
                    vm = re.match(r"(\w+)\s*(.*)$", v, re.S)
                    if vm:
                        payload = vm.group(2).strip()
                        payload = "" if payload.startswith("=") else normalise(payload)
                        item.members.append((vm.group(1), payload))
            else:
                for fm in re.finditer(r"\b(?:async\s+)?fn\s+(\w+)", body):
                    item.members.append((fm.group(1) + "()", ""))
                for tm in re.finditer(r"\btype\s+(\w+)", body):
                    item.members.append(("type " + tm.group(1), ""))
        found.append(item)
    return found


def module_of(crate: Path, path: Path) -> str:
    parts = list(path.relative_to(crate / "src").with_suffix("").parts)
    if parts[-1] in {"lib", "main", "mod"}:
        parts = parts[:-1]
    return "::".join(parts) or "(crate)"


def realisations(crate: Path) -> set[tuple[str, str, str]]:
    """Each `impl Trait for Type` in the crate, with the module it is written in."""
    found = set()
    for path in sorted((crate / "src").rglob("*.rs")):
        text, module = strip(path.read_text()), module_of(crate, path)
        for m in re.finditer(r"\bimpl\s*(<[^{]*?>)?\s*([\w:]+)(<[^{]*?>)?\s+for\s+&?(?:'\w+\s+)?([\w:]+)", text):
            found.add((m.group(4), m.group(2), module))
    return found


def dependencies(crate: Path) -> set[str]:
    text = (crate / "Cargo.toml").read_text()
    deps = re.findall(r"(?m)^(orexis[\w-]*)\s*=", text)
    return {d.replace("_", "-") for d in deps} - {crate.name}


def references(t: str) -> list[tuple[str, str, bool]]:
    """Each type `t` names, with its multiplicity and whether it is shared, the wrappers peeled."""
    out = []

    def walk(s: str, mult: str, shared: bool):
        s = s.strip()
        if s.startswith("&"):
            walk(re.sub(r"^&('\w+\s+)?(mut\s+)?", "", s), mult, True)
            return
        if s.startswith("(") or s.startswith("["):
            for p in split_top(s[1:-1].replace(";", ",")):
                walk(p, "*" if s.startswith("[") else mult, shared)
            return
        if s.startswith("dyn ") or s.startswith("impl "):
            for p in split_top(s.split(" ", 1)[1], "+"):
                walk(p, mult, shared)
            return
        m = re.match(r"([\w:]+)\s*(<.*>)?", s, re.S)
        if not m:
            return
        path, args = m.group(1), m.group(2)
        last = path.split("::")[-1]
        inner = split_top(args[1:-1]) if args else []
        inner = [a for a in inner if not a.startswith("'")]
        if last in MANY:
            for a in inner:
                walk(a, "*", shared)
        elif last == "Option":
            for a in inner:
                walk(a, "0..1" if mult == "1" else mult, shared)
        elif last in SHARED or last in {"Box", "Mutex", "RwLock", "RefCell", "Cell", "Pin", "OnceLock", "OnceCell"}:
            for a in inner:
                walk(a, mult, shared or last in SHARED)
        else:
            out.append((path, mult, shared))
            for a in inner:
                if not re.match(r"^[A-Z]$", a):
                    walk(a, mult, shared)
    walk(t, "1", False)
    return out


def ident(crate: str, name: str) -> str:
    return re.sub(r"\W", "_", f"{crate}__{name}")


def diagram(crate: Path, catalogue: dict[str, dict[str, list[Item]]]) -> str:
    own = catalogue[crate.name]
    deps = dependencies(crate)
    title = crate.name
    lines = [f"@startuml package-{crate.name}", "!pragma layout smetana",
             f"title {title} — every struct, enum and trait in src/, by module\\n"
             "generated by tools/class-diagrams.py · ~*~-~- held by value · o~-~- shared · ..|> implements",
             "skinparam shadowing false", "skinparam classAttributeIconSize 0", "skinparam defaultFontSize 11",
             "skinparam packageStyle rectangle", "hide empty members", "left to right direction", ""]
    stereo = {"struct": "<< (S,#A8D8EA) struct >>", "enum": "<< (E,#F6D6A8) enum >>", "trait": "<< (T,#C9E4C5) trait >>"}
    kind_of = {"struct": "class", "enum": "enum", "trait": "interface"}
    by_module: dict[str, list[Item]] = {}
    for items in own.values():
        for it in items:
            by_module.setdefault(it.module, []).append(it)
    for module in sorted(by_module):
        lines.append(f'package "{module}" {{')
        for it in sorted(by_module[module], key=lambda i: i.name):
            vis = "" if it.visibility == "+" else (" ~" if it.visibility == "~" else " -")
            lines.append(f'  {kind_of[it.kind]} "{it.name}" as {ident(crate.name, it.module + "::" + it.name)} '
                         f'{stereo[it.kind]} {{')
            for name, t in it.members:
                t = t.replace("{", "(").replace("}", ")")
                if it.kind == "struct":
                    #  `{field}` keeps a type with parentheses in it from being read as a method.
                    lines.append(f"    {{field}} {name} : {t}" if not name[0].isdigit() else f"    {{field}} .{name} : {t}")
                elif it.kind == "enum":
                    lines.append(f"    {name}{(' ' + t) if t else ''}")
                else:
                    lines.append(f"    {{abstract}} {name}" if name.endswith("()") else f"    {name}")
            lines.append("  }")
        lines.append("}")
    lines.append("")

    def resolve(path: str, near: str = "") -> tuple[str, Item] | None:
        """The crate and item `path` names, seen from module `near`: a name two modules declare is the one in
        `near`, or the one whose module the path spells."""
        parts = path.split("::")
        name = parts[-1]
        head = parts[0].replace("_", "-") if len(parts) > 1 else None
        if head in (None, "crate", "self", "super") and name in own:
            candidates = own[name]
            spelled = "::".join(p for p in parts[:-1] if p not in ("crate", "self", "super"))
            pick = next((c for c in candidates if c.module == near), None) or \
                next((c for c in candidates if spelled and c.module.endswith(spelled)), None) or candidates[0]
            return crate.name, pick
        if head and head in catalogue and head != crate.name and name in catalogue[head]:
            return head, catalogue[head][name][0]
        if head is None:
            homes = [c for c in deps if name in catalogue.get(c, {})]
            if len(homes) == 1:
                return homes[0], catalogue[homes[0]][name][0]
        return None

    arrows, stubs = [], {}
    for items in own.values():
        for it in items:
            src = ident(crate.name, it.module + "::" + it.name)
            for name, t in it.members:
                if not t:
                    continue
                for path, mult, shared in references(t):
                    hit = resolve(path, it.module)
                    if not hit:
                        continue
                    home, target = hit
                    dst = ident(home, target.module + "::" + target.name)
                    if home != crate.name:
                        stubs.setdefault(home, {})[dst] = target
                    label = name.lstrip("+-~") if it.kind != "struct" or not name[1:].isdigit() else ""
                    head = "o--" if shared else "*--"
                    arrows.append(f'{src} {head} "{mult}" {dst} : {label}' if label
                                  else f'{src} {head} "{mult}" {dst}')
    for implementor, trait, module in sorted(realisations(crate)):
        a, b = resolve(implementor, module), resolve(trait, module)
        if a and b and a[0] == crate.name and b[1].kind == "trait":
            dst = ident(b[0], b[1].module + "::" + b[1].name)
            if b[0] != crate.name:
                stubs.setdefault(b[0], {})[dst] = b[1]
            arrows.append(f"{ident(a[0], a[1].module + '::' + a[1].name)} ..|> {dst}")
    for home in sorted(stubs):
        lines.append(f'package "{home}" #EEEEEE {{')
        for dst, target in sorted(stubs[home].items()):
            lines.append(f'  {kind_of[target.kind]} "{target.name}" as {dst} {stereo[target.kind]}')
        lines.append("}")
    lines.append("")
    #  The arrows go in order, a repeated one once: two fields of one type are two arrows, but one field naming a
    #  type twice is one.
    seen = set()
    for a in arrows:
        if a not in seen:
            seen.add(a)
            lines.append(a)
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def catalogue_of() -> dict[str, dict[str, list[Item]]]:
    out: dict[str, dict[str, list[Item]]] = {}
    for crate in crates():
        own: dict[str, list[Item]] = {}
        for path in sorted((crate / "src").rglob("*.rs")):
            for it in items_of(path, module_of(crate, path)):
                own.setdefault(it.name, []).append(it)
        out[crate.name] = own
    return out


def diagrams() -> dict[str, str]:
    """Every crate's diagram, by the file name it is written under."""
    catalogue = catalogue_of()
    return {f"package-{c.name}.puml": diagram(c, catalogue) for c in crates() if catalogue[c.name]}


def main() -> int:
    for name, text in diagrams().items():
        (OUT / name).write_text(text)
        print(f"wrote knowledge/diagrams/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
