//! SPEECH'S PART, as `agent/speech/create.py` makes it (a-package-starts-itself): it says what a step said, as the
//! agent said it (`said`), and says `speech:Said`, naming the statements and each agent they are to, which whoever
//! reaches a peer — a transport — or a person — translation — puts beneath a trigger of its own. What
//! a peer says to it, `heard` keeps, called by the transport. STARTED, IT EXTRACTS WHAT IS BELIEVED OF EVERY STATEMENT
//! WRITTEN (#958): it hears its own kind, heard or said alike, and `extract` writes what the extractions conclude of
//! it into a belief graph, which the runtime then hands whoever revises beliefs. A statement written before the part
//! started — a volume lived in — is extracted from at start where nothing was.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::RECEIVED;
use orexis::store::{Store, iri};
use orexis::task::{Arrived, Every, Handed, Heard as HeardEvent, Hears, Package, Task, Turn, Woke, sooner};
use oxigraph::model::{BlankNode, GraphName, NamedNode, Quad, Triple};

use crate::events::{Heard, Said, Statement};

use crate::extract::extract;
use crate::ontology::{SPEAKING, SPEAKING_TRIGGER, STATEMENT, STATEMENT_GRAPH, TO};
use crate::said::said;

const STATED: usize = 0;
const EXTRACTED: usize = 1;
const SPEAK: usize = 2;

/// EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
const UNEXTRACTED_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { ?g a speech:StatementGraph FILTER NOT EXISTS { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g";

/// HOW A STATEMENT ARRIVED, and THE KINDS IT SAYS IT IS: what is said of it.
const ARRIVAL_Q: &str = "SELECT ?arrival WHERE { GRAPH $cat { $graph orexis:arrivedBy ?arrival } }";
/// A STATEMENT'S PERIOD, as it was said.
const PERIOD_Q: &str = "
SELECT ?start ?end WHERE { GRAPH $cat { $graph dcterms:temporal ?p OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } LIMIT 1";
const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const TEMPORAL: &str = "http://purl.org/dc/terms/temporal";
const START: &str = "http://example.org/orexis#start";
const END: &str = "http://example.org/orexis#end";
const KINDS_Q: &str = "
SELECT ?k WHERE { GRAPH $cat { $graph a ?k FILTER(?k NOT IN (speech:StatementGraph, orexis:Graph)) } } ORDER BY ?k";

/// The kinds `graph` says it is, and what it says.
fn described(beliefs: &Store, graph: &str) -> Result<(Vec<String>, Vec<Triple>), Error> {
    let kinds = match beliefs.catalogue()? {
        Some(cat) => beliefs
            .rows(
                &bind(KINDS_Q, &[("cat", Value::iri(cat)), ("graph", Value::iri(graph))])?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "k"))
            .collect(),
        None => Vec::new(),
    };
    let said = match NamedNode::new(graph) {
        Ok(g) => beliefs
            .engine()
            .quads_for_pattern(None, None, None, Some(g.as_ref().into()))
            .flatten()
            .map(|q| Triple::new(q.subject, q.predicate, q.object))
            .collect(),
        Err(_) => Vec::new(),
    };
    Ok((kinds, said))
}

/// What says a document: shared by the part and whoever says through it.
pub struct Speaker {
    beliefs: Store,
    pub me: String,
    /// Whoever watches the agent, and the instant the pass stands at.
    pub watch: Watch,
}

impl Speaker {
    /// Believe `document` as the agent said it, and say it said to every agent it is `to`; the graphs believed.
    pub fn say(&self, document: &Document, to: &[String]) -> Result<Vec<String>, Error> {
        let written = said(&self.beliefs, &self.me, document)?;
        self.tell_said(&written, to)?;
        Ok(written)
    }

    /// Say that the statements `written` were said to `to`, for whoever carries them to each.
    fn tell_said(&self, written: &[String], to: &[String]) -> Result<(), Error> {
        let watch = self.watch.clone();
        if !watch.connected() {
            return Ok(());
        }
        let mut statements = Vec::new();
        for graph in written {
            let (kinds, said) = described(&self.beliefs, graph)?;
            statements.push(Statement {
                graph: graph.clone(),
                kinds,
                said,
            });
        }
        watch.emit(&Said {
            statements,
            to: to.to_vec(),
            at: watch.at(),
        });
        Ok(())
    }
}

/// THE STATEMENTS `graphs` AS THEY WERE SAID, read back from the store: each graph's contents, the kinds it says it
/// is - the most specific, since the store wrote every kind each is beneath and the statement kind beside them - and
/// its period, where it says one.
pub fn document_of(beliefs: &Store, graphs: &[String]) -> Result<Document, Error> {
    let mut quads = Vec::new();
    let Some(cat) = beliefs.catalogue()? else {
        return Ok(Document::of_quads(quads));
    };
    let rdf_type = NamedNode::new_unchecked(RDF_TYPE);
    for graph in graphs {
        let g = NamedNode::new(graph.as_str()).map_err(|e| Error::Evaluation(e.to_string()))?;
        quads.extend(
            beliefs
                .engine()
                .quads_for_pattern(None, None, None, Some(g.as_ref().into()))
                .flatten(),
        );
        let kinds: Vec<String> = beliefs
            .rows(
                &bind(
                    KINDS_Q,
                    &[("cat", Value::iri(cat.as_str())), ("graph", Value::iri(graph))],
                )?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "k"))
            .collect();
        let mut beneath = Vec::new();
        for kind in &kinds {
            beneath.push(beliefs.closed(kind)?);
        }
        for (i, kind) in kinds.iter().enumerate() {
            let above_another = kinds
                .iter()
                .enumerate()
                .any(|(j, other)| j != i && other != kind && beneath[j].contains(kind));
            if !above_another {
                quads.push(Quad::new(
                    g.clone(),
                    rdf_type.clone(),
                    NamedNode::new_unchecked(kind.as_str()),
                    GraphName::DefaultGraph,
                ));
            }
        }
        let periods = beliefs.rows(
            &bind(
                PERIOD_Q,
                &[("cat", Value::iri(cat.as_str())), ("graph", Value::iri(graph))],
            )?,
            &[],
        )?;
        if let Some(row) = periods.first() {
            let p = BlankNode::default();
            quads.push(Quad::new(
                g.clone(),
                NamedNode::new_unchecked(TEMPORAL),
                p.clone(),
                GraphName::DefaultGraph,
            ));
            for (key, predicate) in [("start", START), ("end", END)] {
                if let Some(value) = row.get(key) {
                    quads.push(Quad::new(
                        p.clone(),
                        NamedNode::new_unchecked(predicate),
                        value.clone(),
                        GraphName::DefaultGraph,
                    ));
                }
            }
        }
    }
    Ok(Document::of_quads(quads))
}

/// Speech's part: the speaker, and the beliefs extracted at start for the pass to hand on.
pub struct Speech {
    pub speaker: Speaker,
    beliefs: Store,
    pending: Vec<String>,
}

impl Speech {
    pub fn new(beliefs: &Store, me: &str) -> Self {
        Speech {
            speaker: Speaker {
                beliefs: beliefs.clone(),
                me: me.to_string(),
                watch: Watch::default(),
            },
            beliefs: beliefs.clone(),
            pending: Vec::new(),
        }
    }
}

impl Speech {
    fn arrival(&self, graph: &str) -> Result<Option<String>, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(None);
        };
        Ok(self
            .beliefs
            .rows(
                &bind(ARRIVAL_Q, &[("cat", Value::iri(cat)), ("graph", Value::iri(graph))])?,
                &[],
            )?
            .first()
            .and_then(|r| iri(r, "arrival")))
    }
}

