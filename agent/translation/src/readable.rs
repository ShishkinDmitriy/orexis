//! WHAT A CHAT MAY READ, as `agent/translation/readable.py` copies it: the graphs of every kind the chat `speech:reads`,
//! copied under their names for the model's queries, and the two tools that read it, `vocabulary` and `query`
//! (the-model-queries-what-its-chat-may-read).
//!
//! **THE CHAT SAYS WHAT IT READS, AND THE MODEL NEVER CHOOSES A GRAPH.** The graphs of its kinds are COPIED on the mind's
//! thread, each under its own name with the catalogue's rows about it, so a query runs over what the chat admits and
//! nothing else, and a slow one stalls the model's thread and never a pass. **A QUERY STATES THE KINDS IT READS**: their
//! graphs are its default graph and its `GRAPH` range, and the catalogue is named beside them and never merged into
//! them. **A QUERY IS READ, AND REFUSED BEFORE IT RUNS WHERE IT COULD DO ANYTHING BUT READ**: anything but a SELECT or
//! an ASK, and a `SERVICE` or a `FROM` anywhere in it, is refused with the reason. Its rows are capped at `ROWS`.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::{GraphName, NamedNode, NamedOrBlankNode, Quad, Term};
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;
use regex::Regex;
use serde_json::{Value as Json, json};
use spargebra::Query;
use spargebra::algebra::{Expression, GraphPattern};

use orexis::Error;
use orexis::ontology::{CLOSURE_GRAPH, ONTOLOGY, local_of};
use orexis::store::{Store, Within};

/// HOW MANY ROWS A QUERY HANDS THE MODEL: past these it is told how many there were.
pub const ROWS: usize = 50;
pub const VOCABULARY: &str = "vocabulary";
pub const QUERY: &str = "query";
const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
/// HOW LONG A GLOSSARY'S SENTENCE MAY RUN: past it the sentence is cut, and the query tool reads the rest.
pub const SENTENCE: usize = 200;

/// The prefixes a chat's rows are written with, by name.
pub type Prefixes = BTreeMap<String, String>;

/// The store's own prefixes, as `NAMESPACES` names them.
pub fn namespaces(store: &Store) -> Prefixes {
    store
        .namespaces()
        .iter()
        .map(|(l, i)| (l.to_string(), i.to_string()))
        .collect()
}

/// What one chat may read: the graphs of its kinds, copied, and each vocabulary among them by its prefix.
pub struct Readable {
    pub store: Engine,
    pub prefixes: Prefixes,
    /// Each kind a copied graph is, and the graphs it is.
    pub kinds: BTreeMap<String, BTreeSet<String>>,
    pub catalogues: BTreeSet<String>,
    pub world: Option<String>,
    pub vocabularies: BTreeMap<String, String>,
}

fn failed(e: impl std::fmt::Display) -> Error {
    Error::Evaluation(e.to_string())
}

/// The namespace of an IRI: up to its last `#` or `/`.
pub fn namespace_of(iri: &str) -> &str {
    &iri[..iri.rfind(['#', '/']).map_or(0, |i| i + 1)]
}

/// A prefix for `ns`: its last word, made apart from every name in `taken`.
pub fn named(ns: &str, taken: &BTreeSet<String>) -> String {
    let trimmed = ns.trim_end_matches(['#', '/']);
    let mut name = trimmed.rsplit('/').next().unwrap_or_default().to_string();
    if name.is_empty() {
        name = "world".into();
    }
    while taken.contains(&name) {
        name.push('_');
    }
    name
}

