//! WHAT A PERSON MAY STATE IN A CHAT, as `agent/translation/stated.py` holds it: in the words the world's vocabularies
//! declare — a statement made of it, the belief it is taken as, and a statement the agent makes, as the model reads it
//! to say it to a person (a-person-states-what-the-chat-allows-in-the-worlds-words).
//!
//! **A WORD A CHAT ALLOWS IS A PROPERTY A VOCABULARY DECLARES**, `rdf:Property` for every one; a triple is held to its
//! word's bounds — the subject a thing the world states of the property's `rdfs:domain`, the object of its
//! `rdfs:range` — and a triple outside them refuses the statement, the model told why. **ONE STATEMENT PER SUBJECT AND
//! PROPERTY**, a graph named by the two, so a thing said again of a subject replaces what was said of it. **BELIEVED AS
//! THE WORLD'S WORD**: what the statement says is a belief no agent owns, derived from the statement and holding from
//! when it was said.

use std::collections::BTreeMap;
use std::str::FromStr;

use oxigraph::io::{RdfFormat, RdfParser};
use oxigraph::model::vocab::xsd;
use oxigraph::model::{BlankNode, GraphName, Literal, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use oxsdatatypes::{Date, DateTime};
use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat};
use orexis::document::Document;
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED, local_of};
use orexis::store::{Store, Within, iri, value};

use crate::briefing::turtle_of;
use crate::readable::Prefixes;

pub const SPEECH: &str = "http://example.org/orexis/speech#";
const RDF: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
const RDFS: &str = "http://www.w3.org/2000/01/rdf-schema#";
const XSD: &str = "http://www.w3.org/2001/XMLSchema#";
/// EVERY PROPERTY, where a chat allows it: the class every property is.
pub const PROPERTY: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property";
pub const STATE: &str = "state";
/// THE MOST THINGS OF A WORD'S DOMAIN THE MODEL IS TOLD OF, where the chat lets it read none.
pub const THINGS: usize = 40;

const WORDS_Q: &str = "
SELECT ?p (SAMPLE(?l) AS ?label) (SAMPLE(?c) AS ?comment) (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range) WHERE {
  ?p a ?t . VALUES ?t { rdf:Property owl:ObjectProperty owl:DatatypeProperty }
  OPTIONAL { ?p rdfs:label ?l } OPTIONAL { ?p rdfs:comment ?c }
  OPTIONAL { ?p rdfs:domain ?d } OPTIONAL { ?p rdfs:range ?r } } GROUP BY ?p ORDER BY ?p";
const OF_Q: &str =
    "SELECT ?c WHERE { $thing a ?c . FILTER(?c = $class || EXISTS { ?c rdfs:subClassOf $class }) } LIMIT 1";
const THINGS_Q: &str = "SELECT DISTINCT ?i ?label WHERE { ?i a ?c . FILTER(isIRI(?i))
  FILTER(?c = $class || EXISTS { ?c rdfs:subClassOf $class }) OPTIONAL { ?i rdfs:label ?label } } ORDER BY ?i";
const START_Q: &str = "SELECT ?start WHERE { GRAPH $cat { $g dcterms:temporal ?p . ?p orexis:start ?start } } LIMIT 1";
const LABELS_Q: &str = "SELECT ?t ?label ?comment WHERE { VALUES ?t { $terms } OPTIONAL { ?t rdfs:label ?label }
  OPTIONAL { ?t rdfs:comment ?comment } } ORDER BY ?t";

/// A word a person may state: the property, its label and comment, and what it is said of and what it says.
#[derive(Clone, Debug, PartialEq)]
pub struct Word {
    pub iri: String,
    pub label: String,
    pub comment: String,
    pub domain: Option<String>,
    pub range: Option<String>,
}

