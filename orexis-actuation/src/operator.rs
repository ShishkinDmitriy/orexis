//! THE OPERATOR, the package's core: the agent's members, and what it does of a step's commands — each sent to its
//! actuator through the member that reaches it.

use oxigraph::model::{NamedNode, Term};

use orexis::Error;
use orexis::ontology::local_of;
use orexis::store::Store;
use orexis::task::{Heard, Turn};
use orexis_transport::{Exchange, Members};

/// What the operator does as an activity.
const ACTUATING: &str = "http://example.org/orexis/actuation#Actuating";
/// What a step's commands are kept as, in execution's words, which the operator reads.
const COMMANDS: &str = "http://example.org/orexis/execution#commands";
const ACTUATOR: &str = "http://example.org/orexis/execution#actuator";
const PAYLOAD: &str = "http://example.org/orexis/execution#payload";

/// THE OPERATOR THE SELF PLAYS: the agent's beliefs, where a step's commands are kept, and its members.
pub struct Operator {
    beliefs: Store,
    members: Members,
}

impl Operator {
    pub fn new(store: &Store, members: Members) -> Self {
        Operator {
            beliefs: store.clone(),
            members,
        }
    }

    /// What the operator's policy does of its trigger: each command of the order the event names sent to its actuator
    /// through the member that reaches it as a channel it is sent on; one no member reaches passed over, in the log.
    pub fn heard_event(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let Some(graph) = event.named(COMMANDS).cloned() else {
            return Ok(Vec::new());
        };
        let commands = commands_of(&self.beliefs, graph.as_str())?;
        let activity = pass.begin(ACTUATING, std::slice::from_ref(&graph));
        let sent = commands
            .iter()
            .try_for_each(|(actuator, payload)| match self.members.reaching(actuator)? {
                Some((member, Exchange::Sent)) => member.send(actuator, payload.as_bytes(), None),
                _ => {
                    log::warn!(
                        "{}: no member of the agent's reaches it, so its command is not sent",
                        local_of(actuator)
                    );
                    Ok(())
                }
            });
        pass.end(activity);
        sent?;
        Ok(Vec::new())
    }
}

/// The commands a command graph keeps, in the order kept: each actuator and the document it is sent.
fn commands_of(store: &Store, graph: &str) -> Result<Vec<(String, String)>, Error> {
    let g = NamedNode::new(graph).map_err(|e| Error::Evaluation(e.to_string()))?;
    let engine = store.engine();
    let mut out = Vec::new();
    for q in engine
        .quads_for_pattern(
            None,
            Some(NamedNode::new_unchecked(ACTUATOR).as_ref()),
            None,
            Some(g.as_ref().into()),
        )
        .flatten()
    {
        let Term::NamedNode(actuator) = q.object else {
            continue;
        };
        let payload = engine
            .quads_for_pattern(
                Some(q.subject.as_ref()),
                Some(NamedNode::new_unchecked(PAYLOAD).as_ref()),
                None,
                Some(g.as_ref().into()),
            )
            .flatten()
            .find_map(|p| match p.object {
                Term::Literal(l) => Some(l.value().to_string()),
                _ => None,
            });
        if let Some(payload) = payload {
            out.push((actuator.as_str().to_string(), payload));
        }
    }
    Ok(out)
}