impl Readable {
    /// What `kinds` let a chat of the agent `me` read of `store`, copied now, on the mind's thread.
    pub fn new(store: &Store, kinds: &[String], me: Option<&str>) -> Result<Self, Error> {
        let engine = Engine::new().map_err(failed)?;
        let mut prefixes = namespaces(store);
        let mut by_kind: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        let mut catalogues = BTreeSet::new();
        let mut read: BTreeMap<String, Vec<Quad>> = BTreeMap::new();
        let ontologies: BTreeSet<String> = store
            .graphs_of(&[ONTOLOGY], &Within::default())?
            .into_iter()
            .filter(|g| g != CLOSURE_GRAPH)
            .collect();
        let catalogue = store.catalogue()?;
        let kinds: Vec<&str> = kinds.iter().map(String::as_str).collect();
        for graph in store.graphs_of(&kinds, &Within::default())? {
            let quads = store.quads(&graph)?;
            engine.extend(quads.iter().cloned()).map_err(failed)?;
            if let Some(catalogue) = &catalogue {
                let described = described(store, &graph, catalogue)?;
                engine.extend(described.iter().cloned()).map_err(failed)?;
                catalogues.insert(catalogue.clone());
                for q in &described {
                    if matches!(&q.subject, NamedOrBlankNode::NamedNode(s) if s.as_str() == graph)
                        && q.predicate.as_str() == RDF_TYPE
                        && let Term::NamedNode(kind) = &q.object
                    {
                        by_kind
                            .entry(kind.as_str().to_string())
                            .or_default()
                            .insert(graph.clone());
                    }
                }
            }
            if ontologies.contains(&graph) && !quads.is_empty() {
                let (mut name, ns) = prefix_of(store, &quads).unwrap_or_else(|| (local_of(&graph), String::new()));
                while read.contains_key(&name) {
                    name.push('_');
                }
                if !ns.is_empty() && !prefixes.values().any(|v| *v == ns) && !prefixes.contains_key(&name) {
                    prefixes.insert(name.clone(), ns);
                }
                read.insert(name, quads);
            }
        }
        let world = me.map(|me| {
            let ns = namespace_of(me).to_string();
            let taken: BTreeSet<String> = prefixes.keys().chain(read.keys()).cloned().collect();
            let name = named(&ns, &taken);
            prefixes.insert(name.clone(), ns);
            name
        });
        let mut readable = Readable {
            store: engine,
            prefixes,
            kinds: by_kind,
            catalogues,
            world,
            vocabularies: BTreeMap::new(),
        };
        let vocabularies: BTreeMap<String, String> = read
            .iter()
            .map(|(name, quads)| Ok((name.clone(), glossary(quads, &readable.prefixes)?)))
            .collect::<Result<_, Error>>()?;
        readable.vocabularies = vocabularies;
        Ok(readable)
    }

