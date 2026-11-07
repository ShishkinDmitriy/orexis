//! ONE WANT'S SEARCH: `search` takes and weighs worlds until the budget is spent or a world meets the want, and
//! `expand` is one iteration of it — the frontier's best candidate taken, its world weighed, and marked impossible
//! where it violates a constraint the agent holds.

use std::collections::HashSet;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Store, iri};

use super::{Planner, Searching, beaten, broken, cat, held_constraints, said, spent};
use crate::admit::{Scope, admit, local_of};
use crate::extract_plan::extract_plan;
use crate::memo::Memo;
use crate::take::take;
use crate::unweighed::unweighed;
use crate::weigh::weigh;

const FRONTIER_Q: &str = r#"
SELECT ?w ?spent ?remaining ?minted ?weighing ?late ?lands ?best ?bestLate ?bestLands WHERE {
  GRAPH $cat { ?weighing a planning:Weighing ; planning:for $want ; planning:open true ; planning:weighs ?w .
    OPTIONAL { ?w planning:spent ?s } OPTIONAL { ?w planning:minted ?m }
    OPTIONAL { ?weighing planning:remaining ?r }
    OPTIONAL { ?weighing planning:late ?lands } }
  OPTIONAL { SELECT ?best ?bestLate ?bestLands WHERE {
    GRAPH $cat { ?y a planning:Weighing ; planning:for $want ; planning:met true ; planning:weighs ?bw .
      ?bw planning:spent ?best
      OPTIONAL { ?y planning:late ?bestLands } }
    BIND(IF(BOUND(?bestLands), 1, 0) AS ?bestLate) }
    ORDER BY ?bestLate ?bestLands ?best LIMIT 1 }
  BIND(COALESCE(?s, 0.0) AS ?spent) BIND(COALESCE(?m, 0) AS ?minted) BIND(COALESCE(?r, 0.0) AS ?remaining)
  BIND(IF(BOUND(?lands), 1, 0) AS ?late) }
ORDER BY ?late ?lands (?spent + ?remaining) ?minted LIMIT 1"#;

const CLOSE_U: &str = r#"
DELETE { GRAPH ?cat { $weighing planning:open ?o } }
INSERT { GRAPH ?cat { $weighing planning:expanded true } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $weighing planning:open ?o } }"#;

const REACHED_Q: &str = r#"
SELECT ?w ?marked WHERE { GRAPH $cat { $x planning:weighs ?w . ?w a planning:PossibleGraph .
                                       OPTIONAL { ?w planning:impossible ?marked } } } LIMIT 1"#;

const MARK_U: &str = r#"
DELETE { GRAPH ?cat { $weighing planning:open ?o . $weighing planning:met ?m . $weighing planning:remaining ?r .
                      $weighing planning:late ?l . $weighing planning:violation ?v . ?v ?p ?x } }
INSERT { GRAPH ?cat { $world planning:impossible $by } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      OPTIONAL { $weighing planning:open ?o } OPTIONAL { $weighing planning:met ?m }
                      OPTIONAL { $weighing planning:remaining ?r } OPTIONAL { $weighing planning:late ?l }
                      OPTIONAL { $weighing planning:violation ?v . ?v ?p ?x } } }"#;

impl<'a> Planner<'a> {
    /// Plan for `want` from the ground holding at its instant, spending at most `budget` candidates beyond what its
    /// search spent before, and write the plan, whatever the search concluded.
    pub fn search(
        &self,
        store: &Store,
        want: &str,
        budget: usize,
        scoped: &Searching<'_>,
        memo: &mut Memo,
    ) -> Result<(), Error> {
        let started = std::time::Instant::now();
        for pair in unweighed(store, Some(want), None, memo)? {
            if !pair.contains_key("from")
                && let Some(about) = iri(&pair, "about")
            {
                weigh(store, want, &about, memo)?;
            }
        }
        let ceiling = spent(store, want, memo)? + budget;
        while let Some(spent) = self.expand(store, want, ceiling, scoped, memo)? {
            if spent >= ceiling {
                break;
            }
        }
        extract_plan(store, want)?;
        let weighed = spent(store, want, memo)?.saturating_sub(ceiling - budget);
        self.searched(store, want, started, budget, weighed, scoped.scope)?;
        Ok(())
    }

    /// Open the top of `want`'s frontier: admit what it admits, take each candidate this want has not yet weighed,
    /// weigh what it reached — for the want and every constraint the scope's actions can write — and close it. What the
    /// search has spent afterwards, or None where there was nothing to open or the cheapest achiever refuses the top.
    pub fn expand(
        &self,
        store: &Store,
        want: &str,
        budget: usize,
        scoped: &Searching<'_>,
        memo: &mut Memo,
    ) -> Result<Option<usize>, Error> {
        let c = cat(store, memo)?;
        let top = store.rows(
            &bind(FRONTIER_Q, &[("want", Value::iri(want)), ("cat", c.clone())])?,
            &[],
        )?;
        let Some(top) = top.into_iter().next() else {
            return Ok(None);
        };
        if beaten(&top)? {
            return Ok(None);
        }
        let world = iri(&top, "w").ok_or_else(|| Error::Evaluation("a frontier row naming no world".into()))?;
        let constraints = held_constraints(store, &self.uri, scoped.only, scoped.at, memo)?;
        let only: Option<HashSet<String>> = scoped.only.map(|o| o.iter().cloned().collect());
        let elsewhere: HashSet<String> = scoped.elsewhere.iter().cloned().collect();
        admit(
            store,
            &world,
            &Scope {
                only: only.as_ref(),
                elsewhere: Some(&elsewhere),
            },
            memo,
        )?;
        let mut used = spent(store, want, memo)?;
        for pair in unweighed(store, Some(want), Some(&world), memo)? {
            if used >= budget {
                return Ok(Some(used));
            }
            let Some(about) = iri(&pair, "about") else { continue };
            if !pair.contains_key("child") {
                take(store, &about, scoped.within, memo)?;
            }
            let weighing = weigh(store, want, &about, memo)?;
            if !constraints.is_empty() {
                self.mark(store, &weighing, &constraints, memo)?;
            }
            used += 1;
        }
        let weighing =
            iri(&top, "weighing").ok_or_else(|| Error::Evaluation("a frontier row naming no weighing".into()))?;
        store.update(&bind(CLOSE_U, &[("weighing", Value::iri(weighing.as_str()))])?)?;
        Ok(Some(used))
    }

    /// Mark the world `weighing` is of impossible where some constraint yields a row there.
    fn mark(&self, store: &Store, weighing: &str, constraints: &[String], memo: &mut Memo) -> Result<(), Error> {
        let c = cat(store, memo)?;
        let reached = store.rows(&bind(REACHED_Q, &[("x", Value::iri(weighing)), ("cat", c)])?, &[])?;
        let Some(r) = reached.first() else { return Ok(()) };
        if r.contains_key("marked") {
            return Ok(());
        }
        let Some(world) = iri(r, "w") else { return Ok(()) };
        for constraint in constraints {
            let rows = broken(store, constraint, &world, memo)?;
            if !rows.is_empty() {
                store.update(&bind(
                    MARK_U,
                    &[
                        ("weighing", Value::iri(weighing)),
                        ("world", Value::iri(world.as_str())),
                        ("by", Value::iri(constraint.as_str())),
                    ],
                )?)?;
                log::info!(
                    "{}: {} is impossible — it violates {}: {}",
                    self.id,
                    world.rsplit('/').next().unwrap_or(&world),
                    local_of(constraint),
                    said(&rows)
                );
            }
        }
        Ok(())
    }
}
