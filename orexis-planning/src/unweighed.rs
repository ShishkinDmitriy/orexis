//! WHAT IS STILL TO BE WEIGHED, as `agent/planning/unweighed.py` reads it: every desire in every ground it is not
//! weighed in; every want in the ground holding at its instant; and for every want, every candidate leaving a world
//! the want has weighed that it has weighed neither the candidate nor the world it reached. Narrowed where the
//! caller knows: to one want's or desire's, or to the candidates leaving one world.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Row, Store};

use crate::Memo;
use crate::world_at::catalogue;

const IN_GROUNDS_Q: &str = "
SELECT DISTINCT ?for ?about WHERE {
  { GRAPH $cat { ?d a planning:DesireGraph } GRAPH ?d { ?holder planning:holds ?for . ?for a planning:Desire $narrow }
    GRAPH $cat { ?about a planning:GroundGraph } }
  UNION
  { GRAPH $cat { ?d a planning:WantGraph . OPTIONAL { ?d dcterms:temporal/orexis:start ?ws } }
    GRAPH ?d { ?holder planning:holds ?for . ?for a planning:Want $narrow }
    GRAPH $cat { ?about a planning:GroundGraph ; dcterms:temporal/orexis:start ?gs }
    BIND(COALESCE(?ws, \"0001-01-01T00:00:00Z\"^^xsd:dateTime) AS ?at)
    FILTER NOT EXISTS { GRAPH $cat { ?other a planning:GroundGraph ; dcterms:temporal/orexis:start ?os .
                                     FILTER((?os <= ?at && ?os > ?gs) || (?gs > ?at && ?os < ?gs)) } } }
  FILTER NOT EXISTS { GRAPH $cat { ?x planning:weighs ?about ; planning:for ?for } } }
ORDER BY ?for ?about";

const CANDIDATES_Q: &str = "
SELECT DISTINCT ?for ?about ?from ?child WHERE {
  GRAPH $cat { ?d a planning:WantGraph }
  GRAPH ?d { ?holder planning:holds ?for . ?for a planning:Want $narrow }
  GRAPH $cat {
    ?about a planning:Candidate ; planning:from ?from ; planning:minted ?m $leaving .
    ?y planning:weighs ?from ; planning:for ?for ; a planning:Weighing . }
  FILTER NOT EXISTS { GRAPH $cat { ?x planning:weighs ?about ; planning:for ?for } }
  FILTER NOT EXISTS { GRAPH $cat { ?c planning:by ?about . ?z planning:weighs ?c ; planning:for ?for } }
  OPTIONAL { GRAPH $cat { ?child planning:by ?about } } }
ORDER BY ?for ?m";

/// Every `(for, about)` still to be weighed, desires and wants in grounds first, then candidates in mint order —
/// each candidate's row with `from`, the world it leaves, and `child`, where it reached one.
pub fn unweighed(store: &Store, for_: Option<&str>, leaving: Option<&str>, memo: &mut Memo) -> Result<Vec<Row>, Error> {
    let cat = Value::iri(catalogue(store, memo)?);
    let narrow = Value::raw(for_.map(|f| format!("VALUES ?for {{ <{f}> }}")).unwrap_or_default());
    let mut out = if leaving.is_some() {
        Vec::new()
    } else {
        store.rows(
            &bind(IN_GROUNDS_Q, &[("cat", cat.clone()), ("narrow", narrow.clone())])?,
            &[],
        )?
    };
    let leaving = Value::raw(leaving.map(|l| format!("VALUES ?from {{ <{l}> }}")).unwrap_or_default());
    out.extend(store.rows(
        &bind(CANDIDATES_Q, &[("cat", cat), ("narrow", narrow), ("leaving", leaving)])?,
        &[],
    )?);
    Ok(out)
}