    /// The two tools the model reads the chat's graphs with, each answered by `call`.
    pub fn tools(&self) -> Vec<Json> {
        let prefixes = self.prefixes.keys().cloned().collect::<Vec<_>>().join(", ");
        let world = self
            .world
            .as_ref()
            .map(|w| format!(", {w}: naming the agent's own world"))
            .unwrap_or_default();
        vec![
            json!({"name": VOCABULARY, "description": "One vocabulary this chat lets you read, as a glossary: each class and \
property, a class with what it is beneath and a property with its domain and range, then the first sentence of what it \
means. Load the ones a question needs before querying their terms; a term's whole rdfs:comment, and anything else the \
vocabulary states, is read with the query tool.", "input_schema": {"type": "object", "properties": {"name": {
                "type": "string", "description": "the vocabulary's name, as the briefing lists it"}}, "required": ["name"]}}),
            json!({"name": QUERY, "description": format!("A SPARQL SELECT or ASK over the graphs of the kinds you name, of those \
the briefing lists: their union is the default graph, so name the kinds the question is about — observations, forecasts, \
the world's documents — and not more. GRAPH ?g ranges over those graphs, each named for its document, and over the \
catalogue, whose rows say of each graph its kinds (a), how it arrived (orexis:arrivedBy), whose it is (orexis:ownedBy) \
and when it holds (dcterms:temporal): where a belief came from is `GRAPH ?g {{ …the belief… }} GRAPH ?c {{ ?g \
orexis:arrivedBy ?how }}`. These prefixes are declared for you: {prefixes}{world}; declare any other with PREFIX. The \
rows write a name with them, as the vocabularies do. Write no SERVICE or FROM. At most {ROWS} rows come back."),
             "input_schema": {"type": "object", "properties": {
                 "kinds": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                           "description": "the kinds of graph the query reads, as the briefing names them"},
                 "sparql": {"type": "string"}}, "required": ["kinds", "sparql"]}}),
        ]
    }

    /// What one of the two tools answers, or None where `name` is neither.
    pub fn call(&self, name: &str, inputs: &Json) -> Option<String> {
        match name {
            VOCABULARY => Some(self.vocabulary(inputs.get("name").and_then(Json::as_str).unwrap_or_default())),
            QUERY => {
                let kinds: Vec<String> = inputs
                    .get("kinds")
                    .and_then(Json::as_array)
                    .map(|k| k.iter().filter_map(|v| v.as_str().map(str::to_string)).collect())
                    .unwrap_or_default();
                Some(self.query(inputs.get("sparql").and_then(Json::as_str).unwrap_or_default(), &kinds))
            }
            _ => None,
        }
    }

    /// What the model chooses from: each vocabulary the chat may read, by its prefix, with how many terms it has,
    /// then each kind of graph a query may name, with how many graphs are of it.
    pub fn listing(&self) -> String {
        let vocabularies: Vec<String> = self
            .vocabularies
            .iter()
            .map(|(name, text)| format!(" - {name} ({} terms)", text.lines().count()))
            .collect();
        let kinds: Vec<String> = self
            .kinds
            .iter()
            .map(|(kind, graphs)| format!(" - {} ({} graphs)", self.iri(kind), graphs.len()))
            .collect();
        format!(
            "Vocabularies, loaded by name:\n{}\nKinds of graph, named by a query:\n{}",
            vocabularies.join("\n"),
            kinds.join("\n")
        )
    }

    /// One vocabulary the chat may read, as its glossary; told so where it reads none of that name.
    pub fn vocabulary(&self, name: &str) -> String {
        let name = name.trim().trim_end_matches(':');
        match self.vocabularies.get(name) {
            Some(found) => found.clone(),
            None => format!(
                "no vocabulary '{name}' in this chat; these are: {}",
                self.vocabularies.keys().cloned().collect::<Vec<_>>().join(", ")
            ),
        }
    }

    /// The model's SELECT or ASK over the graphs of `kinds`, the catalogue named beside them, its rows as lines; the
    /// reason, where it is refused.
    pub fn query(&self, text: &str, kinds: &[String]) -> String {
        if let Some(why) = refusal(text, &self.prefixes) {
            return format!("refused: {why}");
        }
        let mut graphs: BTreeSet<String> = BTreeSet::new();
        for kind in kinds {
            match self.kinds.get(&self.expanded(kind)) {
                Some(found) => graphs.extend(found.iter().cloned()),
                None => {
                    let listed = self.kinds.keys().map(|k| self.iri(k)).collect::<Vec<_>>().join(", ");
                    return format!("refused: no graph of kind {kind} in this chat; these are: {listed}");
                }
            }
        }
        if graphs.is_empty() {
            return "refused: name the kinds of graph the query reads".into();
        }
        let named: BTreeSet<String> = graphs.union(&self.catalogues).cloned().collect();
        match run(&self.store, text, &self.prefixes, Some(&graphs), Some(&named)) {
            Ok(answer) => answer,
            Err(e) => format!("the engine would not run it: {e}"),
        }
    }

    /// A name the model wrote — `prefix:local`, `<iri>` or an IRI — as the IRI it is.
    pub fn expanded(&self, name: &str) -> String {
        let name = name.trim();
        if name.starts_with('<') && name.ends_with('>') {
            return name[1..name.len() - 1].to_string();
        }
        match name.split_once(':') {
            Some((prefix, local)) if !local.starts_with("//") && self.prefixes.contains_key(prefix) => {
                format!("{}{local}", self.prefixes[prefix])
            }
            _ => name.to_string(),
        }
    }

    fn iri(&self, iri: &str) -> String {
        written(&Term::NamedNode(NamedNode::new_unchecked(iri)), &self.prefixes)
    }
}

