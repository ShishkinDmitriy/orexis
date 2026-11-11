//! WHAT SPEECH SAYS HAPPENED, as `agent/speech/events.py` declares it: every STATEMENT is history, an event in the
//! journal in speech's words — `speech:Said`, a document the agent said, naming each of its graphs and every agent it
//! was told to (`speech:to`), and `speech:Heard`, each graph of a document a peer said to it. Each names its statements
//! (`speech:statement`) and carries what each said, its triples copied, and the kinds it says it is, so the journal
//! holds the exchange between two agents in the words they spoke it in, and this module spells none of them. A
//! `speech:Said` is heard too: whoever carries a document to an agent, or phrases it for a person, puts it beneath a
//! trigger of its own and reads the statements it names back from the store.

use oxigraph::model::{NamedNode, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::events::{Event, node, triple, typed};

use crate::ontology::{SAID, STATEMENT, TO};

pub const SPEECH: &str = "http://example.org/orexis/speech#";

/// A statement of a document: the graph, the kinds it says it is and what it says.
#[derive(Clone, Debug, PartialEq)]
pub struct Statement {
    pub graph: String,
    pub kinds: Vec<String>,
    pub said: Vec<Triple>,
}

/// A document the agent said at `at`: each of its statements, and the agents it was told to.
#[derive(Clone, Debug, PartialEq)]
pub struct Said {
    pub statements: Vec<Statement>,
    pub to: Vec<String>,
    pub at: Option<DateTime>,
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
        for s in &self.statements {
            out.extend(statement(entry, &s.graph, &s.kinds, &s.said));
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }

    fn kind(&self) -> Option<&'static str> {
        Some(SAID)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        let named = |p: &'static str, iri: &str| NamedNode::new(iri).ok().map(|n| (p, Term::NamedNode(n)));
        self.statements
            .iter()
            .filter_map(|s| named(STATEMENT, &s.graph))
            .chain(self.to.iter().filter_map(|a| named(TO, a)))
            .collect()
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
