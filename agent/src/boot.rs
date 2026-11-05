//! THE BOOT: one agent's store from the world's documents, as `agent/runtime.py`'s `boot` builds it. The kernel's
//! T-Box and the world's documents go in, the vocabulary first and closed, so that what a graph is is the
//! vocabulary's to say and a graph of a kind it does not declare is passed over; then who the agent is, by the one
//! identifier the process is told, and THE SELF, checked and never minted; then the packages its roles call for —
//! each declared in its own ontology, read apart — and the world's graphs that say they are this agent's. A volume
//! lived in forgets every common graph and reads the documents again, and keeps the agent's own.
//!
//! Writing the scopes is planning's, which the kernel names nothing of: whoever boots an agent that plans says so
//! (`packages`).

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use oxigraph::model::{Literal, Term};

use crate::Error;
use crate::bind::{Value, bind};
use crate::document::Document;
use crate::hash::hash_named_graph;
use crate::ontology::{
    BELIEF, CATALOGUE_GRAPH, CLOSURE_GRAPH, DERIVED, GRAPH, ONTOLOGY, ROLE, SELF_GRAPH, SOCIETY_GRAPH, WORLD_GRAPH,
};
use crate::store::{Store, Within, iri};

/// The tree this kernel was built from: where its documents and its packages' are, unless a caller says another.
pub const TREE: &str = env!("CARGO_MANIFEST_DIR");

const DOCUMENTS: [&str; 2] = ["ttl", "trig"];
const SECRETS: &str = "secrets";
const BELIEFS: &str = "beliefs";
const VOCABULARY: &str = "ontology.ttl";

/// THE ORDER A PASS RUNS THE PARTS IN, and every package of the tree is ordered by it.
pub const PASS: &[&str] = &[
    "belief",
    "planning",
    "execution",
    "sensing",
    "prediction",
    "speech",
    "translation",
    "coordination",
    "transport/mqtt",
    "transport/http",
    "transport/telegram",
    "transport/email",
];

const SUBCLASS: &str = "http://www.w3.org/2000/01/rdf-schema#subClassOf";
const TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const CLASS: &str = "http://www.w3.org/2002/07/owl#Class";

const TERMS: &str = "http://example.org/orexis/";
const MINE: &str = "?me orexis:plays/sensing:sensor ?sensor .";
const IN_A_CHAT: &str = "?chat speech:participant ?me ; speech:channel ?channel . ";

/// A TRANSPORT IS NO ROLE: it is loaded where a loaded role needs bytes and the society wires a bus.
fn transports() -> Vec<(&'static str, Vec<(String, String)>)> {
    let observer = format!("{TERMS}sensing#Observer");
    let speaker = format!("{TERMS}speech#Speaker");
    let translator = format!("{TERMS}translation#Translator");
    vec![
        (
            "transport/mqtt",
            vec![
                (
                    observer.clone(),
                    format!("{MINE} ?sensor mqtt4ssn:observesTopic ?topic"),
                ),
                (speaker, "?me mqtt4ssn:listensToTopic ?topic".into()),
                (translator.clone(), format!("{IN_A_CHAT}?channel a mqtt4ssn:Topic")),
            ],
        ),
        (
            "transport/http",
            vec![(observer, format!("{MINE} ?sensor td:hasForm ?form"))],
        ),
        (
            "transport/telegram",
            vec![(translator.clone(), "?me telegram:hasBot ?bot".into())],
        ),
        (
            "transport/email",
            vec![(translator, format!("{IN_A_CHAT}?channel schema:email ?address"))],
        ),
    ]
}

const ME_Q: &str = "SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id }";
const DECLARED_Q: &str = "SELECT DISTINCT ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }";
const AGENTS_Q: &str = "SELECT DISTINCT ?a WHERE { ?a a orexis:Agent }";
const SELVES_Q: &str = "SELECT DISTINCT ?self WHERE { GRAPH ?g { ?self a orexis:Self } } ORDER BY ?self";
const ASSERTED_Q: &str =
    "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g orexis:arrivedBy orexis:Asserted } }";
/// WHAT A BOOT PUT IN AND NOBODY HOLDS: asserted from a document, with no owner, and the closure.
const FILES_Q: &str = "
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  { ?g orexis:arrivedBy orexis:Asserted FILTER NOT EXISTS { ?g orexis:ownedBy ?who } }
  UNION { VALUES ?g { $closure } ?g orexis:arrivedBy ?any } FILTER(?g != ?cat) } }";

/// What the boot reads: the tree, the world, and the agent it was told to be.
pub struct Booting<'a> {
    pub tree: &'a Path,
    pub world: &'a Path,
    pub agent: &'a str,
}

