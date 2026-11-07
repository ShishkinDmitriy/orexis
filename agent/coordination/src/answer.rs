//! WHAT AN AGENT SAYS BACK TO A PEER'S QUESTION, as `agent/coordination/answer.py` says it. **ONLY UNDER A SHARED
//! CONSTRAINT**: an agent that does not hold the question's constraint says nothing, which the asker takes as silence.
//! **ONLY WHAT MEETS**: the answerer's own holdings under the constraint that the constraint reads as violating an
//! asked one, and none other — said even where nothing meets, in the answer's graph, replaced each time.

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::ontology::RECEIVED;
use orexis::store::{Store, iri};

use crate::holdings::{RDF_TYPE, constraints_and_self, heard, holdings, rows_of, said, violates};
use crate::ontology::{ANSWER, ANSWER_GRAPH, COORDINATION, answer_graph};

/// WHAT A QUESTION HEARD SAYS: who asks, and under which constraint; only one that arrived from a peer.
const QUESTION_Q: &str = "
SELECT ?asker ?constraint WHERE { GRAPH $cat { $graph orexis:arrivedBy $received }
  GRAPH $graph { ?q a coordination:Question ; coordination:asks ?asker ; coordination:over ?constraint } } LIMIT 1";

const HOLDS_Q: &str =
    "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds $constraint . BIND($constraint AS ?c) } LIMIT 1";

/// The answer the self `me` of `store` says to the question heard in the graph `question`, with the peer it is to — or
/// None where the question is no peer's, or names a constraint the agent does not hold.
pub fn answer(store: &Store, me: &str, question: &str, at: DateTime) -> Result<Option<(String, Document)>, Error> {
    let Some(cat) = store.catalogue()? else { return Ok(None) };
    let text = bind(
        QUESTION_Q,
        &[
            ("cat", Value::iri(cat)),
            ("graph", Value::iri(question)),
            ("received", Value::iri(RECEIVED)),
        ],
    )?;
    let found = store.rows(&text, &[])?;
    let Some(row) = found.first() else { return Ok(None) };
    let (Some(asker), Some(constraint)) = (iri(row, "asker"), iri(row, "constraint")) else {
        return Ok(None);
    };
    if asker == me
        || rows_of(
            store,
            HOLDS_Q,
            &[("constraint", Value::iri(constraint.as_str()))],
            &constraints_and_self(store)?,
        )?
        .is_empty()
    {
        return Ok(None);
    }
    let asked = heard(store, question)?;
    let mut meeting = Vec::new();
    for h in holdings(store, &constraint, at)? {
        let mut meets = false;
        for q in &asked {
            if violates(store, &constraint, &h, q)? {
                meets = true;
                break;
            }
        }
        if meets {
            meeting.push(h);
        }
    }
    let graph = answer_graph(me, &asker, &constraint);
    let about = vec![
        (RDF_TYPE.to_string(), NamedNode::new_unchecked(ANSWER).into()),
        (
            format!("{COORDINATION}answers"),
            NamedNode::new_unchecked(question).into(),
        ),
        (format!("{COORDINATION}answeredBy"), NamedNode::new_unchecked(me).into()),
        (
            format!("{COORDINATION}over"),
            NamedNode::new_unchecked(&constraint).into(),
        ),
    ];
    Ok(Some((
        asker,
        said(&graph, ANSWER_GRAPH, &graph, &about, &meeting, None),
    )))
}
