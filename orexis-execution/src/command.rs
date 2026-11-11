//! WHAT TAKING A STEP SENDS, sized from the present, as `agent/execution/command.py` sizes it.
//!
//! An action a device takes has an `execution:Command` among its operations, an `sh:select` over the beliefs as
//! they stand when the step is taken, with the step's parameters as `$tokens` and `$now`, answering `?actuator` and
//! `?payload`. The search never sizes an act, so how much to pour or how long to heat is decided here, from the
//! reading in hand, by the text the domain declares — whose `GRAPH` clauses reach the kind sensing keeps a reading in,
//! a word this package names none of. The answer is what the container hands the transport; execution names no
//! transport, and a step whose action carries no command sends nothing.

use oxsdatatypes::DateTime;
use serde_json::Value as Json;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF, RECORD, local_of};
use orexis::store::{Store, Within, instant, iri, value};

use crate::Said;
use crate::implementation::operations;
use crate::ontology::COMMAND;

const TAKES_Q: &str = "SELECT ?takes WHERE { $action orexis:takes ?takes }";

/// A step's parameter as the term it is: an IRI wrapped, anything else — a number's lexical form — as written.
fn term(text: &str) -> Value {
    let iri = ["http://", "https://", "urn:", "mailto:", "file:"]
        .iter()
        .any(|s| text.starts_with(s))
        && !text.chars().any(char::is_whitespace);
    if iri { Value::iri(text) } else { Value::raw(text) }
}

/// The `$tokens` a step's operation takes: `$now`, and each parameter its action takes that the step's rows hold.
pub fn tokens(store: &Store, said: &Said, action: &str, now: DateTime) -> Result<Vec<(String, Value)>, Error> {
    let actions = store.graphs_of(&[ACTION], &Within::default())?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let mut out = vec![("now".to_string(), instant(now))];
    for row in store.rows(&bind(TAKES_Q, &[("action", Value::iri(action))])?, &actions)? {
        let Some(takes) = iri(&row, "takes") else { continue };
        let local = local_of(&takes);
        if let Some(given) = said.get(&local) {
            out.push((local, term(given)));
        }
    }
    Ok(out)
}

/// Every `(actuator, payload)` the step `said` sends — its rows keyed by local part — asked over the beliefs holding
/// at `now`: every command of the action's implementation, or those of one `order`. Empty where it has none or its
/// texts answer nothing; a payload that is no JSON is refused in the log.
pub fn command(store: &Store, said: &Said, order: Option<f64>, now: DateTime) -> Result<Vec<(String, Json)>, Error> {
    let Some(action) = said.get("fills") else {
        return Ok(Vec::new());
    };
    let texts: Vec<String> = operations(store, action)?
        .into_iter()
        .filter(|op| op.kind == COMMAND && order.is_none_or(|o| op.order == o))
        .filter_map(|op| op.text)
        .collect();
    if texts.is_empty() {
        return Ok(Vec::new());
    }
    let tokens = tokens(store, said, action, now)?;
    let tokens: Vec<(&str, Value)> = tokens.iter().map(|(k, v)| (k.as_str(), v.clone())).collect();
    let known = store.graphs_of(
        &[BELIEF, RECORD],
        &Within {
            at: Some(now),
            now: Some(now),
            ..Within::default()
        },
    )?;
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    let mut out = Vec::new();
    for text in texts {
        for row in store.rows(&bind(&text, &tokens)?, &known)? {
            let actuator = iri(&row, "actuator");
            let payload = value(&row, "payload").map(|p| serde_json::from_str::<Json>(&p));
            match (actuator, payload) {
                (Some(actuator), Some(Ok(payload))) => out.push((actuator, payload)),
                (_, Some(Err(e))) => log::error!("{}: its command answered no JSON payload: {e}", local_of(action)),
                _ => log::error!("{}: its command answered no actuator and payload", local_of(action)),
            }
        }
    }
    Ok(out)
}
