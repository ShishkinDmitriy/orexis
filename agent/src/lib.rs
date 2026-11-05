//! THE KERNEL, in Rust: what every package meets at, ported from the Python kernel beside it one function at a
//! time and held to the same cases (knowledge/decisions/the-agent-moves-to-rust-one-package-at-a-time.md).
//!
//! - [`namespaces`]: every prefix the tree's ontologies declare, found by looking, one label one IRI;
//! - [`bind`]: a rule text's `$tokens` bound to the terms they are, refusing a token nobody bound;
//! - [`store`]: the engine, every text parsed once, and the catalogue that says what each graph is;
//! - [`clock`]: the one timeline, which may run fast;
//! - [`ontology`]: the kernel's terms code may name (rule 1: a T-Box term, never an instance).

pub mod bind;
pub mod clock;
pub mod error;
pub mod namespaces;
pub mod ontology;
pub mod store;

pub use error::Error;