inventory::submit! { Package { name: "speech", start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    let mut part = Speech::new(&handed.store, &me);
    let mut hears = handed.events.hears();
    let arrived = handed.arrived();
    let mut timers = Vec::new();
    part.start(handed, &mut hears, &arrived, &mut timers)?;
    Ok(Some(Box::pin(task(handed.clone(), part, hears, arrived, timers))))
}

/// THE PACKAGE'S TASK: it decides as the run begins, then waits for what it hears, an arrival or the instant it is
/// next due; once nothing more waits to be heard it does what it queued for itself and what has fallen due.
async fn task(
    handed: Handed,
    mut part: Speech,
    mut hears: Hears,
    mut arrived: Arrived,
    mut timers: Vec<(Every, usize)>,
) -> Result<(), Error> {
    let mut heard = None;
    let mut due = None;
    loop {
        let mut turn = handed.turn();
        match heard.take() {
            Some(Woke::Event(tag, event)) => {
                let wrote = part.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            Some(Woke::Graphs(tag, graphs)) => {
                let wrote = part.heard(tag, &graphs, &mut turn);
                turn.done(wrote)?;
            }
            _ => {}
        }
        if hears.is_empty() {
            let wrote = part.queued(&mut turn);
            turn.done(wrote)?;
            for (every, tag) in &mut timers {
                if every.due(turn.now) {
                    let wrote = part.run(*tag, &mut turn);
                    turn.done(wrote)?;
                    let wrote = part.queued(&mut turn);
                    turn.done(wrote)?;
                }
            }
            due = timers
                .iter()
                .fold(turn.next(), |soonest, (every, _)| sooner(soonest, every.at()));
        }
        heard = tokio::select! {
            biased;
            _ = handed.stopped() => break,
            woke = hears.next() => match woke {
                Some(woke) => Some(woke),
                None => break,
            },
            _ = arrived.wait() => None,
            _ = handed.sleep_until(due) => None,
        };
    }
    Ok(())
}

impl Speech {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        loop {
            let jobs = self.submitted();
            if jobs.is_empty() {
                return Ok(Vec::new());
            }
            for job in jobs {
                let wrote = self.run(job, pass)?;
                pass.told(wrote)?;
            }
        }
    }

    fn start(
        &mut self,
        handed: &Handed,
        hears: &mut Hears,
        arrived: &Arrived,
        timers: &mut Vec<(Every, usize)>,
    ) -> Result<(), Error> {
        let _ = (&handed, &hears, &arrived, &timers);
        self.speaker.watch = handed.events.watch().clone();
        if let Some(cat) = self.beliefs.catalogue()? {
            let unextracted: Vec<String> = self
                .beliefs
                .rows(&bind(UNEXTRACTED_Q, &[("cat", Value::iri(cat))])?, &[])?
                .iter()
                .filter_map(|r| iri(r, "g"))
                .collect();
            for statement in unextracted {
                self.pending.extend(extract(&self.beliefs, &statement)?);
            }
        }
        hears.graph(STATEMENT_GRAPH, STATED);
        hears.event(SPEAKING_TRIGGER, SPEAK);
        Ok(())
    }

    fn run(&mut self, job: usize, _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            EXTRACTED => Ok(std::mem::take(&mut self.pending)),
            _ => Ok(Vec::new()),
        }
    }

    /// The statements written together, each said heard where it was received, and each extracted.
    fn heard(&mut self, _job: usize, graphs: &[String], pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let watch = self.speaker.watch.clone();
        let mut written = Vec::new();
        for graph in graphs {
            if watch.connected() && self.arrival(graph)?.as_deref() == Some(RECEIVED) {
                let (kinds, said) = described(&self.beliefs, graph)?;
                watch.emit(&Heard {
                    statement: graph.to_string(),
                    at: Some(pass.now),
                    kinds,
                    said,
                });
            }
            written.extend(extract(&self.beliefs, graph)?);
        }
        Ok(written)
    }

    /// What speech's policy does of a trigger: tell each statement it names, as it was said, to each agent it names.
    fn heard_event(&mut self, _job: usize, event: &HeardEvent, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let statements: Vec<NamedNode> = event.all(STATEMENT).into_iter().cloned().collect();
        let to: Vec<String> = event.all(TO).iter().map(|a| a.as_str().to_string()).collect();
        if statements.is_empty() || to.is_empty() {
            return Ok(Vec::new());
        }
        let graphs: Vec<String> = statements.iter().map(|s| s.as_str().to_string()).collect();
        let activity = pass.begin(SPEAKING, &statements);
        let told = self.speaker.tell_said(&graphs, &to);
        pass.end(activity);
        told?;
        Ok(Vec::new())
    }

    fn submitted(&mut self) -> Vec<usize> {
        if self.pending.is_empty() {
            Vec::new()
        } else {
            vec![EXTRACTED]
        }
    }
}

