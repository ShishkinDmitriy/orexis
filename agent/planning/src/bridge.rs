//! A BRIDGE: a rule of the store that concludes ONE triple of a vocabulary from another's, run backwards — as
//! `agent/planning/bridge.py` reads it, off the rule's text. A step whose predicted fact a bridge's head binds is
//! refined: what it comes to one level down is the bridge's WHERE with the head's variables bound
//! (the-hierarchy-is-found-in-the-rules). A transition is no bridge, and a rule of two head triples or binding a head
//! variable by `BIND` is not run backwards.

use std::collections::BTreeMap;
use std::sync::LazyLock;

use oxigraph::model::{Term, Triple};
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Store, Within, iri, value};
use orexis_belief::ontology::RULES_GRAPH;

use crate::admit::local_of;

const RULES_Q: &str = "
SELECT ?rule ?text WHERE { ?rule a sh:SPARQLRule ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true }
                           FILTER NOT EXISTS { ?rule a belief:Transition } } ORDER BY ?rule";

/// THE TWO GRAPHS A STEP PREDICTS IN, wherever its plan is.
const PREDICTED_Q: &str = "
SELECT ?adds ?retracts WHERE {
  OPTIONAL { GRAPH ?a { $step execution:adds ?adds } }
  OPTIONAL { GRAPH ?r { $step execution:retracts ?retracts } } } LIMIT 1";

static PREFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?im)^\s*PREFIX\s+(?:[A-Za-z][\w.-]*)?\s*:\s*<[^>]*>\s*$").expect("a valid pattern"));
static PREFIX_PARTS: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)^\s*PREFIX\s+([A-Za-z][\w.-]*)?\s*:\s*<([^>]*)>").expect("a valid pattern"));
const TERM: &str = r"(\?\w+|<[^>]+>|(?:[A-Za-z][\w.-]*)?:[\w.-]*|a)";
static HEAD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(&format!(r"^\s*{TERM}\s+{TERM}\s+{TERM}\s*\.?\s*$")).expect("a valid pattern"));
static CONSTRUCT: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?is)^CONSTRUCT\s*\{").expect("a valid pattern"));
static WHERE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?is)^WHERE\s*\{").expect("a valid pattern"));

/// One bridge: its PREFIX lines, its head `(s, p, o)` as written, its WHERE body, and the names it may spell.
#[derive(Clone, Debug)]
pub struct Bridge {
    pub declared: Vec<String>,
    pub head: (String, String, String),
    pub r#where: String,
    pub names: BTreeMap<String, String>,
}

/// Every bridge the store holds.
pub fn heads(store: &Store) -> Result<Vec<Bridge>, Error> {
    let graphs = store.graphs_of(&[RULES_GRAPH], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let mut out = Vec::new();
    for row in store.rows(RULES_Q, &graphs)? {
        let (Some(rule), Some(text)) = (iri(&row, "rule"), value(&row, "text")) else {
            continue;
        };
        if let Some((declared, head, r#where)) = parse(&text, &rule) {
            let names = names(store, &declared);
            out.push(Bridge {
                declared,
                head,
                r#where,
                names,
            });
        }
    }
    Ok(out)
}

/// Whether `step` is kept below: a bridge's head binds a fact the step predicts its world gains.
pub fn keeps(store: &Store, step: &str) -> Result<bool, Error> {
    let found = heads(store)?;
    let (adds, _) = predicted(store, step)?;
    Ok(adds
        .iter()
        .any(|f| found.iter().any(|b| binding(&b.head, f, &b.names).is_some())))
}

/// What `step` predicts, the facts of the graph it adds and of the one it retracts, each sorted as Python sorts a
/// tuple of pyoxigraph's terms.
pub fn predicted(store: &Store, step: &str) -> Result<(Vec<Triple>, Vec<Triple>), Error> {
    let found = store.rows(&bind(PREDICTED_Q, &[("step", Value::iri(step))])?, &[])?;
    let row = found.first();
    let facts = |side: &str| -> Result<Vec<Triple>, Error> {
        match row.and_then(|r| iri(r, side)) {
            Some(g) => Ok(sorted(store.triples(&g)?)),
            None => Ok(Vec::new()),
        }
    };
    Ok((facts("adds")?, facts("retracts")?))
}

/// Triples sorted by Python's `str` of the tuple of their pyoxigraph terms.
pub fn sorted(mut triples: Vec<Triple>) -> Vec<Triple> {
    triples.sort_by_cached_key(repr);
    triples
}

fn term_repr(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => format!("<NamedNode value={}>", n.as_str()),
        Term::BlankNode(b) => format!("<BlankNode value={}>", b.as_str()),
        Term::Literal(l) => match l.language() {
            Some(language) => format!("<Literal value={} language={language}>", l.value()),
            None => format!(
                "<Literal value={} datatype=<NamedNode value={}>>",
                l.value(),
                l.datatype().as_str()
            ),
        },
        #[allow(unreachable_patterns)]
        other => other.to_string(),
    }
}

/// A triple as Python's `str` of its terms' tuple.
pub fn repr(t: &Triple) -> String {
    let subject: Term = t.subject.clone().into();
    let predicate: Term = t.predicate.clone().into();
    format!(
        "({}, {}, {})",
        term_repr(&subject),
        term_repr(&predicate),
        term_repr(&t.object)
    )
}

/// A rule as its PREFIX lines, its one head triple and its WHERE body — or None, said, where it cannot be run back.
/// A rule's PREFIX lines, its head and its WHERE.
type Parsed = (Vec<String>, (String, String, String), String);

fn parse(text: &str, rule: &str) -> Option<Parsed> {
    let declared: Vec<String> = PREFIX.find_iter(text).map(|m| m.as_str().trim().to_string()).collect();
    let body = PREFIX.replace_all(text, "").trim().to_string();
    let m = CONSTRUCT.find(&body)?;
    let head_end = closing(&body, m.end() - 1)?;
    let template = body[m.end()..head_end].trim();
    let rest = body[head_end + 1..].trim();
    let w = WHERE.find(rest)?;
    let r#where = rest[w.end()..closing(rest, w.end() - 1)?].trim().to_string();
    let Some(head) = HEAD.captures(template) else {
        log::warn!(
            "{} concludes more than one triple and is not run backwards",
            local_of(rule)
        );
        return None;
    };
    let head = (head[1].to_string(), head[2].to_string(), head[3].to_string());
    for var in [&head.0, &head.1, &head.2].into_iter().filter(|t| t.starts_with('?')) {
        let bound = Regex::new(&format!(r"(?i)\bAS\s+\{var}\b")).expect("a valid pattern");
        if bound.is_match(&r#where) {
            log::warn!("{} binds {var} with BIND and is not run backwards", local_of(rule));
            return None;
        }
    }
    Some((declared, head, r#where))
}

/// The index of the brace closing the one at `opening`, strings skipped.
fn closing(text: &str, opening: usize) -> Option<usize> {
    let bytes = text.as_bytes();
    let (mut depth, mut i, mut quote) = (0i32, opening, None::<u8>);
    while i < bytes.len() {
        let c = bytes[i];
        if let Some(q) = quote {
            if c == b'\\' {
                i += 2;
                continue;
            }
            if c == q {
                quote = None;
            }
        } else if c == b'"' || c == b'\'' {
            quote = Some(c);
        } else if c == b'{' {
            depth += 1;
        } else if c == b'}' {
            depth -= 1;
            if depth == 0 {
                return Some(i);
            }
        }
        i += 1;
    }
    None
}

/// The rule's own PREFIX lines as a map, over the store's.
fn names(store: &Store, declared: &[String]) -> BTreeMap<String, String> {
    let mut out: BTreeMap<String, String> = store
        .namespaces()
        .iter()
        .map(|(l, i)| (l.to_string(), i.to_string()))
        .collect();
    for line in declared {
        if let Some(m) = PREFIX_PARTS.captures(line) {
            out.insert(m.get(1).map_or("", |g| g.as_str()).to_string(), m[2].to_string());
        }
    }
    out
}

/// The head's variables bound to one predicted fact, as SPARQL text; None where the head does not conclude it.
pub fn binding(
    head: &(String, String, String),
    fact: &Triple,
    names: &BTreeMap<String, String>,
) -> Option<BTreeMap<String, String>> {
    let (s, p, o) = head;
    if expand(p, names)? != fact.predicate.as_str() {
        return None;
    }
    let subject: Term = fact.subject.clone().into();
    let mut bound: BTreeMap<String, String> = BTreeMap::new();
    for (term, value) in [(s, &subject), (o, &fact.object)] {
        let rendered = render(value)?;
        if let Some(var) = term.strip_prefix('?') {
            if bound.entry(var.to_string()).or_insert_with(|| rendered.clone()) != &rendered {
                return None;
            }
        } else {
            let named = match value {
                Term::NamedNode(n) => Some(n.as_str().to_string()),
                _ => None,
            };
            if expand(term, names) != named {
                return None;
            }
        }
    }
    Some(bound)
}

/// A head's predicate or constant as a full IRI, through the rule's prefixes.
pub fn expand(term: &str, names: &BTreeMap<String, String>) -> Option<String> {
    if let Some(inner) = term.strip_prefix('<') {
        return Some(inner.trim_end_matches('>').to_string());
    }
    if term == "a" {
        return Some("http://www.w3.org/1999/02/22-rdf-syntax-ns#type".into());
    }
    if !term.starts_with('?')
        && let Some((label, local)) = term.split_once(':')
    {
        return names.get(label).map(|ns| format!("{ns}{local}"));
    }
    None
}

/// A term as SPARQL: an IRI in angles, a literal in its N-Triples form; a blank node is refused.
fn render(value: &Term) -> Option<String> {
    match value {
        Term::NamedNode(_) | Term::Literal(_) => Some(value.to_string()),
        _ => None,
    }
}

/// A text as a triple-quoted SPARQL literal.
pub fn literal(text: &str) -> String {
    format!("\"\"\"{}\"\"\"", text.replace('\\', "\\\\").replace('"', "\\\""))
}

#[cfg(test)]
mod tests;
