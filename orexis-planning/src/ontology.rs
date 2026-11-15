//! PLANNING'S TERMS that code names, as `agent/planning/ontology.py` names them.

use orexis::ontology::{BELIEF, RECORD};

pub const PLANNING: &str = "http://example.org/orexis/planning#";
/// A pass of the Planner, as the activity it is.
pub const PLANNING_ACTIVITY: &str = "http://example.org/orexis/planning#Planning";
/// What starts a planning, and the wants it names to search again.
pub const PLANNING_TRIGGER: &str = "http://example.org/orexis/planning#PlanningTrigger";
pub const REOPENS: &str = "http://example.org/orexis/planning#reopens";

pub const DESIRE: &str = "http://example.org/orexis/planning#DesireGraph";
pub const WANT: &str = "http://example.org/orexis/planning#WantGraph";

/// What a planning text is answered over: the kernel's kinds, and the desires and wants.
pub const KNOWN: &[&str] = &[BELIEF, RECORD, DESIRE, WANT];

pub const CANDIDATE: &str = "http://example.org/orexis/planning#Candidate";
pub const WAIT: &str = "http://example.org/orexis/planning#Wait";
pub const FILLS: &str = "http://example.org/orexis/planning#fills";
pub const FROM: &str = "http://example.org/orexis/planning#from";
pub const MINTED: &str = "http://example.org/orexis/planning#minted";
pub const PRECONDITION: &str = "http://example.org/orexis/planning#precondition";

pub const POSSIBLE_GRAPH: &str = "http://example.org/orexis/planning#PossibleGraph";
pub const GROUND_GRAPH: &str = "http://example.org/orexis/planning#GroundGraph";
pub const CHANGEABLE_GRAPH: &str = "http://example.org/orexis/planning#ChangeableGraph";
pub const SPENT: &str = "http://example.org/orexis/planning#spent";
pub const BY: &str = "http://example.org/orexis/planning#by";

/// A step's prediction, two graphs it names: EXECUTION'S words, which the Python planning package imports from
/// `agent/execution/ontology.py` as these two terms alone.
pub const ADDS_GRAPH: &str = "http://example.org/orexis/execution#AddsGraph";
pub const RETRACTS_GRAPH: &str = "http://example.org/orexis/execution#RetractsGraph";
pub const SHAPES: &str = "http://example.org/orexis/planning#ShapesGraph";
pub const CONSTRAINT_GRAPH: &str = "http://example.org/orexis/planning#ConstraintGraph";
pub const DERIVATION_GRAPH: &str = "http://example.org/orexis/planning#DerivationGraph";
pub const SCOPE_GRAPH: &str = "http://example.org/orexis/planning#ScopeGraph";
pub const ABOUT: &str = "http://example.org/orexis/planning#about";
pub const ANYTHING: &str = "http://example.org/orexis/planning#Anything";
pub const PLAN_GRAPH: &str = "http://example.org/orexis/planning#PlanGraph";
pub const SATISFIED: &str = "http://example.org/orexis/planning#Satisfied";
pub const NO_CANDIDATE: &str = "http://example.org/orexis/planning#NoCandidate";
pub const EXHAUSTED: &str = "http://example.org/orexis/planning#Exhausted";
pub const BUDGET_TERM: &str = "http://example.org/orexis/planning#budget";
/// How long a budget is for, the planner's role's figure: a search the budget cut short is given another this long after.
pub const BUDGET_EVERY_TERM: &str = "http://example.org/orexis/planning#budgetEveryS";
pub const PLAN: &str = "http://example.org/orexis#PlanGraph";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("planning", include_str!("../ontology.ttl")));

/// A FIGURE OF THE ROLE THIS PACKAGE IS LOADED FOR: what a role the self plays says of `term` in the agent's self
/// graph, read by this package's own query, and where no role says it the default this ontology states. Two
/// answers are never picked between: several, or one that is no number, is the default, said in the log.
pub fn figure_of(store: &orexis::store::Store, term: &str) -> Result<f64, orexis::Error> {
    use orexis::bind::{Value, bind};
    use orexis::store::{Within, value};
    let selves = store.graphs_of(&[orexis::ontology::SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let text = bind(
        "SELECT DISTINCT ?n WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role $figure ?n }",
        &[("figure", Value::iri(term))],
    )?;
    let said: Vec<String> = store
        .rows(&text, &selves)?
        .iter()
        .filter_map(|row| value(row, "n"))
        .collect();
    if let [one] = said.as_slice()
        && let Ok(figure) = one.parse::<f64>()
    {
        return Ok(figure);
    }
    let default = DEFAULTS.figure(term)?;
    if !said.is_empty() {
        log::warn!(
            "the self's roles say {} for {}: the default, {default}, holds",
            said.join(", "),
            orexis::ontology::local_of(term)
        );
    }
    Ok(default)
}
