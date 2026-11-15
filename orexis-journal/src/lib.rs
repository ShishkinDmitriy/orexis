//! THE JOURNAL, KEPT: the half of the pair that does the work. Where the agent keeps a journal, this hears everything
//! its packages say and writes what happened there as it happens: each event that states triples, as an entry in its
//! package's words (`events`), and each activity as it ends, in PROV's words, with what started it and what it
//! generated (`activities`). It has no task; what it keeps it keeps as it is said. It knows no package's words.
//!
//! LOADED FOR A ROLE, as every package is: an agent keeps a journal where its self graph says it plays a
//! `journal:Recorder` (`ontology.ttl`), and where it plays none its packages say what happens and nobody writes it
//! down. The kernel knows no journal: an event may state triples (`Event::statements`), and that is all it says.
//!
//! The journal itself is here too (`journal`): the store, its window and its incidents. What ships the activities to
//! a tracer is the other half, `orexis-journal-otlp/`, which reads them here on a timer. A reading's point in the
//! series is neither's: what archives sensing's readings writes it (`orexis-sensing-influxdb/`).
//!
//! - [`role`]: the role the package is loaded for and what it says, read as one struct with its ontology's defaults;
//! - [`create`]: the package's start, which every package this binary holds is given, and its task.

pub mod activities;
pub mod create;
pub mod events;
pub mod journal;
pub mod role;

pub use create::{Keeps, Traced};
pub use journal::Journal;