#[cfg(test)]
mod tests {
    //! Speech's part, held as `agent/speech/tests/test_create.py` holds it: it says a document as the agent said it,
    //! and tells each agent it is to through whoever reaches a peer.

    use super::*;
    use crate::said::tests::{T, me, quads, store};
    use std::sync::{Arc, Mutex};

    #[test]
    fn its_part_believes_what_was_said_and_says_it_said_to_each_agent() {
        let store = store();
        let part = Speech::new(&store, &me());
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.speaker.watch.connect(move |event, _| {
            into.lock().unwrap().push((event.kind(), event.about()));
        });
        let round = format!("{T}round");
        let to = [format!("{T}rose"), format!("{T}fern")];
        assert_eq!(
            part.speaker
                .say(&Document::of_quads(quads(&round, "open")), &to)
                .unwrap(),
            std::slice::from_ref(&round)
        );
        let node = |s: &str| oxigraph::model::Term::NamedNode(NamedNode::new(s).unwrap());
        assert_eq!(
            *heard.lock().unwrap(),
            [(
                Some(crate::ontology::SAID),
                vec![(STATEMENT, node(&round)), (TO, node(&to[0])), (TO, node(&to[1]))]
            )],
            "one telling, naming its statement and each agent it is to"
        );
    }
}