/// `text`, a SELECT or an ASK, over `store` with `prefixes` declared — over the union of `graphs` as its default graph
/// and `named` as its `GRAPH` range where given, every graph's union otherwise — answered as the model reads it.
pub fn run(
    store: &Engine,
    text: &str,
    prefixes: &Prefixes,
    graphs: Option<&BTreeSet<String>>,
    named: Option<&BTreeSet<String>>,
) -> Result<String, Error> {
    let mut evaluator = SparqlEvaluator::new();
    for (name, iri) in prefixes {
        evaluator = evaluator.with_prefix(name, iri).map_err(failed)?;
    }
    let mut query = evaluator.parse_query(text).map_err(failed)?;
    match graphs {
        Some(graphs) => {
            query.dataset_mut().set_default_graph(
                graphs
                    .iter()
                    .map(|g| GraphName::NamedNode(NamedNode::new_unchecked(g)))
                    .collect(),
            );
            if let Some(named) = named {
                query.dataset_mut().set_available_named_graphs(
                    named
                        .iter()
                        .map(|g| NamedOrBlankNode::NamedNode(NamedNode::new_unchecked(g)))
                        .collect(),
                );
            }
        }
        None => query.dataset_mut().set_default_graph_as_union(),
    }
    let results = query.on_store(store).execute().map_err(failed)?;
    answered(results, prefixes)
}

/// A query's result as the model reads it: an ASK's truth, or a row per line with each value written with `prefixes`,
/// the rows capped at `ROWS` and their count said past it.
pub fn answered(results: QueryResults<'_>, prefixes: &Prefixes) -> Result<String, Error> {
    match results {
        QueryResults::Boolean(b) => Ok(b.to_string()),
        QueryResults::Solutions(solutions) => {
            let mut rows = Vec::new();
            for solution in solutions {
                let solution = solution.map_err(failed)?;
                rows.push(
                    solution
                        .iter()
                        .map(|(v, t)| format!("{}: {}", v.as_str(), written(t, prefixes)))
                        .collect::<Vec<_>>()
                        .join(", "),
                );
            }
            let total = rows.len();
            let shown: Vec<String> = rows.into_iter().take(ROWS).collect();
            let more = if total > ROWS {
                format!("\n(the first {ROWS} of {total} rows: ask more narrowly)")
            } else {
                String::new()
            };
            Ok(if shown.is_empty() {
                "(no rows)".to_string()
            } else {
                shown.join("\n")
            } + &more)
        }
        QueryResults::Graph(_) => Err(Error::Evaluation("only a SELECT or an ASK is run".into())),
    }
}

/// One value of a row as the model reads it: an IRI by the longest of `prefixes` it is under, whole where none fits; a
/// literal by its text on one line, so a row stays one.
pub fn written(term: &Term, prefixes: &Prefixes) -> String {
    let local = Regex::new(r"^[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?$").expect("a pattern");
    match term {
        Term::NamedNode(n) => {
            let iri = n.as_str();
            let mut by_length: Vec<(&String, &String)> = prefixes.iter().collect();
            by_length.sort_by_key(|(_, ns)| std::cmp::Reverse(ns.len()));
            for (prefix, ns) in by_length {
                if let Some(tail) = iri.strip_prefix(ns.as_str())
                    && local.is_match(tail)
                {
                    return format!("{prefix}:{tail}");
                }
            }
            format!("<{iri}>")
        }
        Term::Literal(l) => l.value().split_whitespace().collect::<Vec<_>>().join(" "),
        Term::BlankNode(b) => b.as_str().to_string(),
        #[allow(unreachable_patterns)]
        other => other.to_string(),
    }
}

/// What the catalogue says of one graph the chat reads — its kinds, how it arrived, whose it is, when it holds — and of
/// each blank node it says that through, kept in the catalogue's name.
fn described(store: &Store, graph: &str, catalogue: &str) -> Result<Vec<Quad>, Error> {
    let cat = NamedNode::new_unchecked(catalogue);
    let mut found = Vec::new();
    let mut todo: Vec<NamedOrBlankNode> = vec![NamedNode::new_unchecked(graph).into()];
    let mut seen: BTreeSet<String> = BTreeSet::new();
    while let Some(node) = todo.pop() {
        if !seen.insert(node.to_string()) {
            continue;
        }
        for q in store
            .engine()
            .quads_for_pattern(Some(node.as_ref()), None, None, Some(cat.as_ref().into()))
        {
            let q = q.map_err(failed)?;
            if let Term::BlankNode(b) = &q.object {
                todo.push(b.clone().into());
            }
            found.push(q);
        }
    }
    Ok(found)
}

