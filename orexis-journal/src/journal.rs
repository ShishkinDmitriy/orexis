//! THE JOURNAL: what happened to one agent, in RDF, in a triplestore of the agent's own
//! beside its beliefs and apart from them — the events its packages say, kept for good, and its log, kept for the last
//! minutes (the-journal-is-the-agents-flight-recorder).
//!
//! THREE KINDS OF ENTRY, each a named graph named by the node it is about: an EVENT a package says, beneath
//! `orexis:Event`, at its `prov:atTime`, kept for good; a LOG RECORD, `orexis:LogRecord`, its logger, level and
//! message; and an ACTIVITY a package did, a `prov:Activity`, with what started it and what it generated
//! (`orexis-journal/`). The last two are kept for the WINDOW (`JOURNAL_WINDOW_S`, ten minutes where nothing says) and
//! swept after, unless an INCIDENT kept them: the minutes before one are kept for good beside it (`orexis:keptBy`).
//!
//! WHAT AN INCIDENT IS, IS THE VOCABULARY'S, AND WHICH ONES COUNT, THE DEPLOYMENT'S: an entry the history part hands
//! as one, an entry of a class the deployment names (`JOURNAL_INCIDENTS`), and a log record from a level
//! (`JOURNAL_INCIDENT_LEVEL`, WARNING where nothing says). An incident's entry says so, `a orexis:Incident`.
//!
//! SERVED READ-ONLY over the SPARQL protocol (`serve`), on a thread of its own that reads the store and never writes it.

use std::collections::BTreeSet;
use std::sync::{Arc, Mutex};

use oxigraph::io::{RdfFormat, RdfSerializer};
use oxigraph::model::{GraphName, NamedNode, Quad, Term, Triple};
use oxigraph::sparql::results::{QueryResultsFormat, QueryResultsSerializer};
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store as Engine;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::{isoformat, seconds};
use orexis::events::{RDF_TYPE, instant, mint, node, text, typed};

pub const OREXIS: &str = "http://example.org/orexis#";
pub const EVENT: &str = "http://example.org/orexis#Event";
pub const INCIDENT: &str = "http://example.org/orexis#Incident";
pub const LOG_RECORD: &str = "http://example.org/orexis#LogRecord";
pub const AT: &str = "http://www.w3.org/ns/prov#atTime";
pub const KEPT_BY: &str = "http://example.org/orexis#keptBy";
/// An activity a package did, kept as one entry when it ended: PROV's class. Kept for the window, as a log record is.
pub const ACTIVITY: &str = "http://www.w3.org/ns/prov#Activity";
const LOGGER: &str = "http://example.org/orexis#logger";
const LEVEL: &str = "http://example.org/orexis#level";
const MESSAGE: &str = "http://example.org/orexis#message";

/// How long the log is kept where no incident keeps it, in the agent's seconds, where the environment says nothing.
pub const WINDOW_S: f64 = 600.0;
/// How often the window is swept, at most, in the agent's seconds.
const SWEEP_S: f64 = 60.0;
/// The port the endpoint listens on inside the container, where the environment says nothing: oxigraph's own.
pub const PORT: u16 = 7878;

/// The agent's clock, read where an entry says no instant of its own.
pub type Now = Arc<dyn Fn() -> DateTime + Send + Sync>;

/// One agent's journal over a store of its own, keeping its log for `window` of the agent's seconds.
pub struct Journal {
    pub store: Engine,
    window: f64,
    now: Now,
    swept: Mutex<Option<DateTime>>,
    /// From which level a log record is an incident.
    pub incident_level: log::Level,
    /// The classes the deployment counts as incidents besides the vocabulary.
    pub incidents: BTreeSet<String>,
}

/// A log level as the Python journal names it.
pub fn level_name(level: log::Level) -> &'static str {
    match level {
        log::Level::Error => "ERROR",
        log::Level::Warn => "WARNING",
        log::Level::Info => "INFO",
        log::Level::Debug | log::Level::Trace => "DEBUG",
    }
}

