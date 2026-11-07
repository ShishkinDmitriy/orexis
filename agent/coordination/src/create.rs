//! COORDINATION'S PART, as `agent/coordination/create.py` makes it (a-package-starts-itself). LINKED, it holds
//! whoever says what it asks and answers — speech — and whoever plans — the Planner, to reopen the walking wants a draw
//! it has won decides. STARTED, it mints the agent's secret where it holds none; answers every question heard as it
//! arrives; concludes its conflicts and lays what it yields to as each question or answer arrives; and every pass asks
//! the peers in range, concludes and lays again — after planning and execution, so what it says of its future is what
//! the pass left walking. A draw the agent concludes it has WON reopens the walking wants whose plans change a value
//! on the key of the constraint the draw was over, since nothing a belief makes impossible reopens a plan that has
//! only been made slower than it need be.
//!
//! NOT PORTED: the events it signals (`held`, `concluded`), which wait for the journal.

use std::collections::BTreeSet;

use orexis::Error;
use orexis::document::Document;
use orexis::ontology::local_of;
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::Store;

use crate::answer::answer;
use crate::ask::ask;
use crate::conclude::{conclude, wins};
use crate::holdings::walking_over;
use crate::lay::lay;
use crate::mint::mint;
use crate::ontology::{ANSWER_GRAPH, QUESTION_GRAPH};

const PASS: usize = 0;
const QUESTIONED: usize = 1;
const ANSWERED: usize = 2;
const MINTED: usize = 3;

/// Whoever says a document to a peer: the peer and the document; the graphs believed of it.
pub type Says<'a> = Box<dyn FnMut(&str, &Document) -> Result<Vec<String>, Error> + 'a>;

/// Whoever plans: the wants to reopen.
pub type Reopens<'a> = Box<dyn FnMut(BTreeSet<String>) + 'a>;

/// Coordination's part.
pub struct Coordination<'a> {
    beliefs: &'a Store,
    me: String,
    pub say: Option<Says<'a>>,
    pub reopen: Option<Reopens<'a>>,
    pending: Vec<String>,
}

impl<'a> Coordination<'a> {
    pub fn new(beliefs: &'a Store, me: &str) -> Self {
        Coordination {
            beliefs,
            me: me.to_string(),
            say: None,
            reopen: None,
            pending: Vec::new(),
        }
    }

    fn said(&mut self, peer: &str, document: &Document) -> Result<Vec<String>, Error> {
        let Some(say) = self.say.as_mut() else {
            return Ok(Vec::new());
        };
        let graphs: Vec<String> = document.kinds().into_keys().collect();
        log::info!(
            "{}: says {} to {}",
            local_of(&self.me),
            graphs
                .iter()
                .map(|g| g.split("/coordination/").last().unwrap_or(g))
                .collect::<Vec<_>>()
                .join(", "),
            local_of(peer)
        );
        say(peer, document)
    }

    /// Conclude the conflicts and lay what the agent yields to; a draw won reopens what it decides.
    fn yielded(&mut self, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let (store, me, at) = (self.beliefs, self.me.clone(), pass.now);
        let before = wins(store, &me)?;
        let mut written = conclude(store, &me, at)?;
        let won: Vec<String> = wins(store, &me)?
            .into_iter()
            .filter(|(draw, _)| !before.contains_key(draw))
            .map(|(_, constraint)| constraint)
            .collect();
        written.extend(lay(store, &me, at)?);
        let mut wants = BTreeSet::new();
        for constraint in &won {
            wants.extend(walking_over(store, constraint)?);
        }
        if !wants.is_empty()
            && let Some(reopen) = self.reopen.as_mut()
        {
            log::info!(
                "{}: won a draw, so asks that {} be planned again",
                local_of(&me),
                wants.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
            );
            reopen(wants);
            pass.again();
        }
        Ok(written)
    }
}

impl Part for Coordination<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        self.pending.extend(mint(self.beliefs, &self.me)?);
        starting.on(QUESTION_GRAPH, QUESTIONED);
        starting.on(ANSWER_GRAPH, ANSWERED);
        starting.every(0.0, PASS);
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        match job {
            MINTED => Ok(std::mem::take(&mut self.pending)),
            PASS => {
                let mut written = Vec::new();
                for (peer, document) in ask(self.beliefs, &self.me, pass.now)? {
                    written.extend(self.said(&peer, &document)?);
                }
                written.extend(self.yielded(pass)?);
                Ok(written)
            }
            _ => Ok(Vec::new()),
        }
    }

    fn heard(&mut self, job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        if job == QUESTIONED
            && let Some((peer, document)) = answer(self.beliefs, &self.me, graph, pass.now)?
        {
            written.extend(self.said(&peer, &document)?);
        }
        written.extend(self.yielded(pass)?);
        Ok(written)
    }

    fn submitted(&mut self) -> Vec<usize> {
        if self.pending.is_empty() {
            Vec::new()
        } else {
            vec![MINTED]
        }
    }
}
