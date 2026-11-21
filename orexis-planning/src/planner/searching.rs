//! ONE SCOPE'S SEARCH, handed everything it reads of the beliefs: the grounds laid in its imaginarium and the present
//! re-rooted, every desire weighed, the wants derived and withdrawn, each want searched and reconsidered against what
//! walks — and what it found handed back, for the planner to apply to the beliefs. It reads and writes its imaginarium
//! and nothing else.

use std::collections::{BTreeMap, BTreeSet};

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::events::Laps;
use orexis::foresight::Foresight;
use orexis::store::{Store, iri, value};

use super::search::Searcher;
use super::{Walks, beside, broken, held_constraints, of_scope, plan_of, said, zero};
use crate::admit::local_of;
use crate::derive_wants::derive_wants;
use crate::events::{Rerooted, WantReached};
use crate::find_scopes::Scopes;
use crate::lay_ground::{Landed, Laying, cut_out, lay_ground_foreseeing, no_longer_ahead};
use crate::memo::Memo;
use crate::ontology::EXHAUSTED;
use crate::prepare_ground::Crossed;
use crate::reroot::reroot;
use crate::scope::Scope;
use crate::unweighed::unweighed;
use crate::weigh::{shapes, weigh};
use crate::withdraw::withdraw;

/// When a search the budget cut short was, and the grounds it was searched in, by hash.
pub(super) type Cut = (DateTime, BTreeSet<String>);

/// WHAT ONE SCOPE'S SEARCH IS HANDED: its imaginarium, filled, and everything it reads of the beliefs, read as the
/// planning began.
pub(super) struct Searching {
    pub(super) scope: String,
    pub(super) store: Store,
    pub(super) scopes: Scopes,
    /// The actions the scope admits; `None` meaning every action the store holds.
    pub(super) only: Option<BTreeSet<String>>,
    /// The values that are another scope's.
    pub(super) elsewhere: BTreeSet<String>,
    /// What a world is identified by.
    pub(super) within: Option<BTreeSet<String>>,
    /// When each step in flight of the scope lands, and what it changes there.
    pub(super) landings: Vec<DateTime>,
    pub(super) landed: Vec<Landed>,
    /// The instants the last planning of this scope laid a ground at for a want kept below to begin in.
    pub(super) begun: Vec<DateTime>,
    pub(super) foresight: Option<Box<dyn Foresight>>,
    pub(super) walks: Walks,
    pub(super) walking: BTreeSet<String>,
    /// The wants a role above planning asked to have reopened.
    pub(super) asked: BTreeSet<String>,
    /// The walking wants already said reached this pass.
    pub(super) already: BTreeSet<String>,
    /// Each want whose search the budget last cut short.
    pub(super) cut: BTreeMap<String, Cut>,
    /// What the scope's worlds read beside their grounds as the last planning left it.
    pub(super) beside: Option<u64>,
    pub(super) budget_every_s: f64,
    pub(super) laps: Option<Laps>,
    pub(super) at: DateTime,
    pub(super) searcher: Searcher,
    /// What crossed into the imaginarium, where the search is set going off planning's task.
    pub(super) crossed: Option<Crossed>,
}

/// WHAT ONE SCOPE'S SEARCH FOUND, for the planner to apply.
pub(crate) struct Searched {
    pub(super) scope: String,
    pub(super) store: Store,
    /// Which of the four the scope's present was in.
    pub(super) rerooted: &'static str,
    /// The present's ground.
    pub(super) present: String,
    /// The walking wants the present meets.
    pub(super) met: BTreeSet<String>,
    /// The wants no intention walks that the present meets, to withdraw from the beliefs.
    pub(super) reached: BTreeSet<String>,
    /// The walking wants whose plans stand, and the steps of a joint plan kept out of what is published, by want.
    pub(super) unwalked: BTreeSet<String>,
    pub(super) kept: BTreeMap<String, Vec<String>>,
    /// The wants searched here, or waiting for their next budget.
    pub(super) here: BTreeSet<String>,
    /// Each want's search the budget cut short now, or not.
    pub(super) cut: BTreeMap<String, Option<Cut>>,
    /// Each walking want after whose step a world of its plan was foreseen impossible now, or not.
    pub(super) doomed: Vec<(String, Option<String>)>,
    pub(super) beside: u64,
    pub(super) laps: Option<Laps>,
    pub(super) at: DateTime,
    pub(super) crossed: Option<Crossed>,
}

