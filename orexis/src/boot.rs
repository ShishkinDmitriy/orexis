//! THE BOOT: one agent's store from the world's documents and the documents its packages bring, in three steps.
//! BEGUN (`begin`): the kernel's T-Box, compiled into the kernel, and the world's documents, read off the disk, go
//! in, the vocabulary first and closed, so that what a graph is is the vocabulary's to say and a graph of a kind it
//! does not declare is passed over; then who the agent is, by the one identifier the process is told, and THE SELF,
//! checked and never minted. A volume lived in forgets every common graph and reads the documents again, and keeps
//! the agent's own.
//!
//! JOINED, PACKAGE BY PACKAGE (`Begun::bring`): each package this binary holds decides in its own start whether the
//! agent runs it — by the role the self plays, which the package knows as its own, or by what it needs of the world —
//! and one that joins brings its documents, compiled in beside its code (`task::Package::documents`): they are put
//! in, the vocabulary closed again, and the world's graphs passed over until now offered again. The kernel names no
//! package and no role, and knows no package's reason to join (`task::Handed::joins`).
//!
//! FINISHED (`Begun::finish`), once every package has decided: a role the self plays that no package of this binary
//! declares is refused, the graphs that say they are this agent's are put in, and each graph's row is stamped.
//!
//! Writing the scopes is planning's, which the kernel names nothing of: whoever boots an agent that plans says so.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use oxigraph::model::Literal;

use crate::Error;
use crate::bind::{Value, bind};
use crate::document::Document;
use crate::hash::hash_named_graph;
use crate::ontology::{
    BELIEF, CATALOGUE_GRAPH, CLOSURE_GRAPH, DERIVED, GRAPH, ONTOLOGY, ROLE, SELF_GRAPH, SOCIETY_GRAPH, WORLD_GRAPH,
};
use crate::store::{Store, Within, iri};
use crate::task::Package;

/// The tree this kernel was built from: the repo's root, where a test finds the worlds and the cases. The boot reads
/// nothing of it.
pub const TREE: &str = env!("OREXIS_CRATES");

/// THE KERNEL'S CRATE, and every package's is named after it.
const KERNEL: &str = "orexis";

/// THE KERNEL'S T-BOX, compiled in, as each package's documents are.
const KERNEL_VOCABULARY: &str = include_str!("../ontology.ttl");

/// A PACKAGE'S CRATE: `transport/mqtt` is `orexis-transport-mqtt`.
pub fn crate_of(package: &str) -> String {
    format!("{KERNEL}-{}", package.replace('/', "-"))
}

/// THE NAME OF THE GRAPH A BROUGHT DOCUMENT IS: the file `name` of `krate`, which is no file where the agent runs, so
/// it is named for the crate and the file and not for a place on a disk. A name is for eyes.
pub fn brought_uri(krate: &str, name: &str) -> String {
    format!("urn:orexis:{krate}/{name}")
}

/// The document `name` of `krate` as it was compiled in, with the path it is told apart by: never one under a world.
fn brought(krate: &str, name: &str, text: &str) -> Result<(PathBuf, Document), Error> {
    let doc = Document::brought(&format!("{krate}/{name}"), text, &brought_uri(krate, name))?;
    Ok((PathBuf::from(krate).join(name), doc))
}

/// The package that registered itself as `name`, where this binary holds it.
fn registered(name: &str) -> Option<&'static Package> {
    inventory::iter::<Package>().find(|p| p.name == name)
}

const DOCUMENTS: [&str; 2] = ["ttl", "trig"];
const SECRETS: &str = "secrets";
const BELIEFS: &str = "beliefs";
const VOCABULARY: &str = "ontology.ttl";

