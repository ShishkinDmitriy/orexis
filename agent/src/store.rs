//! THE STORE: Oxigraph's engine, every text parsed once, and the catalogue that says what each graph is — the
//! functions over the engine `agent/store.py` offers, the same questions in the same texts.
//!
//! **EVERY TEXT IS PARSED ONCE.** A text a pass runs is parsed the first time it is run and kept parsed by its
//! text, so a rule asked per world, a read asked per candidate, is parsed once a process. Measured on the bench Pi
//! (`examples/parsing.rs`), a statement takes 40 µs to parse, and a greenhouse pass runs about 1,650: 66 ms of a
//! 460 ms pass, every pass, where ten passes' 16,551 statements are 1,454 texts, parsed once in 68 ms.
//!
//! **A READER STATES THE GRAPHS IT READS**, and the store decides nothing (a-reader-states-the-kinds-it-reads):
//! `rows` is handed the graphs its default graph is the union of, `graphs_of` answers which by kind and instant,
//! and a text that reads one graph names it in its own `GRAPH` clause. Never wrap `GRAPH <…>` around a select.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

use oxigraph::io::RdfFormat;
use oxigraph::model::vocab::{rdf, xsd};
use oxigraph::model::{GraphName, GraphNameRef, Literal, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use oxigraph::sparql::{PreparedSparqlQuery, PreparedSparqlUpdate, QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;
use oxsdatatypes::DateTime;

use crate::Error;
use crate::bind::{Value, bind};
use crate::namespaces::Namespaces;
use crate::ontology::BELIEF;

/// One solution: each variable it binds, to the term it binds.
pub type Row = BTreeMap<String, Term>;

/// The engine, the namespaces every text may speak, and what has been parsed.
pub struct Store {
    engine: Engine,
    namespaces: Arc<Namespaces>,
    queries: Mutex<HashMap<String, PreparedSparqlQuery>>,
    updates: Mutex<HashMap<String, PreparedSparqlUpdate>>,
    algebra: Mutex<HashMap<String, spargebra::Update>>,
    parsed: AtomicUsize,
    run: AtomicUsize,
    updated: AtomicUsize,
}

/// What a reader of `graphs_of` stands at: an instant, or a period from `at` to `until`; whose graphs; and the
/// instant a record is read at, which is the present whatever is asked about (#645).
#[derive(Clone, Debug, Default)]
pub struct Within {
    pub at: Option<DateTime>,
    pub until: Option<DateTime>,
    pub holder: Option<String>,
    pub now: Option<DateTime>,
    /// The graphs no agent owns alone: what the world states, shared by every agent of it.
    pub common: bool,
}

impl Within {
    pub fn at(at: DateTime) -> Self {
        Within {
            at: Some(at),
            ..Within::default()
        }
    }

    pub fn common() -> Self {
        Within {
            common: true,
            ..Within::default()
        }
    }
}

const CATALOGUES_Q: &str = "SELECT ?g WHERE { GRAPH ?g { ?g a orexis:CatalogueGraph } }";

/// WHICH GRAPHS, in one text: those of any kind named — every row carries every kind its class is beneath, so no
/// path is walked — the holder's or the common ones where a holder is named, and holding at the instant where one
/// is given.
const GRAPHS_Q: &str = "
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph .
    ?g a ?kind . FILTER(isIRI(?g)) VALUES ?kind { $kinds }
    $owned
    $holding } }
ORDER BY ?g";

const OWNED: &str = "OPTIONAL { ?g orexis:ownedBy ?owner } FILTER(!BOUND(?owner) || ?owner = $holder)";

const COMMON: &str = "FILTER NOT EXISTS { ?g orexis:ownedBy ?anyone }";

/// HOLDING AT `$at` AND STILL AT `$until`: begun by the first and not ended by the second; a record at the present.
const HOLDING: &str = "OPTIONAL { ?g dcterms:temporal ?period .
               OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
    BIND(IF(EXISTS { ?g a orexis:RecordGraph }, $now, $at) AS ?when)
    BIND(IF(EXISTS { ?g a orexis:RecordGraph }, $now, $until) AS ?till)
    FILTER(!BOUND(?start) || ?when >= ?start) FILTER(!BOUND(?end) || ?till < ?end)";

/// A class and every class the vocabulary puts it beneath: the closure is materialised at genesis, so one step is
/// every step.
const ROWS_Q: &str = "
SELECT ?g ?class WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?class . FILTER(isIRI(?g)) } }";

const PROV_DERIVED: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";
const DCTERMS_TEMPORAL: &str = "http://purl.org/dc/terms/temporal";

const SUBCLASSES_Q: &str = "
SELECT DISTINCT ?super WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }
  GRAPH ?vocabulary { $cls rdfs:subClassOf ?super . FILTER(isIRI(?super)) } }";

impl Store {
    /// An empty store, in memory, speaking `namespaces`.
    pub fn new(namespaces: Arc<Namespaces>) -> Result<Self, Error> {
        Ok(Store {
            engine: Engine::new().map_err(|e| Error::Evaluation(e.to_string()))?,
            namespaces,
            queries: Mutex::new(HashMap::new()),
            updates: Mutex::new(HashMap::new()),
            algebra: Mutex::new(HashMap::new()),
            parsed: AtomicUsize::new(0),
            run: AtomicUsize::new(0),
            updated: AtomicUsize::new(0),
        })
    }

