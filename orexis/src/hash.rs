//! WHAT ONE NAMED GRAPH HOLDS, as a hash — and the hash written onto the graph's own row, as
//! `agent/hash_named_graph.py` writes it, digit for digit: a case's diff records the digest, so the two kernels
//! hashing one graph alike is what the case holds them to.
//!
//! **IT IS THE CONTENT AND NOTHING ELSE**: a blank node is its content, not its label; a number is its value
//! rounded to six decimals; every other term is its kind and its text. **A WORLD IS HASHED WITHIN WHAT IS READ**:
//! where a caller names the predicates and classes a world is identified by, only those facts count, a type fact
//! by its class. The argument for each lives in the Python module's docstring, which this follows.
//!
//! **THE DIGEST IS PYTHON'S `repr` OF THE CANONICAL FACTS**, sorted, joined by newlines and hashed with SHA-256,
//! because that is what the Python kernel writes, and a Rust agent and a Python one keeping one world's volume
//! must agree on where it stands. So each form below is spelled as Python spells the tuple it is: strings quoted
//! as `repr` quotes them, a float as `repr` writes it, a one-element tuple with its trailing comma.

use std::collections::{BTreeSet, HashMap};

use oxigraph::model::{BlankNode, GraphNameRef, Literal, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use sha2::{Digest, Sha256};

use crate::Error;
use crate::ontology::HASH;
use crate::store::Store;

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// How far a number is trusted: two worlds whose readings agree to six decimals are one place.
const ROUND: i32 = 6;

/// SHA-256, named in the value, so a digest says how it was made.
const ALGORITHM: &str = "sha256";

const XSD: &str = "http://www.w3.org/2001/XMLSchema#";

/// What counts as a number, and so what gets rounded: named, never discovered by trying to parse a literal.
const NUMERIC: &[&str] = &[
    "decimal",
    "double",
    "float",
    "integer",
    "long",
    "int",
    "short",
    "byte",
    "nonNegativeInteger",
    "positiveInteger",
    "nonPositiveInteger",
    "negativeInteger",
    "unsignedLong",
    "unsignedInt",
    "unsignedShort",
    "unsignedByte",
];

/// The canonical hash of what `graph` holds, written onto its catalogue row in place of any before it, and
/// answered. `within` is what a world is identified by, predicates and classes; None hashes every fact. A graph
/// the store has never heard of hashes like an empty one.
pub fn hash_named_graph(store: &Store, graph: &str, within: Option<&BTreeSet<String>>) -> Result<String, Error> {
    let digest = digest_of(store, graph, within)?;
    let catalogue = store
        .catalogue()?
        .ok_or_else(|| Error::Catalogue(format!("no catalogue to write the hash of {graph} on")))?;
    let (subject, hash, row) = (named(graph)?, named(HASH)?, named(&catalogue)?);
    let engine = store.engine();
    let old: Vec<Quad> = engine
        .quads_for_pattern(
            Some(subject.as_ref().into()),
            Some(hash.as_ref()),
            None,
            Some(GraphNameRef::NamedNode(row.as_ref())),
        )
        .collect::<Result<_, _>>()
        .map_err(|e| Error::Evaluation(e.to_string()))?;
    for quad in &old {
        engine.remove(quad).map_err(|e| Error::Evaluation(e.to_string()))?;
    }
    engine
        .insert(&Quad::new(subject, hash, Literal::new_simple_literal(&digest), row))
        .map_err(|e| Error::Evaluation(e.to_string()))?;
    Ok(digest)
}

/// The canonical hash of what `graph` holds, answered and written nowhere — for a writer that puts it on the
/// graph's row itself, in the update that writes the row.
pub fn digest_of(store: &Store, graph: &str, within: Option<&BTreeSet<String>>) -> Result<String, Error> {
    let triples = store.triples(graph)?;
    let kept: Vec<Triple> = match within {
        None => triples,
        Some(within) => triples.into_iter().filter(|t| counts(t, within)).collect(),
    };
    Ok(digest(&forms(&kept).into_iter().collect()))
}

/// Whether a triple is among what `within` names: by its predicate, and a type fact by its class.
fn counts(triple: &Triple, within: &BTreeSet<String>) -> bool {
    within.contains(triple.predicate.as_str())
        || (triple.predicate.as_str() == RDF_TYPE
            && matches!(&triple.object, Term::NamedNode(class) if within.contains(class.as_str())))
}

/// One hash of a fact set, `sha256:<hex>`, the facts' forms sorted as Python sorts strings — by code point,
/// which is UTF-8's byte order.
fn digest(facts: &BTreeSet<String>) -> String {
    let joined = facts.iter().map(String::as_str).collect::<Vec<_>>().join("\n");
    let hex: String = Sha256::digest(joined.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    format!("{ALGORITHM}:{hex}")
}

/// The canonical form of EACH triple, in the order given, in the universe of the triples given — a blank node
/// being its neighbourhood there — as the text Python's `repr` gives the tuple. For a writer deciding which of a
/// rule's conclusions it already holds, as well as for the hash.
pub fn forms(triples: &[Triple]) -> Vec<String> {
    let mut world = World::default();
    for t in triples {
        if let NamedOrBlankNode::BlankNode(s) = &t.subject {
            world
                .outgoing
                .entry(s.clone())
                .or_default()
                .push((t.predicate.clone(), t.object.clone()));
        }
        if let Term::BlankNode(o) = &t.object {
            world
                .incoming
                .entry(o.clone())
                .or_default()
                .push((t.subject.clone().into(), t.predicate.clone()));
        }
    }
    triples
        .iter()
        .map(|t| {
            let s = world.term(&t.subject.clone().into());
            let o = world.term(&t.object);
            format!("({s}, {}, {o})", py_str(t.predicate.as_str()))
        })
        .collect()
}

/// One call's view of its triples: what hangs off each blank node and what points at it, and the forms already
/// made, so a blank node said of k times is walked once.
#[derive(Default)]
struct World {
    outgoing: HashMap<BlankNode, Vec<(NamedNode, Term)>>,
    incoming: HashMap<BlankNode, Vec<(Term, NamedNode)>>,
    memo: HashMap<BlankNode, String>,
}

impl World {
    fn term(&mut self, x: &Term) -> String {
        match x {
            Term::BlankNode(node) => {
                if let Some(form) = self.memo.get(node) {
                    return form.clone();
                }
                let form = self.content(node, &BTreeSet::new());
                self.memo.insert(node.clone(), form.clone());
                form
            }
            other => leaf(other),
        }
    }

    /// A blank node as what is said about it and what says it, recursively; a revisit closes the walk.
    fn content(&self, node: &BlankNode, seen: &BTreeSet<String>) -> String {
        if seen.contains(node.as_str()) {
            return "('bnode', '~')".to_string();
        }
        let mut seen = seen.clone();
        seen.insert(node.as_str().to_string());
        let mut out: Vec<String> = self
            .outgoing
            .get(node)
            .into_iter()
            .flatten()
            .map(|(p, o)| format!("({}, {})", py_str(p.as_str()), self.leaf(o, &seen)))
            .collect();
        let mut into: Vec<String> = self
            .incoming
            .get(node)
            .into_iter()
            .flatten()
            .map(|(s, p)| format!("({}, {})", self.leaf(s, &seen), py_str(p.as_str())))
            .collect();
        out.sort();
        into.sort();
        format!("('bnode', {}, {})", py_tuple(&out), py_tuple(&into))
    }

    fn leaf(&self, x: &Term, seen: &BTreeSet<String>) -> String {
        match x {
            Term::BlankNode(node) => self.content(node, seen),
            other => leaf(other),
        }
    }
}

/// A term that is no blank node: an IRI as its kind and text, a literal as `literal` says.
fn leaf(x: &Term) -> String {
    match x {
        Term::NamedNode(node) => format!("('iri', {})", py_str(node.as_str())),
        Term::Literal(lit) => literal(lit),
        Term::BlankNode(node) => format!("('iri', {})", py_str(node.as_str())),
    }
}

/// A literal as its kind and value: a number rounded, anything else its text beside its language or datatype. A
/// number whose text will not parse is its text, the safe direction.
fn literal(lit: &Literal) -> String {
    let datatype = lit.datatype().as_str();
    if let Some(local) = datatype.strip_prefix(XSD)
        && NUMERIC.contains(&local)
        && let Some(x) = py_float(lit.value())
    {
        return format!("('num', {})", py_float_repr(py_round(x)));
    }
    let tag = lit.language().unwrap_or(datatype);
    format!("('lit', {}, {})", py_str(lit.value()), py_str(tag))
}

fn named(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Evaluation(e.to_string()))
}

// --- Python's spelling -----------------------------------------------------------------------------------------

/// A tuple of already-spelled items, as `repr` writes one: `()`, `(a,)`, `(a, b)`.
fn py_tuple(items: &[String]) -> String {
    match items {
        [] => "()".to_string(),
        [one] => format!("({one},)"),
        many => format!("({})", many.join(", ")),
    }
}

/// A string as `repr` writes it: single quotes unless it holds one and no double, the quote and the backslash
/// escaped, `\t` `\n` `\r`, `\xNN` for the rest below a space and DEL, and a character Python will not print
/// escaped by its width.
///
/// Python's printability is its Unicode database's; this asks what Rust can — control, whitespace other than a
/// space, the format characters and the private and unpaired ranges — and an unassigned code point, which
/// Python escapes, is printed. No document this project hashes holds one.
/// A string as Python's `repr` spells it.
pub fn py_str(text: &str) -> String {
    let quote = if text.contains('\'') && !text.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::with_capacity(text.len() + 2);
    out.push(quote);
    for c in text.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\t' => out.push_str("\\t"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if (c as u32) < 0x7f || printable(c) => out.push(c),
            c if (c as u32) <= 0xff => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if (c as u32) <= 0xffff => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push_str(&format!("\\U{:08x}", c as u32)),
        }
    }
    out.push(quote);
    out
}