fn engine(e: impl std::fmt::Display) -> Error {
    Error::Evaluation(e.to_string())
}

fn literal_of(at: DateTime) -> String {
    format!("\"{}\"^^<http://www.w3.org/2001/XMLSchema#dateTime>", isoformat(at))
}

fn less(at: DateTime, s: f64) -> DateTime {
    at.checked_sub_day_time_duration(seconds(s)).unwrap_or(at)
}

impl Journal {
    /// A journal over `store`, or one in memory, its window `window_s`, read off `now`.
    pub fn new(store: Option<Engine>, window_s: f64, now: Now) -> Result<Self, Error> {
        Ok(Journal {
            store: match store {
                Some(store) => store,
                None => Engine::new().map_err(engine)?,
            },
            window: window_s,
            now,
            swept: Mutex::new(None),
            incident_level: log::Level::Warn,
            incidents: BTreeSet::new(),
        })
    }

    /// The instant the journal stands at, as it stamps an entry given none.
    pub fn now(&self) -> DateTime {
        (self.now)()
    }

    /// Keep the entry `node` — its `triples`, which say what it is — at `at`, or now: a graph named by it, its instant
    /// stamped. An `incident`, or an entry of a class the deployment counts as one, says so and keeps the window of log
    /// before it.
    pub fn record(
        &self,
        entry: &NamedNode,
        triples: Vec<Triple>,
        at: Option<DateTime>,
        incident: bool,
    ) -> Result<(), Error> {
        let at = at.unwrap_or_else(|| (self.now)());
        let mut triples = triples;
        triples.push(Triple::new(entry.clone(), node(AT), instant(at)));
        let counted = triples.iter().any(|t| {
            t.subject == entry.clone().into()
                && t.predicate.as_str() == RDF_TYPE
                && matches!(&t.object, Term::NamedNode(c) if self.incidents.contains(c.as_str()))
        });
        let incident = incident || counted;
        if incident {
            triples.push(typed(entry.clone(), INCIDENT));
        }
        let graph = GraphName::NamedNode(entry.clone());
        self.store
            .extend(
                triples
                    .into_iter()
                    .map(|t| Quad::new(t.subject, t.predicate, t.object, graph.clone())),
            )
            .map_err(engine)?;
        if incident {
            self.keep(entry, at)?;
        }
        let due = self
            .swept
            .lock()
            .unwrap()
            .is_none_or(|last| orexis::clock::seconds_of(at.checked_sub(last).unwrap_or_default()) >= SWEEP_S);
        if due {
            self.sweep(Some(at))?;
        }
        Ok(())
    }

    /// Add `triples` to the entry `entry`, already kept: what is learnt of it after it was — the graphs an activity
    /// wrote, which its turn says once it has ended.
    pub fn add(&self, entry: &NamedNode, triples: Vec<Triple>) -> Result<(), Error> {
        let graph = GraphName::NamedNode(entry.clone());
        self.store
            .extend(
                triples
                    .into_iter()
                    .map(|t| Quad::new(t.subject, t.predicate, t.object, graph.clone())),
            )
            .map_err(engine)
    }

    /// Keep a log record — at the incident level or above an incident, keeping the window before it.
    pub fn remark(
        &self,
        logger: &str,
        level: log::Level,
        message: &str,
        at: Option<DateTime>,
    ) -> Result<NamedNode, Error> {
        let entry = mint();
        let triples = vec![
            typed(entry.clone(), LOG_RECORD),
            typed(entry.clone(), EVENT),
            Triple::new(entry.clone(), node(LOGGER), text(logger)),
            Triple::new(entry.clone(), node(LEVEL), text(level_name(level))),
            Triple::new(entry.clone(), node(MESSAGE), text(message)),
        ];
        self.record(&entry, triples, at, level <= self.incident_level)?;
        Ok(entry)
    }