impl Searching {
    /// Search the scope, and say what was found.
    pub(super) fn search(self) -> Result<Searched, Error> {
        const GROUND_HASHES_Q: &str = r#"PREFIX orexis: <http://example.org/orexis#>
            PREFIX planning: <http://example.org/orexis/planning#>
            SELECT ?h WHERE { GRAPH ?g { ?g a planning:GroundGraph ; orexis:hash ?h } }"#;
        const REOPENING_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
        SELECT ?w WHERE { GRAPH ?g { ?w planning:reopens ?w }
          FILTER NOT EXISTS { GRAPH ?p { ?root a planning:Plan ; planning:for ?w ; planning:outcome planning:Satisfied } } }"#;
        const HASHES_Q: &str = r#"PREFIX orexis: <http://example.org/orexis#>
          PREFIX planning: <http://example.org/orexis/planning#>
          SELECT DISTINCT ?h WHERE { GRAPH ?w { ?w orexis:hash ?h .
          { ?w a planning:GroundGraph } UNION { ?w a planning:PossibleGraph } } }"#;
        const MET_NOW_Q: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX orexis: <http://example.org/orexis#>
        PREFIX planning: <http://example.org/orexis/planning#>
        SELECT DISTINCT ?for WHERE {
          GRAPH ?cat { ?x planning:weighs $ground ; planning:for ?for ; planning:met true .
                       ?cat a orexis:CatalogueGraph .
                       ?d a planning:WantGraph . OPTIONAL { ?d dcterms:temporal/orexis:start ?ws } }
          GRAPH ?d { ?for a planning:Want }
          FILTER(!BOUND(?ws) || ?ws <= $now) }"#;
        let Searching {
            scope,
            store,
            scopes,
            only,
            elsewhere,
            within,
            landings,
            landed,
            begun,
            mut foresight,
            walks,
            walking,
            asked,
            already,
            cut: was_cut,
            beside: as_was,
            budget_every_s,
            mut laps,
            at,
            searcher,
            crossed,
        } = self;
        let mut lap = |part: &str| {
            if let Some(laps) = laps.as_mut() {
                laps.lap(part);
            }
        };
        let store = &store;
        let mut memo = Memo::default();
        let foreseen: BTreeSet<String> = if walks.is_empty() {
            BTreeSet::new()
        } else {
            store
                .rows(HASHES_Q, &[])?
                .iter()
                .filter_map(|r| value(r, "h"))
                .collect()
        };
        //  WHETHER WHAT A WORLD READS BESIDE ITS GROUND STANDS AS IT DID WHEN THE LAST PLANNING BEGAN: asked here,
        //  the imaginarium refreshed, what the scope can change cut out of it and nothing else of this planning
        //  written yet, and of the same moment of the planning before, since the derivation writes wants into these
        //  graphs. So the planning after one that minted a want begins its searches again, once (#1158). ASKED BEFORE
        //  THE CUT, what a step changes was beside every ground, and a ground ahead laid again while a plan was walked
        //  towards it kept nothing: the search of a want beginning there began again at every step.
        let laying_for = Scope {
            actions: only.as_ref(),
            within: within.as_ref(),
            ..Scope::default()
        };
        //  WHERE A WANT KEPT BELOW BEGAN AT THE LAST PLANNING is no ground ahead until this one lays it again.
        for was in begun {
            no_longer_ahead(store, was)?;
        }
        cut_out(store, at, &laying_for)?;
        let stands = beside(store)?;
        let as_stood = as_was == Some(stands);
        let laid = lay_ground_foreseeing(
            store,
            at,
            &Laying {
                scope: laying_for,
                landings: &landings,
                landed: &landed,
                as_stood,
                cut: true,
            },
            foresight.as_mut().map(|f| f.as_mut() as &mut dyn Foresight),
        )?;
        let present = laid
            .first()
            .cloned()
            .ok_or_else(|| Error::Evaluation("no ground was laid".into()))?;
        let arrived = !walks.is_empty() && {
            store
                .rows(GROUND_HASHES_Q, &[])?
                .iter()
                .filter_map(|r| value(r, "h"))
                .any(|h| !foreseen.contains(&h))
        };
        let rerooting = reroot(store, &present)?;
        if searcher.watch.connected() {
            searcher.say(&Rerooted {
                scope: local_of(&scope),
                present: rerooting.present.to_string(),
                kept: Some(rerooting.kept.len() as f64),
                dropped: Some(rerooting.dropped.len() as f64),
            });
        }
        lap("ground");
        let constraints = held_constraints(store, &searcher.uri, only.as_ref(), at, &mut memo)?;
        for constraint in &constraints {
            let broken = broken(store, constraint, &present, &mut memo)?;
            if !broken.is_empty() {
                log::warn!(
                    "{}: the present violates {}, a constraint of this world, and nothing repairs it: {}",
                    searcher.id,
                    local_of(constraint),
                    said(&broken)
                );
            }
        }
        for pair in unweighed(store, None, None, &mut memo)? {
            if !pair.contains_key("from")
                && let (Some(for_), Some(about)) = (iri(&pair, "for"), iri(&pair, "about"))
            {
                weigh(store, &for_, &about, &mut memo)?;
            }
        }
        let mut doomed = Vec::new();
        let mut reopen = if arrived && !walks.is_empty() && !constraints.is_empty() {
            searcher.impossible_ahead(store, &walks, &constraints, only.as_ref(), &mut doomed, &mut memo)?
        } else {
            BTreeSet::new()
        };
        reopen.extend(searcher.asked_here(store, &walks, only.as_ref(), &asked)?);
        lap("weigh");
        let met_now: BTreeSet<String> = store
            .rows(
                &bind(
                    MET_NOW_Q,
                    &[("ground", Value::iri(present.as_str())), ("now", Value::instant(at))],
                )?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "for"))
            .collect();
        let met: BTreeSet<String> = met_now.intersection(&walking).cloned().collect();
        for want in met.difference(&already) {
            if searcher.watch.connected() {
                searcher.say(&WantReached { want: want.clone(), at });
            }
        }
        let reached: BTreeSet<String> = met_now.difference(&walking).cloned().collect();
        let opens: BTreeMap<String, DateTime> = walking
            .iter()
            .map(|w| (w.clone(), walks.get(w).map_or(at, |f| f.landing)))
            .collect();
        let none = BTreeSet::new();
        if !reopen.is_empty() {
            withdraw(store, None, &none, &reopen)?;
        }
        let mut wanted = derive_wants(store, at, &opens, &reopen)?;
        wanted.extend(walking.iter().cloned());
        withdraw(store, Some(&wanted), &reached, &none)?;
        lap("derive");
        //  THE SHAPES ARE FORGOTTEN AFTER THE DERIVATION, because the derivation WRITES them.
        memo.shapes = None;
        memo.selects.clear();
        let shapes = shapes(store, &mut memo)?;
        let mut kept: BTreeMap<String, Vec<String>> = BTreeMap::new();
        let mut here = BTreeSet::new();
        let reopening: BTreeSet<String> = if walks.is_empty() {
            BTreeSet::new()
        } else {
            store
                .rows(REOPENING_Q, &[])?
                .iter()
                .filter_map(|r| iri(r, "w"))
                .filter(|w| walking.contains(w))
                .collect()
        };
        let grounds: BTreeSet<String> = {
            store
                .rows(GROUND_HASHES_Q, &[])?
                .iter()
                .filter_map(|r| value(r, "h"))
                .collect()
        };
        let mut cut: BTreeMap<String, Option<Cut>> = BTreeMap::new();
        for want in of_scope(store, &shapes, &searcher.uri, &scope, &scopes, at)? {
            if walking.contains(&want) && !reopening.contains(&want) {
                continue;
            }
            //  A BUDGET IS FOR A STRETCH OF THE AGENT'S TIME (`planning:budgetEveryS`): a search it cut short is given
            //  another where its grounds differ from those it was cut short in, which is news, or that stretch has
            //  passed, and not before. With no pass to pace it, every event heard handed the same search a fresh
            //  budget, and the budget was no ceiling.
            if let Some((when, seen)) = was_cut.get(&want)
                && *seen == grounds
                && orexis::clock::seconds_of(at.checked_sub(*when).unwrap_or_else(zero)) < budget_every_s
            {
                here.insert(want.clone());
                continue;
            }
            let searched = Scope {
                name: Some(scope.as_str()),
                actions: only.as_ref(),
                elsewhere: Some(&elsewhere),
                within: within.as_ref(),
            };
            searcher.search(store, &want, searcher.budget, &searched, at, &mut memo)?;
            let exhausted = plan_of(store, &want)?.outcome.is_some_and(|o| o == EXHAUSTED);
            cut.insert(want.clone(), exhausted.then(|| (at, grounds.clone())));
            here.insert(want.clone());
            searcher.reconsider(store, &want, &walks, &mut kept)?;
        }
        lap("search");
        let mut unwalked: BTreeSet<String> = walking.clone();
        for w in reopening.intersection(&here) {
            unwalked.remove(w);
        }
        Ok(Searched {
            scope,
            store: store.clone(),
            rerooted: rerooting.present,
            present,
            met,
            reached,
            unwalked,
            kept,
            here,
            cut,
            doomed,
            beside: stands,
            laps,
            at,
            crossed,
        })
    }
}