/// Why a query may not run: not parsed, not a SELECT or an ASK, or holding what reads past the chat.
pub fn refusal(text: &str, prefixes: &Prefixes) -> Option<String> {
    let head: String = prefixes.iter().map(|(p, ns)| format!("PREFIX {p}: <{ns}>\n")).collect();
    let query = match spargebra::SparqlParser::new().parse_query(&format!("{head}{text}")) {
        Ok(q) => q,
        Err(e) => return Some(format!("it does not parse: {e}")),
    };
    let (dataset, pattern) = match &query {
        Query::Select { dataset, pattern, .. } | Query::Ask { dataset, pattern, .. } => (dataset, pattern),
        _ => return Some("only a SELECT or an ASK is run".into()),
    };
    if dataset.is_some() {
        return Some("it holds a FROM, and a query reads only what the chat reads".into());
    }
    if serviced(pattern) {
        return Some("it holds a SERVICE clause, and a query reads only what the chat reads".into());
    }
    None
}

/// Whether a SERVICE clause is anywhere under `pattern`, inside an EXISTS among them.
fn serviced(pattern: &GraphPattern) -> bool {
    use GraphPattern as G;
    match pattern {
        G::Service { .. } => true,
        G::Join { left, right } | G::Union { left, right } | G::Minus { left, right } => {
            serviced(left) || serviced(right)
        }
        G::LeftJoin {
            left,
            right,
            expression,
        } => serviced(left) || serviced(right) || expression.as_ref().is_some_and(exists_serviced),
        G::Filter { expr, inner } => exists_serviced(expr) || serviced(inner),
        G::Extend { inner, expression, .. } => exists_serviced(expression) || serviced(inner),
        G::Graph { inner, .. }
        | G::OrderBy { inner, .. }
        | G::Project { inner, .. }
        | G::Distinct { inner }
        | G::Reduced { inner }
        | G::Slice { inner, .. }
        | G::Group { inner, .. } => serviced(inner),
        _ => false,
    }
}

fn exists_serviced(expression: &Expression) -> bool {
    use Expression as E;
    match expression {
        E::Exists(pattern) => serviced(pattern),
        E::Or(a, b)
        | E::And(a, b)
        | E::Equal(a, b)
        | E::SameTerm(a, b)
        | E::Greater(a, b)
        | E::GreaterOrEqual(a, b)
        | E::Less(a, b)
        | E::LessOrEqual(a, b)
        | E::Add(a, b)
        | E::Subtract(a, b)
        | E::Multiply(a, b)
        | E::Divide(a, b) => exists_serviced(a) || exists_serviced(b),
        E::UnaryPlus(a) | E::UnaryMinus(a) | E::Not(a) => exists_serviced(a),
        E::If(a, b, c) => exists_serviced(a) || exists_serviced(b) || exists_serviced(c),
        E::In(a, list) => exists_serviced(a) || list.iter().any(exists_serviced),
        E::Coalesce(list) | E::FunctionCall(_, list) => list.iter().any(exists_serviced),
        _ => false,
    }
}

/// The name a vocabulary goes by, and its namespace: the store's prefix for the namespace most of its subjects are
/// named in, or the namespace's last word where the store has none for it.
fn prefix_of(store: &Store, quads: &[Quad]) -> Option<(String, String)> {
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    let mut order: Vec<String> = Vec::new();
    for q in quads {
        if let NamedOrBlankNode::NamedNode(s) = &q.subject {
            let ns = namespace_of(s.as_str()).to_string();
            if !counts.contains_key(&ns) {
                order.push(ns.clone());
            }
            *counts.entry(ns).or_default() += 1;
        }
    }
    //  THE FIRST OF THE MOST, as Python's `max` over a dict in the order its keys came.
    let most = order
        .iter()
        .max_by(|a, b| counts[*a].cmp(&counts[*b]).then(std::cmp::Ordering::Greater))?
        .clone();
    let known = store
        .namespaces()
        .iter()
        .find(|(_, iri)| *iri == most)
        .map(|(l, _)| l.to_string());
    let name = known.unwrap_or_else(|| {
        most.trim_end_matches(['#', '/'])
            .rsplit('/')
            .next()
            .unwrap_or_default()
            .to_string()
    });
    (!name.is_empty()).then_some((name, most))
}