fn common(store: &Store) -> Result<Vec<String>, Error> {
    store.graphs_of(&[BELIEF], &Within::common())
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

/// The words a chat allowing `allows` lets a person state: each property a vocabulary declares that it names, or every
/// one where it allows `rdf:Property`.
pub fn words(store: &Store, allows: &[String]) -> Result<Vec<Word>, Error> {
    if allows.is_empty() {
        return Ok(Vec::new());
    }
    let every = allows.iter().any(|a| a == PROPERTY);
    let stated = common(store)?;
    Ok(store
        .rows(WORDS_Q, &strs(&stated))?
        .iter()
        .filter_map(|r| {
            let p = iri(r, "p")?;
            (every || allows.contains(&p)).then(|| Word {
                label: value(r, "label").unwrap_or_else(|| local_of(&p)),
                comment: value(r, "comment")
                    .unwrap_or_default()
                    .split_whitespace()
                    .collect::<Vec<_>>()
                    .join(" "),
                domain: iri(r, "domain"),
                range: iri(r, "range"),
                iri: p,
            })
        })
        .collect())
}

/// `iri` as Turtle writes it: by a prefix that covers it, or whole.
pub fn written(iri: &str, prefixes: &Prefixes) -> String {
    let mut by_length: Vec<(&String, &String)> = prefixes.iter().collect();
    by_length.sort_by_key(|(_, ns)| std::cmp::Reverse(ns.len()));
    for (name, ns) in by_length {
        if let Some(tail) = iri.strip_prefix(ns.as_str())
            && !tail.is_empty()
            && tail.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-')
        {
            return format!("{name}:{tail}");
        }
    }
    format!("<{iri}>")
}

/// What the briefing says a person may state: each word, what it is said of and what it says, then the things of its
/// domain where the model reads nothing to find them by — or that any word a vocabulary declares may be.
pub fn listing(
    store: &Store,
    allowed: &[Word],
    every: bool,
    prefixes: &Prefixes,
    things: bool,
) -> Result<String, Error> {
    if every {
        return Ok(
            "A person may state here anything in a word a vocabulary declares, of what its domain says it is \
                   said of, a value its range says it takes."
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" "),
        );
    }
    let stated = common(store)?;
    let mut out = Vec::new();
    for w in allowed {
        let mut line = format!(" - {} ({})", written(&w.iri, prefixes), w.label);
        if let Some(d) = &w.domain {
            line += &format!(", of a {}", written(d, prefixes));
        }
        if let Some(r) = &w.range {
            line += &format!(", a {}", written(r, prefixes));
        }
        if !w.comment.is_empty() {
            line += &format!(": {}", w.comment);
        }
        out.push(line);
        if things && let Some(domain) = &w.domain {
            for t in store
                .rows(
                    &bind(THINGS_Q, &[("class", Value::iri(domain.as_str()))])?,
                    &strs(&stated),
                )?
                .iter()
                .take(THINGS)
            {
                let Some(i) = iri(t, "i") else { continue };
                let label = value(t, "label").map(|l| format!(" ({l})")).unwrap_or_default();
                out.push(format!("     {}{label}", written(&i, prefixes)));
            }
        }
    }
    Ok(format!(
        "A person may state here, in these words alone:\n{}",
        out.join("\n")
    ))
}

/// The tool the model states what a person says with: triples in the words the chat allows, and keys unsaid.
pub fn tool(prefixes: &Prefixes) -> Json {
    let names = prefixes.keys().cloned().collect::<Vec<_>>().join(", ");
    json!({"name": STATE, "description": format!(
        "State what the person says, that the agent then believes as the world's word: triples in Turtle, in the \
words the briefing says a person may state here, of a thing the world names; and unsay what was said of a subject in a \
word. Saying a word of a subject again replaces what was said of it. The agent answers what it kept, or why it refused. \
These prefixes are declared for you: {names}."),
        "input_schema": {"type": "object", "properties": {
            "says": {"type": "string", "description": "the triples, in Turtle, without @prefix lines"},
            "unsays": {"type": "array", "items": {"type": "string"},
                       "description": "each 'subject word' pair what was said of is taken back, as Turtle names"}},
            "additionalProperties": false}})
}

