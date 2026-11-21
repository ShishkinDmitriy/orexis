//! THE STORE: Oxigraph's engine, the texts it keeps parsed, and what each graph's metadata graph says it is.
//!
//! **A TEXT IS KEPT PARSED, AND WHAT IS KEPT IS CAPPED.** A text a pass runs is parsed the first time it is run and
//! kept parsed by its text, so a rule asked per world, a read asked per candidate, is not parsed again. Measured on
//! the bench Pi (`examples/parsing.rs`), a statement takes 40 µs to parse, and a greenhouse pass runs about 1,650:
//! 66 ms of a 460 ms pass, every pass, where ten passes' 16,551 statements are 1,454 texts, parsed once in 68 ms.
//! A value is bound into the text, so a text naming an instant or a possible world is new each time and is never
//! asked again: kept without a cap, a day of the greenhouse left 118 MB of them, so each cache holds the texts
//! asked most recently (`KEPT`), and one that falls out is parsed again if it is ever asked.
//!
//! **A READER STATES THE GRAPHS IT READS**, and the store decides nothing (a-reader-states-the-kinds-it-reads):
//! `rows` is handed the graphs its default graph is the union of, `graphs_of` answers which by kind and instant,
//! and a text that reads one graph names it in its own `GRAPH` clause. Never wrap `GRAPH <…>` around a select.

use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::num::NonZeroUsize;
use std::ops::Deref;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

