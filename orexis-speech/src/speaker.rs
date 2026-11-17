//! THE SPEAKER, the package's core: the role the self plays, read off its self graph, and what it does of a statement
//! written and of a step that says something - extract what it believes of each, and say each to whom it is said.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::RECEIVED;
use orexis::store::{Store, iri};
use orexis::task::{Heard as HeardEvent, Turn};
use oxigraph::model::NamedNode;

use crate::events::{Heard, Said, Statement};
use crate::extract::extract;
use crate::ontology::{SPEAKING, STATEMENT, TO};
use crate::said::said;
use crate::statements::described;

pub(crate) const STATED: usize = 0;
const EXTRACTED: usize = 1;
pub(crate) const SPEAK: usize = 2;

/// THE SPEAKER THE SELF PLAYS, the package's core: who says, whoever watches it say, and the beliefs extracted as it
/// started for the first turn to hand on. `speech:Speaker` states no figure.
pub struct Speaker {
    beliefs: Store,
    pub me: String,
    /// Whoever watches the agent, and the instant the pass stands at.
    pub watch: Watch,
    pending: Vec<String>,
}

impl Speaker {
    /// The speaker the self plays, read off the store.
    pub fn new(store: &Store) -> Result<Self, Error> {
        Ok(Speaker {
            beliefs: store.clone(),
            me: orexis::boot::selves(store)?.into_iter().next().unwrap_or_default(),
            watch: Watch::default(),
            pending: Vec::new(),
        })
    }

    /// What a restart finds unextracted: every statement nothing was extracted from, extracted now and handed on at
    /// the first turn.
    pub(crate) fn unextracted(&mut self) -> Result<(), Error> {
        /// EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
        const UNEXTRACTED_Q: &str = "PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX speech: <http://example.org/orexis/speech#>
        SELECT ?g WHERE { GRAPH $cat { ?g a speech:StatementGraph FILTER NOT EXISTS { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g";
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
        Ok(())
    }

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

    fn arrival(&self, graph: &str) -> Result<Option<String>, Error> {
        /// HOW A STATEMENT ARRIVED, and THE KINDS IT SAYS IT IS: what is said of it.
        const ARRIVAL_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
            SELECT ?arrival WHERE { GRAPH $cat { $graph orexis:arrivedBy ?arrival } }";
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

    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    pub(crate) fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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

    pub(crate) fn run(&mut self, job: usize, _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            EXTRACTED => Ok(std::mem::take(&mut self.pending)),
            _ => Ok(Vec::new()),
        }
    }

    /// The statements written together, each said heard where it was received, and each extracted.
    pub(crate) fn heard(&mut self, _job: usize, graphs: &[String], pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let watch = self.watch.clone();
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
    pub(crate) fn heard_event(
        &mut self,
        _job: usize,
        event: &HeardEvent,
        pass: &mut Turn<'_>,
    ) -> Result<Vec<String>, Error> {
        let statements: Vec<NamedNode> = event.all(STATEMENT).into_iter().cloned().collect();
        let to: Vec<String> = event.all(TO).iter().map(|a| a.as_str().to_string()).collect();
        if statements.is_empty() || to.is_empty() {
            return Ok(Vec::new());
        }
        let graphs: Vec<String> = statements.iter().map(|s| s.as_str().to_string()).collect();
        let activity = pass.begin(SPEAKING, &statements);
        let told = self.tell_said(&graphs, &to);
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
    use crate::ontology::{STATEMENT, TO};
    use crate::said::tests::{T, me, quads, store};
    use oxigraph::model::NamedNode;
    use std::sync::{Arc, Mutex};

    #[test]
    fn its_part_believes_what_was_said_and_says_it_said_to_each_agent() {
        let store = store();
        let mut part = Speaker::new(&store).unwrap();
        part.me = me();
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.watch.connect(move |event, _| {
            into.lock().unwrap().push((event.kind(), event.about()));
        });
        let round = format!("{T}round");
        let to = [format!("{T}rose"), format!("{T}fern")];
        assert_eq!(
            part.say(&Document::of_quads(quads(&round, "open")), &to).unwrap(),
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
