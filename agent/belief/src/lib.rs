//! BELIEF, in Rust, ported from `agent/belief/` as its readers arrive:
//!
//! - [`transition`]: rules that change a state rather than conclude of it, and the one machine that applies them,
//!   which planning applies an action's effect by.

pub mod ontology;
pub mod transition;
