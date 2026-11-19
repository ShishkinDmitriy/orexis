//! ONE WANT'S SEARCH: `search` takes and weighs worlds until the budget is spent or a world meets the want, and
//! `expand` is one iteration of it — the frontier's best candidate taken, its world weighed, and marked impossible
//! where it violates a constraint the agent holds. Each is a method of the [`Searcher`], what a search carries of the
//! agent, so that a scope's search needs nothing of the planner.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::events::{Event, Watch};
use orexis::rdf::round6;
use orexis::store::{Store, iri};
use oxigraph::model::NamedNode;

use super::{beaten, broken, cat, desire_of, held_constraints, plan_of, said, spent};
use crate::admit::{admit, local_of};
use crate::events::SearchEnded;
use crate::extract_plan::extract_plan;
use crate::memo::Memo;
use crate::scope::Scope;
use crate::take::take;
use crate::unweighed::unweighed;
use crate::weigh::weigh;

/// Each want searched and not yet published: when it was first searched, and in how many passes. Shared by every
/// scope's search and the planner that publishes, which takes a want's tally with its plan.
pub(super) type Tallies = Arc<Mutex<BTreeMap<String, (Instant, usize)>>>;

/// WHO SEARCHES, carried into a scope's search: the agent's identifier and IRI, how much a search may spend, whoever
/// watches, and the tally of each want's searches.
#[derive(Clone)]
pub(crate) struct Searcher {
    pub(super) id: String,
    pub(super) uri: String,
    pub(super) budget: usize,
    pub(super) watch: Watch,
    pub(super) searches: Tallies,
    /// The planning a search on a thread of its own says its events within; none where it runs on planning's task,
    /// which says them within the activity open there.
    pub(super) within: Option<NamedNode>,
}

impl Searcher {
    /// Say `event`, within the planning this search is part of.
    pub(super) fn say(&self, event: &dyn Event) {
        match &self.within {
            Some(planning) => {
                self.watch.emit_within(event, Some(planning.clone()));
            }
            None => {
                self.watch.emit(event);
            }
        }
    }

    /// Plan for `want` from the ground holding at its instant, spending at most `budget` candidates beyond what its
    /// search spent before, and write the plan, whatever the search concluded.
    pub fn search(
        &self,
        store: &Store,
        want: &str,
        budget: usize,
        scope: &Scope<'_>,
        at: DateTime,
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
        while let Some(spent) = self.expand(store, want, ceiling, scope, at, memo)? {
            if spent >= ceiling {
                break;
            }
        }
        extract_plan(store, want)?;
        let weighed = spent(store, want, memo)?.saturating_sub(ceiling - budget);
        self.searched(store, want, started, budget, weighed, scope.name)?;
        Ok(())
    }

    /// Tally a search of `want` begun at `started`, and say how it ended, where anybody watches.
    fn searched(
        &self,
        store: &Store,
        want: &str,
        started: Instant,
        budget: usize,
        weighed: usize,
        scope: Option<&str>,
    ) -> Result<(), Error> {
        self.searches
            .lock()
            .unwrap()
            .entry(want.to_string())
            .or_insert((started, 0))
            .1 += 1;
        if !self.watch.connected() {
            return Ok(());
        }
        let outcome = plan_of(store, want)?.outcome.map(|o| local_of(&o));
        self.say(&SearchEnded {
            want: want.to_string(),
            desire: desire_of(store, want)?,
            scope: scope.map(local_of),
            outcome,
            duration_s: Some(round6(started.elapsed().as_secs_f64())),
            budget: Some(budget as f64),
            weighed: Some(weighed as f64),
        });
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
        scope: &Scope<'_>,
        at: DateTime,
        memo: &mut Memo,
    ) -> Result<Option<usize>, Error> {
        const FRONTIER_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
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
        const CLOSE_U: &str = r#"PREFIX orexis: <http://example.org/orexis#>
        PREFIX planning: <http://example.org/orexis/planning#>
        DELETE { GRAPH ?cat { $weighing planning:open ?o } }
        INSERT { GRAPH ?cat { $weighing planning:expanded true } }
        WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $weighing planning:open ?o } }"#;
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
        let constraints = held_constraints(store, &self.uri, scope.actions, at, memo)?;
        admit(store, &world, scope, memo)?;
        let mut used = spent(store, want, memo)?;
        for pair in unweighed(store, Some(want), Some(&world), memo)? {
            if used >= budget {
                return Ok(Some(used));
            }
            let Some(about) = iri(&pair, "about") else { continue };
            if !pair.contains_key("child") {
                take(store, &about, scope.within, memo)?;
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
        const REACHED_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
        SELECT ?w ?marked WHERE { GRAPH $cat { $x planning:weighs ?w . ?w a planning:PossibleGraph .
                                               OPTIONAL { ?w planning:impossible ?marked } } } LIMIT 1"#;
        const MARK_U: &str = r#"PREFIX orexis: <http://example.org/orexis#>
        PREFIX planning: <http://example.org/orexis/planning#>
        DELETE { GRAPH ?cat { $weighing planning:open ?o . $weighing planning:met ?m . $weighing planning:remaining ?r .
                              $weighing planning:late ?l . $weighing planning:violation ?v . ?v ?p ?x } }
        INSERT { GRAPH ?cat { $world planning:impossible $by } }
        WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                              OPTIONAL { $weighing planning:open ?o } OPTIONAL { $weighing planning:met ?m }
                              OPTIONAL { $weighing planning:remaining ?r } OPTIONAL { $weighing planning:late ?l }
                              OPTIONAL { $weighing planning:violation ?v . ?v ?p ?x } } }"#;
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
