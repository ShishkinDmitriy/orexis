//! WHAT A HOLDER'S CONSTRAINTS CAN MAKE COLLIDE — which instances' plans may interfere under one, read off the
//! constraint's footprint over what the actions can REACH from the present, as `agent/planning/couplings.py` reads
//! it (one-mind-couples-the-wants-a-constraint-can-make-collide).
//!
//! **THE REACH** is every fact some sequence of the actions could make true from the present ground with nothing
//! taken away: each effect's insert template closed over its precondition, round after round, until no round adds
//! a triple. A constraint's rows over it are the collisions plans could make, and two instances are coupled where
//! one component of what those rows join meets what each is bound with by a filling admitted in the reach.
//! **A VALUE AN EFFECT COMPUTES IS REACHABLE ANYWHERE**, so where a template writes a value arithmetic binds, every
//! instance is coupled and no reach is run; so is it where a constraint or an effect will not be read, since what
//! cannot be read cannot be proven not to collide.
//!
//! The Python copy composes an effect over its precondition by splicing their texts; this composes the parsed
//! algebra and prints it back as SPARQL, which the engine parses again. A `BIND` in the effect's WHERE of a variable
//! the precondition projects is refused either way: the engine refuses the spliced text, and this the algebra.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::LazyLock;

use oxigraph::model::{GraphName, NamedNode, Quad, Term};
use oxsdatatypes::DateTime;
use regex::Regex;
use spargebra::Query;
use spargebra::algebra::{Expression, Function, GraphPattern};
use spargebra::term::{TermPattern, TriplePattern, Variable};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::ACTION;
use orexis::store::{Store, Within, iri, value};
use orexis_belief::transition::parts;

use crate::memo::Memo;
use crate::ontology::{CONSTRAINT_GRAPH, SHAPES};
use crate::shapes::Shapes;
use crate::violation::{Compiled, select_of};
use crate::world_at::{Asking, world_at};

/// WHERE THE REACH IS WRITTEN while it is computed, and taken away before the answer is given.
pub const REACH_GRAPH: &str = "http://example.org/orexis/graph/reach";

/// A round is every construct asked once over what stands; the reach closes on its own, so this is a guard.
pub const ROUNDS: usize = 64;

const CONSTRAINTS_Q: &str = "SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c";

const ACTIONS_Q: &str = "
SELECT ?action ?precondition ?update WHERE {
  ?action a orexis:Action ; planning:precondition ?precondition ;
          planning:effect/sh:rule ?r . ?r a belief:Transition ; belief:update ?update }
ORDER BY ?action ?update";

static TOKEN: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$([A-Za-z_][A-Za-z0-9_]*)\b").expect("a valid pattern"));
static HEAD: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?is)^(\s*(?:PREFIX\s+\S+\s+<[^>]*>\s*)*)SELECT\s+(?:DISTINCT\s+|REDUCED\s+)?(.*?)\s+WHERE\b")
        .expect("a valid pattern")
});
static THIS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$this\b").expect("a valid pattern"));

/// What one holder's constraints can make collide: the components of the terms the constraints' rows join over the
/// reach, and each term to every term some filling admitted there binds it with. `anything` joins everything.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Couplings {
    pub parts: Vec<BTreeSet<String>>,
    pub bound: BTreeMap<String, BTreeSet<String>>,
    pub anything: bool,
}

impl Couplings {
    fn anything() -> Self {
        Couplings {
            anything: true,
            ..Couplings::default()
        }
    }

    /// Can some constraint make a plan for `a` and a plan for `b` collide?
    pub fn joins(&self, a: &str, b: &str) -> bool {
        if self.anything {
            return true;
        }
        let reach = |x: &str| {
            let mut out = self.bound.get(x).cloned().unwrap_or_default();
            out.insert(x.to_string());
            out
        };
        let (reach_a, reach_b) = (reach(a), reach(b));
        self.parts
            .iter()
            .any(|part| !part.is_disjoint(&reach_a) && !part.is_disjoint(&reach_b))
    }
}