    /// A store on disk at `path`, opened or made, speaking `namespaces`: a volume an agent lives in.
    #[cfg(feature = "volume")]
    pub fn open(path: &std::path::Path, namespaces: Arc<Namespaces>) -> Result<Self, Error> {
        Ok(Store {
            engine: Engine::open(path).map_err(|e| Error::Evaluation(e.to_string()))?,
            namespaces,
            queries: Mutex::new(HashMap::new()),
            updates: Mutex::new(HashMap::new()),
            algebra: Mutex::new(HashMap::new()),
            parsed: AtomicUsize::new(0),
            run: AtomicUsize::new(0),
            updated: AtomicUsize::new(0),
        })
    }

    /// The engine itself, for a reader of quads.
    pub fn engine(&self) -> &Engine {
        &self.engine
    }

    pub fn namespaces(&self) -> &Namespaces {
        &self.namespaces
    }

    /// How many texts were parsed, and how many statements run: what parsing once saved.
    pub fn statements(&self) -> (usize, usize) {
        (self.parsed.load(Ordering::Relaxed), self.run.load(Ordering::Relaxed))
    }

    /// The statements run, as the queries and the updates among them: what the bench's ledger counts a pass by.
    pub fn ran(&self) -> (usize, usize) {
        let updated = self.updated.load(Ordering::Relaxed);
        (self.run.load(Ordering::Relaxed) - updated, updated)
    }

    /// A dataset into the store, as TriG.
    pub fn load_trig(&self, text: &str) -> Result<(), Error> {
        self.engine
            .load_from_slice(RdfFormat::TriG, text.as_bytes())
            .map_err(|e| Error::Document(e.to_string()))
    }

    fn evaluator(&self) -> SparqlEvaluator {
        self.namespaces
            .iter()
            .fold(SparqlEvaluator::new(), |evaluator, (label, iri)| {
                evaluator
                    .with_prefix(label, iri)
                    .expect("a namespace the tree declares is an IRI")
            })
    }

    fn query(&self, text: &str) -> Result<PreparedSparqlQuery, Error> {
        self.run.fetch_add(1, Ordering::Relaxed);
        let mut parsed = self.queries.lock().expect("a cache nobody poisoned");
        if let Some(query) = parsed.get(text) {
            return Ok(query.clone());
        }
        let query = self
            .evaluator()
            .parse_query(text)
            .map_err(|e| Error::Syntax(format!("{e}: {text}")))?;
        self.parsed.fetch_add(1, Ordering::Relaxed);
        parsed.insert(text.to_string(), query.clone());
        Ok(query)
    }

    /// `text` over the union of `graphs` as its default graph: each solution, by variable. A text that names its
    /// own graphs is handed none, and reads them through its `GRAPH` clauses.
    pub fn rows(&self, text: &str, graphs: &[&str]) -> Result<Vec<Row>, Error> {
        let mut query = self.query(text)?;
        let default = graphs
            .iter()
            .map(|g| {
                NamedNode::new(*g)
                    .map(GraphName::from)
                    .map_err(|e| Error::Evaluation(e.to_string()))
            })
            .collect::<Result<Vec<_>, _>>()?;
        query.dataset_mut().set_default_graph(default);
        self.solutions(query)
    }

    /// `text` over the store's own default graph, which only the catalogue's reads ask: they name every graph
    /// they read.
    fn rows_named(&self, text: &str) -> Result<Vec<Row>, Error> {
        let query = self.query(text)?;
        self.solutions(query)
    }

