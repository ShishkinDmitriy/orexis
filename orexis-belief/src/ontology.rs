//! BELIEF'S TERMS that code names, as `agent/belief/ontology.py` names them, and the names it spells for eyes.

pub const BELIEF: &str = "http://example.org/orexis/belief#";
pub const TRANSITION: &str = "http://example.org/orexis/belief#Transition";
pub const UPDATE: &str = "http://example.org/orexis/belief#update";
pub const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";
pub const REVISION_GRAPH: &str = "http://example.org/orexis/belief#RevisionGraph";
/// Whether a revision graph's rules settled over it.
pub const SETTLED: &str = "http://example.org/orexis/belief#settled";
/// How many rule executions one pass may spend: a figure the deliberator's role states.
pub const BUDGET_TERM: &str = "http://example.org/orexis/belief#budget";
/// The role a deliberator plays.
pub const DELIBERATOR: &str = "http://example.org/orexis/belief#Deliberator";
/// A revision pass, as the event it is said as, and what it names: each source it revised, each state it changed.
pub const REVISED: &str = "http://example.org/orexis/belief#Revised";
pub const REVISED_SOURCE: &str = "http://example.org/orexis/belief#revised";
pub const CHANGED: &str = "http://example.org/orexis/belief#changed";
/// What belief does as an activity, and what starts it: each graph to revise, and the kind its revisions are to be.
pub const REVISING: &str = "http://example.org/orexis/belief#Revising";
pub const REVISING_TRIGGER: &str = "http://example.org/orexis/belief#RevisingTrigger";
pub const REVISES: &str = "http://example.org/orexis/belief#revises";
pub const INTO: &str = "http://example.org/orexis/belief#into";
pub const DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

/// Where the revisions of `source` — what the rules conclude of it — are kept.
pub fn revision_graph(source: &str) -> String {
    format!("{source}/revisions")
}

/// Where what the transitions `arrival` triggered inserted is kept: the state graph the runner prepares for them,
/// one per arrival of testimony.
pub fn state_graph(arrival: &str) -> String {
    format!("{arrival}/believed")
}

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("belief", include_str!("../ontology.ttl")));

/// A FIGURE OF THE ROLE THIS PACKAGE IS LOADED FOR: what a role the self plays says of `term` in the agent's self
/// graph, read by this package's own query, and where no role says it the default this ontology states. Two
/// answers are never picked between: several, or one that is no number, is the default, said in the log.
pub fn figure_of(store: &orexis::store::Store, term: &str) -> Result<f64, orexis::Error> {
    use orexis::bind::{Value, bind};
    use orexis::store::{Within, value};
    let selves = store.graphs_of(&[orexis::ontology::SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let text = bind(
        "SELECT ?n WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role $figure ?n }",
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