/// What a chat lets a person state, handed to the model's thread with the conversation: the words, whether every word
/// is allowed, and the prefixes a statement is written with.
#[derive(Clone, Debug)]
pub struct Stating {
    pub allowed: Vec<Word>,
    pub every: bool,
    pub prefixes: Prefixes,
}

fn turtle(text: &str) -> Result<Vec<Quad>, String> {
    RdfParser::from_format(RdfFormat::Turtle)
        .for_slice(text.as_bytes())
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| e.to_string())
}

/// The statements a person makes, as the TriG a peer's document is — one graph per subject and word, each triple held
/// to its word's bounds — and the reasons it is refused, where any triple is outside them.
pub fn statement_of(
    store: &Store,
    stating: &Stating,
    inputs: &Json,
    by: &str,
    prose: &str,
    at: DateTime,
) -> Result<(Option<Vec<u8>>, Vec<String>), Error> {
    let head: String = stating
        .prefixes
        .iter()
        .map(|(n, ns)| format!("@prefix {n}: <{ns}> .\n"))
        .collect();
    let says = inputs.get("says").and_then(Json::as_str).unwrap_or_default();
    let said = if says.trim().is_empty() {
        Vec::new()
    } else {
        match turtle(&format!("{head}{says}")) {
            Ok(q) => q,
            Err(e) => return Ok((None, vec![format!("not Turtle: {e}")])),
        }
    };
    let mut unsaid = Vec::new();
    for pair in inputs
        .get("unsays")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default()
    {
        match turtle(&format!("{head}{} [] .", pair.as_str().unwrap_or_default())) {
            Ok(q) => unsaid.extend(q),
            Err(e) => return Ok((None, vec![format!("not Turtle: {e}")])),
        }
    }
    let by_word: BTreeMap<&str, &Word> = stating.allowed.iter().map(|w| (w.iri.as_str(), w)).collect();
    let mut why = Vec::new();
    let mut keys: BTreeMap<(String, String), Vec<Triple>> = BTreeMap::new();
    for q in &said {
        why.extend(outside(store, q, &by_word, stating.every)?);
        let word = by_word.get(q.predicate.as_str());
        keys.entry((subject_text(&q.subject), q.predicate.as_str().to_string()))
            .or_default()
            .push(Triple::new(
                q.subject.clone(),
                q.predicate.clone(),
                typed(&q.object, word.and_then(|w| w.range.as_deref())),
            ));
    }
    for q in &unsaid {
        why.extend(
            outside(store, q, &by_word, stating.every)?
                .into_iter()
                .filter(|w| !w.starts_with("its object")),
        );
        keys.entry((subject_text(&q.subject), q.predicate.as_str().to_string()))
            .or_default();
    }
    if !why.is_empty() || keys.is_empty() {
        if why.is_empty() {
            why.push("nothing is said".into());
        }
        return Ok((None, why));
    }
    let mut quads = Vec::new();
    for ((subject, predicate), triples) in keys {
        let name = format!(
            "urn:uuid:{}",
            uuid::Uuid::new_v5(&uuid::Uuid::NAMESPACE_URL, format!("{subject} {predicate}").as_bytes())
        );
        let g = NamedNode::new_unchecked(&name);
        let into = GraphName::NamedNode(g.clone());
        quads.extend(
            triples
                .into_iter()
                .map(|t| Quad::new(t.subject, t.predicate, t.object, into.clone())),
        );
        quads.push(Quad::new(
            g.clone(),
            NamedNode::new_unchecked(format!("{SPEECH}prose")),
            Literal::new_simple_literal(prose),
            into.clone(),
        ));
        quads.push(Quad::new(
            g.clone(),
            NamedNode::new_unchecked(format!("{SPEECH}saidBy")),
            NamedNode::new_unchecked(by),
            into.clone(),
        ));
        let period = BlankNode::default();
        let dg = GraphName::DefaultGraph;
        quads.push(Quad::new(
            g.clone(),
            NamedNode::new_unchecked(format!("{RDF}type")),
            NamedNode::new_unchecked(format!("{SPEECH}StatementGraph")),
            dg.clone(),
        ));
        quads.push(Quad::new(
            g.clone(),
            NamedNode::new_unchecked("http://purl.org/dc/terms/temporal"),
            period.clone(),
            dg.clone(),
        ));
        quads.push(Quad::new(
            period.clone(),
            NamedNode::new_unchecked(format!("{RDF}type")),
            NamedNode::new_unchecked("http://purl.org/dc/terms/PeriodOfTime"),
            dg.clone(),
        ));
        quads.push(Quad::new(
            period,
            NamedNode::new_unchecked("http://example.org/orexis#start"),
            Literal::new_typed_literal(isoformat(at), xsd::DATE_TIME),
            dg.clone(),
        ));
    }
    Ok((Some(Document::of_quads(quads).trig()?), Vec::new()))
}