    /// Keep for good, beside `incident` at `at`, every log record and every activity of the window before it.
    pub fn keep(&self, incident: &NamedNode, at: DateTime) -> Result<(), Error> {
        let text = format!(
            "INSERT {{ GRAPH ?r {{ ?r <{KEPT_BY}> <{}> }} }} WHERE {{ VALUES ?c {{ <{LOG_RECORD}> <{ACTIVITY}> }} GRAPH ?r {{ ?r a ?c ; <{AT}> ?t }} \
             FILTER(?t >= {} && ?t <= {}) FILTER NOT EXISTS {{ GRAPH ?r {{ ?r <{KEPT_BY}> ?any }} }} }}",
            incident.as_str(),
            literal_of(less(at, self.window)),
            literal_of(at)
        );
        SparqlEvaluator::new()
            .parse_update(&text)
            .map_err(engine)?
            .on_store(&self.store)
            .execute()
            .map_err(engine)
    }

    /// Take out every log record and every activity the window has passed that no incident keeps; how many.
    pub fn sweep(&self, now: Option<DateTime>) -> Result<usize, Error> {
        let now = now.unwrap_or_else(|| (self.now)());
        let text = format!(
            "SELECT DISTINCT ?r WHERE {{ VALUES ?c {{ <{LOG_RECORD}> <{ACTIVITY}> }} GRAPH ?r {{ ?r a ?c ; <{AT}> ?t }} FILTER(?t < {}) \
             FILTER NOT EXISTS {{ GRAPH ?r {{ ?r <{KEPT_BY}> ?any }} }} }}",
            literal_of(less(now, self.window))
        );
        let mut gone = Vec::new();
        if let QueryResults::Solutions(solutions) = SparqlEvaluator::new()
            .parse_query(&text)
            .map_err(engine)?
            .on_store(&self.store)
            .execute()
            .map_err(engine)?
        {
            for solution in solutions {
                if let Some(Term::NamedNode(r)) = solution.map_err(engine)?.get("r") {
                    gone.push(r.clone());
                }
            }
        }
        for graph in &gone {
            self.store.remove_named_graph(graph).map_err(engine)?;
        }
        *self.swept.lock().unwrap() = Some(now);
        Ok(gone.len())
    }

    /// What is written reaches the disk, where the store is on one.
    pub fn flush(&self) {
        #[cfg(feature = "volume")]
        let _ = self.store.flush();
    }
}

/// How long the log is kept, in the agent's seconds: `JOURNAL_WINDOW_S`, or ten minutes.
pub fn window_s(env: &dyn Fn(&str) -> Option<String>) -> f64 {
    env("JOURNAL_WINDOW_S").and_then(|s| s.parse().ok()).unwrap_or(WINDOW_S)
}

/// From which level a log record is an incident: `JOURNAL_INCIDENT_LEVEL`, a level's name, or WARNING.
pub fn incident_level(env: &dyn Fn(&str) -> Option<String>) -> log::Level {
    let said = env("JOURNAL_INCIDENT_LEVEL")
        .unwrap_or_else(|| "WARNING".into())
        .to_uppercase();
    match said.as_str() {
        "CRITICAL" | "ERROR" => log::Level::Error,
        "WARNING" | "WARN" => log::Level::Warn,
        "INFO" => log::Level::Info,
        "DEBUG" | "NOTSET" => log::Level::Debug,
        other => {
            log::warn!("JOURNAL_INCIDENT_LEVEL {other:?} is no level — WARNING holds");
            log::Level::Warn
        }
    }
}

/// The classes the deployment counts as incidents beside the vocabulary's: `JOURNAL_INCIDENTS`, IRIs apart.
pub fn incidents(env: &dyn Fn(&str) -> Option<String>) -> BTreeSet<String> {
    env("JOURNAL_INCIDENTS")
        .unwrap_or_default()
        .split_whitespace()
        .map(str::to_string)
        .collect()
}

