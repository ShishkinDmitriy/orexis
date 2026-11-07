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
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::{Store, iri};
use oxigraph::model::{NamedNode, Triple};

use crate::events::{Heard, Said};

use crate::extract::extract;
use crate::ontology::STATEMENT_GRAPH;
use crate::said::said;

const STATED: usize = 0;
const EXTRACTED: usize = 1;

/// EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
const UNEXTRACTED_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { ?g a speech:StatementGraph FILTER NOT EXISTS { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g";

/// HOW A STATEMENT ARRIVED, and THE KINDS IT SAYS IT IS: what is said of it.
const ARRIVAL_Q: &str = "SELECT ?arrival WHERE { GRAPH $cat { $graph orexis:arrivedBy ?arrival } }";
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
    beliefs: &'a Store,
    pub me: String,
    pub tell: RefCell<Option<Tells<'a>>>,
    /// Whoever watches the agent, and the instant the pass stands at.
    pub watch: RefCell<Watch>,
}

impl Speaker<'_> {
    /// Believe `document` as the agent said it, and tell it to every agent it is `to`; the graphs believed.
    pub fn say(&self, document: &Document, to: &[String]) -> Result<Vec<String>, Error> {
        let written = said(self.beliefs, &self.me, document)?;
        let watch = self.watch.borrow().clone();
        if watch.connected() {
            for graph in &written {
                let (kinds, said) = described(self.beliefs, graph)?;
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
        Ok(written)
    }
}

/// Speech's part: the speaker, and the beliefs extracted at start for the pass to hand on.
pub struct Speech<'a> {
    pub speaker: Rc<Speaker<'a>>,
    beliefs: &'a Store,
    pending: Vec<String>,
}

impl<'a> Speech<'a> {
    pub fn new(beliefs: &'a Store, me: &str) -> Self {
        Speech {
            speaker: Rc::new(Speaker {
                beliefs,
                me: me.to_string(),
                tell: RefCell::new(None),
                watch: RefCell::new(Watch::default()),
            }),
            beliefs,
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
                self.pending.extend(extract(self.beliefs, &statement)?);
            }
        }
        starting.on(STATEMENT_GRAPH, STATED);
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
            let (kinds, said) = described(self.beliefs, graph)?;
            watch.emit(&Heard {
                statement: graph.to_string(),
                at: Some(pass.now),
                kinds,
                said,
            });
        }
        extract(self.beliefs, graph)
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