/// WHAT A GLOSSARY SAYS OF A TERM: its kind, one class it is beneath or a property's domain and range, and its comment.
const GLOSSARY_Q: &str = "
SELECT ?term (SAMPLE(?k) AS ?kind) (SAMPLE(?a) AS ?above) (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range)
       (SAMPLE(?c) AS ?comment) WHERE {
  { ?term a ?t . VALUES ?t { owl:Class rdfs:Class } BIND(\"class\" AS ?k)
    OPTIONAL { ?term rdfs:subClassOf ?a . FILTER(isIRI(?a)) } }
  UNION
  { ?term a ?t . VALUES ?t { owl:ObjectProperty owl:DatatypeProperty owl:AnnotationProperty rdf:Property }
    BIND(\"property\" AS ?k)
    OPTIONAL { ?term rdfs:domain ?d . FILTER(isIRI(?d)) } OPTIONAL { ?term rdfs:range ?r . FILTER(isIRI(?r)) } }
  FILTER(isIRI(?term))
  OPTIONAL { ?term rdfs:comment ?c } } GROUP BY ?term";

/// A vocabulary as one line per class and property it declares: the term, what it is beneath or its domain and range,
/// and the first sentence of its comment, each name written as a row writes it.
fn glossary(quads: &[Quad], prefixes: &Prefixes) -> Result<String, Error> {
    let vocabulary = Engine::new().map_err(failed)?;
    vocabulary
        .extend(quads.iter().map(|q| {
            Quad::new(
                q.subject.clone(),
                q.predicate.clone(),
                q.object.clone(),
                GraphName::DefaultGraph,
            )
        }))
        .map_err(failed)?;
    let mut evaluator = SparqlEvaluator::new();
    for (name, iri) in [
        ("owl", "http://www.w3.org/2002/07/owl#"),
        ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
        ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ] {
        evaluator = evaluator.with_prefix(name, iri).map_err(failed)?;
    }
    let QueryResults::Solutions(solutions) = evaluator
        .parse_query(GLOSSARY_Q)
        .map_err(failed)?
        .on_store(&vocabulary)
        .execute()
        .map_err(failed)?
    else {
        return Ok(String::new());
    };
    let mut terms = Vec::new();
    for solution in solutions {
        let s = solution.map_err(failed)?;
        let Some(term) = s.get("term") else { continue };
        let name = written(term, prefixes);
        let kind = match s.get("kind") {
            Some(Term::Literal(l)) => l.value().to_string(),
            _ => continue,
        };
        let about = if kind == "class" {
            s.get("above")
                .map(|a| format!(", beneath {}", written(a, prefixes)))
                .unwrap_or_default()
        } else {
            let end = |k: &str| s.get(k).map_or("?".to_string(), |t| written(t, prefixes));
            let (d, r) = (end("domain"), end("range"));
            if d == "?" && r == "?" {
                String::new()
            } else {
                format!(", {d} → {r}")
            }
        };
        let said = match s.get("comment") {
            Some(Term::Literal(l)) => first_sentence(l.value()),
            _ => String::new(),
        };
        terms.push(
            format!("{name} ({kind}{about})")
                + &if said.is_empty() {
                    String::new()
                } else {
                    format!(": {said}")
                },
        );
    }
    terms.sort();
    Ok(terms.join("\n"))
}

/// The first sentence of a comment, on one line, cut at `SENTENCE` characters.
pub fn first_sentence(text: &str) -> String {
    let flat = text.split_whitespace().collect::<Vec<_>>().join(" ");
    let chars: Vec<char> = flat.chars().collect();
    let end = (1..chars.len())
        .find(|&i| chars[i].is_whitespace() && matches!(chars[i - 1], '.' | '!' | '?'))
        .unwrap_or(chars.len());
    let first: String = chars[..end].iter().collect();
    if first.chars().count() <= SENTENCE {
        return first;
    }
    let cut: String = first.chars().take(SENTENCE).collect();
    let kept = cut.rsplit_once(' ').map_or(cut.as_str(), |(head, _)| head);
    format!("{kept} …")
}