fn subject_text(subject: &NamedOrBlankNode) -> String {
    match subject {
        NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
        other => other.to_string(),
    }
}

/// Why one triple is outside what the chat allows and its word's bounds: nothing, where it is within them.
fn outside(store: &Store, q: &Quad, by_word: &BTreeMap<&str, &Word>, every: bool) -> Result<Vec<String>, Error> {
    let p = q.predicate.as_str();
    let Some(word) = by_word.get(p) else {
        let tail = if every {
            String::new()
        } else {
            let mut names: Vec<String> = by_word.keys().map(|w| local_of(w)).collect();
            names.sort();
            format!(": {}", names.join(", "))
        };
        return Ok(vec![format!(
            "{} is no word a person may state here{tail}",
            local_of(p)
        )]);
    };
    let stated = common(store)?;
    let of = |thing: &str, class: &str| -> Result<bool, Error> {
        Ok(!store
            .rows(
                &bind(OF_Q, &[("thing", Value::iri(thing)), ("class", Value::iri(class))])?,
                &strs(&stated),
            )?
            .is_empty())
    };
    let NamedOrBlankNode::NamedNode(s) = &q.subject else {
        return Ok(vec![format!("{} is said of no thing the world names", local_of(p))]);
    };
    if let Some(domain) = &word.domain
        && !of(s.as_str(), domain)?
    {
        return Ok(vec![format!(
            "{} is no {}, which {} is said of",
            local_of(s.as_str()),
            local_of(domain),
            local_of(p)
        )]);
    }
    let Some(range) = word.range.as_deref().filter(|r| *r != format!("{RDFS}Literal")) else {
        return Ok(Vec::new());
    };
    if let Some(kind) = range.strip_prefix(XSD) {
        let Term::Literal(o) = &q.object else {
            return Ok(vec![format!("its object for {} is no {kind}", local_of(p))]);
        };
        if o.datatype().as_str() != range && !lexical(kind, o.value()) {
            return Ok(vec![format!(
                "its object for {}, '{}', is no {kind}",
                local_of(p),
                o.value()
            )]);
        }
        return Ok(Vec::new());
    }
    match &q.object {
        Term::NamedNode(o) if of(o.as_str(), range)? => Ok(Vec::new()),
        _ => Ok(vec![format!(
            "its object for {} is no {} the world names",
            local_of(p),
            local_of(range)
        )]),
    }
}

/// Whether `text` is a literal of the datatype `kind`, as Python's reading of it would take it; a datatype nothing here
/// reads takes anything.
fn lexical(kind: &str, text: &str) -> bool {
    match kind {
        "integer" => text.trim().parse::<i64>().is_ok(),
        "decimal" | "double" | "float" => text.trim().parse::<f64>().is_ok(),
        "boolean" => text == "true" || text == "false",
        "dateTime" => instant(text).is_ok(),
        "date" => Date::from_str(text).is_ok() || DateTime::from_str(text).is_ok(),
        _ => true,
    }
}

/// A plain literal of a word whose range is another datatype, as that datatype, so a person's "18:00" said of an
/// instant is believed as one.
fn typed(term: &Term, range: Option<&str>) -> Term {
    match (term, range) {
        (Term::Literal(l), Some(range))
            if range.starts_with(XSD) && range != format!("{XSD}string") && l.datatype() == xsd::STRING =>
        {
            Literal::new_typed_literal(l.value(), NamedNode::new_unchecked(range)).into()
        }
        _ => term.clone(),
    }
}