fn printable(c: char) -> bool {
    let n = c as u32;
    !(c.is_control()
        || (c.is_whitespace() && c != ' ')
        || matches!(n, 0xad | 0x600..=0x605 | 0x61c | 0x6dd | 0x70f | 0x180e | 0x200b..=0x200f | 0x202a..=0x202e
            | 0x2060..=0x2064 | 0x2066..=0x206f | 0xfeff | 0xfff9..=0xfffb | 0xe000..=0xf8ff | 0xf0000..)
        || (n & 0xfffe) == 0xfffe)
}

/// A literal's text as Python's `float()` reads it, where it does.
fn py_float(text: &str) -> Option<f64> {
    text.trim().parse::<f64>().ok()
}

/// `round(x, 6)`: correctly rounded to six decimals, the way Python rounds, and read back. A tie is never met,
/// since no binary fraction ends in a five at the seventh decimal.
pub fn py_round(x: f64) -> f64 {
    if !x.is_finite() {
        return x;
    }
    format!("{x:.prec$}", prec = ROUND as usize).parse().unwrap_or(x)
}

/// A float as `repr` writes it: the shortest digits that read back, fixed between 1e-4 and 1e16 with a `.0` where
/// it has no fraction, and an exponent of two digits at least outside.
pub fn py_float_repr(x: f64) -> String {
    if x.is_nan() {
        return "nan".to_string();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf" } else { "-inf" }.to_string();
    }
    let sci = format!("{:e}", x.abs());
    let (mantissa, exponent) = sci.split_once('e').expect("Rust's exponent form has an e");
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let point: i32 = exponent.parse::<i32>().expect("an exponent") + 1;
    let sign = if x.is_sign_negative() { "-" } else { "" };
    let n = digits.len() as i32;
    let body = if (-4 < point) && (point <= 16) {
        if point <= 0 {
            format!("0.{}{digits}", "0".repeat((-point) as usize))
        } else if point >= n {
            format!("{digits}{}.0", "0".repeat((point - n) as usize))
        } else {
            format!("{}.{}", &digits[..point as usize], &digits[point as usize..])
        }
    } else {
        let mantissa = if n == 1 {
            digits.clone()
        } else {
            format!("{}.{}", &digits[..1], &digits[1..])
        };
        let e = point - 1;
        format!("{mantissa}e{}{:02}", if e < 0 { '-' } else { '+' }, e.abs())
    };
    format!("{sign}{body}")
}

