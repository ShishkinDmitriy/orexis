//! EVERY NAMESPACE THE TREE DECLARES, found by looking at it and never listed: each `@prefix` line of every
//! `.ttl` under the agent's tree, as `agent/store.py` finds them, and the kernel's own few beside them.
//!
//! **ONE LABEL, ONE IRI**, across every ontology, refused otherwise: one package's query silently reading another's
//! terms is the quietest bug there is, and both spellings are valid SPARQL, so no engine could report it. And a
//! label the kernel binds is the kernel's: an ontology binding it elsewhere is refused too.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use regex::Regex;

use crate::Error;

/// The kernel's prefixes: the vocabularies it speaks in itself, provenance and time in PROV's and Dublin Core's words.
pub const KERNEL: &[(&str, &str)] = &[
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("owl", "http://www.w3.org/2002/07/owl#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
    ("sh", "http://www.w3.org/ns/shacl#"),
    ("prov", "http://www.w3.org/ns/prov#"),
    ("dcterms", "http://purl.org/dc/terms/"),
];

/// What a text may say a prefixed name in: label to namespace.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Namespaces(BTreeMap<String, String>);

impl Namespaces {
    /// Every prefix declared in the crates of `tree`, the agent's tree, and the kernel's: refused where a label means
    /// two IRIs. Only a crate is read, `orexis/` and each `orexis-*/` — never a domain or a world beside them — and in
    /// it neither the build's output nor the interpreter's caches. A CASE RUNNER'S, which holds a package alone to
    /// texts speaking any package's words; an agent's are `linked`.
    pub fn of_tree(tree: &Path) -> Result<Self, Error> {
        let mut files = Vec::new();
        for krate in crates(tree)? {
            files.extend(ttl_under(&krate)?);
        }
        files.sort();
        let mut texts = Vec::new();
        for path in files {
            texts.push((path.display().to_string(), fs::read_to_string(&path)?));
        }
        Namespaces::of_texts(texts.iter().map(|(origin, text)| (origin.as_str(), text.as_str())))
    }

    /// Every prefix declared in the documents this binary holds — the kernel's ontology and each document a package
    /// built into it brings — and the kernel's: what an agent's texts may spell, read off no disk.
    pub fn linked() -> Result<Self, Error> {
        let mut texts = vec![("orexis/ontology.ttl".to_string(), include_str!("../ontology.ttl"))];
        let mut packages: Vec<&crate::task::Package> = inventory::iter::<crate::task::Package>().collect();
        packages.sort_by_key(|p| p.name);
        for package in packages {
            for (name, text) in package.documents {
                texts.push((format!("{}/{name}", crate::boot::crate_of(package.name)), *text));
            }
        }
        Namespaces::of_texts(texts.iter().map(|(origin, text)| (origin.as_str(), *text)))
    }

    /// The prefixes `texts` declare, each text with where it is from, and the kernel's beside them.
    fn of_texts<'a>(texts: impl Iterator<Item = (&'a str, &'a str)>) -> Result<Self, Error> {
        let prefix = Regex::new(r"@prefix\s+([A-Za-z][\w.-]*):\s*<([^>]*)>").expect("a valid pattern");
        let mut found: BTreeMap<String, (String, String)> = BTreeMap::new();
        for (origin, text) in texts {
            for caps in prefix.captures_iter(text) {
                let (label, iri) = (caps[1].to_string(), caps[2].to_string());
                match found.get(&label) {
                    Some((prior, first)) if *prior != iri => {
                        return Err(Error::Namespace(format!(
                            "prefix '{label}' means <{prior}> in {first} and <{iri}> in {origin}. One label, one \
                             namespace — a query cannot mean both."
                        )));
                    }
                    Some(_) => {}
                    None => {
                        found.insert(label, (iri, origin.to_string()));
                    }
                }
            }
        }
        let mut out: BTreeMap<String, String> = found.into_iter().map(|(label, (iri, _))| (label, iri)).collect();
        for (label, iri) in KERNEL {
            if let Some(other) = out.get(*label).filter(|other| other.as_str() != *iri) {
                return Err(Error::Namespace(format!(
                    "prefix '{label}' is the kernel's, bound to <{iri}>, and an ontology binds it to <{other}>"
                )));
            }
            out.insert((*label).to_string(), (*iri).to_string());
        }
        Ok(Namespaces(out))
    }

    pub fn get(&self, label: &str) -> Option<&str> {
        self.0.get(label).map(String::as_str)
    }

    pub fn iter(&self) -> impl Iterator<Item = (&str, &str)> {
        self.0.iter().map(|(label, iri)| (label.as_str(), iri.as_str()))
    }

    pub fn len(&self) -> usize {
        self.0.len()
    }

    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }
}

