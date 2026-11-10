//! SPEECH'S PART, as `agent/speech/create.py` makes it (a-package-starts-itself): it says what a step said, as the
//! agent said it (`said`), and tells each agent it is to through whoever is linked to reach a peer — a transport. What
//! a peer says to it, `heard` keeps, called by the transport. STARTED, IT EXTRACTS WHAT IS BELIEVED OF EVERY STATEMENT
//! WRITTEN (#958): it hears its own kind, heard or said alike, and `extract` writes what the extractions conclude of
//! it into a belief graph, which the runtime then hands whoever revises beliefs. A statement written before the part
//! started — a volume lived in — is extracted from at start where nothing was.

use std::cell::RefCell;
use std::rc::Rc;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::RECEIVED;
use orexis::runtime::{Heard as HeardEvent, Part, Pass, Starting};
use orexis::store::{Store, iri};
use oxigraph::model::{BlankNode, GraphName, NamedNode, Quad, Triple};

use crate::events::{Heard, Said};

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

/// Whoever reaches a peer: the agent a document is for, and the document's bytes.
pub type Tells<'a> = Box<dyn FnMut(&str, &[u8]) -> Result<(), Error> + 'a>;

/// What says a document and tells it: shared by the part and whoever says through it.
pub struct Speaker<'a> {
    beliefs: Store,
    pub me: String,
    pub tell: RefCell<Option<Tells<'a>>>,
    /// Whoever watches the agent, and the instant the pass stands at.
    pub watch: RefCell<Watch>,
}

impl Speaker<'_> {
    /// Believe `document` as the agent said it, and tell it to every agent it is `to`; the graphs believed.
    pub fn say(&self, document: &Document, to: &[String]) -> Result<Vec<String>, Error> {
        let written = said(&self.beliefs, &self.me, document)?;
        self.tell_said(document, &written, to)?;
        Ok(written)
    }

    /// Say that the statements `written` were said to `to`, and tell `document` to each.
    fn tell_said(&self, document: &Document, written: &[String], to: &[String]) -> Result<(), Error> {
        let watch = self.watch.borrow().clone();
        if watch.connected() {
            for graph in written {
                let (kinds, said) = described(&self.beliefs, graph)?;
                watch.emit(&Said {
                    statement: graph.clone(),
                    to: to.to_vec(),
                    at: watch.at(),
                    kinds,
                    said,
                });
            }
        }
        if let Some(tell) = self.tell.borrow_mut().as_mut() {
            let payload = document.trig()?;
            for agent in to {
                tell(agent, &payload)?;
            }
        }
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
pub struct Speech<'a> {
    pub speaker: Rc<Speaker<'a>>,
    beliefs: Store,
    pending: Vec<String>,
}

impl<'a> Speech<'a> {
    pub fn new(beliefs: &'a Store, me: &str) -> Self {
        Speech {
            speaker: Rc::new(Speaker {
                beliefs: beliefs.clone(),
                me: me.to_string(),
                tell: RefCell::new(None),
                watch: RefCell::new(Watch::default()),
            }),
            beliefs: beliefs.clone(),
            pending: Vec::new(),
        }
    }
}

impl Speech<'_> {
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

impl Part for Speech<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
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
        starting.on(STATEMENT_GRAPH, STATED);
        starting.hears(SPEAKING_TRIGGER, SPEAK);
        Ok(())
    }

    fn run(&mut self, job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        match job {
            EXTRACTED => Ok(std::mem::take(&mut self.pending)),
            _ => Ok(Vec::new()),
        }
    }

    fn heard(&mut self, _job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let watch = self.speaker.watch.borrow().clone();
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

    fn watch(&self) -> Option<Watch> {
        Some(self.speaker.watch.borrow().clone())
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
        let told = document_of(&self.beliefs, &graphs).and_then(|d| self.speaker.tell_said(&d, &graphs, &to));
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

    #[test]
    fn its_part_believes_what_was_said_and_tells_each_agent() {
        let store = store();
        let part = Speech::new(&store, &me());
        let told = Rc::new(RefCell::new(Vec::new()));
        let into = told.clone();
        *part.speaker.tell.borrow_mut() = Some(Box::new(move |to, _| {
            into.borrow_mut().push(to.to_string());
            Ok(())
        }));
        let round = format!("{T}round");
        let to = [format!("{T}rose"), format!("{T}fern")];
        assert_eq!(
            part.speaker
                .say(&Document::of_quads(quads(&round, "open")), &to)
                .unwrap(),
            [round]
        );
        assert_eq!(*told.borrow(), to);
    }
}
