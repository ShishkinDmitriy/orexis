//! `derive_wants`: every desire judged, and a want minted for every cluster of what its met-test reads unmet — as
//! `agent/planning/derive_wants.py` mints them, and held to its cases. NOTHING STANDS BETWEEN A DESIRE AND A WANT
//! but the weighings the Planner wrote: a desire is weighed in every ground, and read across the grounds in order
//! a violation has a stretch, from the first ground it holds in to the first later one it does not. A want is
//! minted per cluster of them — by scope, by instance and by stretch, and where a holder's constraint can make two
//! instances' plans collide, the two as one. **IT WITHDRAWS NOTHING**: the answer is every want the desires imply,
//! and `withdraw` is handed it.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::sync::LazyLock;

use oxigraph::model::{Literal, NamedNode, Term};
use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::isoformat;
use orexis::ontology::{BELIEF, RECORD};
use orexis::store::{Store, Within, iri, value};

use crate::couplings::{Couplings, couplings};
use crate::find_scopes::{Scopes, find_scopes};
use crate::memo::Memo;
use crate::ontology::{DESIRE, SHAPES, WANT};
use crate::shapes::Shapes;
use crate::withdraw::forget_one;
use crate::world_at::{Asking, lexical, world_at};

pub const RECOGNIZED: &str = "http://example.org/orexis/planning#Recognized";
const MET_WHEN: &str = "http://example.org/orexis/planning#metWhen";
const UNMET_WHEN: &str = "http://example.org/orexis/planning#unmetWhen";
const ABOUT: &str = "http://example.org/orexis/planning#about";
const ESTIMATES: &str = "http://example.org/orexis/planning#estimates";
const KEYED_BY: &str = "http://example.org/orexis/planning#keyedBy";
const REOPENS: &str = "http://example.org/orexis/planning#reopens";
const RDFS_LABEL: &str = "http://www.w3.org/2000/01/rdf-schema#label";
const SH: &str = "http://www.w3.org/ns/shacl#";

/// WHAT A DESIRE SAYS, from the graphs of desires and wants: its met-test, its estimate, what it is about, its label.
const SAID_Q: &str = "
SELECT ?p ?o WHERE {
  GRAPH ?g { $desire ?p ?o
    FILTER(?p IN (planning:metWhen, planning:unmetWhen, planning:estimates, planning:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { planning:DesireGraph planning:WantGraph } } }";

/// WHAT THIS DERIVATION HAS MINTED UNDER ONE DESIRE, across all time: existence is not an instant question.
const STANDING_Q: &str = "
SELECT ?w WHERE {
  GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom $desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }
ORDER BY ?w";

/// EVERY GRAPH OF WANTS THE DERIVATION WROTE THAT HOLDS ONE WANT, and how many wants each holds.
const HOMES_Q: &str = "
SELECT ?g (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a planning:Want . ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }
GROUP BY ?g";

const DESIRES_Q: &str = "
SELECT DISTINCT ?holder ?desire WHERE {
  GRAPH ?g { ?holder planning:holds ?desire . ?desire a planning:Desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:DesireGraph } }
ORDER BY ?holder ?desire";

/// THE TIMELINE: every ground, earliest first.
const GROUNDS_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start";

/// WHAT ONE DESIRE'S WEIGHINGS SAY, ground by ground.
const TROUBLES_Q: &str = "
SELECT ?start ?g ?met ?instance ?constraint ?about ?offending WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $desire ; planning:weighs ?g .
    ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
    OPTIONAL { ?x planning:met ?met }
    OPTIONAL { ?x planning:violation ?v . ?v planning:instance ?instance .
               OPTIONAL { ?v planning:constraint ?constraint }
               OPTIONAL { ?v planning:about ?about }
               OPTIONAL { ?v planning:offending ?offending FILTER(isIRI(?offending)) } } } }
ORDER BY ?start ?instance ?constraint ?offending";

/// WHAT A NODE NAMES IN A GROUND, as the objects of its own facts.
const NAMES_Q: &str = "SELECT DISTINCT ?o WHERE { $node ?p ?o FILTER(isIRI(?o)) }";

static THIS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$this\b").expect("a valid pattern"));

