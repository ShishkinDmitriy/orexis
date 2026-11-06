//! A DOCUMENT SAYS WHICH GRAPH IT IS, and what each of its graphs is, as `agent/store.py` reads one
//! (a-documents-kind-says-who-reads-it): a Turtle file is one graph named by the file, whose `<>` rows say what it
//! is; a TriG file is the graphs it names, whose rows sit in its default graph; a peer's bytes are TriG. A document
//! that says too little, or what only the loader or only the world may say, is REFUSED, with the reason.
//!
//! **THE SELF HAS ONE HOME** (the-self-is-a-class-held-to-one-instance): a file the world authored may say whose a
//! graph is and, in a self graph alone, who the self is; a document from anywhere else may say neither.

use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::fs;
use std::path::Path;

use oxigraph::io::{RdfFormat, RdfParser};
use oxigraph::model::{GraphName, GraphNameRef, NamedNode, NamedOrBlankNode, Quad, Term};

use crate::Error;
use crate::ontology::{ASSERTED, BELIEF, CATALOGUE, OREXIS, SELF, SELF_GRAPH};
use crate::store::Store;

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const OWL_IMPORTS: &str = "http://www.w3.org/2002/07/owl#imports";

fn arrived_by() -> String {
    format!("{OREXIS}arrivedBy")
}

fn owned_by() -> String {
    format!("{OREXIS}ownedBy")
}

/// A document's graphs, named, and its rows about them, in the default graph.
#[derive(Clone, Debug)]
pub struct Document {
    graphs: BTreeSet<String>,
    quads: Vec<Quad>,
}

impl Document {
    /// The document at `path`, refused where it says too little or too much; a file is a document the world
    /// authors.
    pub fn read(path: &Path) -> Result<Self, Error> {
        let base = file_uri(path)?;
        let bytes = fs::read(path)?;
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        let trig = path.extension().is_some_and(|e| e == "trig");
        let parsed = parse(
            if trig { RdfFormat::TriG } else { RdfFormat::Turtle },
            &bytes,
            Some(&base),
        )
        .map_err(|e| refused(format!("{name} will not parse: {e}")))?;
        let doc = if trig {
            Document::of_quads(parsed)
        } else {
            Document::of_turtle(parsed, &base)?
        };
        doc.checked(&name, true)
    }

    /// A document handed as TriG bytes — what a peer says, as the transport received it — refused as a file is,
    /// and refused besides where it says whose a graph is or who the self is.
    pub fn of(bytes: &[u8]) -> Result<Self, Error> {
        let parsed =
            parse(RdfFormat::TriG, bytes, None).map_err(|e| refused(format!("a document that is no TriG: {e}")))?;
        Document::of_quads(parsed).checked("a document", false)
    }

    fn of_quads(quads: Vec<Quad>) -> Self {
        let graphs = quads
            .iter()
            .filter_map(|q| match &q.graph_name {
                GraphName::NamedNode(g) => Some(g.as_str().to_string()),
                _ => None,
            })
            .collect();
        Document { graphs, quads }
    }

    /// A Turtle file's triples: those about `<>`, and the blank nodes they reach, are its rows; the rest is the
    /// graph the file names. A file holding anything is a graph, though its rows were all it said.
    fn of_turtle(triples: Vec<Quad>, base: &str) -> Result<Self, Error> {
        let named = NamedNode::new(base).map_err(|e| Error::Document(e.to_string()))?;
        let me: NamedOrBlankNode = named.clone().into();
        let mut about: BTreeSet<usize> = BTreeSet::new();
        let mut reached: HashSet<NamedOrBlankNode> = HashSet::from([me]);
        loop {
            let more: Vec<usize> = triples
                .iter()
                .enumerate()
                .filter(|(i, q)| !about.contains(i) && reached.contains(&q.subject))
                .map(|(i, _)| i)
                .collect();
            if more.is_empty() {
                break;
            }
            for i in more {
                about.insert(i);
                if let Term::BlankNode(b) = &triples[i].object {
                    reached.insert(b.clone().into());
                }
            }
        }
        let graphs = if triples.is_empty() {
            BTreeSet::new()
        } else {
            [base.to_string()].into()
        };
        let quads = triples
            .into_iter()
            .enumerate()
            .map(|(i, q)| {
                let graph: GraphName = if about.contains(&i) {
                    GraphName::DefaultGraph
                } else {
                    named.clone().into()
                };
                Quad::new(q.subject, q.predicate, q.object, graph)
            })
            .collect();
        Ok(Document { graphs, quads })
    }

