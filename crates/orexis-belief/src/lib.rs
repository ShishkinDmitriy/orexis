//! BELIEF, in Rust, ported from `crates/orexis-belief/`:
//!
//! - [`transition`]: rules that change a state rather than conclude of it, and the one machine that applies them,
//!   which planning applies an action's effect by;
//! - `revise`: what the rules conclude of one graph, its revisions;
//! - `trigger`: the transitions an arrival of testimony triggers, applied to the agent's own state;
//! - `deliberator`: the pass that sequences the two over what was written, within a budget;
//! - [`create`]: the package's part, which revises what is written as it is written.

pub mod create;
mod deliberator;
pub mod ontology;
mod revise;
pub mod transition;
mod trigger;

pub use deliberator::{Deliberator, Revised};