    fn solutions(&self, query: PreparedSparqlQuery) -> Result<Vec<Row>, Error> {
        match query
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))?
        {
            QueryResults::Solutions(solutions) => solutions
                .map(|solution| {
                    let solution = solution.map_err(|e| Error::Evaluation(e.to_string()))?;
                    Ok(solution
                        .iter()
                        .map(|(v, t)| (v.as_str().to_string(), t.clone()))
                        .collect())
                })
                .collect(),
            QueryResults::Boolean(_) | QueryResults::Graph(_) => Err(Error::Evaluation(
                "a select was asked for and the text is not one".into(),
            )),
        }
    }

    /// `text`, a CONSTRUCT, over the union of `graphs` as its default graph: the triples it makes.
    pub fn construct(&self, text: &str, graphs: &[&str]) -> Result<Vec<Triple>, Error> {
        let mut query = self.query(text)?;
        let default = graphs
            .iter()
            .map(|g| {
                NamedNode::new(*g)
                    .map(GraphName::from)
                    .map_err(|e| Error::Evaluation(e.to_string()))
            })
            .collect::<Result<Vec<_>, _>>()?;
        query.dataset_mut().set_default_graph(default);
        match query
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))?
        {
            QueryResults::Graph(triples) => triples
                .map(|t| t.map_err(|e| Error::Evaluation(e.to_string())))
                .collect(),
            _ => Err(Error::Evaluation(
                "a construct was asked for and the text is not one".into(),
            )),
        }
    }

    /// Whether `text`, an ASK, holds over the union of `graphs`.
    pub fn ask(&self, text: &str, graphs: &[&str]) -> Result<bool, Error> {
        let mut query = self.query(text)?;
        let default = graphs
            .iter()
            .map(|g| {
                NamedNode::new(*g)
                    .map(GraphName::from)
                    .map_err(|e| Error::Evaluation(e.to_string()))
            })
            .collect::<Result<Vec<_>, _>>()?;
        query.dataset_mut().set_default_graph(default);
        match query
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))?
        {
            QueryResults::Boolean(b) => Ok(b),
            _ => Err(Error::Evaluation("an ask was asked for and the text is not one".into())),
        }
    }

    /// An update, which names the graphs it writes.
    pub fn update(&self, text: &str) -> Result<(), Error> {
        self.run.fetch_add(1, Ordering::Relaxed);
        self.updated.fetch_add(1, Ordering::Relaxed);
        let update = {
            let mut parsed = self.updates.lock().expect("a cache nobody poisoned");
            match parsed.get(text) {
                Some(update) => update.clone(),
                None => {
                    let update = self
                        .evaluator()
                        .parse_update(text)
                        .map_err(|e| Error::Syntax(format!("{e}: {text}")))?;
                    self.parsed.fetch_add(1, Ordering::Relaxed);
                    parsed.insert(text.to_string(), update.clone());
                    update
                }
            }
        };
        update
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))
    }

    /// An update text as its ALGEBRA, parsed once by its text with every prefix the tree declares — for a runner
    /// that says on the parse what the text does not: which graph it changes and which it reads.
    pub fn parse_update(&self, text: &str) -> Result<spargebra::Update, Error> {
        self.run.fetch_add(1, Ordering::Relaxed);
        self.updated.fetch_add(1, Ordering::Relaxed);
        let mut parsed = self.algebra.lock().expect("a cache nobody poisoned");
        if let Some(update) = parsed.get(text) {
            return Ok(update.clone());
        }
        let parser = self
            .namespaces
            .iter()
            .try_fold(spargebra::SparqlParser::new(), |parser, (label, iri)| {
                parser.with_prefix(label, iri)
            })
            .map_err(|e| Error::Syntax(e.to_string()))?;
        let update = parser
            .parse_update(text)
            .map_err(|e| Error::Syntax(format!("{e}: {text}")))?;
        self.parsed.fetch_add(1, Ordering::Relaxed);
        parsed.insert(text.to_string(), update.clone());
        Ok(update)
    }

    /// A query text as its ALGEBRA, with every prefix the tree declares — for a reader of what a text says, never
    /// to run it.
    pub fn parse_query(&self, text: &str) -> Result<spargebra::Query, Error> {
        let parser = self
            .namespaces
            .iter()
            .try_fold(spargebra::SparqlParser::new(), |parser, (label, iri)| {
                parser.with_prefix(label, iri)
            })
            .map_err(|e| Error::Syntax(e.to_string()))?;
        parser
            .parse_query(text)
            .map_err(|e| Error::Syntax(format!("{e}: {text}")))
    }

    /// An update's algebra, run.
    pub fn run_update(&self, update: spargebra::Update) -> Result<(), Error> {
        SparqlEvaluator::new()
            .for_update(update)
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))
    }

    /// THE ONE GRAPH THAT DESCRIBES EVERY GRAPH AND ITSELF, found by its own row: None for a store nobody has told
    /// anything, and two refused, since a store with two catalogues has two truths about what its graphs are.
    pub fn catalogue(&self) -> Result<Option<String>, Error> {
        let mut found: Vec<String> = self
            .rows_named(CATALOGUES_Q)?
            .into_iter()
            .filter_map(|r| iri(&r, "g"))
            .collect();
        found.sort();
        if found.len() > 1 {
            return Err(Error::Catalogue(format!(
                "two graphs describe themselves as the catalogue: {}",
                found.join(", ")
            )));
        }
        Ok(found.pop())
    }

    /// Every graph the catalogue types under any of `kinds` — beneath them too, the rows closed when written — as
    /// `within` narrows them, in name order. THE ONE LOOKUP A READER TAKES, and it decides nothing else.
    pub fn graphs_of(&self, kinds: &[&str], within: &Within) -> Result<Vec<String>, Error> {
        let mut owned = match &within.holder {
            Some(holder) => bind(OWNED, &[("holder", Value::iri(holder.clone()))])?,
            None => String::new(),
        };
        if within.common {
            owned.push_str(COMMON);
        }
        let holding = match within.at {
            Some(at) => bind(
                HOLDING,
                &[
                    ("at", instant(at)),
                    ("until", instant(within.until.unwrap_or(at))),
                    ("now", instant(within.now.unwrap_or(at))),
                ],
            )?,
            None => String::new(),
        };
        let kinds = kinds.iter().map(|k| format!("<{k}>")).collect::<Vec<_>>().join(" ");
        let text = bind(
            GRAPHS_Q,
            &[
                ("kinds", Value::Raw(kinds)),
                ("owned", Value::Raw(owned)),
                ("holding", Value::Raw(holding)),
            ],
        )?;
        Ok(self
            .rows_named(&text)?
            .into_iter()
            .filter_map(|r| iri(&r, "g"))
            .collect())
    }

    /// `class` and every class the vocabulary puts it beneath, sorted; the class alone where no vocabulary is.
    pub fn closed(&self, class: &str) -> Result<Vec<String>, Error> {
        let text = bind(SUBCLASSES_Q, &[("cls", Value::iri(class))])?;
        let mut out: Vec<String> = self
            .rows(&text, &[])?
            .into_iter()
            .filter_map(|r| iri(&r, "super"))
            .collect();
        out.push(class.to_string());
        out.sort();
        out.dedup();
        Ok(out)
    }

    /// What the catalogue says of a graph, as the `GRAPH … { … }` block a writer puts beside the graph's own in ONE
    /// update, so a graph and its description land together or not at all: every kind it is, how it arrived,
    /// whose, and the period it holds over.
    pub fn entry(
        &self,
        graph: &str,
        classes: &[&str],
        arrival: &str,
        owner: Option<&str>,
        start: Option<DateTime>,
        end: Option<DateTime>,
    ) -> Result<String, Error> {
        let catalogue = self.catalogue()?.ok_or_else(|| {
            Error::Catalogue("no graph describes itself as the catalogue — nothing has said what the graphs are".into())
        })?;
        let whose = owner.map(|o| format!(" ; orexis:ownedBy <{o}>")).unwrap_or_default();
        let bounds: String = [("start", start), ("end", end)]
            .iter()
            .filter_map(|(k, v)| v.map(|v| format!(" ; orexis:{k} \"{}\"^^xsd:dateTime", crate::clock::isoformat(v))))
            .collect();
        let when = if bounds.is_empty() {
            String::new()
        } else {
            format!(" ; dcterms:temporal [ a dcterms:PeriodOfTime{bounds} ]")
        };
        let mut kinds = Vec::new();
        for class in classes {
            kinds.extend(self.closed(class)?);
        }
        kinds.sort();
        kinds.dedup();
        let kinds = kinds.iter().map(|k| format!("<{k}>")).collect::<Vec<_>>().join(" , ");
        Ok(format!(
            "GRAPH <{catalogue}> {{ <{graph}> a {kinds} ; orexis:arrivedBy <{arrival}>{whose}{when} . }}"
        ))
    }

    /// Say what a graph IS, how it arrived, whose it is and when it holds, as its owner does when it creates the
    /// graph. IDEMPOTENT, INCLUDING THE PERIOD: a period is a blank node, so it is written only where the graph
    /// has none — a graph's stretch is fixed when it is created.
    pub fn classify(
        &self,
        graph: &str,
        class: &str,
        arrival: &str,
        owner: Option<&str>,
        start: Option<DateTime>,
        end: Option<DateTime>,
    ) -> Result<(), Error> {
        let block = self.entry(graph, &[class], arrival, owner, start, end)?;
        if start.is_none() && end.is_none() {
            return self.update(&format!("INSERT DATA {{ {block} }}"));
        }
        let catalogue = self.catalogue()?.unwrap_or_default();
        self.update(&format!(
            "INSERT {{ {block} }}\nWHERE  {{ GRAPH <{catalogue}> {{ }}\n          FILTER NOT EXISTS {{ GRAPH \
             <{catalogue}> {{ <{graph}> dcterms:temporal ?period }} }} }}"
        ))
    }

    // --- graphs, as quads -----------------------------------------------------------------------------------------

    /// One graph's contents as the quads they are.
    pub fn quads(&self, graph: &str) -> Result<Vec<Quad>, Error> {
        let name = named(graph)?;
        self.engine
            .quads_for_pattern(None, None, None, Some(GraphNameRef::NamedNode(name.as_ref())))
            .collect::<Result<_, _>>()
            .map_err(engine)
    }

    /// One graph's contents as triples.
    pub fn triples(&self, graph: &str) -> Result<Vec<Triple>, Error> {
        Ok(self.quads(graph)?.into_iter().map(Triple::from).collect())
    }

    /// Every named graph present, by name, sorted.
    pub fn graph_names(&self) -> Result<Vec<String>, Error> {
        let mut out: Vec<String> = self
            .engine
            .named_graphs()
            .filter_map(|g| match g {
                Ok(NamedOrBlankNode::NamedNode(node)) => Some(Ok(node.into_string())),
                Ok(NamedOrBlankNode::BlankNode(_)) => None,
                Err(e) => Some(Err(engine(e))),
            })
            .collect::<Result<_, _>>()?;
        out.sort();
        Ok(out)
    }

    /// What `subject` says under `predicate` in `graph`, in no order: the one-hop read a catalogue row is, asked of
    /// the engine's index rather than a text bound per subject and parsed per subject.
    pub fn objects(&self, subject: &Term, predicate: &str, graph: &str) -> Result<Vec<Term>, Error> {
        let subject = match subject {
            Term::NamedNode(n) => NamedOrBlankNode::from(n.clone()),
            Term::BlankNode(b) => NamedOrBlankNode::from(b.clone()),
            Term::Literal(_) => return Ok(Vec::new()),
        };
        let (predicate, graph) = (named(predicate)?, named(graph)?);
        self.engine
            .quads_for_pattern(
                Some(subject.as_ref()),
                Some(predicate.as_ref()),
                None,
                Some(GraphNameRef::NamedNode(graph.as_ref())),
            )
            .map(|q| q.map(|q| q.object).map_err(engine))
            .collect()
    }

    /// Whether `graph` holds the triple.
    pub fn holds(&self, subject: &str, predicate: &str, object: &str, graph: &str) -> Result<bool, Error> {
        let quad = Quad::new(named(subject)?, named(predicate)?, named(object)?, named(graph)?);
        self.engine.contains(&quad).map_err(engine)
    }

    /// Quads straight in, as the terms they are.
    pub fn add(&self, quads: impl IntoIterator<Item = Quad>) -> Result<(), Error> {
        for quad in quads {
            self.engine.insert(&quad).map_err(engine)?;
        }
        Ok(())
    }

    /// Take every quad of `quads` out of the store.
    pub fn remove_all(&self, quads: &[Quad]) -> Result<(), Error> {
        for quad in quads {
            self.engine.remove(quad).map_err(engine)?;
        }
        Ok(())
    }

    /// Empty one graph, its name with it — for one about to be refilled.
    pub fn clear_graph(&self, graph: &str) -> Result<(), Error> {
        let name = named(graph)?;
        self.engine.remove_named_graph(name.as_ref()).map_err(engine)?;
        Ok(())
    }

    /// A TriG dataset in, every graph it names REPLACING the graph of that name, and its default graph's quads
    /// into `into`, which is replaced too — what a case is loaded by, as `put_graph(…, dataset=True)` loads one.
    pub fn put_trig(&self, into: &str, text: &str) -> Result<(), Error> {
        let target = named(into)?;
        //  THROUGH A STORE OF ITS OWN, as `put_graph` reads a dataset: parsed into one, then each quad of it put
        //  here in the order that store hands them back. The order a reader later meets quads in is the engine's,
        //  and a case's compiled met-test numbers its constraints in it, so the two kernels load alike.
        let staged = Engine::new().map_err(engine)?;
        staged
            .load_from_slice(RdfFormat::TriG, text.as_bytes())
            .map_err(|e| Error::Document(e.to_string()))?;
        let parsed: Vec<Quad> = staged.iter().collect::<Result<_, _>>().map_err(engine)?;
        let mut replaced: HashSet<GraphName> = parsed
            .iter()
            .map(|q| q.graph_name.clone())
            .filter(|g| !g.is_default_graph())
            .collect();
        replaced.insert(target.clone().into());
        for graph in &replaced {
            if let GraphName::NamedNode(node) = graph {
                self.engine.remove_named_graph(node.as_ref()).map_err(engine)?;
            }
        }
        self.add(parsed.into_iter().map(|q| {
            if q.graph_name.is_default_graph() {
                Quad::new(q.subject, q.predicate, q.object, target.clone())
            } else {
                q
            }
        }))
    }

    /// Everything `parent` holds, under `name` as well, copied by the engine. The name, for chaining.
    pub fn copy_graph(&self, parent: &str, name: &str) -> Result<String, Error> {
        let into = named(name)?;
        let copied: Vec<Quad> = self
            .quads(parent)?
            .into_iter()
            .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone()))
            .collect();
        self.add(copied)?;
        Ok(name.to_string())
    }

    /// `parent`'s facts under `name`, less what each retraction takes, plus `added` — THE ORDER IS THE WHOLE OF
    /// IT: copy, every delete, then the adds, since a construct reuses the very node its retraction names. The
    /// name.
    ///
    /// A RETRACTION THAT WILL NOT RUN RETRACTS NOTHING, LOUDLY, and the fork exists either way: it is a package's
    /// bug and must not take an agent down. Each runs on its own, parsed once by its text, so the Python kernel's
    /// joining of them into one text — a round trip saved — has nothing to save here.
    pub fn fork(&self, parent: &str, name: &str, added: &[Triple], retracts: &[String]) -> Result<String, Error> {
        self.copy_graph(parent, name)?;
        for text in retracts {
            if let Err(refused) = self.update(text) {
                log::error!("a retraction would not run, so it retracts nothing: {refused}");
            }
        }
        let into = named(name)?;
        self.add(added.iter().map(|t| t.clone().in_graph(into.clone())))?;
        Ok(name.to_string())
    }

    /// Every graph of `kind` the catalogue says was derived from one of `sources`, sorted: what the rules
    /// concluded of them, their revisions.
    pub fn revisions_of(&self, sources: &[&str], kind: &str) -> Result<Vec<String>, Error> {
        let Some(catalogue) = self.catalogue()? else {
            return Ok(Vec::new());
        };
        let (cat, derived, kind) = (named(&catalogue)?, named(PROV_DERIVED)?, named(kind)?);
        let mut out = BTreeSet::new();
        for source in sources {
            let source = named(source)?;
            for quad in self.engine.quads_for_pattern(
                None,
                Some(derived.as_ref()),
                Some(source.as_ref().into()),
                Some(GraphNameRef::NamedNode(cat.as_ref())),
            ) {
                let quad = quad.map_err(engine)?;
                let typed = Quad::new(quad.subject.clone(), rdf::TYPE, kind.clone(), cat.clone());
                if self.engine.contains(&typed).map_err(engine)?
                    && let NamedOrBlankNode::NamedNode(r) = quad.subject
                {
                    out.insert(r.into_string());
                }
            }
        }
        Ok(out.into_iter().collect())
    }

    /// Empty one graph AND take back everything the catalogue said of it, its period with its row — and its
    /// revisions, of the kind `revisions` says they are; None takes the graph alone.
    pub fn forget_graph(&self, graph: &str, revisions: Option<&str>) -> Result<(), Error> {
        if let Some(kind) = revisions {
            for revision in self.revisions_of(&[graph], kind)? {
                self.forget_graph(&revision, Some(BELIEF))?;
            }
        }
        self.clear_graph(graph)?;
        let Some(catalogue) = self.catalogue()? else {
            return Ok(());
        };
        let (cat, subject, temporal) = (named(&catalogue)?, named(graph)?, named(DCTERMS_TEMPORAL)?);
        let row: Vec<Quad> = self
            .engine
            .quads_for_pattern(
                Some(subject.as_ref().into()),
                None,
                None,
                Some(GraphNameRef::NamedNode(cat.as_ref())),
            )
            .collect::<Result<_, _>>()
            .map_err(engine)?;
        let mut gone = row.clone();
        for quad in &row {
            if quad.predicate == temporal
                && let Term::BlankNode(period) = &quad.object
            {
                gone.extend(
                    self.engine
                        .quads_for_pattern(
                            Some(period.as_ref().into()),
                            None,
                            None,
                            Some(GraphNameRef::NamedNode(cat.as_ref())),
                        )
                        .collect::<Result<Vec<_>, _>>()
                        .map_err(engine)?,
                );
            }
        }
        self.remove_all(&gone)
    }

    /// Say on every row each kind the vocabulary puts its class beneath — what `entry` writes on a new row, said
    /// again of every row there is. Idempotent.
    pub fn close_catalogue(&self) -> Result<(), Error> {
        let Some(catalogue) = self.catalogue()? else {
            return Ok(());
        };
        let mut held: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for row in self.rows_named(ROWS_Q)? {
            if let (Some(g), Some(class)) = (iri(&row, "g"), iri(&row, "class")) {
                held.entry(g).or_default().insert(class);
            }
        }
        let cat = named(&catalogue)?;
        let mut rows = Vec::new();
        for (graph, classes) in held {
            let subject = named(&graph)?;
            for class in classes {
                for kind in self.closed(&class)? {
                    rows.push(Quad::new(subject.clone(), rdf::TYPE, named(&kind)?, cat.clone()));
                }
            }
        }
        self.add(rows)
    }

    /// How many quads the store holds.
    pub fn len(&self) -> Result<usize, Error> {
        self.engine.len().map_err(|e| Error::Evaluation(e.to_string()))
    }

    pub fn is_empty(&self) -> Result<bool, Error> {
        Ok(self.len()? == 0)
    }
}