    /// Every quad the document holds, its graphs' and its rows.
    pub fn quads(&self) -> &[Quad] {
        &self.quads
    }

    /// The rows: what the document says about its graphs.
    fn rows(&self) -> impl Iterator<Item = &Quad> {
        self.quads.iter().filter(|q| q.graph_name.is_default_graph())
    }

    /// Each graph the document holds, with the kinds it says that graph is.
    pub fn kinds(&self) -> BTreeMap<String, BTreeSet<String>> {
        let mut out: BTreeMap<String, BTreeSet<String>> =
            self.graphs.iter().map(|g| (g.clone(), BTreeSet::new())).collect();
        for q in self.rows().filter(|q| q.predicate.as_str() == RDF_TYPE) {
            if let NamedOrBlankNode::NamedNode(s) = &q.subject
                && let Some(held) = out.get_mut(s.as_str())
            {
                held.insert(term_value(&q.object));
            }
        }
        out
    }

    /// Whose the graph `graph` is, by what the document says: the owner it states, or for a self graph the self
    /// it states. Never the file's name.
    pub fn whose(&self, graph: &str) -> Option<String> {
        let owner = owned_by();
        if let Some(q) = self
            .rows()
            .find(|q| q.predicate.as_str() == owner && subject_is(&q.subject, graph))
        {
            return Some(term_value(&q.object));
        }
        if self.kinds().get(graph).is_some_and(|k| k.contains(SELF_GRAPH)) {
            return self
                .quads
                .iter()
                .find(|q| {
                    q.predicate.as_str() == RDF_TYPE
                        && term_value(&q.object) == SELF
                        && matches!(&q.graph_name, GraphName::NamedNode(g) if g.as_str() == graph)
                })
                .map(|q| subject_value(&q.subject));
        }
        None
    }

    /// The documents this one imports, `owl:imports` on a graph it holds, sorted.
    pub fn imports(&self) -> Vec<String> {
        self.rows()
            .filter(|q| q.predicate.as_str() == OWL_IMPORTS)
            .filter_map(|q| match &q.object {
                Term::NamedNode(n) => Some(n.as_str().to_string()),
                _ => None,
            })
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect()
    }

    /// The document where it says what each graph is and nothing only the loader may say. `authored` where the
    /// world wrote it.
    fn checked(self, name: &str, authored: bool) -> Result<Self, Error> {
        let rows: Vec<&Quad> = self.rows().collect();
        let mut reachable: BTreeSet<String> = self.graphs.iter().map(|g| format!("<{g}>")).collect();
        let mut frontier = reachable.clone();
        while !frontier.is_empty() {
            frontier = rows
                .iter()
                .filter(|q| frontier.contains(&q.subject.to_string()))
                .filter_map(|q| match &q.object {
                    Term::BlankNode(b) => Some(b.to_string()),
                    _ => None,
                })
                .filter(|b| !reachable.contains(b))
                .collect();
            reachable.extend(frontier.iter().cloned());
        }
        let stray: BTreeSet<String> = rows
            .iter()
            .map(|q| q.subject.to_string())
            .filter(|s| !reachable.contains(s))
            .collect();
        if !stray.is_empty() {
            return Err(refused(format!(
                "{name} states rows about {}, which is no graph it holds",
                stray.into_iter().collect::<Vec<_>>().join(", ")
            )));
        }
        if self.graphs.is_empty() {
            return Err(refused(format!("{name} holds no graph")));
        }
        let kinds = self.kinds();
        let unkinded: Vec<&String> = kinds.iter().filter(|(_, k)| k.is_empty()).map(|(g, _)| g).collect();
        if !unkinded.is_empty() {
            return Err(refused(format!(
                "{name} says of {} no kind — `<> a <a graph kind>` says it",
                unkinded.iter().map(|g| g.as_str()).collect::<Vec<_>>().join(", ")
            )));
        }
        let arrival = arrived_by();
        for q in &rows {
            if q.predicate.as_str() == arrival {
                return Err(refused(format!(
                    "{name} says {arrival} of a graph, which only the loader says"
                )));
            }
            if q.predicate.as_str() == RDF_TYPE && term_value(&q.object) == CATALOGUE {
                return Err(refused(format!(
                    "{name} says a graph is the catalogue, which is created and never loaded"
                )));
            }
        }
        if authored {
            self.one_home(name)?;
        } else {
            self.no_sovereigns(name)?;
        }
        Ok(self)
    }