fn is_document(p: &Path) -> bool {
    p.is_file()
        && p.extension()
            .and_then(|e| e.to_str())
            .is_some_and(|e| DOCUMENTS.contains(&e))
}

fn under(directory: &Path) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = fs::read_dir(directory)
        .map(|entries| {
            entries
                .filter_map(|e| e.ok().map(|e| e.path()))
                .filter(|p| is_document(p))
                .collect()
        })
        .unwrap_or_default();
    out.sort();
    out
}

fn walk(directory: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = fs::read_dir(directory) else { return };
    let mut paths: Vec<PathBuf> = entries.filter_map(|e| e.ok().map(|e| e.path())).collect();
    paths.sort();
    for p in paths {
        if p.is_dir() {
            if p.file_name()
                .is_some_and(|n| n != "tests" && n != "target" && n != "src")
            {
                walk(&p, out);
            }
        } else if is_document(&p) {
            out.push(p);
        }
    }
}

/// Every package of the tree — each directory beneath the kernel's holding an `ontology.ttl`, its tests' apart — in
/// the order a pass runs their parts, and any the order does not name after, by its name.
pub fn every_package(tree: &Path) -> Vec<String> {
    let mut vocabularies = Vec::new();
    walk(tree, &mut vocabularies);
    let mut found: Vec<String> = vocabularies
        .iter()
        .filter(|p| p.file_name().is_some_and(|n| n == VOCABULARY))
        .filter_map(|p| {
            p.parent()?
                .strip_prefix(tree)
                .ok()
                .map(|r| r.to_string_lossy().replace('\\', "/"))
        })
        .filter(|r| !r.is_empty())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    found.sort_by_key(|p| (PASS.iter().position(|q| q == p).unwrap_or(PASS.len()), p.clone()));
    found
}

/// Every document in the directories of `packages`, their tests' cases apart.
fn documents_of(tree: &Path, packages: &[String]) -> Vec<PathBuf> {
    let mut out = Vec::new();
    for package in packages {
        walk(&tree.join(package), &mut out);
    }
    out
}

/// What a boot reads first: the kernel's T-Box, then the world's directory, the agent's own `secrets/<agent>/`, and
/// `beliefs/`. Found by looking, never listed.
fn documents(booting: &Booting<'_>) -> Vec<PathBuf> {
    let mut out = vec![booting.tree.join(VOCABULARY)];
    out.extend(under(booting.world));
    out.extend(under(&booting.world.join(SECRETS).join(booting.agent)));
    out.extend(under(&booting.world.join(BELIEFS)));
    out
}

fn path_of(iri: &str) -> Option<PathBuf> {
    let rest = iri.strip_prefix("file://")?;
    let mut bytes = Vec::new();
    let raw = rest.as_bytes();
    let mut i = 0;
    while i < raw.len() {
        if raw[i] == b'%'
            && i + 2 < raw.len()
            && let Ok(b) = u8::from_str_radix(&rest[i + 1..i + 3], 16)
        {
            bytes.push(b);
            i += 3;
            continue;
        }
        bytes.push(raw[i]);
        i += 1;
    }
    Some(PathBuf::from(String::from_utf8_lossy(&bytes).into_owned()))
}

/// Every document `paths` names and every one they import, each read once, in the order met.
fn read_with_imports(paths: &[PathBuf]) -> Result<Vec<(PathBuf, Document)>, Error> {
    let (mut read, mut seen) = (Vec::new(), BTreeSet::new());
    let mut queue: std::collections::VecDeque<PathBuf> =
        paths.iter().filter_map(|p| fs::canonicalize(p).ok()).collect();
    while let Some(path) = queue.pop_front() {
        if !seen.insert(path.clone()) {
            continue;
        }
        let doc = Document::read(&path)?;
        for import in doc.imports() {
            if let Some(p) = path_of(&import).and_then(|p| fs::canonicalize(p).ok()) {
                queue.push_back(p);
            }
        }
        read.push((path, doc));
    }
    Ok(read)
}

/// What every package's ontology says of roles, READ APART: each role a package declares, with the package, and
/// every `rdfs:subClassOf` step the packages' ontologies state.
type Vocabularies = (BTreeMap<String, String>, BTreeMap<String, BTreeSet<String>>);