/// What `holder`'s constraints can make collide, read over the reach from the `present` ground — None where the
/// holder holds no constraint, which costs one query and couples nothing.
pub fn couplings(
    store: &Store,
    holder: &str,
    present: &str,
    now: DateTime,
    memo: &mut Memo,
) -> Result<Option<Couplings>, Error> {
    let constraint_graphs = store.graphs_of(&[CONSTRAINT_GRAPH], &Within::default())?;
    let graphs: Vec<&str> = constraint_graphs.iter().map(String::as_str).collect();
    let constraints: Vec<String> = store
        .rows(&bind(CONSTRAINTS_Q, &[("holder", Value::iri(holder))])?, &graphs)?
        .iter()
        .filter_map(|r| iri(r, "c"))
        .collect();
    if constraints.is_empty() {
        return Ok(None);
    }
    let shapes = Shapes::of(
        store,
        &store.graphs_of(&[CONSTRAINT_GRAPH, SHAPES], &Within::default())?,
    )?;
    let mut selects = Vec::new();
    for c in &constraints {
        let subject: Term = NamedNode::new(c.as_str())
            .map_err(|e| Error::Evaluation(e.to_string()))?
            .into();
        match select_of(&shapes, &subject, store.namespaces()) {
            Ok(Some(text)) => selects.push(text),
            Ok(None) => {}
            Err(Compiled::Unsupported(u)) => {
                log::warn!("a constraint cannot be compiled; every instance is coupled: {u}");
                return Ok(Some(Couplings::anything()));
            }
            Err(Compiled::Error(e)) => return Err(e),
        }
    }
    let world = world_at(
        store,
        Some(present),
        &Asking {
            now: Some(now),
            ..Asking::default()
        },
        memo,
    )?;
    let actions = store.graphs_of(&[ACTION], &Within::at(now))?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let declared = store.rows(ACTIONS_Q, &actions)?;
    let mut texts = Vec::new();
    for row in &declared {
        let (Some(precondition), Some(update)) = (value(row, "precondition"), value(row, "update")) else {
            continue;
        };
        match composed(store, &precondition, &update) {
            Ok(Some(text)) => texts.push(text),
            Ok(None) => {}
            Err(e) => {
                log::warn!("a construct could not be closed over its precondition; every instance is coupled: {e}");
                return Ok(Some(Couplings::anything()));
            }
        }
    }
    if texts.iter().any(|(_, computes)| *computes) {
        log::info!(
            "an effect writes a value its precondition computes, which is reachable anywhere; every instance is coupled"
        );
        return Ok(Some(Couplings::anything()));
    }
    let mut default: Vec<&str> = world.iter().map(String::as_str).collect();
    default.push(REACH_GRAPH);
    let texts: Vec<String> = texts.into_iter().map(|(t, _)| t).collect();
    let found = (|| {
        if let Err(e) = reach(store, &texts, &default) {
            log::warn!("a construct could not be run over the reach; every instance is coupled: {e}");
            return Ok(Couplings::anything());
        }
        let Some(parts) = parts_of(store, &selects, &default)? else {
            return Ok(Couplings::anything());
        };
        let preconditions: Vec<String> = declared.iter().filter_map(|r| value(r, "precondition")).collect();
        Ok(Couplings {
            parts,
            bound: bound(store, &preconditions, &default),
            anything: false,
        })
    })();
    store.clear_graph(REACH_GRAPH)?;
    found.map(Some)
}

/// The effect's insert template closed over its precondition as ONE construct — the template over the
/// precondition, as a subselect, joined with the effect's own WHERE — and whether a template value is one an
/// expression computes. None where the update inserts nothing; refused where it will not be read so.
fn composed(store: &Store, precondition: &str, update: &str) -> Result<Option<(String, bool)>, Error> {
    let precondition = bind(precondition, &[])?;
    let update = TOKEN.replace_all(update, "?${1}");
    let parts = parts(store, &update)?;
    if parts.insert.is_empty() {
        return Ok(None);
    }
    let Query::Select { pattern: select, .. } = store.parse_query(&precondition)? else {
        return Err(Error::Syntax("a precondition that is no select".into()));
    };
    let projected = projected(&select);
    let mut made = BTreeSet::new();
    extended(&parts.pattern, &mut |v, _| {
        made.insert(v.clone());
    });
    if let Some(v) = made.iter().find(|v| projected.contains(*v)) {
        return Err(Error::Syntax(format!(
            "BIND rebinds ?{} the precondition projects",
            v.as_str()
        )));
    }
    let template: Vec<TriplePattern> = parts
        .insert
        .iter()
        .map(|q| TriplePattern {
            subject: q.subject.clone(),
            predicate: q.predicate.clone(),
            object: q.object.clone(),
        })
        .collect();
    let pattern = GraphPattern::Join {
        left: Box::new(select),
        right: Box::new(parts.pattern.clone()),
    };
    let mut computed = BTreeSet::new();
    extended(&pattern, &mut |v, e| {
        if computes(e) {
            computed.insert(v.clone());
        }
    });
    let computes = template.iter().any(|t| {
        matches!(&t.predicate, spargebra::term::NamedNodePattern::Variable(v) if computed.contains(v))
            || [&t.subject, &t.object]
                .into_iter()
                .any(|term| matches!(term, TermPattern::Variable(v) if computed.contains(v)))
    });
    let query = Query::Construct {
        template,
        dataset: None,
        pattern,
        base_iri: None,
    };
    Ok(Some((query.to_string(), computes)))
}

