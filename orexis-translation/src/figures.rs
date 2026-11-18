//! THE FIGURES THIS PACKAGE RUNS BY, each its own word, and the defaults its ontology states, for a model's client made
//! with no role to read (knowledge/domain/kernel/role.md); the translator reads its role's off the store.

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("translation", include_str!("../ontology.ttl")));

/// THE FIGURES A TRANSLATOR'S ROLE MAY STATE, each its own word.
pub const TURNS: &str = "http://example.org/orexis/translation#turns";
pub const ROWS: &str = "http://example.org/orexis/translation#rows";
pub const ANSWERED_WITHIN_S: &str = "http://example.org/orexis/translation#answeredWithinS";