    /// Nothing says whose a graph is, that anything is the self, or that a graph is a self graph: what a document
    /// the world did not author is held to.
    fn no_sovereigns(&self, name: &str) -> Result<(), Error> {
        let owner = owned_by();
        if let Some(q) = self.rows().find(|q| q.predicate.as_str() == owner) {
            return Err(refused(format!(
                "{name} says whose {} is, which only the world's own documents say",
                q.subject
            )));
        }
        for kind in [SELF, SELF_GRAPH] {
            if let Some(q) = self
                .quads
                .iter()
                .find(|q| q.predicate.as_str() == RDF_TYPE && term_value(&q.object) == kind)
            {
                return Err(refused(format!(
                    "{name} says {} is {}, which only the world's own documents say",
                    q.subject,
                    kind.rsplit('#').next().unwrap_or(kind)
                )));
            }
        }
        Ok(())
    }

    /// Every graph says at most one owner, a self is stated only in a graph that says it is a self graph and
    /// nothing else, every self graph states exactly one self, and an owner stated of a self graph is that self.
    fn one_home(&self, name: &str) -> Result<(), Error> {
        let stated = self.kinds();
        let owner = owned_by();
        let mut owners: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for q in self.rows().filter(|q| q.predicate.as_str() == owner) {
            let Term::NamedNode(who) = &q.object else {
                return Err(refused(format!(
                    "{name} says {} is {}'s, and an owner is an agent, named",
                    q.subject, q.object
                )));
            };
            owners
                .entry(subject_value(&q.subject))
                .or_default()
                .insert(who.as_str().to_string());
        }
        for (graph, said) in &owners {
            if said.len() > 1 {
                return Err(refused(format!(
                    "{name} says {graph} is {}'s — a graph has one owner",
                    said.iter().map(String::as_str).collect::<Vec<_>>().join(" and ")
                )));
            }
        }
        for q in self
            .quads
            .iter()
            .filter(|q| q.predicate.as_str() == RDF_TYPE && term_value(&q.object) == SELF_GRAPH)
        {
            if !q.graph_name.is_default_graph() {
                return Err(refused(format!(
                    "{name} says inside {} that {} is a self graph, which a document says of its own graph, in its rows",
                    q.graph_name, q.subject
                )));
            }
        }
        let mut selves: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for q in self
            .quads
            .iter()
            .filter(|q| q.predicate.as_str() == RDF_TYPE && term_value(&q.object) == SELF)
        {
            let graph = match &q.graph_name {
                GraphName::NamedNode(g) => Some(g.as_str().to_string()),
                _ => None,
            };
            match &graph {
                Some(g) if stated.get(g).is_some_and(|k| k.contains(SELF_GRAPH)) => {
                    selves.entry(g.clone()).or_default().insert(subject_value(&q.subject));
                }
                Some(g) => {
                    return Err(refused(format!(
                        "{name} says {} is Self in {g}, which is no self graph — the self is stated in a self graph \
                         and nowhere else",
                        q.subject
                    )));
                }
                None => {
                    return Err(refused(format!(
                        "{name} says {} is Self of a graph — the self is stated in a self graph and nowhere else",
                        q.subject
                    )));
                }
            }
        }
        for (graph, kinds) in &stated {
            if !kinds.contains(SELF_GRAPH) {
                continue;
            }
            if kinds.len() > 1 {
                let others: Vec<&str> = kinds.iter().filter(|k| *k != SELF_GRAPH).map(String::as_str).collect();
                return Err(refused(format!(
                    "{name} says {graph} is a self graph and {} too — a self graph is nothing else",
                    others.join(", ")
                )));
            }
            let held = selves.get(graph).cloned().unwrap_or_default();
            if held.len() != 1 {
                return Err(refused(format!(
                    "{name} states {} selves in the self graph {graph} — a self graph states one",
                    held.len()
                )));
            }
            if let Some(said) = owners.get(graph)
                && *said != held
            {
                return Err(refused(format!(
                    "{name} says {graph} is {}'s, and its self is {} — a self graph is its self's",
                    said.iter().next().map(String::as_str).unwrap_or_default(),
                    held.iter().next().map(String::as_str).unwrap_or_default()
                )));
            }
        }
        Ok(())
    }
}