fn named(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("no IRI: {iri}: {e}")))
}

fn engine(e: impl std::fmt::Display) -> Error {
    Error::Evaluation(e.to_string())
}

/// An instant as the term a query compares it as, spelled as the Python kernel spells it.
pub fn instant(at: DateTime) -> Value {
    Value::Term(Literal::new_typed_literal(crate::clock::isoformat(at), xsd::DATE_TIME).into())
}

/// The IRI a row binds `variable` to, where it binds one.
pub fn iri(row: &Row, variable: &str) -> Option<String> {
    match row.get(variable) {
        Some(Term::NamedNode(node)) => Some(node.as_str().to_string()),
        _ => None,
    }
}

/// The lexical value a row binds `variable` to — an IRI's text, a literal's value.
pub fn value(row: &Row, variable: &str) -> Option<String> {
    match row.get(variable)? {
        Term::NamedNode(node) => Some(node.as_str().to_string()),
        Term::Literal(literal) => Some(literal.value().to_string()),
        Term::BlankNode(node) => Some(node.as_str().to_string()),
    }
}

#[cfg(test)]
mod tests {
    //! The store's reads, held to what `agent/store.py` answers over the same catalogue.

    use std::path::Path;
    use std::sync::Arc;

    use super::*;
    use crate::clock::instant as at;
    use crate::namespaces::Namespaces;
    use crate::ontology::{BELIEF, DERIVED, RECORD};

