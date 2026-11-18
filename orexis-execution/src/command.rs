//! WHAT TAKING A STEP SENDS, sized from the present, as `agent/execution/command.py` sizes it.
//!
//! An action a device takes has an `execution:Command` among its operations, an `sh:select` over the beliefs as
//! they stand when the step is taken, with the step's parameters as `$tokens` and `$now`, answering `?actuator`,
//! `?property` and `?value`, a row per property a device is set. The search never sizes an act, so how much to pour or how long to heat is decided here, from the
//! reading in hand, by the text the domain declares — whose `GRAPH` clauses reach the kind sensing keeps a reading in,
//! a word this package names none of. What a device is sent of its rows is actuation's to make; execution names no
//! transport and no wire, and a step whose action carries no command sends nothing.

use oxigraph::model::Term;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF, RECORD, local_of};
use orexis::store::{Store, Within, iri};

use crate::Said;
use crate::implementation::operations;
use crate::ontology::COMMAND;

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
    const TAKES_Q: &str =
        "PREFIX orexis: <http://example.org/orexis#> SELECT ?takes WHERE { $action orexis:takes ?takes }";
    let actions = store.graphs_of(&[ACTION], &Within::default())?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let mut out = vec![("now".to_string(), Value::instant(now))];
    for row in store.rows(&bind(TAKES_Q, &[("action", Value::iri(action))])?, &actions)? {
        let Some(takes) = iri(&row, "takes") else { continue };
        let local = local_of(&takes);
        if let Some(given) = said.get(&local) {
            out.push((local, term(given)));
        }
    }
    Ok(out)
}

/// What one row of a command sets: the actuator, the property of it acted on, and the value it is set to.
#[derive(Debug, Clone, PartialEq)]
pub struct Setting {
    pub actuator: String,
    pub property: String,
    pub value: Term,
}

/// Every setting the step `said` sends — its rows keyed by local part — asked over the beliefs holding at `now`:
/// every command of the action's implementation, or those of one `order`. Empty where it has none or its texts answer
/// nothing; a row missing a column is refused in the log.
pub fn command(store: &Store, said: &Said, order: Option<f64>, now: DateTime) -> Result<Vec<Setting>, Error> {
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
            match (iri(&row, "actuator"), iri(&row, "property"), row.get("value")) {
                (Some(actuator), Some(property), Some(value @ Term::Literal(_))) => out.push(Setting {
                    actuator,
                    property,
                    value: value.clone(),
                }),
                _ => log::error!(
                    "{}: its command answered no actuator, property and literal value",
                    local_of(action)
                ),
            }
        }
    }
    Ok(out)
}