impl Store {
    /// A document's graphs into the store, each REPLACING any graph of its name, and its rows into the catalogue
    /// with the arrival — asserted, for a file — and, where `owner` is given, whose it is. `graphs`, where given,
    /// puts only those. The names put, sorted. `close` says each row's every kind at once, for a writer putting
    /// one document while the agent runs; a boot closes the catalogue once when every document is in.
    pub fn put_document(
        &self,
        doc: &Document,
        owner: Option<&str>,
        graphs: Option<&[&str]>,
        arrival: Option<&str>,
        close: bool,
    ) -> Result<Vec<String>, Error> {
        let catalogue = self.catalogue()?.ok_or_else(|| {
            Error::Catalogue("no graph describes itself as the catalogue — nothing has said what the graphs are".into())
        })?;
        let cat = node(&catalogue)?;
        let arrival = node(arrival.unwrap_or(ASSERTED))?;
        let names: Vec<String> = doc
            .kinds()
            .into_keys()
            .filter(|g| graphs.is_none_or(|only| only.contains(&g.as_str())))
            .collect();
        let rows: Vec<&Quad> = doc.rows().collect();
        for name in &names {
            let graph = node(name)?;
            self.forget_graph(name, Some(BELIEF))?;
            self.add(
                doc.quads
                    .iter()
                    .filter(|q| matches!(q.graph_name.as_ref(), GraphNameRef::NamedNode(g) if g == graph.as_ref()))
                    .cloned(),
            )?;
            let mut reached: HashSet<NamedOrBlankNode> = HashSet::new();
            let mut frontier: HashSet<NamedOrBlankNode> = HashSet::from([graph.clone().into()]);
            while !frontier.is_empty() {
                let mine: Vec<&&Quad> = rows.iter().filter(|q| frontier.contains(&q.subject)).collect();
                self.add(
                    mine.iter()
                        .map(|q| Quad::new(q.subject.clone(), q.predicate.clone(), q.object.clone(), cat.clone())),
                )?;
                reached.extend(frontier);
                frontier = mine
                    .iter()
                    .filter_map(|q| match &q.object {
                        Term::BlankNode(b) => Some(NamedOrBlankNode::from(b.clone())),
                        _ => None,
                    })
                    .filter(|b| !reached.contains(b))
                    .collect();
            }
            let mut said = vec![Quad::new(
                graph.clone(),
                node(&arrived_by())?,
                arrival.clone(),
                cat.clone(),
            )];
            if let Some(owner) = owner {
                said.push(Quad::new(graph.clone(), node(&owned_by())?, node(owner)?, cat.clone()));
            }
            if close {
                for kind in doc.kinds().get(name).into_iter().flatten() {
                    for beneath in self.closed(kind)? {
                        said.push(Quad::new(graph.clone(), node(RDF_TYPE)?, node(&beneath)?, cat.clone()));
                    }
                }
            }
            self.add(said)?;
        }
        Ok(names)
    }
}

/// A path as the `file:` IRI Python's `Path.resolve().as_uri()` makes of it: resolved, and every byte but the
/// unreserved and `/` percent-encoded.
pub fn file_uri(path: &Path) -> Result<String, Error> {
    let resolved = fs::canonicalize(path)?;
    let mut out = String::from("file://");
    for byte in resolved.to_string_lossy().bytes() {
        match byte {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' | b'/' => out.push(byte as char),
            other => out.push_str(&format!("%{other:02X}")),
        }
    }
    Ok(out)
}

fn parse(format: RdfFormat, bytes: &[u8], base: Option<&str>) -> Result<Vec<Quad>, String> {
    let mut parser = RdfParser::from_format(format).rename_blank_nodes();
    if let Some(base) = base {
        parser = parser.with_base_iri(base).map_err(|e| e.to_string())?;
    }
    parser
        .for_slice(bytes)
        .collect::<Result<_, _>>()
        .map_err(|e| e.to_string())
}