    const T: &str = "http://example.org/test#";

    /// A catalogue of five graphs: the world's, the agent's own state, a peer's, one holding for an hour, and a record
    /// whose hour is over — with the vocabulary saying a state graph is a belief.
    const CATALOGUED: &str = r#"
@prefix orexis: <http://example.org/orexis#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix : <http://example.org/test#> .

:catalogue {
  :catalogue a orexis:CatalogueGraph .
  :vocabulary a orexis:OntologyGraph .
  :world a orexis:BeliefGraph .
  :mine a orexis:BeliefGraph ; orexis:ownedBy :me .
  :theirs a orexis:BeliefGraph ; orexis:ownedBy :them .
  :hour a orexis:BeliefGraph ; dcterms:temporal [ orexis:start "2026-01-01T12:00:00Z"^^xsd:dateTime ;
                                                    orexis:end "2026-01-01T13:00:00Z"^^xsd:dateTime ] .
  :record a orexis:RecordGraph ; dcterms:temporal [ orexis:start "2026-01-01T10:00:00Z"^^xsd:dateTime ;
                                                     orexis:end "2026-01-01T11:00:00Z"^^xsd:dateTime ] .
}
:vocabulary { :StateGraph rdfs:subClassOf orexis:BeliefGraph . }
:world { :bed :moisture 0.3 . }
:mine { :bed :believed :dry . }
"#;