/// What the SPARQL protocol answers `text` with over `store`: its media type and its body. Every graph is the default
/// graph, so an open pattern reads every entry; `GRAPH` still names one. A query is all it answers.
pub fn answer(store: &Engine, text: &str) -> Result<(&'static str, Vec<u8>), String> {
    let mut query = SparqlEvaluator::new().parse_query(text).map_err(|e| e.to_string())?;
    query.dataset_mut().set_default_graph_as_union();
    let results = query.on_store(store).execute().map_err(|e| e.to_string())?;
    let json = QueryResultsSerializer::from_format(QueryResultsFormat::Json);
    let failed = |e: std::io::Error| e.to_string();
    match results {
        QueryResults::Graph(triples) => {
            let mut serializer = RdfSerializer::from_format(RdfFormat::NTriples).for_writer(Vec::new());
            for t in triples {
                serializer
                    .serialize_triple(&t.map_err(|e| e.to_string())?)
                    .map_err(failed)?;
            }
            Ok(("application/n-triples", serializer.finish().map_err(failed)?))
        }
        QueryResults::Boolean(b) => Ok((
            "application/sparql-results+json",
            json.serialize_boolean_to_writer(Vec::new(), b).map_err(failed)?,
        )),
        QueryResults::Solutions(solutions) => {
            let mut serializer = json
                .serialize_solutions_to_writer(Vec::new(), solutions.variables().to_vec())
                .map_err(failed)?;
            for solution in solutions {
                let solution = solution.map_err(|e| e.to_string())?;
                serializer
                    .serialize(solution.iter().map(|(v, t)| (v.as_ref(), t.as_ref())))
                    .map_err(failed)?;
            }
            Ok(("application/sparql-results+json", serializer.finish().map_err(failed)?))
        }
    }
}

/// Serve `journal` read-only over the SPARQL protocol at `http://<host>:<port>/sparql` — `GET ?query=`, or `POST` of
/// `application/sparql-query` or a form — on a thread of its own; the port it listens on.
#[cfg(feature = "serve")]
pub fn serve(journal: Arc<Journal>, host: &str, port: u16) -> Result<u16, Error> {
    let server = tiny_http::Server::http((host, port)).map_err(engine)?;
    let bound = server.server_addr().to_ip().map_or(port, |a| a.port());
    std::thread::Builder::new()
        .name("journal".into())
        .spawn(move || {
            for mut request in server.incoming_requests() {
                let (path, query) = request.url().split_once('?').unwrap_or((request.url(), ""));
                let (path, query) = (path.to_string(), query.to_string());
                let kind = request
                    .headers()
                    .iter()
                    .find(|h| h.field.equiv("Content-Type"))
                    .map(|h| {
                        h.value
                            .as_str()
                            .split(';')
                            .next()
                            .unwrap_or_default()
                            .trim()
                            .to_string()
                    })
                    .unwrap_or_default();
                let mut body = String::new();
                let _ = request.as_reader().read_to_string(&mut body);
                let text = if *request.method() == tiny_http::Method::Post {
                    if kind == "application/sparql-query" {
                        Some(body)
                    } else {
                        form(&body, "query")
                    }
                } else {
                    form(&query, "query")
                };
                let (status, kind, body) = if path != "/sparql" {
                    (404, "text/plain", b"the journal answers at /sparql\n".to_vec())
                } else {
                    match text.filter(|t| !t.is_empty()) {
                        None => (400, "text/plain", b"a query is asked as ?query= or a body\n".to_vec()),
                        Some(text) => match answer(&journal.store, &text) {
                            Ok((kind, body)) => (200, kind, body),
                            Err(e) => (400, "text/plain", format!("{e}\n").into_bytes()),
                        },
                    }
                };
                let response = tiny_http::Response::from_data(body)
                    .with_status_code(status)
                    .with_header(tiny_http::Header::from_bytes("Content-Type", kind).unwrap())
                    .with_header(tiny_http::Header::from_bytes("Access-Control-Allow-Origin", "*").unwrap());
                let _ = request.respond(response);
            }
        })
        .map_err(engine)?;
    log::info!("the journal answers at http://{host}:{bound}/sparql");
    Ok(bound)
}