/// THE CRATES OF THE TREE: `orexis/`, the kernel, and every `orexis-*/` beside it.
pub fn crates(tree: &Path) -> Result<Vec<PathBuf>, Error> {
    let mut out: Vec<PathBuf> = fs::read_dir(tree)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_dir())
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n == "orexis" || n.starts_with("orexis-"))
        })
        .collect();
    out.sort();
    Ok(out)
}

/// Every `.ttl` under `dir`, in path order, as Python's sorted `rglob` walks it.
fn ttl_under(dir: &Path) -> Result<Vec<PathBuf>, Error> {
    let mut out = Vec::new();
    let mut pending = vec![dir.to_path_buf()];
    while let Some(here) = pending.pop() {
        for entry in fs::read_dir(&here)? {
            let path = entry?.path();
            if path.is_dir() {
                if !matches!(
                    path.file_name().and_then(|n| n.to_str()),
                    Some("target" | "__pycache__")
                ) {
                    pending.push(path);
                }
            } else if path.extension().is_some_and(|e| e == "ttl") {
                out.push(path);
            }
        }
    }
    out.sort();
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tree(files: &[(&str, &str)]) -> tempdir::Dir {
        let dir = tempdir::Dir::new();
        for (name, text) in files {
            let path = dir.0.join(name);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, text).unwrap();
        }
        dir
    }

    #[test]
    fn every_prefix_the_tree_declares_is_found_and_the_kernels_beside_them() {
        let dir = tree(&[(
            "orexis-planning/ontology.ttl",
            "@prefix planning: <http://example.org/orexis/planning#> .\n",
        )]);
        let found = Namespaces::of_tree(&dir.0).unwrap();
        assert_eq!(found.get("planning"), Some("http://example.org/orexis/planning#"));
        assert_eq!(found.get("dcterms"), Some("http://purl.org/dc/terms/"));
    }

    #[test]
    fn one_label_bound_to_two_iris_is_refused() {
        let dir = tree(&[
            ("orexis-a/ontology.ttl", "@prefix x: <http://a.example/> .\n"),
            ("orexis-b/ontology.ttl", "@prefix x: <http://b.example/> .\n"),
        ]);
        let refused = Namespaces::of_tree(&dir.0).unwrap_err().to_string();
        assert!(refused.contains("prefix 'x' means <http://a.example/>"), "{refused}");
    }

    #[test]
    fn a_kernel_label_bound_elsewhere_is_refused() {
        let dir = tree(&[("orexis-a/ontology.ttl", "@prefix prov: <http://elsewhere.example/> .\n")]);
        assert!(
            Namespaces::of_tree(&dir.0)
                .unwrap_err()
                .to_string()
                .contains("is the kernel's")
        );
    }

    #[test]
    fn the_build_output_is_not_the_tree() {
        let dir = tree(&[("orexis/target/x.ttl", "@prefix x: <http://built.example/> .\n")]);
        assert_eq!(Namespaces::of_tree(&dir.0).unwrap().get("x"), None);
    }

    /// A directory of the test's own, removed when it is done.
    mod tempdir {
        use std::path::PathBuf;
        use std::sync::atomic::{AtomicUsize, Ordering};

        pub struct Dir(pub PathBuf);

        impl Dir {
            pub fn new() -> Self {
                static N: AtomicUsize = AtomicUsize::new(0);
                let path = std::env::temp_dir().join(format!(
                    "orexis-ns-{}-{}",
                    std::process::id(),
                    N.fetch_add(1, Ordering::SeqCst)
                ));
                std::fs::create_dir_all(&path).unwrap();
                Dir(path)
            }
        }

        impl Drop for Dir {
            fn drop(&mut self) {
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
    }
}