fn vocabularies(tree: &Path) -> Result<Vocabularies, Error> {
    let mut above: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut declared: BTreeMap<String, String> = BTreeMap::new();
    for package in every_package(tree) {
        let doc = Document::read(&tree.join(&package).join(VOCABULARY))?;
        for q in doc.quads() {
            let oxigraph::model::NamedOrBlankNode::NamedNode(s) = &q.subject else {
                continue;
            };
            match (q.predicate.as_str(), &q.object) {
                (SUBCLASS, Term::NamedNode(o)) => {
                    above
                        .entry(s.as_str().to_string())
                        .or_default()
                        .insert(o.as_str().to_string());
                }
                (TYPE, Term::NamedNode(o)) if o.as_str() == CLASS => {
                    declared
                        .entry(s.as_str().to_string())
                        .or_insert_with(|| package.clone());
                }
                _ => {}
            }
        }
    }
    let roles = declared
        .into_iter()
        .filter(|(cls, _)| beneath(cls, &above, None).is_ok_and(|b| b.contains(ROLE)))
        .collect();
    Ok((roles, above))
}

/// `cls` and every class it is beneath, by the packages' own steps and, where a store is given, its closure.
fn beneath(
    cls: &str,
    steps: &BTreeMap<String, BTreeSet<String>>,
    store: Option<&Store>,
) -> Result<BTreeSet<String>, Error> {
    let (mut reached, mut frontier) = (BTreeSet::new(), vec![cls.to_string()]);
    while let Some(c) = frontier.pop() {
        if !reached.insert(c.clone()) {
            continue;
        }
        frontier.extend(steps.get(&c).into_iter().flatten().cloned());
        if let Some(store) = store {
            frontier.extend(store.closed(&c)?);
        }
    }
    Ok(reached)
}

/// Every role class the self plays — read off the self graph alone — that is beneath `orexis:Role`.
pub fn roles_of(store: &Store, tree: &Path) -> Result<BTreeSet<String>, Error> {
    let (_, steps) = vocabularies(tree)?;
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let mut reached = BTreeSet::new();
    for row in store.rows(DECLARED_Q, &selves)? {
        if let Some(kind) = iri(&row, "kind") {
            reached.extend(beneath(&kind, &steps, Some(store))?);
        }
    }
    let mut out = BTreeSet::new();
    for c in reached {
        if c != ROLE && beneath(&c, &steps, Some(store))?.contains(ROLE) {
            out.insert(c);
        }
    }
    Ok(out)
}

