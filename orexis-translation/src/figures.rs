//! THE FIGURES THIS PACKAGE RUNS BY: what a role the self plays says of each, and the default its ontology states
//! where none says (knowledge/domain/kernel/role.md).

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("translation", include_str!("../ontology.ttl")));

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

/// THE FIGURES A TRANSLATOR'S ROLE MAY STATE, each its own word.
pub const TURNS: &str = "http://example.org/orexis/translation#turns";
pub const ROWS: &str = "http://example.org/orexis/translation#rows";
pub const ANSWERED_WITHIN_S: &str = "http://example.org/orexis/translation#answeredWithinS";
pub const CALLED_WITHIN_S: &str = "http://example.org/orexis/translation#calledWithinS";
pub const RETRIES: &str = "http://example.org/orexis/translation#retries";

/// A figure for a part made where nothing is refused: what a role says, or the ontology's default, and the default
/// too where the store will not be read, said in the log.
pub fn figure(store: &orexis::store::Store, term: &str) -> f64 {
    figure_of(store, term).unwrap_or_else(|e| {
        log::warn!("{} is not read off the role: {e}", orexis::ontology::local_of(term));
        DEFAULTS
            .figure(term)
            .expect("translation's ontology states a default for each of its figures")
    })
}