/// The value `key` takes in a form or a query string, percent-decoded.
pub fn form(text: &str, key: &str) -> Option<String> {
    text.split('&').find_map(|pair| {
        let (k, v) = pair.split_once('=')?;
        (decode(k) == key).then(|| decode(v))
    })
}

fn decode(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'+' => out.push(b' '),
            b'%' if i + 2 < bytes.len() => {
                match u8::from_str_radix(std::str::from_utf8(&bytes[i + 1..i + 3]).unwrap_or("zz"), 16) {
                    Ok(b) => {
                        out.push(b);
                        i += 2;
                    }
                    Err(_) => out.push(b'%'),
                }
            }
            b => out.push(b),
        }
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

#[cfg(test)]
mod tests {
    //! The journal, held to what `agent/tests/test_journal.py` holds the Python one to.

    use super::*;
    use orexis::clock::instant as parse;

    fn at(s: &str) -> DateTime {
        parse(s).unwrap()
    }

    fn standing(s: &'static str) -> Now {
        Arc::new(move || parse(s).unwrap())
    }

    fn count(journal: &Journal, text: &str) -> usize {
        let (_, body) = answer(&journal.store, text).unwrap();
        let json: String = String::from_utf8(body).unwrap();
        json.matches("\"type\":").count()
    }

    fn rows(journal: &Journal, text: &str) -> Vec<String> {
        let mut query = SparqlEvaluator::new().parse_query(text).unwrap();
        query.dataset_mut().set_default_graph_as_union();
        let QueryResults::Solutions(solutions) = query.on_store(&journal.store).execute().unwrap() else {
            panic!("a select")
        };
        solutions
            .map(|s| {
                let s = s.unwrap();
                s.iter().map(|(_, t)| t.to_string()).collect::<Vec<_>>().join(" ")
            })
            .collect()
    }

    #[test]
    fn an_event_is_kept_for_good_at_its_instant_in_a_graph_named_by_it() {
        let journal = Journal::new(None, 600.0, standing("2026-01-01T12:00:00+00:00")).unwrap();
        let entry = mint();
        journal
            .record(
                &entry,
                vec![typed(entry.clone(), "http://example.org/test#Happened")],
                None,
                false,
            )
            .unwrap();
        let found = rows(
            &journal,
            &format!(
                "SELECT ?t WHERE {{ GRAPH <{}> {{ <{}> <{AT}> ?t }} }}",
                entry.as_str(),
                entry.as_str()
            ),
        );
        assert_eq!(
            found,
            ["\"2026-01-01T12:00:00Z\"^^<http://www.w3.org/2001/XMLSchema#dateTime>"]
        );
        journal.sweep(Some(at("2026-01-02T12:00:00+00:00"))).unwrap();
        assert_eq!(
            count(&journal, "SELECT ?e WHERE { ?e a <http://example.org/test#Happened> }"),
            1,
            "an event is kept for good"
        );
    }