/// Every package the self loads, in the order a pass runs their parts: each whose ontology declares the class of a
/// role the self plays, and each transport a loaded role needs bytes from. Nothing where it plays no role.
pub fn packages_of(store: &Store, tree: &Path) -> Result<Vec<String>, Error> {
    let roles = roles_of(store, tree)?;
    let (serving, _) = vocabularies(tree)?;
    let mut loaded: BTreeSet<String> = serving
        .iter()
        .filter(|(r, _)| roles.contains(*r))
        .map(|(_, p)| p.clone())
        .collect();
    let mut known = store.graphs_of(&[BELIEF], &Within::common())?;
    known.extend(store.graphs_of(&[SELF_GRAPH], &Within::default())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    for (transport, needs) in transports() {
        for (role, pattern) in needs {
            if roles.contains(&role) && store.ask(&format!("ASK {{ ?me a orexis:Self . {pattern} }}"), &known)? {
                loaded.insert(transport.to_string());
            }
        }
    }
    Ok(every_package(tree).into_iter().filter(|p| loaded.contains(p)).collect())
}

/// Whether the vocabulary declares one of `kinds` a kind of graph.
fn known(store: &Store, kinds: &BTreeSet<String>) -> Result<bool, Error> {
    for kind in kinds {
        if store.closed(kind)?.iter().any(|c| c == GRAPH) {
            return Ok(true);
        }
    }
    Ok(false)
}

/// Every `rdfs:subClassOf` step the ontology graphs reach, into the closure graph, so that one step is every step.
fn close_vocabulary(store: &Store) -> Result<(), Error> {
    let vocabularies = store.graphs_of(&[ONTOLOGY], &Within::default())?;
    let using: String = vocabularies.iter().map(|g| format!("USING <{g}>\n")).collect();
    store.forget_graph(CLOSURE_GRAPH, Some(BELIEF))?;
    store.update(&format!(
        "INSERT {{ GRAPH <{CLOSURE_GRAPH}> {{ ?a rdfs:subClassOf ?c }} }}\n{using}WHERE  {{ ?a rdfs:subClassOf+ ?c FILTER(isIRI(?a) && isIRI(?c) && ?a != ?c) }}"
    ))?;
    store.classify(CLOSURE_GRAPH, ONTOLOGY, DERIVED, None, None, None)
}

/// One graph a document holds, passed over or to be put: its document's path, the document, the graph, its kinds.
type Held = (PathBuf, usize, String, BTreeSet<String>);

/// Put the vocabulary `read` holds and close it, then every common graph whose kind the vocabulary declares — a
/// graph from outside the world's directory, or one of the world's saying no owner. The world's graphs of an
/// agent's own, and what is still passed over.
fn put(
    store: &Store,
    world: &Path,
    read: &[(PathBuf, Document)],
    passed: Vec<Held>,
    offset: usize,
    all: &[&Document],
) -> Result<(Vec<Held>, Vec<Held>), Error> {
    let vocabulary: BTreeSet<usize> = read
        .iter()
        .enumerate()
        .filter(|(_, (_, doc))| doc.kinds().values().any(|k| k.contains(ONTOLOGY)))
        .map(|(i, _)| i)
        .collect();
    for i in &vocabulary {
        store.put_document(&read[*i].1, None, None, None, false)?;
    }
    close_vocabulary(store)?;
    let mut candidates = passed;
    for (i, (path, doc)) in read.iter().enumerate() {
        if vocabulary.contains(&i) {
            continue;
        }
        for (graph, kinds) in doc.kinds() {
            candidates.push((path.clone(), offset + i, graph, kinds));
        }
    }
    let (mut common, mut own, mut still) = (Vec::new(), Vec::new(), Vec::new());
    for held in candidates {
        if !known(store, &held.3)? {
            still.push(held);
            continue;
        }
        let doc = all[held.1];
        if !held.0.starts_with(world) || doc.whose(&held.2).is_none() {
            common.push(held);
        } else {
            own.push(held);
        }
    }
    for (_, d, graph, _) in &common {
        store.put_document(all[*d], None, Some(&[graph.as_str()]), None, false)?;
    }
    Ok((own, still))
}

/// Each graph of an agent's own with whose its document says it is — refused where that is no agent of the world.
fn owned(store: &Store, own: Vec<Held>, all: &[&Document]) -> Result<Vec<(Held, String)>, Error> {
    let graphs = store.graphs_of(&[SOCIETY_GRAPH, WORLD_GRAPH], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let agents: BTreeSet<String> = store
        .rows(AGENTS_Q, &graphs)?
        .iter()
        .filter_map(|r| iri(r, "a"))
        .collect();
    let mut out = Vec::new();
    for held in own {
        let owner = all[held.1].whose(&held.2).unwrap_or_default();
        if !agents.contains(&owner) {
            return Err(Error::Document(format!(
                "{} says it is {owner}'s, and the world states no such agent",
                held.2
            )));
        }
        out.push((held, owner));
    }
    Ok(out)
}

/// Who the agent is, off the society or the world, by the one identifier the process is told.
pub fn identity(store: &Store, agent: &str) -> Result<String, Error> {
    let graphs = store.graphs_of(&[SOCIETY_GRAPH, WORLD_GRAPH], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let text = bind(ME_Q, &[("id", Value::Term(Literal::new_simple_literal(agent).into()))])?;
    let found = store.rows(&text, &graphs)?;
    match found.as_slice() {
        [one] => iri(one, "me").ok_or_else(|| Error::Evaluation("an agent that is no IRI".into())),
        [] => Err(Error::Evaluation(format!("the world says nobody is '{agent}'"))),
        _ => Err(Error::Evaluation(format!(
            "the world says several agents are '{agent}'"
        ))),
    }
}

/// Every agent the store says is the self, in any graph, sorted.
pub fn selves(store: &Store) -> Result<Vec<String>, Error> {
    Ok(store
        .rows(SELVES_Q, &[])?
        .iter()
        .filter_map(|r| iri(r, "self"))
        .collect())
}

/// The self, checked and never minted: exactly one of the agent's own graphs is a self graph, put in where the store
/// holds no self, and the store's selves are that agent alone. The self graph's name.
fn hold_the_self(store: &Store, agent: &str, me: &str, mine: &[(&Document, &str)]) -> Result<String, Error> {
    let authored: Vec<&(&Document, &str)> = mine
        .iter()
        .filter(|(doc, g)| doc.kinds().get(*g).is_some_and(|k| k.contains(SELF_GRAPH)))
        .collect();
    let [(doc, graph)] = authored.as_slice() else {
        let said = if authored.is_empty() {
            format!("no self graph of the world says who '{agent}' is")
        } else {
            format!("{} self graphs of the world say who '{agent}' is", authored.len())
        };
        return Err(Error::Evaluation(format!(
            "{said}: a world authors one for each of its agents, and the boot checks it and never writes one"
        )));
    };
    if selves(store)?.is_empty() {
        store.put_document(doc, Some(me), Some(&[graph]), None, true)?;
    }
    let held = selves(store)?;
    if held != [me.to_string()] {
        return Err(Error::Evaluation(if held.len() == 1 {
            format!(
                "this store's self is {}, and the process was told to be '{agent}': a volume is one agent's",
                held[0]
            )
        } else {
            format!("this store says {} agents are the self: a self is one", held.len())
        }));
    }
    Ok(graph.to_string())
}

/// Every belief and every graph a document put, its row stamped with the hash of what it holds.
fn stamp(store: &Store) -> Result<(), Error> {
    let mut graphs: Vec<String> = store.graphs_of(&[BELIEF], &Within::default())?;
    for g in store.rows(ASSERTED_Q, &[])?.iter().filter_map(|r| iri(r, "g")) {
        if !graphs.contains(&g) {
            graphs.push(g);
        }
    }
    for g in graphs {
        hash_named_graph(store, &g, None)?;
    }
    Ok(())
}

/// The agent's store from the documents, into `store` — empty, or a volume lived in, whose own graphs are kept:
/// every graph classified by the document that holds it, the vocabulary closed, the catalogue closed. The packages
/// it loads, for whoever boots it to start their parts and say what is theirs at boot — planning its scopes.
pub fn boot(store: &Store, booting: &Booting<'_>) -> Result<Vec<String>, Error> {
    let world = fs::canonicalize(booting.world)?;
    let booting = Booting {
        tree: booting.tree,
        world: &world,
        agent: booting.agent,
    };
    let lived_in = store.catalogue()?.is_some();
    if lived_in {
        let text = bind(FILES_Q, &[("closure", Value::iri(CLOSURE_GRAPH))])?;
        for g in store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")) {
            store.forget_graph(&g, Some(BELIEF))?;
        }
    } else {
        store.update(&format!(
            "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}"
        ))?;
    }
    let read = read_with_imports(&documents(&booting))?;
    let docs: Vec<&Document> = read.iter().map(|(_, d)| d).collect();
    let (own, passed) = put(store, &world, &read, Vec::new(), 0, &docs)?;
    let own = owned(store, own, &docs)?;
    store.close_catalogue()?;
    let me = identity(store, booting.agent)?;
    let mine: Vec<(&Document, &str)> = own
        .iter()
        .filter(|(_, o)| *o == me)
        .map(|(h, _)| (docs[h.1], h.2.as_str()))
        .collect();
    let self_graph = hold_the_self(store, booting.agent, &me, &mine)?;
    let loaded = packages_of(store, booting.tree)?;
    let seen: BTreeSet<&PathBuf> = read.iter().map(|(p, _)| p).collect();
    let more: Vec<(PathBuf, Document)> = read_with_imports(&documents_of(booting.tree, &loaded))?
        .into_iter()
        .filter(|(p, _)| !seen.contains(p))
        .collect();
    let mut all: Vec<&Document> = docs.clone();
    all.extend(more.iter().map(|(_, d)| d));
    let (also, still) = if more.is_empty() {
        (Vec::new(), passed)
    } else {
        put(store, &world, &more, passed, read.len(), &all)?
    };
    let mut own = own;
    own.extend(owned(store, also, &all)?);
    let absent: Vec<&String> = loaded.iter().filter(|p| !booting.tree.join(p).is_dir()).collect();
    if !absent.is_empty() {
        return Err(Error::Evaluation(format!(
            "{} plays a role whose package this tree does not hold: {}",
            booting.agent,
            absent.iter().map(|p| p.as_str()).collect::<Vec<_>>().join(", ")
        )));
    }
    if loaded.is_empty() {
        log::warn!(
            "{} plays no role, so it loads no package and runs nothing",
            booting.agent
        );
    } else {
        log::info!("{} loads {}", booting.agent, loaded.join(", "));
    }
    for (path, _, graph, kinds) in &still {
        log::debug!(
            "passed over {graph} of {}: {} is no kind this agent reads",
            path.display(),
            kinds.iter().cloned().collect::<Vec<_>>().join(", ")
        );
    }
    if !lived_in {
        for (held, owner) in &own {
            if *owner == me && held.2 != self_graph {
                store.put_document(all[held.1], Some(&me), Some(&[held.2.as_str()]), None, false)?;
            }
        }
    }
    store.close_catalogue()?;
    stamp(store)?;
    log::info!(
        "{} booted from {}{}",
        booting.agent,
        world.display(),
        if lived_in {
            " (a volume lived in: its own graphs kept)"
        } else {
            ""
        }
    );
    Ok(loaded)
}