#[cfg(test)]
mod tests {
    //! Hashing what a named graph holds, held to `orexis/tests/hash_named_graph/`'s cases — the digests the Python
    //! kernel wrote into each diff, so the two kernels agree on where a world stands — and to the partition each case
    //! is about, as `agent/tests/test_hash_named_graph.py` declares it.

    use std::collections::{BTreeMap, BTreeSet};
    use std::path::PathBuf;

    use super::*;
    use crate::snapshots;

    fn cases() -> Vec<PathBuf> {
        snapshots::cases_in(&snapshots::tree().join("orexis/tests/hash_named_graph"))
    }

    /// Which graphs of a case are one place: every graph it names stands in exactly one group.
    fn same(case: &str) -> Vec<BTreeSet<&'static str>> {
        let groups: &[&[&str]] = match case {
            "a_graph_is_its_content_and_not_its_name" => &[&["here", "there"], &["elsewhere"]],
            "a_term_is_its_kind_and_not_only_its_text" => {
                &[&["iri"], &["text"], &["one"], &["number"], &["en"], &["de"]]
            }
            "a_number_is_its_value_rounded" => &[&["integer", "decimal", "near"], &["apart"]],
            "a_blank_node_is_its_content" => &[&["minted", "again"], &["deeper"], &["cyclic"]],
            other => panic!("{other} declares no partition"),
        };
        groups.iter().map(|g| g.iter().copied().collect()).collect()
    }

    /// Every graph of a store hashed, bar the catalogue, by the local part of its name.
    fn hashed(store: &Store) -> BTreeMap<String, String> {
        let catalogue = store.catalogue().unwrap();
        store
            .graph_names()
            .unwrap()
            .into_iter()
            .filter(|g| Some(g) != catalogue.as_ref())
            .map(|g| {
                let digest = hash_named_graph(store, &g, None).unwrap();
                (g.rsplit('#').next().unwrap().to_string(), digest)
            })
            .collect()
    }

    #[test]
    fn hashing_leaves_the_catalogue_the_diff_says() {
        for case in cases() {
            let store = snapshots::stand_in(&case);
            hashed(&store);
            snapshots::held_to_diff(&case, &store, "hash_named_graph");
        }
    }

    #[test]
    fn the_graphs_a_case_calls_one_place_hash_alike_and_the_rest_do_not() {
        for case in cases() {
            let stem = case.file_stem().unwrap().to_str().unwrap().to_string();
            let groups = same(&stem);
            let digests = hashed(&snapshots::stand_in(&case));
            let named: BTreeSet<&str> = groups.iter().flatten().copied().collect();
            let held: BTreeSet<&str> = digests.keys().map(String::as_str).collect();
            assert!(
                named.is_subset(&held),
                "{stem}: {:?} is in no graph",
                named.difference(&held)
            );
            let loose: Vec<_> = held.difference(&named).filter(|g| **g != "ontology").collect();
            assert!(loose.is_empty(), "{stem}: {loose:?} is in no group");
            let mut apart = BTreeSet::new();
            for group in &groups {
                let one: BTreeSet<&String> = group.iter().map(|g| &digests[*g]).collect();
                assert_eq!(one.len(), 1, "{stem}: {group:?} is one place, and hashed {one:?}");
                apart.insert(one.into_iter().next().unwrap().clone());
            }
            assert_eq!(apart.len(), groups.len(), "{stem}: two groups hash alike");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        let found = cases();
        assert!(found.len() >= 4, "{found:?}");
        let directory = snapshots::tree().join("orexis/tests/hash_named_graph");
        assert!(snapshots::orphans_in(&directory).is_empty());
    }

    // --- what a case cannot reach ----------------------------------------------------------------------------------

    fn store() -> Store {
        let store = Store::new(snapshots::namespaces()).unwrap();
        store
            .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph } }")
            .unwrap();
        store
    }

    fn row(store: &Store, graph: &str) -> Vec<String> {
        store
            .quads("urn:test:catalogue")
            .unwrap()
            .into_iter()
            .filter(|q| q.subject.to_string() == format!("<{graph}>") && q.predicate.as_str() == HASH)
            .map(|q| match q.object {
                Term::Literal(l) => l.value().to_string(),
                other => other.to_string(),
            })
            .collect()
    }

    #[test]
    fn one_graph_hashes_to_one_row_however_often_it_is_asked() {
        let store = store();
        store
            .update("INSERT DATA { GRAPH <urn:test:a> { <urn:s> <urn:p> 1 } }")
            .unwrap();
        let first = hash_named_graph(&store, "urn:test:a", None).unwrap();
        assert_eq!(row(&store, "urn:test:a"), std::slice::from_ref(&first));
        assert_eq!(hash_named_graph(&store, "urn:test:a", None).unwrap(), first);
        assert_eq!(row(&store, "urn:test:a"), [first], "one row, not two");
    }

    #[test]
    fn a_graph_the_store_never_heard_of_hashes_like_an_empty_one() {
        let store = store();
        assert_eq!(
            hash_named_graph(&store, "urn:test:nothing", None).unwrap(),
            hash_named_graph(&store, "urn:test:else", None).unwrap()
        );
    }

    #[test]
    fn hashed_within_a_scope_a_fact_outside_it_is_not_where_the_world_stands() {
        let store = store();
        store
        .update(
            "INSERT DATA { GRAPH <urn:test:then> { <urn:disk> <urn:on> <urn:peg> . \
             <urn:disk> <urn:seenAt> \"2026-10-03T08:52:46Z\" } \
             GRAPH <urn:test:now> { <urn:disk> <urn:on> <urn:peg> . <urn:disk> <urn:seenAt> \"2026-10-03T09:12:45Z\" } }",
        )
        .unwrap();
        let within: BTreeSet<String> = ["urn:on".to_string()].into();
        assert_eq!(
            hash_named_graph(&store, "urn:test:then", Some(&within)).unwrap(),
            hash_named_graph(&store, "urn:test:now", Some(&within)).unwrap()
        );
        assert_ne!(
            hash_named_graph(&store, "urn:test:then", None).unwrap(),
            hash_named_graph(&store, "urn:test:now", None).unwrap()
        );
    }

    #[test]
    fn within_a_scope_a_type_fact_counts_by_its_class() {
        let store = store();
        store
            .update(
                "INSERT DATA { GRAPH <urn:test:bare> { <urn:r> <urn:on> <urn:v> } \
             GRAPH <urn:test:round> { <urn:r> <urn:on> <urn:v> ; a <urn:Round> } \
             GRAPH <urn:test:other> { <urn:r> <urn:on> <urn:v> ; a <urn:Unread> } }",
            )
            .unwrap();
        let within: BTreeSet<String> = ["urn:on".to_string(), "urn:Round".to_string()].into();
        let [bare, typed, other] = ["bare", "round", "other"]
            .map(|g| hash_named_graph(&store, &format!("urn:test:{g}"), Some(&within)).unwrap());
        assert_ne!(typed, bare, "a type the scope names is a fact the world stands by");
        assert_eq!(other, bare, "and one it does not name is not");
    }

    // --- Python's spelling, where a case does not reach it ---------------------------------------------------------

    #[test]
    fn a_float_is_spelled_as_python_spells_it() {
        for (x, spelled) in [
            (0.0, "0.0"),
            (-0.0, "-0.0"),
            (1.0, "1.0"),
            (0.3, "0.3"),
            (21.0, "21.0"),
            (0.0001, "0.0001"),
            (1e-5, "1e-05"),
            (1.5e-6, "1.5e-06"),
            (1e15, "1000000000000000.0"),
            (1e16, "1e+16"),
            (1.2345e20, "1.2345e+20"),
            (123.456, "123.456"),
            (f64::INFINITY, "inf"),
        ] {
            assert_eq!(py_float_repr(x), spelled, "{x}");
        }
        assert_eq!(py_round(1.0000001), 1.0);
        assert_eq!(
            py_round(0.1234565),
            0.123456,
            "rounded by the binary value, as Python rounds it"
        );
    }

    #[test]
    fn a_string_is_quoted_as_python_quotes_it() {
        assert_eq!(py_str("plain"), "'plain'");
        assert_eq!(py_str("it's"), "\"it's\"");
        assert_eq!(py_str("both ' and \""), "'both \\' and \"'");
        assert_eq!(py_str("a\\b\n\tc\u{1}"), "'a\\\\b\\n\\tc\\x01'");
        assert_eq!(py_str("été"), "'été'");
        assert_eq!(py_str("\u{a0}"), "'\\xa0'");
        assert_eq!(py_tuple(&["x".into()]), "(x,)");
    }
}