    fn store() -> Store {
        let tree = Path::new(env!("CARGO_MANIFEST_DIR"));
        let store = Store::new(Arc::new(Namespaces::of_tree(tree).unwrap())).unwrap();
        store.load_trig(CATALOGUED).unwrap();
        store
    }

    fn t(local: &str) -> String {
        format!("{T}{local}")
    }

    #[test]
    fn the_catalogue_is_found_by_its_own_row_and_two_are_refused() {
        let store = store();
        assert_eq!(store.catalogue().unwrap(), Some(t("catalogue")));
        store
            .load_trig(&format!(
                "<{T}other> {{ <{T}other> a <http://example.org/orexis#CatalogueGraph> . }}"
            ))
            .unwrap();
        assert!(
            store
                .catalogue()
                .unwrap_err()
                .to_string()
                .contains("two graphs describe themselves as the catalogue")
        );
    }

    #[test]
    fn graphs_of_a_kind_are_every_graph_typed_so_in_name_order() {
        let found = store().graphs_of(&[BELIEF], &Within::default()).unwrap();
        assert_eq!(found, [t("hour"), t("mine"), t("theirs"), t("world")]);
    }

    #[test]
    fn a_holder_is_handed_its_own_and_the_common_and_common_is_what_no_agent_owns() {
        let store = store();
        let mine = Within {
            holder: Some(t("me")),
            ..Within::default()
        };
        assert_eq!(
            store.graphs_of(&[BELIEF], &mine).unwrap(),
            [t("hour"), t("mine"), t("world")]
        );
        assert_eq!(
            store.graphs_of(&[BELIEF], &Within::common()).unwrap(),
            [t("hour"), t("world")]
        );
    }

