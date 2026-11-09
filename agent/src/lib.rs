//! THE KERNEL, in Rust: what every package meets at, ported from the Python kernel beside it one function at a
//! time and held to the same cases (knowledge/decisions/the-agent-moves-to-rust-one-package-at-a-time.md).
//!
//! - [`namespaces`]: every prefix the tree's ontologies declare, found by looking, one label one IRI;
//! - [`bind`]: a rule text's `$tokens` bound to the terms they are, refusing a token nobody bound;
//! - [`store`]: the engine, the texts it keeps parsed, and the catalogue that says what each graph is;
//! - [`clock`]: the one timeline, which may run fast;
//! - [`hash`]: what a graph holds, as the digest the Python kernel writes, a world hashed within what is read;
//! - [`boot`]: one agent's store from its world's documents, its self checked, its roles' packages read;
//! - [`document`]: a file or a peer's bytes as a document that says what its graphs are, refused otherwise;
//! - [`events`]: what a package says happened, said whole to whoever watches the agent;
//! - [`journal`]: what happened to the agent, in a triplestore of its own, and its log for a window;
//! - [`series`]: the points an event answers, written to the store the environment names for their purpose;
//! - [`runtime`]: one agent's process, a lifecycle container for its packages' parts, run pass by pass;
//! - [`transport`]: what is the same of every transport member — the inbox, a person's prose, what carries a chat;
//! - [`stance`]: a figure the agent states of itself in its self graph;
//! - [`ontology`]: the kernel's terms code may name (rule 1: a T-Box term, never an instance);
//! - [`snapshots`]: the case runner, holding a store to its `.trig` and `.diff` and writing the diff on request.

pub mod bind;
pub mod boot;
pub mod clock;
pub mod document;
pub mod error;
pub mod events;
pub mod foresight;
pub mod hash;
pub mod journal;
pub mod namespaces;
pub mod ontology;
pub mod runtime;
pub mod series;
#[cfg(any(test, feature = "snapshots"))]
pub mod snapshots;
pub mod stance;
pub mod store;
pub mod transport;

pub use error::Error;