/// Where what a person's statement says is believed: a graph derived from it.
pub fn believed_of(statement: &str) -> String {
    format!(
        "urn:uuid:{}",
        uuid::Uuid::new_v5(&uuid::Uuid::NAMESPACE_URL, format!("{statement} believed").as_bytes())
    )
}

/// What `statement` says, believed as the world's word: its triples in a belief no agent owns, derived from it and
/// holding from when it was said, replacing what was believed of it before. The graph written, or none where it says
/// nothing.
pub fn believe(store: &Store, statement: &str) -> Result<Vec<String>, Error> {
    let target = believed_of(statement);
    store.forget_graph(&target, Some(BELIEF))?;
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let node = NamedNode::new_unchecked(statement);
    let found: Vec<Quad> = store
        .quads(statement)?
        .into_iter()
        .filter(|q| !matches!(&q.subject, NamedOrBlankNode::NamedNode(s) if *s == node))
        .collect();
    if found.is_empty() {
        return Ok(Vec::new());
    }
    let into = GraphName::NamedNode(NamedNode::new_unchecked(&target));
    store.add(
        found
            .into_iter()
            .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone())),
    )?;
    let start = store
        .rows(
            &bind(
                START_Q,
                &[("cat", Value::iri(cat.as_str())), ("g", Value::iri(statement))],
            )?,
            &[],
        )?
        .first()
        .and_then(|r| value(r, "start"))
        .map(|s| instant(&s))
        .transpose()?;
    let entry = store.entry(&target, &[BELIEF], DERIVED, None, start, None)?;
    store.update(&format!(
        "INSERT DATA {{ {entry}\n  GRAPH <{cat}> {{ <{target}> prov:wasDerivedFrom <{statement}> }} }}"
    ))?;
    hash_named_graph(store, &target, None)?;
    Ok(vec![target])
}

/// A statement as the model reads it to say it to a person: its graphs' triples in Turtle, then what each word and
/// thing in it is, by its label and the first sentence of its comment.
pub fn rendered(store: &Store, doc: &Document, prefixes: &Prefixes) -> Result<String, Error> {
    let triples: Vec<Triple> = doc
        .quads()
        .iter()
        .filter(|q| q.graph_name != GraphName::DefaultGraph)
        .map(|q| Triple::new(q.subject.clone(), q.predicate.clone(), q.object.clone()))
        .collect();
    let mut terms: Vec<String> = Vec::new();
    for t in &triples {
        if let NamedOrBlankNode::NamedNode(s) = &t.subject {
            terms.push(s.as_str().to_string());
        }
        terms.push(t.predicate.as_str().to_string());
        if let Term::NamedNode(o) = &t.object {
            terms.push(o.as_str().to_string());
        }
    }
    terms.sort();
    terms.dedup();
    let pairs: Vec<(String, String)> = prefixes.iter().map(|(a, b)| (a.clone(), b.clone())).collect();
    let mut out = turtle_of(&triples, &pairs)?;
    if !terms.is_empty() {
        let stated = common(store)?;
        let values = terms.iter().map(|t| format!("<{t}>")).collect::<Vec<_>>().join(" ");
        let found = store.rows(&bind(LABELS_Q, &[("terms", Value::raw(values))])?, &strs(&stated))?;
        let words: Vec<String> = found
            .iter()
            .filter(|r| r.contains_key("label") || r.contains_key("comment"))
            .filter_map(|r| {
                let t = iri(r, "t")?;
                let comment = value(r, "comment")
                    .map(|c| format!(" — {}", c.split(". ").next().unwrap_or_default()))
                    .unwrap_or_default();
                Some(format!(
                    " - {}: {}{comment}",
                    local_of(&t),
                    value(r, "label").unwrap_or_default()
                ))
            })
            .collect();
        if !words.is_empty() {
            out += &format!("\nThe words in it:\n{}", words.join("\n"));
        }
    }
    Ok(out)
}
