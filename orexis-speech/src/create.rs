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
use orexis::runtime::{Heard as HeardEvent, Pass, Runtime, Wait, Woke};
use orexis::store::{Store, iri};
use oxigraph::model::{BlankNode, GraphName, NamedNode, Quad, Triple};
use std::sync::{Arc, Mutex};

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

/// THE PACKAGE STARTING ITSELF on a runtime: it says what ends its wait and spawns its task. The part is lent, so
/// whoever keeps it reads it between runs.
pub fn start(runtime: &mut Runtime, part: &Arc<Mutex<Speech>>) -> Result<(), Error> {
    let part = part.clone();
    let mut wait = runtime.wait("speech");
    part.lock().expect("a part nobody poisoned").start(&mut wait)?;
    runtime.spawn(wait, move |wait| policy(part, wait));
    Ok(())
}

/// SPEECH'S TASK: it waits for a statement written, an event beneath its trigger, or what it extracted at its start,
/// and does what its policy says of each.
async fn policy(part: Arc<Mutex<Speech>>, mut wait: Wait) {
    while let Some((woke, mut pass)) = wait.next().await {
        let mut speech = part.lock().expect("a part nobody poisoned");
        let wrote = match woke {
            Woke::Due(tag) => speech.run(tag, &mut pass),
            Woke::Graph(tag, graph) => speech.heard(tag, &graph, &mut pass),
            Woke::Event(tag, event) => speech.heard_event(tag, &event, &mut pass),
            Woke::Arrived => speech.queued(&mut pass),
        };
        pass.done(wrote);
    }
}

impl Speech {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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

    fn start(&mut self, wait: &mut Wait) -> Result<(), Error> {
        self.speaker.watch = wait.watch();
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
        wait.on(STATEMENT_GRAPH, STATED);
        wait.hears(SPEAKING_TRIGGER, SPEAK);
        Ok(())
    }

    fn run(&mut self, job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        match job {
            EXTRACTED => Ok(std::mem::take(&mut self.pending)),
            _ => Ok(Vec::new()),
        }
    }

    fn heard(&mut self, _job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let watch = self.speaker.watch.clone();
        if watch.connected() && self.arrival(graph)?.as_deref() == Some(RECEIVED) {
            let (kinds, said) = described(&self.beliefs, graph)?;
            watch.emit(&Heard {
                statement: graph.to_string(),
                at: Some(pass.now),
                kinds,
                said,
            });
        }
        extract(&self.beliefs, graph)
    }

    /// What speech's policy does of a trigger: tell each statement it names, as it was said, to each agent it names.
    fn heard_event(&mut self, _job: usize, event: &HeardEvent, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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