/// One way a desire is failing, and the stretch it fails over: `at` the start of the earliest ground it reads unmet
/// in, `until` the start of the first later ground it reads met in.
#[derive(Clone, Debug)]
struct Witness {
    instance: String,
    constraint: String,
    about: Option<String>,
    key: Vec<String>,
    at: DateTime,
    until: Option<DateTime>,
    /// The key terms that placed it in its scope, where what it is about placed it nowhere.
    placed: Vec<String>,
}

/// A way of failing: the instance, the constraint, and the key.
type Way = (String, String, Vec<String>);

/// What a desire says, `(predicate, the engine's own term)`, sorted by predicate and the term's spelling.
type Said = Vec<(String, Term)>;

/// Mint a want under every desire for every cluster of what its met-test reads unmet, and answer with EVERY want
/// those desires imply — minted here or standing under the same name. `walking` is every want an intention walks,
/// with the instant its step in flight lands; `reopen` the walking wants the Planner reopened (#921).
pub fn derive_wants(
    store: &Store,
    now: DateTime,
    walking: &BTreeMap<String, DateTime>,
    reopen: &BTreeSet<String>,
) -> Result<BTreeSet<String>, Error> {
    let mut memo = Memo::default();
    let shapes = Shapes::of(
        store,
        &store.graphs_of(&[DESIRE, WANT, RECORD, SHAPES], &Within::default())?,
    )?;
    let scopes = find_scopes(store)?;
    let grounds: Vec<String> = store.rows(GROUNDS_Q, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let Some(present) = grounds.first() else {
        return Err(Error::Evaluation(
            "the store holds no ground — lay_ground has not run".into(),
        ));
    };
    let mut coupled: HashMap<String, Option<Couplings>> = HashMap::new();
    let mut wanted = BTreeSet::new();
    for (holder, desire) in desires_in(store)? {
        let Some(found) = troubles(store, &desire, scopes.as_ref(), &holder)? else {
            //  NOT JUDGED IS NOT MET: what stands under it is what it implies.
            wanted.extend(standing_under(store, &desire)?);
            continue;
        };
        if !coupled.contains_key(&holder) {
            let read = couplings(store, &holder, present, now, &mut memo)?;
            coupled.insert(holder.clone(), read);
        }
        let joins = coupled[&holder].as_ref();
        derive_under(
            store,
            &shapes,
            scopes.as_ref(),
            &holder,
            &desire,
            &found,
            now,
            joins,
            walking,
            reopen,
        )?;
        let said = said(store, &desire)?;
        let standing = standing_under(store, &desire)?;
        wanted.extend(named(
            &shapes,
            scopes.as_ref(),
            &desire,
            &said,
            &found,
            joins,
            &standing,
        )?);
    }
    Ok(wanted)
}

fn standing_under(store: &Store, desire: &str) -> Result<BTreeSet<String>, Error> {
    Ok(store
        .rows(&bind(STANDING_Q, &[("desire", Value::iri(desire))])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "w"))
        .collect())
}