/// The variables a select projects.
fn projected(pattern: &GraphPattern) -> BTreeSet<Variable> {
    match pattern {
        GraphPattern::Project { variables, .. } => variables.iter().cloned().collect(),
        GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::OrderBy { inner, .. } => projected(inner),
        _ => BTreeSet::new(),
    }
}

/// Every `BIND` under `pattern`, its variable and its expression.
fn extended(pattern: &GraphPattern, found: &mut impl FnMut(&Variable, &Expression)) {
    match pattern {
        GraphPattern::Extend {
            inner,
            variable,
            expression,
        } => {
            extended(inner, found);
            found(variable, expression);
        }
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right }
        | GraphPattern::LeftJoin { left, right, .. } => {
            extended(left, found);
            extended(right, found);
        }
        GraphPattern::Filter { inner, .. }
        | GraphPattern::Graph { inner, .. }
        | GraphPattern::OrderBy { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::Group { inner, .. }
        | GraphPattern::Service { inner, .. } => extended(inner, found),
        _ => {}
    }
}

/// WHAT AN EXPRESSION COMPUTES RATHER THAN PICKS: arithmetic, a numeric builtin, a cast or another function call;
/// COALESCE and IF choose among terms the patterns bound.
fn computes(expression: &Expression) -> bool {
    match expression {
        Expression::Add(..)
        | Expression::Subtract(..)
        | Expression::Multiply(..)
        | Expression::Divide(..)
        | Expression::UnaryPlus(_)
        | Expression::UnaryMinus(_) => true,
        Expression::FunctionCall(function, _) => matches!(
            function,
            Function::Custom(_) | Function::Abs | Function::Round | Function::Ceil | Function::Floor | Function::Rand
        ),
        _ => false,
    }
}

/// Close the reach: every construct over what stands, round after round, until a round adds nothing.
fn reach(store: &Store, texts: &[String], default: &[&str]) -> Result<usize, Error> {
    let scratch = GraphName::NamedNode(NamedNode::new(REACH_GRAPH).map_err(|e| Error::Evaluation(e.to_string()))?);
    let (mut rounds, mut held) = (0, None);
    while rounds < ROUNDS {
        rounds += 1;
        for text in texts {
            let made = store.construct(text, default)?;
            store.add(
                made.into_iter()
                    .map(|t| Quad::new(t.subject, t.predicate, t.object, scratch.clone())),
            )?;
        }
        let size = store.quads(REACH_GRAPH)?.len();
        if held == Some(size) {
            break;
        }
        held = Some(size);
    }
    Ok(rounds)
}

/// The components of what the constraints' rows join over the reach: every IRI one row binds joined to every
/// other. Each select is asked with every variable projected first, then as written; None where neither runs.
fn parts_of(store: &Store, selects: &[String], default: &[&str]) -> Result<Option<Vec<BTreeSet<String>>>, Error> {
    let mut parent: BTreeMap<String, String> = BTreeMap::new();
    fn find(parent: &mut BTreeMap<String, String>, x: &str) -> String {
        let mut x = x.to_string();
        parent.entry(x.clone()).or_insert_with(|| x.clone());
        while parent[&x] != x {
            let up = parent[&parent[&x]].clone();
            parent.insert(x.clone(), up.clone());
            x = up;
        }
        x
    }
    for text in selects {
        let text = THIS.replace_all(&bind(text, &[])?, "?this").into_owned();
        let every = HEAD.replace(&text, "${1}SELECT * WHERE").into_owned();
        let mut solutions = None;
        for attempt in [&every, &text] {
            match store.rows(attempt, default) {
                Ok(found) => {
                    solutions = Some(found);
                    break;
                }
                Err(e) => log::debug!("a constraint's select would not run over the reach: {e}"),
            }
        }
        let Some(solutions) = solutions else {
            return Ok(None);
        };
        for solution in solutions {
            let terms: Vec<String> = solution
                .values()
                .filter_map(|t| match t {
                    Term::NamedNode(n) => Some(n.as_str().to_string()),
                    _ => None,
                })
                .collect();
            if let Some((first, rest)) = terms.split_first() {
                find(&mut parent, first);
                for other in rest {
                    let (a, b) = (find(&mut parent, first), find(&mut parent, other));
                    if a != b {
                        parent.insert(a, b);
                    }
                }
            }
        }
    }
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for term in parent.keys().cloned().collect::<Vec<_>>() {
        let root = find(&mut parent, &term);
        out.entry(root).or_default().insert(term);
    }
    let mut parts: Vec<BTreeSet<String>> = out.into_values().collect();
    parts.sort();
    Ok(Some(parts))
}