    #[test]
    fn the_log_is_swept_past_its_window_and_an_incident_keeps_the_minutes_before_it() {
        let journal = Journal::new(None, 600.0, standing("2026-01-01T12:00:00+00:00")).unwrap();
        journal
            .remark(
                "planning",
                log::Level::Info,
                "long before",
                Some(at("2026-01-01T11:00:00+00:00")),
            )
            .unwrap();
        journal
            .remark(
                "planning",
                log::Level::Info,
                "just before",
                Some(at("2026-01-01T11:55:00+00:00")),
            )
            .unwrap();
        let failed = journal
            .remark(
                "execution",
                log::Level::Warn,
                "a step did not land",
                Some(at("2026-01-01T12:00:00+00:00")),
            )
            .unwrap();
        journal
            .remark(
                "planning",
                log::Level::Info,
                "after",
                Some(at("2026-01-01T12:01:00+00:00")),
            )
            .unwrap();
        journal.sweep(Some(at("2026-01-01T13:00:00+00:00"))).unwrap();
        let mut left = rows(
            &journal,
            "SELECT ?m WHERE { ?r a <http://example.org/orexis#LogRecord> ; <http://example.org/orexis#message> ?m }",
        );
        left.sort();
        assert_eq!(
            left,
            ["\"a step did not land\"", "\"just before\""],
            "the incident and the window before it"
        );
        assert_eq!(
            rows(
                &journal,
                "SELECT ?r WHERE { ?r a <http://example.org/orexis#Incident> }"
            ),
            [failed.to_string()]
        );
        let mut kept = rows(
            &journal,
            "SELECT ?l WHERE { ?r <http://example.org/orexis#keptBy> ?i ; <http://example.org/orexis#level> ?l }",
        );
        kept.sort();
        assert_eq!(
            kept,
            ["\"INFO\"", "\"WARNING\""],
            "the window before it and itself, levels named as Python names them"
        );
    }

    #[test]
    fn a_class_the_deployment_counts_is_an_incident_though_the_vocabulary_says_nothing() {
        let mut journal = Journal::new(None, 600.0, standing("2026-01-01T12:00:00+00:00")).unwrap();
        journal.incidents =
            incidents(&|k| (k == "JOURNAL_INCIDENTS").then(|| "http://example.org/test#Bad".to_string()));
        let entry = mint();
        journal
            .record(
                &entry,
                vec![typed(entry.clone(), "http://example.org/test#Bad")],
                None,
                false,
            )
            .unwrap();
        assert_eq!(
            count(
                &journal,
                "SELECT ?e WHERE { ?e a <http://example.org/orexis#Incident> }"
            ),
            1
        );
    }

    #[test]
    fn the_environment_says_the_window_and_the_level_and_a_word_that_is_no_level_leaves_warning() {
        let none = |_: &str| None;
        assert_eq!(window_s(&none), 600.0);
        assert_eq!(window_s(&|_: &str| Some("30".into())), 30.0);
        assert_eq!(incident_level(&none), log::Level::Warn);
        assert_eq!(incident_level(&|_: &str| Some("error".into())), log::Level::Error);
        assert_eq!(incident_level(&|_: &str| Some("loud".into())), log::Level::Warn);
    }

    #[test]
    fn a_construct_is_answered_in_n_triples_and_a_select_in_the_results_json() {
        let journal = Journal::new(None, 600.0, standing("2026-01-01T12:00:00+00:00")).unwrap();
        journal.remark("runtime", log::Level::Info, "hello", None).unwrap();
        let (kind, _) = answer(&journal.store, "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }").unwrap();
        assert_eq!(kind, "application/n-triples");
        let (kind, body) = answer(
            &journal.store,
            "SELECT ?m WHERE { ?r <http://example.org/orexis#message> ?m }",
        )
        .unwrap();
        assert_eq!(kind, "application/sparql-results+json");
        assert!(String::from_utf8(body).unwrap().contains("hello"));
        assert!(
            answer(&journal.store, "INSERT DATA { <a:b> <a:c> <a:d> }").is_err(),
            "an update is no query"
        );
    }

    #[test]
    fn a_form_is_read_percent_decoded() {
        assert_eq!(
            form("query=SELECT+%3Fs+WHERE+%7B%7D&x=1", "query").as_deref(),
            Some("SELECT ?s WHERE {}")
        );
        assert_eq!(form("x=1", "query"), None);
    }
}