/// THE ORDER THE PACKAGES START IN, and every package this binary holds is ordered by it: what keeps the journal and
/// what watches first, so that what the others say as they start is heard, then the order a pass ran the parts in.
pub const PASS: &[&str] = &[
    "journal",
    "journal-oxigraph",
    "journal-otlp",
    "metrics",
    "sensing-influxdb",
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

const ME_Q: &str = "SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id }";
const PLAYED_Q: &str = "SELECT ?role ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }";
const AGENTS_Q: &str = "SELECT DISTINCT ?a WHERE { ?a a orexis:Agent }";
const SELVES_Q: &str = "SELECT DISTINCT ?self WHERE { GRAPH ?g { ?self a orexis:Self } } ORDER BY ?self";
const ASSERTED_Q: &str =
    "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g orexis:arrivedBy orexis:Asserted } }";
/// WHAT A BOOT PUT IN AND NOBODY HOLDS: asserted from a document, with no owner, and the closure.
const FILES_Q: &str = "
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  { ?g orexis:arrivedBy orexis:Asserted FILTER NOT EXISTS { ?g orexis:ownedBy ?who } }
  UNION { VALUES ?g { $closure } ?g orexis:arrivedBy ?any } FILTER(?g != ?cat) } }";

/// What the boot reads: the world, and the agent it was told to be.
pub struct Booting<'a> {
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

/// Every package this binary holds, in the order they start, and any the order does not name after, by its name.
pub fn every_package() -> Vec<String> {
    let mut found: Vec<String> = inventory::iter::<Package>()
        .map(|p| p.name.to_string())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    found.sort_by_key(|p| (PASS.iter().position(|q| q == p).unwrap_or(PASS.len()), p.clone()));
    found
}

/// What a boot reads first off the disk: the world's directory, the agent's own `secrets/<agent>/`, and `beliefs/`.
/// Found by looking, never listed.
fn documents(booting: &Booting<'_>) -> Vec<PathBuf> {
    let mut out = under(booting.world);
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

/// Every class `kind` is: itself, and each it is beneath by the closure the store holds.
fn is_a(store: &Store, kind: &str, class: &str) -> Result<bool, Error> {
    Ok(kind == class || store.closed(kind)?.iter().any(|c| c == class))
}

/// WHETHER THE SELF PLAYS A ROLE of one of `classes` — read off the self graph alone, by the vocabulary the store
/// holds as it is asked: a role's class beneath one of them counts, where an ontology in the store says so. What a
/// package asks of its own role as it starts (`task::Handed::plays`).
pub fn plays(store: &Store, classes: &[&str]) -> Result<bool, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    for row in store.rows(PLAYED_Q, &selves)? {
        if let Some(kind) = iri(&row, "kind") {
            for class in classes {
                if is_a(store, &kind, class)? {
                    return Ok(true);
                }
            }
        }
    }
    Ok(false)
}