    #[test]
    fn at_an_instant_a_graph_is_handed_while_its_period_holds_and_a_record_at_the_present() {
        let store = store();
        let inside = store
            .graphs_of(&[BELIEF], &Within::at(at("2026-01-01T12:30:00Z").unwrap()))
            .unwrap();
        assert!(inside.contains(&t("hour")));
        let after = store
            .graphs_of(&[BELIEF], &Within::at(at("2026-01-01T13:00:00Z").unwrap()))
            .unwrap();
        assert!(!after.contains(&t("hour")), "an end is exclusive");
        let over = Within {
            at: Some(at("2026-01-01T12:30:00Z").unwrap()),
            until: Some(at("2026-01-01T13:30:00Z").unwrap()),
            ..Within::default()
        };
        assert!(
            !store.graphs_of(&[BELIEF], &over).unwrap().contains(&t("hour")),
            "held throughout a period, or not"
        );
        let asked = Within {
            at: Some(at("2026-01-01T10:30:00Z").unwrap()),
            now: Some(at("2026-01-01T12:00:00Z").unwrap()),
            ..Within::default()
        };
        assert_eq!(
            store.graphs_of(&[RECORD], &asked).unwrap(),
            Vec::<String>::new(),
            "a record is read at the present"
        );
    }

    #[test]
    fn a_reader_reads_the_union_of_the_graphs_it_is_handed() {
        let store = store();
        let text = "SELECT ?p ?o WHERE { <http://example.org/test#bed> ?p ?o } ORDER BY ?p";
        let both = store.rows(text, &[&t("world"), &t("mine")]).unwrap();
        assert_eq!(
            both.iter().filter_map(|r| value(r, "p")).collect::<Vec<_>>(),
            [t("believed"), t("moisture")]
        );
        assert!(
            store.rows(text, &[]).unwrap().is_empty(),
            "handed nothing, a text naming no graph reads nothing"
        );
    }

    #[test]
    fn a_class_is_closed_by_one_step_of_the_vocabulary() {
        let store = store();
        assert_eq!(
            store.closed(&t("StateGraph")).unwrap(),
            [BELIEF.to_string(), t("StateGraph")]
        );
        assert_eq!(
            store.closed(BELIEF).unwrap(),
            [BELIEF],
            "a class the vocabulary puts beneath nothing is itself"
        );
    }

