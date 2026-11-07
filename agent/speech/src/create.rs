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
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::{Store, iri};

use crate::extract::extract;
use crate::ontology::STATEMENT_GRAPH;
use crate::said::said;

const STATED: usize = 0;
const EXTRACTED: usize = 1;

/// EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
const UNEXTRACTED_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { ?g a speech:StatementGraph FILTER NOT EXISTS { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g";

/// Whoever reaches a peer: the agent a document is for, and the document's bytes.
pub type Tells<'a> = Box<dyn FnMut(&str, &[u8]) -> Result<(), Error> + 'a>;

/// What says a document and tells it: shared by the part and whoever says through it.
pub struct Speaker<'a> {
    beliefs: &'a Store,
    pub me: String,
    pub tell: RefCell<Option<Tells<'a>>>,
}

impl Speaker<'_> {
    /// Believe `document` as the agent said it, and tell it to every agent it is `to`; the graphs believed.
    pub fn say(&self, document: &Document, to: &[String]) -> Result<Vec<String>, Error> {
        let written = said(self.beliefs, &self.me, document)?;
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
            }),
            beliefs,
            pending: Vec::new(),
        }
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

    fn heard(&mut self, _job: usize, graph: &str, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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
