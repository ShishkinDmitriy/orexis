//! What the kernel refuses, by name, so a caller can tell a text that will not parse from a catalogue that
//! says two things.

use std::fmt;

#[derive(Debug)]
pub enum Error {
    /// Two ontologies bind one label to two IRIs, or one binds a kernel label to another.
    Namespace(String),
    /// A rule text still carries `$tokens` after binding: their names, `$this` aside.
    Unbound(Vec<String>),
    /// A text the engine will not parse, with the text.
    Syntax(String),
    /// A text the engine parsed and could not evaluate.
    Evaluation(String),
    /// The catalogue is missing where a writer needs it, or two graphs say they are it.
    Catalogue(String),
    /// A document that will not load.
    Document(String),
    Io(std::io::Error),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Namespace(m)
            | Error::Syntax(m)
            | Error::Evaluation(m)
            | Error::Catalogue(m)
            | Error::Document(m) => f.write_str(m),
            Error::Unbound(names) => write!(
                f,
                "unbound in a rule text: {}",
                names.iter().map(|n| format!("${n}")).collect::<Vec<_>>().join(", ")
            ),
            Error::Io(e) => e.fmt(f),
        }
    }
}

impl std::error::Error for Error {}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Io(e)
    }
}