#[allow(clippy::too_many_arguments)]
fn derive_under(
    store: &Store,
    shapes: &Shapes,
    scopes: Option<&Scopes>,
    holder: &str,
    desire: &str,
    found: &[Witness],
    now: DateTime,
    coupled: Option<&Couplings>,
    walking: &BTreeMap<String, DateTime>,
    reopen: &BTreeSet<String>,
) -> Result<Vec<String>, Error> {
    let standing = standing_under(store, desire)?;
    let said = said(store, desire)?;
    let clusters = clusters(scopes, found, coupled)?;
    let mut minted = Vec::new();
    for cluster in clusters {
        let about: Vec<String> = cluster
            .iter()
            .filter_map(|w| w.about.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instances: Vec<String> = cluster
            .iter()
            .map(|w| w.instance.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instance = (instances.len() == 1).then(|| instances[0].as_str());
        let keys = keys_of(&cluster);
        let child = name_of(shapes, desire, &said, &about, instance, &keys);
        let mut at = cluster
            .iter()
            .map(|w| w.at)
            .reduce(|a, b| if b < a { b } else { a })
            .unwrap_or(now);
        let until = if cluster.is_empty() || cluster.iter().any(|w| w.until.is_none()) {
            None
        } else {
            cluster
                .iter()
                .filter_map(|w| w.until)
                .reduce(|a, b| if b > a { b } else { a })
        };
        //  A WANT ALREADY STANDING FOR THIS CLUSTER IS LEFT ALONE, unless a belief arriving reopened it.
        if standing.contains(&child) && !reopen.contains(&child) {
            continue;
        }
        //  AND SO IS A WANT ALREADY ABOUT EVERY INSTANCE OF IT, unless reopened.
        let covering = if standing.contains(&child) {
            None
        } else {
            covering(shapes, &standing, &instances, &about)
        };
        if let Some(covering) = &covering
            && !reopen.contains(covering)
        {
            log::debug!("{child} is still pursued by {covering}, which is about every instance of it");
            continue;
        }
        let (reopened, why) = if standing.contains(&child) {
            unhome(store, &child)?;
            (vec![child.clone()], "the Planner reopened its untaken steps")
        } else if let Some(covering) = covering {
            (vec![covering], "the Planner reopened its untaken steps")
        } else {
            let walked: BTreeSet<String> = standing.iter().filter(|w| walking.contains_key(*w)).cloned().collect();
            let reopened = if coupled.is_some() {
                reopened(shapes, &walked, &instances, &about)
            } else {
                Vec::new()
            };
            (reopened, "a want a constraint couples to it has arrived")
        };
        if !reopened.is_empty() {
            let opens = reopened
                .iter()
                .map(|w| walking.get(w).copied().unwrap_or(now))
                .fold(at, |a, b| if b > a { b } else { a });
            if until.is_none_or(|u| u > opens) {
                at = opens;
            }
            log::info!("{child} reopens {}: {why}", reopened.join(", "));
        }
        if let Some(child) = mint(
            store, shapes, holder, desire, now, at, until, &said, &about, &instances, &keys, &reopened,
        )? {
            minted.push(child);
        }
    }
    Ok(minted)
}

/// Take `want` out of the graph of the stretch it was minted over: the graph goes where it held this want alone.
fn unhome(store: &Store, want: &str) -> Result<(), Error> {
    for r in store.rows(&bind(HOMES_Q, &[("want", Value::iri(want))])?, &[])? {
        let (Some(g), Some(n)) = (iri(&r, "g"), value(&r, "wants")) else {
            continue;
        };
        if n == "1" {
            store.forget_graph(&g, Some(BELIEF))?;
        } else {
            forget_one(store, &g, want)?;
        }
    }
    Ok(())
}

fn keys_of(cluster: &[Witness]) -> Vec<String> {
    cluster
        .iter()
        .flat_map(|w| w.placed.iter().cloned())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

/// The names the clusters of `found` come to — what minting would call them, or the standing want already about
/// every instance of a cluster. One namer for both halves.
fn named(
    shapes: &Shapes,
    scopes: Option<&Scopes>,
    desire: &str,
    said: &Said,
    found: &[Witness],
    coupled: Option<&Couplings>,
    standing: &BTreeSet<String>,
) -> Result<BTreeSet<String>, Error> {
    let mut out = BTreeSet::new();
    for cluster in clusters(scopes, found, coupled)? {
        let about: Vec<String> = cluster
            .iter()
            .filter_map(|w| w.about.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instances: Vec<String> = cluster
            .iter()
            .map(|w| w.instance.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instance = (instances.len() == 1).then(|| instances[0].as_str());
        let name = name_of(shapes, desire, said, &about, instance, &keys_of(&cluster));
        if standing.contains(&name) {
            out.insert(name);
        } else {
            out.insert(covering(shapes, standing, &instances, &about).unwrap_or(name));
        }
    }
    Ok(out)
}

fn subset(a: &[String], b: &[String]) -> bool {
    a.iter().all(|x| b.contains(x))
}

/// The standing want whose met-test targets every instance of a cluster about those instances themselves.
fn covering(shapes: &Shapes, standing: &BTreeSet<String>, instances: &[String], about: &[String]) -> Option<String> {
    if instances.is_empty() || !subset(about, instances) {
        return None;
    }
    standing
        .iter()
        .find(|want| {
            let held = targets(shapes, want);
            instances.iter().all(|i| held.contains(i))
        })
        .cloned()
}

/// The walking wants a cluster about `instances` reopens: each targeting fewer than all of them, and only those.
fn reopened(shapes: &Shapes, walking: &BTreeSet<String>, instances: &[String], about: &[String]) -> Vec<String> {
    if instances.len() < 2 || !subset(about, instances) {
        return Vec::new();
    }
    let wanted: BTreeSet<&String> = instances.iter().collect();
    walking
        .iter()
        .filter(|w| {
            let held = targets(shapes, w);
            !held.is_empty() && held.len() < wanted.len() && held.iter().all(|h| wanted.contains(h))
        })
        .cloned()
        .collect()
}

fn node(iri: &str) -> Term {
    NamedNode::new_unchecked(iri).into()
}

/// The instances a want is about, off the `sh:targetNode`s of the shape or avoided state it carries.
fn targets(shapes: &Shapes, want: &str) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for polarity in [MET_WHEN, UNMET_WHEN] {
        if let Some(shape) = shapes.value(&node(want), polarity) {
            for t in shapes.objects(&shape, &format!("{SH}targetNode")) {
                out.insert(spelled(&t));
            }
        }
    }
    out
}

/// A term's value as Python's `str(term)` of an rdflib term is: the IRI, the lexical form, a blank node's id.
fn spelled(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => n.as_str().to_string(),
        Term::Literal(l) => l.value().to_string(),
        Term::BlankNode(b) => b.as_str().to_string(),
        #[allow(unreachable_patterns)]
        other => other.to_string(),
    }
}

/// An instant as Python's `str(datetime)` spells it, which the coupled groups are ordered by.
fn py_str(at: Option<DateTime>) -> String {
    at.map_or("None".to_string(), |t| isoformat(t).replacen('T', " ", 1))
}

type GroupKey = (Option<String>, String, DateTime, Option<DateTime>);

/// The witnesses grouped by SCOPE, by instance and by stretch — and where a constraint can make two instances'
/// plans collide, the two as one. A witness its scope cannot place joins every group over its own stretch.
fn clusters(
    scopes: Option<&Scopes>,
    witnesses: &[Witness],
    coupled: Option<&Couplings>,
) -> Result<Vec<Vec<Witness>>, Error> {
    if witnesses.is_empty() {
        return Ok(Vec::new());
    }
    let Some(scopes) = scopes else {
        return Err(Error::Evaluation(
            "the store holds no scope graph — scope_actions has not run".into(),
        ));
    };
    let mut groups: Vec<(GroupKey, Vec<Witness>)> = Vec::new();
    let mut loose = Vec::new();
    for w in witnesses {
        let mut w = w.clone();
        let about: Vec<&str> = w.about.iter().map(String::as_str).collect();
        let mut placed = scopes.meet(about.iter().copied());
        w.placed = Vec::new();
        if placed.len() != 1 && !w.key.is_empty() {
            let narrowed = scopes.meet(about.iter().copied().chain(w.key.iter().map(String::as_str)));
            if narrowed.len() == 1 {
                placed = narrowed;
                w.placed = w.key.clone();
            }
        }
        let scope = (placed.len() == 1).then(|| placed.into_iter().next().expect("one"));
        if scope.is_some() || w.about.as_deref() == Some(w.instance.as_str()) {
            let key = (scope, w.instance.clone(), w.at, w.until);
            match groups.iter_mut().find(|(k, _)| *k == key) {
                Some((_, group)) => group.push(w),
                None => groups.push((key, vec![w])),
            }
        } else {
            loose.push(w);
        }
    }
    if let Some(coupled) = coupled
        && groups.len() > 1
    {
        groups = merged(groups, coupled);
    }
    if groups.is_empty() {
        return Ok(vec![loose]);
    }
    for w in loose {
        let shared: Vec<usize> = (0..groups.len())
            .filter(|&i| (groups[i].0.2, groups[i].0.3) == (w.at, w.until))
            .collect();
        let into: Vec<usize> = if shared.is_empty() {
            (0..groups.len()).collect()
        } else {
            shared
        };
        for i in into {
            groups[i].1.push(w.clone());
        }
    }
    Ok(groups.into_iter().map(|(_, g)| g).collect())
}

/// The groups a constraint couples merged, transitively: two of one scope over one stretch whose instances
/// `coupled.joins`, under the first's key in Python's order of the keys.
fn merged(groups: Vec<(GroupKey, Vec<Witness>)>, coupled: &Couplings) -> Vec<(GroupKey, Vec<Witness>)> {
    let spelled = |k: &GroupKey| {
        (
            k.0.clone().unwrap_or_else(|| "None".into()),
            k.1.clone(),
            py_str(Some(k.2)),
            py_str(k.3),
        )
    };
    let mut groups = groups;
    groups.sort_by_cached_key(|(k, _)| spelled(k));
    let mut parent: Vec<usize> = (0..groups.len()).collect();
    fn find(parent: &mut [usize], mut k: usize) -> usize {
        while parent[k] != k {
            parent[k] = parent[parent[k]];
            k = parent[k];
        }
        k
    }
    for i in 0..groups.len() {
        for j in i + 1..groups.len() {
            let (a, b) = (&groups[i].0, &groups[j].0);
            if (&a.0, a.2, a.3) == (&b.0, b.2, b.3) && coupled.joins(&a.1, &b.1) {
                let (ra, rb) = (find(&mut parent, i), find(&mut parent, j));
                if ra != rb {
                    parent[rb] = ra;
                }
            }
        }
    }
    let mut out: Vec<(usize, GroupKey, Vec<Witness>)> = Vec::new();
    let roots: Vec<usize> = (0..groups.len()).map(|i| find(&mut parent, i)).collect();
    for (i, (key, group)) in groups.into_iter().enumerate() {
        let root = roots[i];
        match out.iter_mut().find(|(r, _, _)| *r == root) {
            Some((_, _, held)) => held.extend(group),
            None => out.push((root, key, group)),
        }
    }
    out.into_iter().map(|(_, k, g)| (k, g)).collect()
}

/// What the desire says, sorted by predicate and the term's spelling.
fn said(store: &Store, desire: &str) -> Result<Said, Error> {
    let mut out: Said = store
        .rows(&bind(SAID_Q, &[("desire", Value::iri(desire))])?, &[])?
        .into_iter()
        .filter_map(|r| Some((iri(&r, "p")?, r.get("o")?.clone())))
        .collect();
    out.sort_by_cached_key(|(p, o)| (p.clone(), o.to_string()));
    Ok(out)
}

fn tail(iri: &str) -> &str {
    let tail = iri.rsplit('#').next().unwrap_or(iri);
    tail.rsplit('/').next().unwrap_or(tail)
}

/// The name of the want minted under `desire` for one cluster: the desire's, suffixed by the key that placed it,
/// what it is about where that is narrower than the desire, and the instance where the desire ranges over several.
fn name_of(
    shapes: &Shapes,
    desire: &str,
    said: &Said,
    about: &[String],
    instance: Option<&str>,
    keys: &[String],
) -> String {
    let declared: BTreeSet<String> = said
        .iter()
        .filter(|(p, _)| p == ABOUT)
        .map(|(_, o)| spelled(o))
        .collect();
    let abouts: BTreeSet<String> = about.iter().cloned().collect();
    let mut tails: Vec<&str> = keys.iter().map(|k| tail(k)).collect();
    if !about.is_empty() && abouts != declared {
        tails.extend(about.iter().map(|a| tail(a)));
    }
    if let Some(instance) = instance
        && !about.iter().any(|a| a == instance)
        && !targets_one_node(shapes, said)
    {
        tails.insert(0, tail(instance));
    }
    let mut out = format!("{desire}.pursued");
    for t in tails {
        out.push('.');
        out.push_str(t);
    }
    out
}

/// Does the desire's met-test name the one node it is about (`sh:targetNode`)?
fn targets_one_node(shapes: &Shapes, said: &Said) -> bool {
    said.iter().any(|(p, o)| {
        (p == MET_WHEN || p == UNMET_WHEN)
            && matches!(o, Term::NamedNode(_))
            && shapes.has(o, &format!("{SH}targetNode"))
    })
}

/// The graph the wants in trouble over ONE STRETCH live in, named for that stretch.
fn graph_of(agent: &str, at: DateTime, until: Option<DateTime>) -> String {
    let until = until.map_or("open".to_string(), stamp);
    format!("http://example.org/orexis/graph/pursued/{agent}/{}--{until}", stamp(at))
}

fn stamp(at: DateTime) -> String {
    isoformat(at).replace(':', "").replace('+', "p")
}

/// An instant as Python's `isoformat(timespec='minutes')` spells it.
fn to_the_minute(at: DateTime) -> String {
    let full = isoformat(at);
    let (date, time) = full.split_once('T').expect("an isoformat has a T");
    let zone = time.find(['+', '-']).map_or("", |i| &time[i..]);
    format!("{date}T{}{zone}", &time[..5])
}

/// A string as a SPARQL literal, quoted and escaped.
fn quoted(text: &str) -> String {
    let mut out = String::from("\"");
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Write one derived want: taken out of its stretch's graph and put back, the graph's row and its period once.
#[allow(clippy::too_many_arguments)]
fn write(
    store: &Store,
    agent: &str,
    uri: &str,
    holder: &str,
    desire: &str,
    label: &str,
    now: DateTime,
    at: DateTime,
    until: Option<DateTime>,
    points: &[(String, String)],
    shape: &[String],
) -> Result<(), Error> {
    let graph = graph_of(agent, at, until);
    let said_points: Vec<String> = points.iter().map(|(p, o)| format!("<{uri}> <{p}> <{o}> .")).collect();
    let found_at = format!(" ; prov:generatedAtTime \"{}\"^^xsd:dateTime", isoformat(now));
    let mut period = format!(" ; orexis:start \"{}\"^^xsd:dateTime", isoformat(at));
    if let Some(until) = until {
        period.push_str(&format!(" ; orexis:end \"{}\"^^xsd:dateTime", isoformat(until)));
    }
    let forget = bind(
        crate::withdraw::FORGET_ONE_U,
        &[("graph", Value::iri(graph.as_str())), ("want", Value::iri(uri))],
    )?;
    store.update(&format!(
        "{forget} ;
INSERT {{
  GRAPH <{graph}> {{
  <{holder}> planning:holds <{uri}> .
  <{uri}> a planning:Want{found_at} ;
      planning:state <{RECOGNIZED}> ;
      prov:wasDerivedFrom <{desire}> ;
      rdfs:label {label} .
  {points}
  {shape} }}
  GRAPH ?cat {{ <{graph}> a planning:WantGraph ; orexis:arrivedBy orexis:Derived ;
      orexis:ownedBy <{holder}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }}
         FILTER NOT EXISTS {{ GRAPH ?cat {{ <{graph}> dcterms:temporal ?held }} }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ planning:WantGraph rdfs:subClassOf ?kind }} }}",
        label = quoted(label),
        points = said_points.join(" "),
        shape = shape.join("\n  "),
    ))
}

/// Derive the want pursued under `desire` and write it — None, and the desire stays the goal, where the desire
/// states its met-test inline, since a blank node has no name another graph could point at.
#[allow(clippy::too_many_arguments)]
fn mint(
    store: &Store,
    shapes: &Shapes,
    holder: &str,
    desire: &str,
    now: DateTime,
    at: DateTime,
    until: Option<DateTime>,
    said: &Said,
    about: &[String],
    instances: &[String],
    keys: &[String],
    reopens: &[String],
) -> Result<Option<String>, Error> {
    let instance = (instances.len() == 1).then(|| instances[0].as_str());
    let child = name_of(shapes, desire, said, about, instance, keys);
    let mut points: Vec<(String, String)> = keys.iter().map(|k| (KEYED_BY.to_string(), k.clone())).collect();
    points.extend(reopens.iter().map(|w| (REOPENS.to_string(), w.clone())));
    let (mut met_test, mut estimate) = (None, None);
    for (p, o) in said {
        if matches!(o, Term::BlankNode(_)) {
            log::warn!("{} states its {} inline; it is pursued itself", tail(desire), tail(p));
            return Ok(None);
        }
        match p.as_str() {
            ABOUT | RDFS_LABEL => {}
            MET_WHEN | UNMET_WHEN => met_test = Some((p.clone(), spelled(o))),
            ESTIMATES => estimate = Some(spelled(o)),
            _ => points.push((p.clone(), spelled(o))),
        }
    }
    let mut shape_lines = Vec::new();
    if let Some((polarity, shape)) = met_test {
        let own = format!("{child}{}", if polarity == MET_WHEN { ".met" } else { ".avoided" });
        shape_lines = narrowed(shapes, &shape, &own, instances, about);
        points.push((polarity, own));
    }
    if let Some(estimate) = estimate {
        let own = format!("{child}.estimate");
        let lines = instantiated(shapes, &estimate, &own, instance)?;
        let pointed = if lines.is_empty() { estimate } else { own };
        shape_lines.extend(lines);
        points.push((ESTIMATES.to_string(), pointed));
    }
    let labels: Vec<String> = said
        .iter()
        .filter(|(p, _)| p == RDFS_LABEL)
        .map(|(_, o)| spelled(o))
        .collect();
    let named = labels
        .first()
        .cloned()
        .unwrap_or_else(|| desire.rsplit('#').next().unwrap_or(desire).to_string());
    let label = if at > now {
        format!("foreseen: {named} at {}", to_the_minute(at))
    } else {
        format!("pursued: {named}")
    };
    write(
        store,
        tail(holder),
        &child,
        holder,
        desire,
        &label,
        now,
        at,
        until,
        &points,
        &shape_lines,
    )?;
    log::info!("{} reads unmet: pursuing {}", tail(desire), tail(&child));
    Ok(Some(child))
}

fn line(s: &Term, p: &NamedNode, o: &Term) -> String {
    format!("{s} {p} {o} .")
}

/// The desire's met-test as THIS want's: the same shape under the want's own name, its targets the instances the
/// want is about, and only the blocks and constraints about what it is about. N-Triples lines.
fn narrowed(shapes: &Shapes, shape: &str, own: &str, instances: &[String], abouts: &[String]) -> Vec<String> {
    let targets = [
        "targetNode",
        "targetClass",
        "targetSubjectsOf",
        "targetObjectsOf",
        "target",
    ]
    .map(|t| format!("{SH}{t}"));
    let (property, sparql, this) = (format!("{SH}property"), format!("{SH}sparql"), format!("{SH}this"));
    let root = node(shape);
    let own_node = NamedNode::new_unchecked(own);
    let own_term: Term = own_node.clone().into();
    let cbd = shapes.cbd(&root);
    let keep: BTreeSet<&str> = abouts.iter().map(String::as_str).collect();
    let mut out: Vec<String> = Vec::new();
    let mut dropped: BTreeSet<String> = BTreeSet::new();
    let add = |l: String, out: &mut Vec<String>| {
        if !out.contains(&l) {
            out.push(l);
        }
    };
    for (p, o) in cbd.predicate_objects(&root) {
        if targets.iter().any(|t| t == p.as_str()) && !instances.is_empty() {
            continue;
        }
        if p.as_str() == property || p.as_str() == sparql {
            let mut about = cbd.value(&o, ABOUT).map(|a| spelled(&a));
            if about.as_deref() == Some(this.as_str()) {
                if !instances.is_empty() && !keep.is_empty() && !instances.iter().any(|i| keep.contains(i.as_str())) {
                    dropped.extend(cbd.cbd(&o).triples().iter().map(|(s, p, o)| line(s, p, o)));
                    continue;
                }
                about = None;
            }
            if !keep.is_empty()
                && let Some(about) = &about
                && !keep.contains(about.as_str())
            {
                dropped.extend(cbd.cbd(&o).triples().iter().map(|(s, p, o)| line(s, p, o)));
                continue;
            }
        }
        add(line(&own_term, &p, &o), &mut out);
    }
    let target = NamedNode::new_unchecked(format!("{SH}targetNode"));
    for instance in instances {
        add(line(&own_term, &target, &node(instance)), &mut out);
    }
    for (s, p, o) in cbd.triples() {
        let l = line(&s, &p, &o);
        if s != root && !dropped.contains(&l) {
            add(l, &mut out);
        }
    }
    out
}

/// The desire's estimate as THIS want's: its `sh:select` with `$this` bound to the one instance — nothing where the
/// want is about no one instance or the select never speaks of `$this`.
fn instantiated(shapes: &Shapes, estimate: &str, own: &str, instance: Option<&str>) -> Result<Vec<String>, Error> {
    let select = format!("{SH}select");
    let root = node(estimate);
    let (Some(instance), Some(text)) = (instance, shapes.value(&root, &select)) else {
        return Ok(Vec::new());
    };
    if !THIS.is_match(&spelled(&text)) {
        return Ok(Vec::new());
    }
    let own: Term = node(own);
    let mut out = Vec::new();
    for (p, o) in shapes.predicate_objects(&root) {
        let o = if p.as_str() == select {
            Literal::new_simple_literal(bind(&spelled(&o), &[("this", Value::iri(instance))])?).into()
        } else {
            o
        };
        let l = line(&own, &p, &o);
        if !out.contains(&l) {
            out.push(l);
        }
    }
    Ok(out)
}

fn desires_in(store: &Store) -> Result<Vec<(String, String)>, Error> {
    Ok(store
        .rows(DESIRES_Q, &[])?
        .iter()
        .filter_map(|r| Some((iri(r, "holder")?, iri(r, "desire")?)))
        .collect())
}

/// Every way `desire` is failing, each with the stretch it fails over — or None where any ground was not judged,
/// which is not the same as met. The key is what the offending value is keyed by in the ground it offended in: the
/// scope members among what it names, less what the violation is about, a member of every scope and the holder.
fn troubles(store: &Store, desire: &str, scopes: Option<&Scopes>, holder: &str) -> Result<Option<Vec<Witness>>, Error> {
    let found = store.rows(&bind(TROUBLES_Q, &[("desire", Value::iri(desire))])?, &[])?;
    if found.is_empty() || found.iter().any(|r| !r.contains_key("met")) {
        return Ok(None);
    }
    let mut read = Memo::default();
    let everywhere = scopes.map(Scopes::all).unwrap_or_default();
    let mut by_ground: BTreeMap<String, Vec<&orexis::store::Row>> = BTreeMap::new();
    for r in &found {
        if let Some(start) = value(r, "start") {
            by_ground.entry(start).or_default().push(r);
        }
    }
    let mut seen: Vec<(Way, Witness)> = Vec::new();
    let mut lifted: HashMap<Way, DateTime> = HashMap::new();
    let mut names: HashMap<(String, String), Vec<String>> = HashMap::new();
    for group in by_ground.values() {
        let at = lexical(&group[0]["start"])?;
        let mut unmet = BTreeSet::new();
        for r in group {
            let Some(instance) = iri(r, "instance") else { continue };
            let about = r.get("about").map(spelled);
            let constraint = r.get("constraint").map(spelled).unwrap_or_default();
            let mut keyed = Vec::new();
            if let (Some(scopes), Some(offending), Some(g)) = (scopes, iri(r, "offending"), iri(r, "g")) {
                let cached = names.get(&(g.clone(), offending.clone())).cloned();
                keyed = match cached {
                    Some(k) => k,
                    None => {
                        let world = world_at(store, Some(&g), &Asking::default(), &mut read)?;
                        let world: Vec<&str> = world.iter().map(String::as_str).collect();
                        let text = bind(NAMES_Q, &[("node", Value::iri(offending.as_str()))])?;
                        let mut named: BTreeSet<String> =
                            store.rows(&text, &world)?.iter().filter_map(|n| iri(n, "o")).collect();
                        named.insert(offending.clone());
                        let k: Vec<String> = named
                            .into_iter()
                            .filter(|o| {
                                scopes.0.get(o).is_some_and(|s| *s != everywhere)
                                    && Some(o) != about.as_ref()
                                    && o != holder
                            })
                            .collect();
                        names.insert((g, offending), k.clone());
                        k
                    }
                };
            }
            let key = (instance.clone(), constraint.clone(), keyed.clone());
            unmet.insert(key.clone());
            if !seen.iter().any(|(k, _)| *k == key) {
                seen.push((
                    key,
                    Witness {
                        instance,
                        constraint,
                        about,
                        key: keyed,
                        at,
                        until: None,
                        placed: Vec::new(),
                    },
                ));
            }
        }
        for (key, _) in &seen {
            if !unmet.contains(key) {
                lifted.entry(key.clone()).or_insert(at);
            }
        }
    }
    let mut out: Vec<Witness> = seen
        .into_iter()
        .map(|(k, mut w)| {
            w.until = lifted.get(&k).copied();
            w
        })
        .collect();
    out.sort_by(|a, b| {
        (a.at, &a.instance, &a.constraint, &a.key)
            .partial_cmp(&(b.at, &b.instance, &b.constraint, &b.key))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    Ok(Some(out))
}

#[cfg(test)]
mod tests;