fn refused(message: String) -> Error {
    Error::Document(message)
}

fn node(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Document(format!("no IRI: {iri}: {e}")))
}

fn subject_is(subject: &NamedOrBlankNode, iri: &str) -> bool {
    matches!(subject, NamedOrBlankNode::NamedNode(n) if n.as_str() == iri)
}

fn subject_value(subject: &NamedOrBlankNode) -> String {
    match subject {
        NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
        NamedOrBlankNode::BlankNode(b) => b.as_str().to_string(),
    }
}

fn term_value(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => n.as_str().to_string(),
        Term::BlankNode(b) => b.as_str().to_string(),
        Term::Literal(l) => l.value().to_string(),
    }
}

#[cfg(test)]
mod tests {
    //! A document says what its graphs are, held to what `agent/tests/test_document.py` holds the Python loader to.

    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicUsize, Ordering};

    use super::*;
    use crate::ontology::CATALOGUE;
    use crate::snapshots;
    use crate::store::{Within, iri, value};

    const PREFIXES: &str = "@prefix orexis: <http://example.org/orexis#> .\n\
@prefix planning: <http://example.org/orexis/planning#> .\n@prefix dcterms: <http://purl.org/dc/terms/> .\n";
    const PLANNING: &str = "http://example.org/orexis/planning#";

    /// A directory of the test's own, removed when it is done.
    struct Dir(PathBuf);

    impl Dir {
        fn new() -> Self {
            static N: AtomicUsize = AtomicUsize::new(0);
            let path = std::env::temp_dir().join(format!(
                "orexis-doc-{}-{}",
                std::process::id(),
                N.fetch_add(1, Ordering::SeqCst)
            ));
            fs::create_dir_all(&path).unwrap();
            Dir(path)
        }

        fn write(&self, name: &str, text: &str) -> PathBuf {
            let path = self.0.join(name);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(&path, format!("{PREFIXES}{text}")).unwrap();
            path
        }
    }

    impl Drop for Dir {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn store() -> Store {
        let store = Store::new(snapshots::namespaces()).unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE}> {{ <{CATALOGUE}> a orexis:CatalogueGraph }} }}"
            ))
            .unwrap();
        store
    }

    fn uri(path: &Path) -> String {
        file_uri(path).unwrap()
    }

    /// What the catalogue says of `graph`, each predicate and object by its local part.
    fn said(store: &Store, graph: &str) -> BTreeSet<(String, String)> {
        let text = format!("SELECT ?p ?o WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{graph}> ?p ?o }} }}");
        let local = |s: String| s.rsplit('#').next().unwrap().to_string();
        store
            .rows(&text, &[])
            .unwrap()
            .iter()
            .map(|r| (local(value(r, "p").unwrap()), local(value(r, "o").unwrap())))
            .collect()
    }

    fn refusal(result: Result<Document, Error>) -> String {
        match result {
            Ok(_) => panic!("a document that should have been refused was read"),
            Err(e) => e.to_string(),
        }
    }

    #[test]
    fn a_turtle_file_is_one_graph_named_by_the_file_and_its_rows_go_to_the_catalogue() {
        let dir = Dir::new();
        let path = dir.write(
            "anything.ttl",
            "<> a orexis:BeliefGraph .\n<urn:disk> <urn:on> <urn:peg> .\n",
        );
        let (store, name) = (store(), uri(&path));
        let put = store
            .put_document(&Document::read(&path).unwrap(), None, None, None, false)
            .unwrap();
        assert_eq!(put, std::slice::from_ref(&name));
        assert_eq!(
            store.graphs_of(&[BELIEF], &Within::default()).unwrap(),
            std::slice::from_ref(&name)
        );
        assert_eq!(
            said(&store, &name),
            [
                ("type".into(), "BeliefGraph".into()),
                ("arrivedBy".into(), "Asserted".into())
            ]
            .into()
        );
        let held = store.rows("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", &[&name]).unwrap();
        assert_eq!(held.len(), 1, "the graph holds its facts and not its kind");
        assert_eq!(iri(&held[0], "o").as_deref(), Some("urn:peg"));
    }

    #[test]
    fn a_period_stated_of_the_document_goes_with_its_row() {
        let dir = Dir::new();
        let path = dir.write(
            "prediction.ttl",
            "<> a orexis:ForecastGraph ;\n    dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start \
         \"2026-01-01T00:00:00Z\" ] .\n<urn:a> <urn:b> <urn:c> .\n",
        );
        let store = store();
        let name = store
            .put_document(&Document::read(&path).unwrap(), None, None, None, false)
            .unwrap()[0]
            .clone();
        let starts = store
        .rows(
            &format!(
                "SELECT ?start WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{name}> dcterms:temporal ?p . \
                 ?p orexis:start ?start }} }}"
            ),
            &[],
        )
        .unwrap();
        assert_eq!(value(&starts[0], "start").as_deref(), Some("2026-01-01T00:00:00Z"));
        assert_eq!(store.rows("SELECT ?s WHERE { ?s ?p ?o }", &[&name]).unwrap().len(), 1);
    }

    #[test]
    fn a_trig_file_names_its_graphs_and_states_their_kinds_in_its_default_graph() {
        let dir = Dir::new();
        let path = dir.write(
            "two.trig",
            "<#desires> a planning:DesireGraph .\n<#state> a orexis:BeliefGraph .\n\
         <#desires> { <urn:me> planning:holds <urn:home> . }\n<#state> { <urn:disk> <urn:on> <urn:peg> . }\n",
        );
        let doc = Document::read(&path).unwrap();
        let base = uri(&path);
        let kinds = doc.kinds();
        assert_eq!(
            kinds[&format!("{base}#desires")],
            [format!("{PLANNING}DesireGraph")].into()
        );
        assert_eq!(kinds[&format!("{base}#state")], [BELIEF.to_string()].into());
        let store = store();
        let put = store.put_document(&doc, Some("urn:me"), None, None, false).unwrap();
        assert_eq!(put, [format!("{base}#desires"), format!("{base}#state")]);
        assert!(said(&store, &format!("{base}#state")).contains(&("ownedBy".into(), "urn:me".into())));
    }

    #[test]
    fn put_again_replaces_the_graph_and_its_row() {
        let dir = Dir::new();
        let path = dir.write(
            "state.ttl",
            "<> a orexis:BeliefGraph .\n<urn:disk> <urn:on> <urn:peg_a> .\n",
        );
        let store = store();
        store
            .put_document(&Document::read(&path).unwrap(), None, None, None, false)
            .unwrap();
        let path = dir.write(
            "state.ttl",
            "<> a orexis:WorldGraph .\n<urn:disk> <urn:on> <urn:peg_c> .\n",
        );
        let name = store
            .put_document(&Document::read(&path).unwrap(), None, None, None, false)
            .unwrap()[0]
            .clone();
        assert_eq!(
            said(&store, &name),
            [
                ("type".into(), "WorldGraph".into()),
                ("arrivedBy".into(), "Asserted".into())
            ]
            .into()
        );
        let held = store.rows("SELECT ?o WHERE { ?s ?p ?o }", &[&name]).unwrap();
        assert_eq!(
            held.iter().filter_map(|r| iri(r, "o")).collect::<Vec<_>>(),
            ["urn:peg_c"]
        );
    }

    #[test]
    fn a_file_is_refused_where_it_says_too_little_or_what_only_the_loader_says_or_the_self_twice() {
        for (text, expected) in [
            ("<urn:a> <urn:b> <urn:c> .\n", "no kind"),
            ("<> a orexis:CatalogueGraph .\n", "catalogue"),
            (
                "<> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .\n",
                "only the loader",
            ),
            (
                "<> a orexis:BeliefGraph ; orexis:ownedBy <urn:ann> , <urn:bob> .\n",
                "a graph has one owner",
            ),
            (
                "<> a orexis:BeliefGraph ; orexis:ownedBy [] .\n",
                "an owner is an agent, named",
            ),
            (
                "<> a orexis:WorldGraph .\n<urn:someone> a orexis:Self .\n",
                "no self graph",
            ),
            (
                "<> a orexis:SelfGraph , orexis:WorldGraph .\n<urn:ann> a orexis:Self .\n",
                "a self graph is nothing else",
            ),
            ("<> a orexis:SelfGraph .\n", "states 0 selves"),
            (
                "<> a orexis:SelfGraph .\n<urn:ann> a orexis:Self .\n<urn:bob> a orexis:Self .\n",
                "states 2 selves",
            ),
            (
                "<> a orexis:SelfGraph ; orexis:ownedBy <urn:bob> .\n<urn:ann> a orexis:Self .\n",
                "a self graph is its self's",
            ),
            (
                "<> a orexis:SelfGraph , orexis:Self .\n<urn:ann> a orexis:Self .\n",
                "of a graph",
            ),
            (
                "<> a orexis:WorldGraph .\n<urn:g> a orexis:SelfGraph .\n",
                "in its rows",
            ),
        ] {
            let dir = Dir::new();
            let got = refusal(Document::read(&dir.write("bad.ttl", text)));
            assert!(
                got.contains(expected),
                "{text:?}: refused with {got:?}, not {expected:?}"
            );
        }
    }

    #[test]
    fn a_file_says_whose_its_graph_is_and_a_self_graph_is_its_selfs() {
        let dir = Dir::new();
        let whose = |name: &str, text: &str| {
            let path = dir.write(name, text);
            Document::read(&path).unwrap().whose(&uri(&path))
        };
        assert_eq!(
            whose("rose.ttl", "<> a planning:DesireGraph ; orexis:ownedBy <urn:fern> .\n").as_deref(),
            Some("urn:fern")
        );
        assert_eq!(
            whose("who.ttl", "<> a orexis:SelfGraph .\n<urn:fern> a orexis:Self .\n").as_deref(),
            Some("urn:fern")
        );
        assert_eq!(
            whose(
                "both.ttl",
                "<> a orexis:SelfGraph ; orexis:ownedBy <urn:fern> .\n<urn:fern> a orexis:Self .\n"
            )
            .as_deref(),
            Some("urn:fern"),
            "one fact, said twice and agreeing"
        );
        assert_eq!(whose("state.ttl", "<> a orexis:BeliefGraph .\n"), None);
    }

    #[test]
    fn a_document_from_no_file_says_neither_whose_a_graph_is_nor_who_the_self_is() {
        for text in [
            "<urn:g> a orexis:BeliefGraph ; orexis:ownedBy <urn:someone> .\n<urn:g> { <urn:a> <urn:b> <urn:c> }\n",
            "<urn:g> a orexis:BeliefGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
            "<urn:g> a orexis:SelfGraph .\n<urn:g> { <urn:someone> a orexis:Self }\n",
        ] {
            let got = refusal(Document::of(format!("{PREFIXES}{text}").as_bytes()));
            assert!(got.contains("only the world's own documents say"), "{text:?}: {got}");
        }
    }

    #[test]
    fn a_trig_row_about_no_graph_the_document_holds_is_refused() {
        let dir = Dir::new();
        let path = dir.write(
            "stray.trig",
            "<#g> a orexis:BeliefGraph .\n<urn:x> <urn:y> <urn:z> .\n<#g> { <urn:a> <urn:b> <urn:c> . }\n",
        );
        assert!(refusal(Document::read(&path)).contains("no graph it holds"));
    }

    #[test]
    fn an_import_by_relative_iri_names_the_graph_the_imported_file_is_loaded_under() {
        let dir = Dir::new();
        let imported = dir.write("domain/ontology.ttl", "<> a orexis:OntologyGraph .\n");
        let path = dir.write(
            "world/world.ttl",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n<> a orexis:WorldGraph ; owl:imports \
         <../domain/ontology.ttl> .\n",
        );
        assert_eq!(Document::read(&path).unwrap().imports(), [uri(&imported)]);
        assert_eq!(
            Document::read(&imported).unwrap().kinds(),
            [(uri(&imported), [crate::ontology::ONTOLOGY.to_string()].into())].into()
        );
    }

    #[test]
    fn a_path_is_the_iri_python_makes_of_it() {
        let dir = Dir::new();
        let path = dir.write("a b+ü.ttl", "<> a orexis:BeliefGraph .\n");
        assert!(uri(&path).ends_with("/a%20b%2B%C3%BC.ttl"), "{}", uri(&path));
    }
}