/// Each term to every term some filling admitted in the reach binds it with; a precondition that will not run binds
/// nothing, the under-approximation, and is said.
fn bound(store: &Store, preconditions: &[String], default: &[&str]) -> BTreeMap<String, BTreeSet<String>> {
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for text in preconditions {
        let found = bind(text, &[]).and_then(|t| store.rows(&t, default));
        match found {
            Ok(solutions) => {
                for solution in solutions {
                    let terms: BTreeSet<String> = solution
                        .values()
                        .filter_map(|t| match t {
                            Term::NamedNode(n) => Some(n.as_str().to_string()),
                            _ => None,
                        })
                        .collect();
                    for term in &terms {
                        out.entry(term.clone())
                            .or_default()
                            .extend(terms.iter().filter(|t| *t != term).cloned());
                    }
                }
            }
            Err(e) => log::warn!("a precondition would not run over the reach, and binds nothing there: {e}"),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    //! What a holder's constraints can make collide, held to what `test_couplings.py` holds the Python read to.

    use orexis::snapshots;

    use super::*;
    use crate::lay_ground::{Laying, lay_ground};

    const T: &str = "http://example.org/test#";

    fn laid(name: &str) -> (Store, String) {
        let store = snapshots::stand_in(&snapshots::tree().join(format!("planning/tests/derive_wants/{name}.trig")));
        let grounds = lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
        let [present] = grounds.as_slice() else {
            panic!("one ground: {grounds:?}")
        };
        let present = present.clone();
        (store, present)
    }

    #[test]
    fn a_drive_to_a_computed_position_couples_everything_and_runs_no_reach() {
        let (store, present) = laid("two_parcels_a_constraint_joins_are_one_want");
        let coupled = couplings(
            &store,
            &format!("{T}keeper"),
            &present,
            snapshots::now(),
            &mut Memo::default(),
        )
        .unwrap()
        .expect("the holder holds a constraint");
        assert!(coupled.anything);
        assert!(coupled.joins(&format!("{T}parcel_a"), &format!("{T}parcel_b")));
        assert!(
            !store.graph_names().unwrap().contains(&REACH_GRAPH.to_string()),
            "no reach is run"
        );
    }

    #[test]
    fn a_holder_with_no_constraint_couples_nothing_and_pays_no_reach() {
        let (store, present) = laid("two_parcels_two_estimates");
        assert_eq!(
            couplings(
                &store,
                &format!("{T}keeper"),
                &present,
                snapshots::now(),
                &mut Memo::default()
            )
            .unwrap(),
            None
        );
    }

    #[test]
    fn a_reach_over_finite_places_joins_only_what_can_meet() {
        let parts = vec![BTreeSet::from(["urn:a".to_string(), "urn:cell".to_string()])];
        let bound = BTreeMap::from([
            ("urn:p".to_string(), BTreeSet::from(["urn:a".to_string()])),
            ("urn:q".to_string(), BTreeSet::from(["urn:cell".to_string()])),
            ("urn:r".to_string(), BTreeSet::from(["urn:b".to_string()])),
        ]);
        let coupled = Couplings {
            parts,
            bound,
            anything: false,
        };
        assert!(
            coupled.joins("urn:p", "urn:q"),
            "one part meets what each is bound with"
        );
        assert!(!coupled.joins("urn:p", "urn:r"), "and nothing joins what no part meets");
    }
}