use lru::LruCache;
use oxigraph::io::RdfFormat;
use oxigraph::model::vocab::rdf;
use oxigraph::model::{GraphName, GraphNameRef, NamedNode, NamedNodeRef, NamedOrBlankNode, Quad, Term, Triple};
use oxigraph::sparql::{PreparedSparqlQuery, PreparedSparqlUpdate, QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;
use oxsdatatypes::DateTime;

use crate::Error;
use crate::bind::{Value, bind};
use crate::ontology::{BELIEF, HASH, METADATA_GRAPH, METADATA_OF};

/// One solution: each variable it binds, to the term it binds.
pub type Row = BTreeMap<String, Term>;

/// How many parsed texts each cache keeps: about 6 KB each, measured over a day of the greenhouse.
const KEPT: NonZeroUsize = NonZeroUsize::new(1000).expect("a cap above nought");

/// A cache of what has been parsed, by its text.
type Parsed<T> = Mutex<LruCache<String, T>>;

fn parsed_cache<T>() -> Parsed<T> {
    Mutex::new(LruCache::new(KEPT))
}

/// THE AGENT'S STORE, a handle: cloned, it is the same store, so whoever holds one holds it for as long as it lives and
/// borrows nothing - as the engine's own handle is.
#[derive(Clone)]
pub struct Store(Arc<Held>);

impl Deref for Store {
    type Target = Held;

    fn deref(&self) -> &Held {
        &self.0
    }
}

/// The engine, and what has been parsed: every text declares the prefixes it speaks.
pub struct Held {
    engine: Engine,
    queries: Parsed<PreparedSparqlQuery>,
    updates: Parsed<PreparedSparqlUpdate>,
    algebra: Parsed<spargebra::Update>,
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

const PROV_DERIVED: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";
const ARRIVED_BY: &str = "http://example.org/orexis#arrivedBy";
const OWNED_BY: &str = "http://example.org/orexis#ownedBy";
/// THE WORDS A GRAPH'S METADATA IS SAID IN, beside its period: what it is, how it arrived, whose it is, what it holds by
/// hash and what it was derived from. What a package says of a graph in words of its own is that package's.
pub const METADATA: [&str; 5] = [crate::rdf::RDF_TYPE, ARRIVED_BY, OWNED_BY, HASH, PROV_DERIVED];
const DCTERMS_TEMPORAL: &str = "http://purl.org/dc/terms/temporal";
const ORE: &str = "http://example.org/orexis#";
const XSD_DATETIME: &str = "http://www.w3.org/2001/XMLSchema#dateTime";

impl Store {
    /// An empty store, in memory.
    pub fn new() -> Result<Self, Error> {
        Ok(Store(Arc::new(Held {
            engine: Engine::new().map_err(|e| Error::Evaluation(e.to_string()))?,
            queries: parsed_cache(),
            updates: parsed_cache(),
            algebra: parsed_cache(),
            parsed: AtomicUsize::new(0),
            run: AtomicUsize::new(0),
            updated: AtomicUsize::new(0),
        })))
    }

    /// A store on disk at `path`, opened or made: a volume an agent lives in.
    #[cfg(feature = "volume")]
    pub fn open(path: &std::path::Path) -> Result<Self, Error> {
        Ok(Store(Arc::new(Held {
            engine: Engine::open(path).map_err(|e| Error::Evaluation(e.to_string()))?,
            queries: parsed_cache(),
            updates: parsed_cache(),
            algebra: parsed_cache(),
            parsed: AtomicUsize::new(0),
            run: AtomicUsize::new(0),
            updated: AtomicUsize::new(0),
        })))
    }

    /// The engine itself, for a reader of quads.
    pub fn engine(&self) -> &Engine {
        &self.engine
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
        SparqlEvaluator::new()
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
        parsed.put(text.to_string(), query.clone());
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
                    parsed.put(text.to_string(), update.clone());
                    update
                }
            }
        };
        update
            .on_store(&self.engine)
            .execute()
            .map_err(|e| Error::Evaluation(e.to_string()))
    }

    /// An update text as its ALGEBRA, parsed once by its text, which declares its own prefixes — for a runner
    /// that says on the parse what the text does not: which graph it changes and which it reads.
    pub fn parse_update(&self, text: &str) -> Result<spargebra::Update, Error> {
        self.run.fetch_add(1, Ordering::Relaxed);
        self.updated.fetch_add(1, Ordering::Relaxed);
        let mut parsed = self.algebra.lock().expect("a cache nobody poisoned");
        if let Some(update) = parsed.get(text) {
            return Ok(update.clone());
        }
        let parser = spargebra::SparqlParser::new();
        let update = parser
            .parse_update(text)
            .map_err(|e| Error::Syntax(format!("{e}: {text}")))?;
        self.parsed.fetch_add(1, Ordering::Relaxed);
        parsed.put(text.to_string(), update.clone());
        Ok(update)
    }

    /// A query text as its ALGEBRA, declaring its own prefixes — for a reader of what a text says, never
    /// to run it.
    pub fn parse_query(&self, text: &str) -> Result<spargebra::Query, Error> {
        let parser = spargebra::SparqlParser::new();
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

    /// THE GRAPH THAT SAYS WHAT `graph` IS, found by what it says of itself: None for a graph nobody has said
    /// anything of. Asked of the index, one lookup by the link.
    pub fn metadata_of(&self, graph: &str) -> Result<Option<String>, Error> {
        let (of, graph) = (named(METADATA_OF)?, named(graph)?);
        for quad in self
            .engine
            .quads_for_pattern(None, Some(of.as_ref()), Some(graph.as_ref().into()), None)
        {
            let quad = quad.map_err(engine)?;
            if let (NamedOrBlankNode::NamedNode(subject), GraphName::NamedNode(within)) =
                (&quad.subject, &quad.graph_name)
                && subject == within
            {
                return Ok(Some(within.as_str().to_string()));
            }
        }
        Ok(None)
    }

    /// Every kind `graph`'s metadata says it is; none for a graph nobody has said anything of.
    pub fn kinds_of(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(metadata) = self.metadata_of(graph)? else {
            return Ok(Vec::new());
        };
        Ok(self
            .objects(&Term::NamedNode(named(graph)?), crate::rdf::RDF_TYPE, &metadata)?
            .into_iter()
            .filter_map(|kind| match kind {
                Term::NamedNode(kind) => Some(kind.into_string()),
                _ => None,
            })
            .collect())
    }

    /// What `graph`'s metadata says of it by `predicate`: nothing for a graph nobody has said anything of.
    pub fn said_of(&self, graph: &str, predicate: &str) -> Result<Vec<Term>, Error> {
        match self.metadata_of(graph)? {
            Some(metadata) => self.objects(&Term::NamedNode(named(graph)?), predicate, &metadata),
            None => Ok(Vec::new()),
        }
    }

    /// The graph `graph`'s metadata is written in: the one that says it is, or the name a writer gives a new one.
    pub fn metadata_for(&self, graph: &str) -> Result<String, Error> {
        Ok(self
            .metadata_of(graph)?
            .unwrap_or_else(|| crate::metadata::named(graph)))
    }

    /// Whether the store holds any graph's metadata: a store somebody has told what its graphs are.
    pub fn described(&self) -> Result<bool, Error> {
        let of = named(METADATA_OF)?;
        Ok(self
            .engine
            .quads_for_pattern(None, Some(of.as_ref()), None, None)
            .next()
            .transpose()
            .map_err(engine)?
            .is_some())
    }

    /// Every graph whose metadata says it is of any of `kinds` — beneath them too, its kinds closed when written —
    /// as `within` narrows them, in name order. THE ONE LOOKUP A READER TAKES, and it decides nothing else.
    ///
    /// ASKED OF THE INDEX, NOT BY A TEXT: what is of a kind is one scan of the type's index, kept where the graph
    /// saying it is the metadata graph of the graph it is said of, and what each then says of its owner and its
    /// period a lookup in that graph.
    pub fn graphs_of(&self, kinds: &[&str], within: &Within) -> Result<Vec<String>, Error> {
        let of = named(METADATA_OF)?;
        let mut found: BTreeMap<String, NamedNode> = BTreeMap::new();
        for kind in kinds {
            let kind = named(kind)?;
            for quad in self
                .engine
                .quads_for_pattern(None, Some(rdf::TYPE), Some(kind.as_ref().into()), None)
            {
                let quad = quad.map_err(engine)?;
                if let (NamedOrBlankNode::NamedNode(graph), GraphName::NamedNode(metadata)) =
                    (quad.subject, quad.graph_name)
                    && !found.contains_key(graph.as_str())
                    && self
                        .engine
                        .contains(&Quad::new(
                            metadata.clone(),
                            of.clone(),
                            graph.clone(),
                            metadata.clone(),
                        ))
                        .map_err(engine)?
                {
                    found.insert(graph.into_string(), metadata);
                }
            }
        }
        let mut out = Vec::with_capacity(found.len());
        for (graph, metadata) in found {
            if self.is_within(&graph, metadata.as_str(), within)? {
                out.push(graph);
            }
        }
        Ok(out)
    }

    /// Whether `graph` is one `within` asks for, by what `metadata` says of it: the holder's or nobody's where a
    /// holder is named, nobody's where the common ones are asked, and HOLDING AT THE INSTANT where one is given —
    /// begun by `at` and not ended by `until`, a record read at the present, a graph saying no period at any.
    fn is_within(&self, graph: &str, metadata: &str, within: &Within) -> Result<bool, Error> {
        let me = Term::NamedNode(named(graph)?);
        if within.holder.is_some() || within.common {
            let owners = self.objects(&me, OWNED_BY, metadata)?;
            let mine = |owner: &Term| matches!((owner, &within.holder), (Term::NamedNode(o), Some(holder)) if o.as_str() == holder);
            if !owners.is_empty() && (within.common || !owners.iter().any(mine)) {
                return Ok(false);
            }
        }
        let Some(at) = within.at else {
            return Ok(true);
        };
        let (when, till) = if self.holds(graph, crate::rdf::RDF_TYPE, crate::ontology::RECORD, metadata)? {
            let now = within.now.unwrap_or(at);
            (now, now)
        } else {
            (at, within.until.unwrap_or(at))
        };
        let instants = |period: &Term, bound: &str| -> Result<Vec<Option<DateTime>>, Error> {
            Ok(self
                .objects(period, bound, metadata)?
                .iter()
                .map(|t| match t {
                    Term::Literal(l) => l.value().parse::<DateTime>().ok(),
                    _ => None,
                })
                .collect())
        };
        let periods = self.objects(&me, DCTERMS_TEMPORAL, metadata)?;
        if periods.is_empty() {
            return Ok(true);
        }
        for period in &periods {
            let (starts, ends) = (
                instants(period, crate::ontology::START)?,
                instants(period, crate::ontology::END)?,
            );
            let begun = starts.is_empty() || starts.iter().any(|s| s.is_some_and(|s| when >= s));
            let holding = ends.is_empty() || ends.iter().any(|e| e.is_some_and(|e| till < e));
            if begun && holding {
                return Ok(true);
            }
        }
        Ok(false)
    }

    /// `class` and every class the vocabulary puts it beneath, sorted; the class alone where no vocabulary is.
    pub fn closed(&self, class: &str) -> Result<Vec<String>, Error> {
        const SUBCLASSES_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?super WHERE {
          GRAPH ?m { ?vocabulary a orexis:OntologyGraph }
          GRAPH ?vocabulary { $cls rdfs:subClassOf ?super . FILTER(isIRI(?super)) } }";
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

    /// A GRAPH'S METADATA, as the `GRAPH … { … }` block a writer puts beside the graph's own in ONE update, so a
    /// graph and its metadata land together or not at all: its metadata graph, saying which graph it is of, every
    /// kind that graph is, how it arrived, whose, and the period it holds over. Written in whole IRIs, so it needs
    /// no prefix of the text it is put in.
    pub fn entry(
        &self,
        graph: &str,
        classes: &[&str],
        arrival: &str,
        owner: Option<&str>,
        start: Option<DateTime>,
        end: Option<DateTime>,
    ) -> Result<String, Error> {
        let metadata = self.metadata_for(graph)?;
        let whose = owner.map(|o| format!(" ; <{ORE}ownedBy> <{o}>")).unwrap_or_default();
        let bounds: String = [("start", start), ("end", end)]
            .iter()
            .filter_map(|(k, v)| {
                v.map(|v| format!(" ; <{ORE}{k}> \"{}\"^^<{XSD_DATETIME}>", crate::clock::isoformat(v)))
            })
            .collect();
        let when = if bounds.is_empty() {
            String::new()
        } else {
            format!(" ; <{DCTERMS_TEMPORAL}> [ a <http://purl.org/dc/terms/PeriodOfTime>{bounds} ]")
        };
        let mut kinds = Vec::new();
        for class in classes {
            kinds.extend(self.closed(class)?);
        }
        kinds.sort();
        kinds.dedup();
        let kinds = kinds.iter().map(|k| format!("<{k}>")).collect::<Vec<_>>().join(" , ");
        Ok(format!(
            "GRAPH <{metadata}> {{ <{metadata}> a <{METADATA_GRAPH}> ; <{METADATA_OF}> <{graph}> . \
             <{graph}> a {kinds} ; <{ORE}arrivedBy> <{arrival}>{whose}{when} . }}"
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
        let metadata = self.metadata_for(graph)?;
        self.update(&format!(
            "INSERT {{ {block} }}\nWHERE  {{ FILTER NOT EXISTS {{ GRAPH <{metadata}> \
             {{ <{graph}> <{DCTERMS_TEMPORAL}> ?period }} }} }}"
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

    /// What `subject` says under `predicate` in `graph`, in no order: the one-hop read a graph's metadata is, asked of
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

    /// Every graph of `kind` that says it was derived from one of `sources`, sorted: what the rules concluded of
    /// them, their revisions.
    pub fn revisions_of(&self, sources: &[&str], kind: &str) -> Result<Vec<String>, Error> {
        let (derived, kind, of) = (named(PROV_DERIVED)?, named(kind)?, named(METADATA_OF)?);
        let mut out = BTreeSet::new();
        for source in sources {
            let source = named(source)?;
            for quad in self
                .engine
                .quads_for_pattern(None, Some(derived.as_ref()), Some(source.as_ref().into()), None)
            {
                let quad = quad.map_err(engine)?;
                let (NamedOrBlankNode::NamedNode(graph), GraphName::NamedNode(metadata)) =
                    (&quad.subject, &quad.graph_name)
                else {
                    continue;
                };
                let says = |p: NamedNodeRef, s: &NamedNode, o: &NamedNode| {
                    self.engine
                        .contains(&Quad::new(s.clone(), p, o.clone(), metadata.clone()))
                        .map_err(engine)
                };
                if says(of.as_ref(), metadata, graph)? && says(rdf::TYPE, graph, &kind)? {
                    out.insert(graph.as_str().to_string());
                }
            }
        }
        Ok(out.into_iter().collect())
    }

    /// Say a graph stops holding at `at`, and its revisions with it, of the kind `revisions` says they are — where it
    /// held past `at`; one that has ended already is left as it stands, and one that begins later ends where it
    /// begins, holding at no instant. An observation's period is said when it arrives, until the next reading is
    /// due, and the next arriving earlier ends it there.
    pub fn end_graph(&self, graph: &str, at: DateTime, revisions: &str) -> Result<(), Error> {
        /// A GRAPH ENDS WHERE IT HELD PAST: its period's end moved to `$at`, or to its start where it begins later.
        const END_U: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX orexis: <http://example.org/orexis#>
        DELETE { GRAPH $in { ?period orexis:end ?was } }
        INSERT { GRAPH $in { ?period orexis:end ?end } }
        WHERE  { GRAPH $in { $graph dcterms:temporal ?period .
                             OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?was }
                             BIND(IF(BOUND(?start) && ?start > $at, ?start, $at) AS ?end)
                             FILTER(!BOUND(?was) || ?was > ?end) } }";
        let mut graphs = vec![graph.to_string()];
        graphs.extend(self.revisions_of(&[graph], revisions)?);
        for graph in graphs {
            let Some(metadata) = self.metadata_of(&graph)? else {
                continue;
            };
            self.update(&bind(
                END_U,
                &[
                    ("in", Value::iri(metadata)),
                    ("at", Value::instant(at)),
                    ("graph", Value::iri(graph)),
                ],
            )?)?;
        }
        Ok(())
    }

    /// Empty one graph AND its metadata graph with it — and its revisions, of the kind `revisions` says they are;
    /// None takes the graph alone.
    pub fn forget_graph(&self, graph: &str, revisions: Option<&str>) -> Result<(), Error> {
        if let Some(kind) = revisions {
            for revision in self.revisions_of(&[graph], kind)? {
                self.forget_graph(&revision, Some(BELIEF))?;
            }
        }
        self.clear_graph(graph)?;
        while let Some(metadata) = self.metadata_of(graph)? {
            self.clear_graph(&metadata)?;
        }
        Ok(())
    }

    /// Say of every graph each kind the vocabulary puts its class beneath — what `entry` writes for a new graph,
    /// said again of every graph there is. Idempotent.
    pub fn close_kinds(&self) -> Result<(), Error> {
        let of = named(METADATA_OF)?;
        let mut rows = Vec::new();
        let said: Vec<Quad> = self
            .engine
            .quads_for_pattern(None, Some(of.as_ref()), None, None)
            .collect::<Result<_, _>>()
            .map_err(engine)?;
        for quad in said {
            let (Term::NamedNode(graph), GraphName::NamedNode(metadata)) = (quad.object, quad.graph_name) else {
                continue;
            };
            let classes: Vec<Quad> = self
                .engine
                .quads_for_pattern(
                    Some(graph.as_ref().into()),
                    Some(rdf::TYPE),
                    None,
                    Some(GraphNameRef::NamedNode(metadata.as_ref())),
                )
                .collect::<Result<_, _>>()
                .map_err(engine)?;
            for class in classes {
                let Term::NamedNode(class) = class.object else {
                    continue;
                };
                for kind in self.closed(class.as_str())? {
                    rows.push(Quad::new(graph.clone(), rdf::TYPE, named(&kind)?, metadata.clone()));
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
    //! The store's reads, over five graphs whose metadata a fixture says together.

    use std::path::Path;

    use super::*;
    use crate::clock::instant as at;
    use crate::ontology::{BELIEF, DERIVED, RECORD};

    const T: &str = "http://example.org/test#";

    /// Five graphs, what they are said together in one block and moved from it: the world's, the agent's own state, a peer's, one holding for an hour, and a record
    /// whose hour is over — with the vocabulary saying a state graph is a belief.
    const SAID_OF_FIVE: &str = r#"
@prefix orexis: <http://example.org/orexis#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix : <http://example.org/test#> .

:said {
  :vocabulary a orexis:Graph , orexis:OntologyGraph .
  :world a orexis:Graph , orexis:BeliefGraph .
  :mine a orexis:Graph , orexis:BeliefGraph ; orexis:ownedBy :me .
  :theirs a orexis:Graph , orexis:BeliefGraph ; orexis:ownedBy :them .
  :hour a orexis:Graph , orexis:BeliefGraph ; dcterms:temporal [ orexis:start "2026-01-01T12:00:00Z"^^xsd:dateTime ;
                                                    orexis:end "2026-01-01T13:00:00Z"^^xsd:dateTime ] .
  :record a orexis:Graph , orexis:RecordGraph ; dcterms:temporal [ orexis:start "2026-01-01T10:00:00Z"^^xsd:dateTime ;
                                                     orexis:end "2026-01-01T11:00:00Z"^^xsd:dateTime ] .
}
:vocabulary { :StateGraph rdfs:subClassOf orexis:BeliefGraph . }
:world { :bed :moisture 0.3 . }
:mine { :bed :believed :dry . }
"#;

    fn store() -> Store {
        let _tree = Path::new(crate::boot::TREE);
        let store = Store::new().unwrap();
        store.load_trig(SAID_OF_FIVE).unwrap();
        crate::snapshots::mirrored(&store, &t("said"));
        store
    }

    fn t(local: &str) -> String {
        format!("{T}{local}")
    }

    #[test]
    fn a_graphs_metadata_graph_is_found_by_what_it_says_it_is_of() {
        let store = store();
        assert_eq!(store.metadata_of(&t("mine")).unwrap(), Some(t("mine.metadata")));
        assert_eq!(store.metadata_of(&t("nobody")).unwrap(), None);
        assert_eq!(store.metadata_for(&t("nobody")).unwrap(), t("nobody.metadata"));
        assert!(store.described().unwrap());
        assert!(!Store::new().unwrap().described().unwrap());
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
        let text = "PREFIX : <http://example.org/test#> SELECT ?p ?o WHERE { :bed ?p ?o } ORDER BY ?p";
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
    fn an_entry_says_every_kind_whose_and_when_and_lands_with_its_graph() {
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
                "PREFIX : <http://example.org/test#>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX orexis: <http://example.org/orexis#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    INSERT DATA {{ GRAPH :state {{ :bed :believed :wet }} {entry} }}"
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
        store.closed(BELIEF).unwrap();
        let (parsed, run) = store.statements();
        for _ in 0..10 {
            store.closed(BELIEF).unwrap();
        }
        assert_eq!(
            store.statements(),
            (parsed, run + 10),
            "the text was parsed as the fixture was made"
        );
    }

    #[test]
    fn what_is_kept_parsed_is_capped_and_the_text_still_asked_stays() {
        let store = store();
        let before = store.statements();
        let asked = "ASK { ?s ?p ?o }";
        let once = KEPT.get() + 1;
        for i in 0..once {
            store.ask(asked, &[]).unwrap();
            store
                .ask(
                    &format!(
                        "PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX orexis: <http://example.org/orexis#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                ASK {{ <urn:once:{i}> ?p ?o }}"
                    ),
                    &[],
                )
                .unwrap();
        }
        let (parsed, run) = store.statements();
        assert_eq!(
            (parsed - before.0, run - before.1),
            (once + 1, 2 * once),
            "the text still asked was parsed the once"
        );
        assert_eq!(store.queries.lock().unwrap().len(), KEPT.get());
    }

    #[test]
    fn a_prefix_the_tree_declares_is_spoken_without_a_header() {
        let store = store();
        let rows = store
            .rows(
                "PREFIX orexis: <http://example.org/orexis#>
                SELECT ?g WHERE { GRAPH ?m { ?g a orexis:OntologyGraph } }",
                &[],
            )
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

    // --- forgetting and closing: the store's writes, as `agent/tests/test_store.py` -----------------------------------

    fn bare() -> Store {
        let _tree = Path::new(crate::boot::TREE);
        Store::new().unwrap()
    }

    fn facts(store: &Store, graph: &str) -> std::collections::BTreeSet<String> {
        store
            .triples(graph)
            .unwrap()
            .into_iter()
            .map(|t| t.to_string())
            .collect()
    }

    #[test]
    fn forgetting_a_graph_forgets_the_beliefs_derived_from_it_and_its_period() {
        let store = bare();
        store
            .update(
                "PREFIX dcterms: <http://purl.org/dc/terms/>
      PREFIX orexis: <http://example.org/orexis#>
      PREFIX prov: <http://www.w3.org/ns/prov#>
      INSERT DATA {
      GRAPH <urn:said> {
        <urn:g> a orexis:Graph , orexis:ForecastGraph ; dcterms:temporal [ orexis:start \"2026-01-01T00:00:00Z\" ] .
        <urn:g/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:g> .
        <urn:other/rev> a orexis:Graph , orexis:BeliefGraph ; prov:wasDerivedFrom <urn:other> . }
      GRAPH <urn:g> { <urn:s> <urn:p> 1 }
      GRAPH <urn:g/rev> { <urn:s> <urn:side> <urn:below> }
      GRAPH <urn:other/rev> { <urn:s> <urn:side> <urn:inside> } }",
            )
            .unwrap();
        crate::snapshots::mirrored(&store, "urn:said");
        assert_eq!(store.revisions_of(&["urn:g"], BELIEF).unwrap(), ["urn:g/rev"]);
        store.forget_graph("urn:g", Some(BELIEF)).unwrap();
        assert!(store.revisions_of(&["urn:g"], BELIEF).unwrap().is_empty());
        assert_eq!(
            store.graphs_of(&[crate::ontology::GRAPH], &Within::default()).unwrap(),
            ["urn:other/rev"]
        );
        assert_eq!(
            store.graph_names().unwrap(),
            ["urn:other/rev", "urn:other/rev.metadata"],
            "each graph forgotten took its metadata graph with it"
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
    fn closing_the_kinds_says_of_every_graph_each_kind_its_class_is_beneath() {
        let store = store();
        store.close_kinds().unwrap();
        let state = Within {
            holder: Some(t("me")),
            ..Within::default()
        };
        store
            .update(
                "PREFIX : <http://example.org/test#>
                    INSERT DATA { GRAPH :said { :lately a <http://example.org/orexis#Graph> , :StateGraph } }",
            )
            .unwrap();
        crate::snapshots::mirrored(&store, &t("said"));
        assert!(!store.graphs_of(&[BELIEF], &state).unwrap().contains(&t("lately")));
        store.close_kinds().unwrap();
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
            !facts(&store, &t("vocabulary")).is_empty(),
            "a graph it does not name stands"
        );
    }
}
