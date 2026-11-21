//! THE KERNEL, in Rust: what every package meets at, ported from the Python kernel beside it one function at a
//! time and held to the same cases (knowledge/decisions/the-agent-moves-to-rust-one-package-at-a-time.md).
//!
//! - [`bind`]: a rule text's `$tokens` bound to the terms they are, refusing a token nobody bound;
//! - [`store`]: the engine, the texts it keeps parsed, and the catalogue that says what each graph is;
//! - [`clock`]: the one timeline, which may run fast;
//! - [`description`]: what a graph states, told by type from what it says of itself;
//! - [`hash`]: what a graph holds, as the digest the Python kernel writes, a world hashed within what is read;
//! - [`boot`]: one agent's store from its world's documents, its self checked, its roles' packages read;
//! - [`document`]: a file or a peer's bytes as a document that says what its graphs are, refused otherwise;
//! - [`events`]: what a package says happened, said whole to whoever watches the agent;
//! - [`series`]: the points an event answers, written to the store the environment names for their purpose;
//! - [`runtime`]: one agent's process, a lifecycle container for its packages' parts, run pass by pass;
//! - [`rdf`]: what a graph is built of — a node, a triple, a literal, a fresh name — and the one spelling of a number;
//! - [`ontology`]: the kernel's terms code may name (rule 1: a T-Box term, never an instance);
//! - [`snapshots`]: the case runner, holding a store to its `.trig` and `.diff` and writing the diff on request.

pub mod activity;
pub mod bind;
pub mod boot;
pub mod clock;
pub mod description;
pub mod document;
pub mod error;
pub mod events;
pub mod foresight;
pub mod hash;
pub mod ontology;
pub mod rdf;
pub mod series;
pub mod shape;
#[cfg(any(test, feature = "snapshots"))]
pub mod snapshots;
pub mod store;
pub mod task;

pub use error::Error;
