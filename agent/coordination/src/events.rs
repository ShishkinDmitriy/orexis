//! WHAT COORDINATION SAYS HAPPENED, as `agent/coordination/events.py` declares it: nothing another part acts on, so
//! each event is made only where somebody watches the agent. THREE THINGS ARE HISTORY, each said whole at the instant
//! the part did it: the HOLDINGS it asked with, its own (`asked`); the holdings it LAID of a peer, as the peer said them
//! (`said`) or as it foresaw them of a silent peer (`foreseen`); and its CONFLICTS. Each is a SET, replacing the one
//! before, and an event in the journal in coordination's own words: `coordination:Asked`, `coordination:Said` or
//! `coordination:Foreseen`, each with the peer, the constraint and each holding — the thing it is of, its values on
//! the constraint's key under their own predicates, from, until, taken; and `coordination:Concluded`, with each
//! conflict as the agent concluded it, under the conflict's own name. Every name is read off what was said.

use oxigraph::model::{NamedNode, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::events::{Event, RDF_TYPE, boolean, instant, integer, mint, node, triple, typed};

use crate::holdings::Holding;
use crate::ontology::{COORDINATION, DRAW_WON, REOPENS};

pub const ASKED: &str = "asked";
pub const SAID: &str = "said";
pub const FORESEEN: &str = "foreseen";

fn term(name: &str) -> String {
    format!("{COORDINATION}{name}")
}

/// The holdings of one `origin` — `asked`, `said` or `foreseen` — under `constraint` with `peer`, as the part said or
/// laid them at `at`: all of them, replacing those said before.
#[derive(Clone, Debug, PartialEq)]
pub struct Held {
    pub at: DateTime,
    pub origin: &'static str,
    pub peer: String,
    pub constraint: String,
    pub holdings: Vec<Holding>,
}

impl Event for Held {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let kind = match self.origin {
            ASKED => "Asked",
            SAID => "Said",
            _ => "Foreseen",
        };
        let mut out = vec![
            typed(entry.clone(), &term(kind)),
            triple(entry.clone(), &term("peer"), node(&self.peer)),
            triple(entry.clone(), &term("over"), node(&self.constraint)),
        ];
        for h in &self.holdings {
            let held = mint();
            out.push(triple(entry.clone(), &term("holding"), held.clone()));
            out.push(typed(held.clone(), &term("Holding")));
            out.push(triple(held.clone(), &term("of"), node(&h.thing)));
            out.push(triple(held.clone(), &term("taken"), boolean(h.taken)));
            //  WHAT THE THING IS stays the thing's: a key's type is said of it, and the holding holds the rest.
            for (p, v) in &h.values {
                if p == RDF_TYPE {
                    out.push(Triple::new(node(&h.thing), node(RDF_TYPE), v.clone()));
                } else {
                    out.push(Triple::new(held.clone(), node(p), v.clone()));
                }
            }
            if let Some(start) = h.start {
                out.push(triple(held.clone(), &term("from"), instant(start)));
            }
            if let Some(end) = h.end {
                out.push(triple(held.clone(), &term("until"), instant(end)));
            }
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// One conflict as the agent concluded it: with `peer` over `constraint`, whether it stands, whether the peer is
/// silent, the round its draw is in and who won that draw, where anybody has; named as both agents name it.
#[derive(Clone, Debug, PartialEq)]
pub struct Conflict {
    pub conflict: String,
    pub peer: String,
    pub constraint: String,
    pub standing: bool,
    pub silent: bool,
    pub round: i64,
    pub won_by: Option<String>,
}

/// Every conflict the agent holds, as it concluded them at `at`: all of them, replacing those said before.
#[derive(Clone, Debug, PartialEq)]
pub struct Concluded {
    pub at: DateTime,
    pub conflicts: Vec<Conflict>,
}

impl Event for Concluded {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![typed(entry.clone(), &term("Concluded"))];
        for c in &self.conflicts {
            let conflict = node(&c.conflict);
            out.extend([
                triple(entry.clone(), &term("conflict"), conflict.clone()),
                typed(conflict.clone(), &term("Conflict")),
                triple(conflict.clone(), &term("with"), node(&c.peer)),
                triple(conflict.clone(), &term("over"), node(&c.constraint)),
                triple(conflict.clone(), &term("standing"), boolean(c.standing)),
                triple(conflict.clone(), &term("silent"), boolean(c.silent)),
                triple(conflict.clone(), &term("round"), integer(c.round)),
            ]);
            if let Some(winner) = &c.won_by {
                out.push(triple(conflict.clone(), &term("wonBy"), Term::from(node(winner))));
            }
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }
}

/// A draw the agent concluded it has won: said to planning, beneath its planning trigger by coordination's ontology and
/// in planning's words, as the walking wants to plan again (`planning:reopens`) - its walking plan yielded while the
/// draw stood undecided, and winning makes no world of it impossible, only slower.
#[derive(Clone, Debug, PartialEq)]
pub struct DrawWon {
    pub wants: Vec<String>,
}

impl Event for DrawWon {
    fn kind(&self) -> Option<&'static str> {
        Some(DRAW_WON)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        self.wants
            .iter()
            .filter_map(|w| NamedNode::new(w.as_str()).ok())
            .map(|w| (REOPENS, Term::NamedNode(w)))
            .collect()
    }
}
