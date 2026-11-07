//! WHAT SPEECH SAYS HAPPENED, as `agent/speech/events.py` declares it: every STATEMENT is history, an event in the
//! journal in speech's words — `speech:Said`, each graph of a document the agent said, with every agent it was told
//! to (`speech:to`), and `speech:Heard`, each graph of a document a peer said to it. Each names the statement
//! (`speech:statement`) and carries what it said, its triples copied, and the kinds it says it is, so the journal
//! holds the exchange between two agents in the words they spoke it in, and this module spells none of them.

use oxigraph::model::{NamedNode, Triple};
use oxsdatatypes::DateTime;

use orexis::events::{Event, node, triple, typed};

pub const SPEECH: &str = "http://example.org/orexis/speech#";

/// A statement the agent said at `at`: the graph, the agents it was told to, the kinds it says it is, what it says.
#[derive(Clone, Debug, PartialEq)]
pub struct Said {
    pub statement: String,
    pub to: Vec<String>,
    pub at: Option<DateTime>,
    pub kinds: Vec<String>,
    pub said: Vec<Triple>,
}

/// A statement a peer said to the agent, heard at `at`: the graph, the kinds it says it is and what it says.
#[derive(Clone, Debug, PartialEq)]
pub struct Heard {
    pub statement: String,
    pub at: Option<DateTime>,
    pub kinds: Vec<String>,
    pub said: Vec<Triple>,
}

fn statement(entry: &NamedNode, graph: &str, kinds: &[String], said: &[Triple]) -> Vec<Triple> {
    let mut out = vec![triple(entry.clone(), &format!("{SPEECH}statement"), node(graph))];
    out.extend(kinds.iter().map(|k| typed(node(graph), k)));
    out.extend(said.iter().cloned());
    out
}

impl Event for Said {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![typed(entry.clone(), &format!("{SPEECH}Said"))];
        out.extend(
            self.to
                .iter()
                .map(|a| triple(entry.clone(), &format!("{SPEECH}to"), node(a))),
        );
        out.extend(statement(entry, &self.statement, &self.kinds, &self.said));
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }
}

impl Event for Heard {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![typed(entry.clone(), &format!("{SPEECH}Heard"))];
        out.extend(statement(entry, &self.statement, &self.kinds, &self.said));
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }
}
