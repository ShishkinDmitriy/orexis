//! THE TAKER, the seam between a step and the world: the action's implementation carried out order by order, each
//! command kept and said for a transport to send, each document said for speech to tell.

use std::sync::Arc;

use oxigraph::model::{GraphName, Literal, NamedNode, Quad};
use serde_json::Value as Json;

use orexis::Error;
use orexis::clock::Clock;
use orexis::document::Document;
use orexis::events::{Watch, mint};
use orexis::ontology::RECORDED;
use orexis::store::Store;

use crate::command::command;
use crate::events::{Commanded, Told};
use crate::executor::{Said, Take};
use crate::implementation::operations;
use crate::ontology::{ACTUATOR, COMMAND, COMMAND_GRAPH, PAYLOAD, SAYING};
use crate::says::says;

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// The taker of an agent that carries out its steps, as Python's `_take` takes a step: the action's implementation,
/// order by order, each command sized from the present at the clock's instant, kept and said `execution:Commanded` where
/// the agent `commands` — has a transport to send it — and each document it says kept by speech and said
/// `execution:Told` where the agent `says`, the statements kept returned, for the executor to hand on with what it wrote. A step whose action
/// carries no command or saying reaches nothing, `None`; a command that answers nothing is a step NOT taken (#869), since the present held
/// nothing it sizes from and recording it taken would have the intention wait out its patience as though the device
/// had run.
pub fn taker(beliefs: Store, me: &str, clock: Arc<dyn Clock>, watch: Watch, commands: bool, says_to: bool) -> Take {
    let me = me.to_string();
    Box::new(move |said: &Said, _intention: &str| {
        let beliefs = &beliefs;
        let action = said.get("fills").cloned().unwrap_or_default();
        let ops = operations(beliefs, &action)?;
        let mut orders: Vec<f64> = ops
            .iter()
            .filter(|op| op.kind == COMMAND || op.kind == SAYING)
            .map(|op| op.order)
            .collect();
        orders.sort_by(f64::total_cmp);
        orders.dedup();
        if orders.is_empty() {
            return Ok(None);
        }
        let mut kept = Vec::new();
        let now = clock.now();
        for order in orders {
            let sent = command(beliefs, said, Some(order), now)?;
            if sent.is_empty() && ops.iter().any(|op| op.kind == COMMAND && op.order == order) {
                return Err(Error::Evaluation(format!(
                    "{}'s command answered nothing in the present",
                    orexis::ontology::local_of(&action)
                )));
            }
            if commands && !sent.is_empty() {
                let graph = commanded(beliefs, &me, &sent)?;
                watch.emit(&Commanded { commands: graph });
            }
            if says_to {
                for (agents, document) in says(beliefs, said, Some(order), now)? {
                    let statements = orexis_speech::said::said(beliefs, &me, &document)?;
                    watch.emit(&Told {
                        statements: statements.clone(),
                        to: agents,
                    });
                    kept.extend(statements);
                }
            }
        }
        Ok(Some(kept))
    })
}

/// THE COMMANDS ONE ORDER OF A STEP SENDS, kept as the agent's own act before any transport sends them: an
/// `execution:CommandGraph` of one node per command, its actuator and its payload; the graph's name.
pub fn commanded(store: &Store, me: &str, sent: &[(String, Json)]) -> Result<String, Error> {
    let tail = |n: &NamedNode| {
        n.as_str()
            .rsplit(['/', ':', '#'])
            .next()
            .unwrap_or_default()
            .to_string()
    };
    let local = me.rsplit(['/', '#']).next().unwrap_or(me);
    let graph = NamedNode::new(format!(
        "http://example.org/orexis/graph/command/{local}/{}",
        tail(&mint())
    ))
    .map_err(|e| Error::Evaluation(e.to_string()))?;
    let into = GraphName::NamedNode(graph.clone());
    let mut quads = vec![Quad::new(
        graph.clone(),
        NamedNode::new_unchecked(RDF_TYPE),
        NamedNode::new_unchecked(COMMAND_GRAPH),
        GraphName::DefaultGraph,
    )];
    for (actuator, payload) in sent {
        let node = NamedNode::new_unchecked(format!("{}#{}", graph.as_str(), tail(&mint())));
        let actuator = NamedNode::new(actuator.as_str()).map_err(|e| Error::Evaluation(e.to_string()))?;
        quads.push(Quad::new(
            node.clone(),
            NamedNode::new_unchecked(ACTUATOR),
            actuator,
            into.clone(),
        ));
        quads.push(Quad::new(
            node,
            NamedNode::new_unchecked(PAYLOAD),
            Literal::new_simple_literal(payload.to_string()),
            into.clone(),
        ));
    }
    store.put_document(&Document::of_quads(quads), Some(me), None, Some(RECORDED), true)?;
    Ok(graph.as_str().to_string())
}