    #[test]
    fn an_entry_says_every_kind_whose_and_when_and_lands_in_the_catalogue_with_its_graph() {
        let store = store();
        let start = at("2026-01-01T12:00:00Z").unwrap();
        let entry = store
            .entry(
                &t("state"),
                &[&t("StateGraph")],
                DERIVED,
                Some(&t("me")),
                Some(start),
                None,
            )
            .unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{T}state> {{ <{T}bed> <{T}believed> <{T}wet> }} {entry} }}"
            ))
            .unwrap();
        let mine = Within {
            holder: Some(t("me")),
            at: Some(at("2026-01-01T12:30:00Z").unwrap()),
            ..Within::default()
        };
        assert!(
            store.graphs_of(&[BELIEF], &mine).unwrap().contains(&t("state")),
            "typed beneath, owned, holding"
        );
        let early = Within {
            at: Some(at("2026-01-01T11:00:00Z").unwrap()),
            ..Within::default()
        };
        assert!(
            !store.graphs_of(&[BELIEF], &early).unwrap().contains(&t("state")),
            "not before it starts"
        );
    }

    #[test]
    fn a_text_run_again_is_not_parsed_again() {
        let store = store();
        for _ in 0..10 {
            store.graphs_of(&[BELIEF], &Within::default()).unwrap();
        }
        let (parsed, run) = store.statements();
        assert_eq!((parsed, run), (1, 10));
    }

    #[test]
    fn a_prefix_the_tree_declares_is_spoken_without_a_header() {
        let store = store();
        let rows = store
            .rows("SELECT ?g WHERE { GRAPH ?g { ?g a orexis:CatalogueGraph } }", &[])
            .unwrap();
        assert_eq!(rows.len(), 1);
        assert!(
            store
                .rows("SELECT * WHERE { ?s nobody:knows ?o }", &[])
                .unwrap_err()
                .to_string()
                .contains("nobody")
        );
    }

    // --- forking, forgetting and closing: the store's writes, as `agent/tests/test_fork.py` and `test_store.py` ----

    fn bare() -> Store {
        let tree = Path::new(env!("CARGO_MANIFEST_DIR"));
        Store::new(Arc::new(Namespaces::of_tree(tree).unwrap())).unwrap()
    }

    fn facts(store: &Store, graph: &str) -> std::collections::BTreeSet<String> {
        store
            .triples(graph)
            .unwrap()
            .into_iter()
            .map(|t| t.to_string())
            .collect()
    }

    fn parent() -> Store {
        let store = bare();
        store
            .update("INSERT DATA { GRAPH <urn:test:parent> { <urn:test:s> <urn:test:level> 5 ; <urn:test:temp> 20 } }")
            .unwrap();
        store
    }

    const LEVEL_10: &str = "<urn:test:s> <urn:test:level> \"10\"^^<http://www.w3.org/2001/XMLSchema#integer>";
    const LEVEL_5: &str = "<urn:test:s> <urn:test:level> \"5\"^^<http://www.w3.org/2001/XMLSchema#integer>";
    const TEMP_20: &str = "<urn:test:s> <urn:test:temp> \"20\"^^<http://www.w3.org/2001/XMLSchema#integer>";

    fn level_10() -> oxigraph::model::Triple {
        oxigraph::model::Triple::new(
            NamedNode::new("urn:test:s").unwrap(),
            NamedNode::new("urn:test:level").unwrap(),
            Literal::new_typed_literal("10", oxigraph::model::vocab::xsd::INTEGER),
        )
    }

    #[test]
    fn a_fork_copies_then_deletes_then_adds_and_leaves_its_parent_as_it_was() {
        let store = parent();
        let retract = "PREFIX t: <urn:test:> DELETE { GRAPH <urn:test:child> { t:s t:level ?l } } \
                   WHERE { GRAPH <urn:test:child> { t:s t:level ?l } }";
        store
            .fork(
                "urn:test:parent",
                "urn:test:child",
                &[level_10()],
                &[retract.to_string()],
            )
            .unwrap();
        assert_eq!(
            facts(&store, "urn:test:child"),
            [LEVEL_10.to_string(), TEMP_20.to_string()].into()
        );
        assert_eq!(
            facts(&store, "urn:test:parent"),
            [LEVEL_5.to_string(), TEMP_20.to_string()].into(),
            "the parent is untouched — a world is a value"
        );
    }

    #[test]
    fn two_retractions_spelling_one_label_two_ways_both_run() {
        let store = parent();
        let one = "PREFIX : <urn:test:> DELETE { GRAPH <urn:test:child> { :s :level ?l } } \
               WHERE { GRAPH <urn:test:child> { :s :level ?l } }";
        let two = "PREFIX : <urn:other:> DELETE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } } \
               WHERE { GRAPH <urn:test:child> { <urn:test:s> <urn:test:temp> ?t } }";
        store
            .fork(
                "urn:test:parent",
                "urn:test:child",
                &[],
                &[one.to_string(), two.to_string()],
            )
            .unwrap();
        assert!(facts(&store, "urn:test:child").is_empty(), "both deletions applied");
    }

    #[test]
    fn a_retraction_that_will_not_run_retracts_nothing_and_the_fork_still_exists() {
        let store = parent();
        store
            .fork(
                "urn:test:parent",
                "urn:test:child",
                &[level_10()],
                &["DELETE nonsense".to_string()],
            )
            .unwrap();
        let child = facts(&store, "urn:test:child");
        assert!(child.contains(LEVEL_5), "the old reading stands");
        assert!(child.contains(LEVEL_10), "and the adds went in");
    }

    #[test]
    fn forgetting_a_graph_forgets_the_beliefs_derived_from_it_and_its_period() {
        let store = bare();
        store
            .update(
                "INSERT DATA {
      GRAPH <urn:cat> { <urn:cat> a orexis:CatalogueGraph .
        <urn:g> a orexis:Graph , orexis:ForecastGraph ; dcterms:temporal [ orexis:start \"2026-01-01T00:00:00Z\" ] .
        <urn:g/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:g> .
        <urn:other/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:other> . }
      GRAPH <urn:g> { <urn:s> <urn:p> 1 }
      GRAPH <urn:g/rev> { <urn:s> <urn:side> <urn:below> }
      GRAPH <urn:other/rev> { <urn:s> <urn:side> <urn:inside> } }",
            )
            .unwrap();
        assert_eq!(store.revisions_of(&["urn:g"], BELIEF).unwrap(), ["urn:g/rev"]);
        store.forget_graph("urn:g", Some(BELIEF)).unwrap();
        assert!(store.revisions_of(&["urn:g"], BELIEF).unwrap().is_empty());
        assert_eq!(
            store
                .rows("SELECT ?g WHERE { GRAPH <urn:cat> { ?g a orexis:Graph } }", &[])
                .unwrap()
                .iter()
                .filter_map(|r| iri(r, "g"))
                .collect::<Vec<_>>(),
            ["urn:other/rev"]
        );
        assert_eq!(
            store.quads("urn:cat").unwrap().len(),
            4,
            "the catalogue's own row and the other revision's three"
        );
        assert!(
            store.quads("urn:g/rev").unwrap().is_empty(),
            "the revision's own quads went too"
        );
        assert!(
            !store.quads("urn:other/rev").unwrap().is_empty(),
            "another graph's revision stands"
        );
    }

    #[test]
    fn closing_the_catalogue_says_on_every_row_each_kind_its_class_is_beneath() {
        let store = store();
        store.close_catalogue().unwrap();
        let state = Within {
            holder: Some(t("me")),
            ..Within::default()
        };
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{T}catalogue> {{ <{T}lately> a <{T}StateGraph> }} }}"
            ))
            .unwrap();
        assert!(!store.graphs_of(&[BELIEF], &state).unwrap().contains(&t("lately")));
        store.close_catalogue().unwrap();
        assert!(
            store.graphs_of(&[BELIEF], &state).unwrap().contains(&t("lately")),
            "closed by one step"
        );
    }

    #[test]
    fn a_trig_dataset_put_replaces_every_graph_it_names_and_its_default_goes_where_it_is_told() {
        let store = store();
        store
            .put_trig(
                &t("world"),
                &format!("<{T}a> <{T}b> <{T}c> . GRAPH <{T}mine> {{ <{T}bed> <{T}believed> <{T}wet> }}"),
            )
            .unwrap();
        assert_eq!(
            facts(&store, &t("world")),
            [format!("<{T}a> <{T}b> <{T}c>")].into(),
            "the world replaced"
        );
        assert_eq!(
            facts(&store, &t("mine")),
            [format!("<{T}bed> <{T}believed> <{T}wet>")].into()
        );
        assert!(
            !facts(&store, &t("catalogue")).is_empty(),
            "a graph it does not name stands"
        );
    }
}