/// WHETHER THE WORLD WIRES THE SELF THROUGH A TRANSPORT: one of `wired` holds, each a role's class the self plays
/// with a pattern about `?me` the common beliefs and the self graph answer, in the `words` the transport declares.
/// What a transport member asks as it starts: the kernel names no transport and no pattern.
pub fn wired(store: &Store, words: &str, wired: &[(&str, &str)]) -> Result<bool, Error> {
    let mut known = store.graphs_of(&[BELIEF], &Within::common())?;
    known.extend(store.graphs_of(&[SELF_GRAPH], &Within::default())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    for (role, pattern) in wired {
        if plays(store, &[role])? && store.ask(&format!("{words}ASK {{ ?me a orexis:Self . {pattern} }}"), &known)? {
            return Ok(true);
        }
    }
    Ok(false)
}

/// A ROLE THE SELF PLAYS THAT NO PACKAGE OF THIS BINARY DECLARES: the role's classes, none beneath `orexis:Role` by
/// the vocabulary the store holds once every package has decided. Its package was built out, and with it the
/// ontology that would have said so.
fn unserved(store: &Store) -> Result<Vec<String>, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let mut kinds: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for row in store.rows(PLAYED_Q, &selves)? {
        if let (Some(role), Some(kind)) = (iri(&row, "role"), iri(&row, "kind")) {
            kinds.entry(role).or_default().push(kind);
        }
    }
    let mut out = Vec::new();
    for (role, kinds) in kinds {
        let mut served = false;
        for kind in &kinds {
            served |= kind != ROLE && is_a(store, kind, ROLE)?;
        }
        if !served {
            out.push(format!("{role} ({})", kinds.join(", ")));
        }
    }
    Ok(out)
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

/// A BOOT BEGUN: what was read and what is still to be put, held while the packages decide.
pub struct Begun {
    world: PathBuf,
    agent: String,
    lived_in: bool,
    read: Vec<(PathBuf, Document)>,
    passed: Vec<Held>,
    own: Vec<(Held, String)>,
    me: String,
    self_graph: String,
}

/// BEGIN THE BOOT of `booting.agent` into `store`: the kernel's vocabulary and the world's documents, and the self.
pub fn begin(store: &Store, booting: &Booting<'_>) -> Result<Begun, Error> {
    let world = fs::canonicalize(booting.world)?;
    let booting = Booting {
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
    let mut read = vec![brought(KERNEL, VOCABULARY, KERNEL_VOCABULARY)?];
    read.extend(read_with_imports(&documents(&booting))?);
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
    let agent = booting.agent.to_string();
    Ok(Begun {
        world,
        agent,
        lived_in,
        read,
        passed,
        own,
        me,
        self_graph,
    })
}

impl Begun {
    /// `package` JOINS: the documents it brings are put in, the vocabulary closed again, and every graph of the
    /// world passed over until now is offered again, since a kind this package declares is now one the agent reads.
    pub fn bring(&mut self, store: &Store, package: &str) -> Result<(), Error> {
        let documents = registered(package).map(|p| p.documents).unwrap_or_default();
        if documents.is_empty() {
            return Ok(());
        }
        let offset = self.read.len();
        for (name, text) in documents {
            self.read.push(brought(&crate_of(package), name, text)?);
        }
        let all: Vec<&Document> = self.read.iter().map(|(_, d)| d).collect();
        let passed = std::mem::take(&mut self.passed);
        let (also, still) = put(store, &self.world, &self.read[offset..], passed, offset, &all)?;
        let also = owned(store, also, &all)?;
        self.passed = still;
        self.own.extend(also);
        store.close_catalogue()
    }

    /// EVERY PACKAGE HAS DECIDED, and `loaded` joined: the boot is finished.
    pub fn finish(self, store: &Store, loaded: &[String]) -> Result<(), Error> {
        let unserved = unserved(store)?;
        if !unserved.is_empty() {
            return Err(Error::Evaluation(format!(
                "{} plays a role no package of this binary declares: {}",
                self.agent,
                unserved.join("; ")
            )));
        }
        if loaded.is_empty() {
            log::warn!("{} is joined by no package, and runs nothing", self.agent);
        } else {
            log::info!("{} loads {}", self.agent, loaded.join(", "));
        }
        for (path, _, graph, kinds) in &self.passed {
            log::debug!(
                "passed over {graph} of {}: {} is no kind this agent reads",
                path.display(),
                kinds.iter().cloned().collect::<Vec<_>>().join(", ")
            );
        }
        if !self.lived_in {
            for (held, owner) in &self.own {
                if *owner == self.me && held.2 != self.self_graph {
                    store.put_document(
                        &self.read[held.1].1,
                        Some(&self.me),
                        Some(&[held.2.as_str()]),
                        None,
                        false,
                    )?;
                }
            }
        }
        store.close_catalogue()?;
        stamp(store)?;
        log::info!(
            "{} booted from {}{}",
            self.agent,
            self.world.display(),
            if self.lived_in {
                " (a volume lived in: its own graphs kept)"
            } else {
                ""
            }
        );
        Ok(())
    }
}

/// BOOT `booting.agent` into `store`, and answer the packages that joined, in the order they start: begun, each
/// package this binary holds asked in its own start whether the agent runs it (`task::decide`), and finished. No
/// package's core is made and no task started: that is `task::start`, over the packages this answers.
pub fn boot(store: &Store, booting: &Booting<'_>) -> Result<Vec<String>, Error> {
    let begun = begin(store, booting)?;
    crate::task::decide(store, booting.agent, begun)
}
