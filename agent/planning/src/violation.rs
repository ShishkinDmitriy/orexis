//! A WANT'S SHAPE, COMPILED INTO THE ONE SELECT WHOSE ROWS ARE ITS VIOLATIONS, as `agent/planning/violation.py`
//! compiles it: each SHACL Core constraint is a violation condition, and a condition is a pattern, so the select
//! is the union of them, one branch per constraint, each carrying the target so a `FILTER` inside it sees `?this`.
//! The other polarity, `planning:unmetWhen`, points at the avoided state's one select, which is put in the
//! report's shape unnegated.
//!
//! **COVERAGE IS EXACTLY WHAT THE PYTHON COPY COVERS, AND ANYTHING ELSE REFUSES**: a shape compiled to an empty
//! pattern would read as met for ever. The argument for each clause is the Python module's docstring; this
//! follows it clause for clause, the constraints numbered in the order the shapes graph hands them (`Shapes`),
//! and its terms written in full where the Python copy abbreviates them for eyes.

use std::collections::BTreeMap;
use std::sync::LazyLock;

use oxigraph::model::Term;
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::namespaces::Namespaces;

use crate::ontology::PLANNING;
use crate::shapes::Shapes;
use crate::terms::{RDF_FIRST, RDF_TYPE, SH, node};

fn sh(local: &str) -> String {
    format!("{SH}{local}")
}

/// What a property shape may carry in SHACL's namespace beside a constraint this compiles.
const PROPERTY_ANNOTATIONS: &[&str] = &["path", "message", "severity", "name", "description", "order", "group"];
/// What a node shape may carry in SHACL's namespace.
const NODE_ANNOTATIONS: &[&str] = &[
    "targetNode",
    "targetClass",
    "targetSubjectsOf",
    "targetObjectsOf",
    "target",
    "property",
    "sparql",
    "not",
    "or",
    "xone",
    "message",
    "severity",
    "name",
    "description",
    "deactivated",
    "class",
    "datatype",
    "nodeKind",
    "in",
    "hasValue",
    "minExclusive",
    "maxExclusive",
    "minInclusive",
    "maxInclusive",
];
/// What an avoided state may say in SHACL's namespace.
const AVOIDED_STATE_WORDS: &[&str] = &["select", "targetNode", "message"];
/// Value constraints a node shape may carry about its focus itself.
const NODE_VALUE_CONSTRAINTS: &[&str] = &[
    "class",
    "datatype",
    "nodeKind",
    "in",
    "hasValue",
    "minExclusive",
    "maxExclusive",
    "minInclusive",
    "maxInclusive",
];

static PREFIX_LINE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)PREFIX\s+([A-Za-z][\w.\-]*)?\s*:\s*<([^>]*)>").expect("a valid pattern"));
static THIS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\?this\b").expect("a valid pattern"));
static VALUE_PROJECTED: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[?$]value\b").expect("a valid pattern"));

/// A SHACL feature this compiler does not cover, named — never a want silently read as met.
#[derive(Debug)]
pub struct Unsupported(pub String);

impl std::fmt::Display for Unsupported {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

/// What a compile can end in: a refusal of the shape, or an error that is no refusal — a token nobody bound.
#[derive(Debug)]
pub enum Compiled {
    Unsupported(Unsupported),
    Error(Error),
}

impl From<Unsupported> for Compiled {
    fn from(u: Unsupported) -> Self {
        Compiled::Unsupported(u)
    }
}

impl From<Error> for Compiled {
    fn from(e: Error) -> Self {
        Compiled::Error(e)
    }
}

type Result<T> = std::result::Result<T, Compiled>;

/// One way a focus can violate a shape: the pattern, the offending value's variable, what the block is about.
type Alternative = (String, Option<String>, Option<Term>);

fn unsupported<T>(message: impl Into<String>) -> Result<T> {
    Err(Compiled::Unsupported(Unsupported(message.into())))
}

/// The select whose rows are `subject`'s violations, under whichever polarity it carries: `planning:metWhen` a
/// shape, `planning:unmetWhen` an avoided state. None where it carries neither; refused where it carries both.
pub fn select_of(shapes: &Shapes, subject: &Term, namespaces: &Namespaces) -> Result<Option<String>> {
    let shape = shapes.value(subject, &format!("{PLANNING}metWhen"));
    let avoided = shapes.value(subject, &format!("{PLANNING}unmetWhen"));
    match (shape, avoided) {
        (Some(_), Some(_)) => unsupported(format!(
            "{subject} carries both planning:metWhen and planning:unmetWhen"
        )),
        (None, None) => Ok(None),
        (Some(shape), None) => Compiler::new(shapes.cbd(&shape), namespaces).report(&shape),
        (None, Some(avoided)) => Compiler::new(shapes.cbd(&avoided), namespaces)
            .entered(&avoided)
            .map(Some),
    }
}

struct Compiler<'a> {
    g: Shapes,
    vars: usize,
    prefixes: BTreeMap<String, String>,
    namespaces: &'a Namespaces,
}

impl<'a> Compiler<'a> {
    fn new(g: Shapes, namespaces: &'a Namespaces) -> Self {
        Compiler {
            g,
            vars: 0,
            prefixes: BTreeMap::new(),
            namespaces,
        }
    }

    fn fresh(&mut self) -> String {
        let v = format!("?v{}", self.vars);
        self.vars += 1;
        v
    }

    fn declare(&mut self, name: &str, iri: &str) -> Result<()> {
        if let Some(known) = self.namespaces.get(name)
            && known != iri
        {
            return unsupported(format!(
                "a select declares {name}: as <{iri}>, and the store calls that prefix <{known}>"
            ));
        }
        if let Some(prior) = self.prefixes.get(name)
            && prior != iri
        {
            return unsupported(format!(
                "two selects declare {name}: differently — <{iri}> and <{prior}>"
            ));
        }
        if self.namespaces.get(name).is_none() {
            self.prefixes.insert(name.to_string(), iri.to_string());
        }
        Ok(())
    }

    fn preamble(&self) -> String {
        self.prefixes
            .iter()
            .map(|(name, iri)| format!("PREFIX {name}: <{iri}> "))
            .collect()
    }

    // --- the whole ------------------------------------------------------------------------------------------------

    fn report(&mut self, shape: &Term) -> Result<Option<String>> {
        let branches = self.report_branches(shape)?;
        if branches.is_empty() {
            return Ok(None);
        }
        Ok(Some(format!(
            "{}SELECT DISTINCT ?this ?_constraint ?_offending ?_about WHERE {{ {} }}",
            self.preamble(),
            branches.join(" UNION ")
        )))
    }

    fn report_branches(&mut self, shape: &Term) -> Result<Vec<String>> {
        if self.g.value(shape, &sh("deactivated")).is_some_and(|d| is_true(&d)) {
            return Ok(Vec::new());
        }
        let target = self.target(shape)?;
        let violation: Term = node(&sh("Violation"));
        let severity = self
            .g
            .value(shape, &sh("severity"))
            .unwrap_or_else(|| violation.clone());
        let mut branches = Vec::new();
        for (k, (text, value, about)) in self
            .alternatives(shape, "?this", Some(&severity), Some(&violation))?
            .into_iter()
            .enumerate()
        {
            for projected in ["?_constraint", "?_offending", "?_about"] {
                if text.contains(projected) || target.contains(projected) {
                    return unsupported(format!(
                        "{shape}: a select body binds {projected}, which the report projects"
                    ));
                }
            }
            let mut bound = value.map(|v| format!(" BIND({v} AS ?_offending)")).unwrap_or_default();
            match about {
                Some(a) if a == node(&sh("this")) => bound.push_str(" BIND(?this AS ?_about)"),
                Some(a) => bound.push_str(&format!(" BIND({} AS ?_about)", self.term(&a)?)),
                None => {}
            }
            branches.push(format!("{{ {target} {text} BIND({k} AS ?_constraint){bound} }}"));
        }
        Ok(branches)
    }

    fn entered(&mut self, node_: &Term) -> Result<String> {
        for (p, _) in self.g.predicate_objects(node_) {
            if is_shacl(p.as_str()) && !AVOIDED_STATE_WORDS.iter().any(|w| sh(w) == p.as_str()) {
                return unsupported(format!(
                    "{node_}: {p} on an avoided state is not compiled — an avoided state is the select whose rows \
                     are the instances in it, not a shape"
                ));
            }
        }
        let texts = self.g.objects(node_, &sh("select"));
        if texts.len() != 1 {
            return unsupported(format!(
                "{node_}: an avoided state carries one sh:select, and this carries {} — a node with none would \
                 read as met for ever",
                texts.len()
            ));
        }
        let text = lexical(&texts[0]);
        let body = self.body_of(&text, node_, "?this")?;
        for projected in ["?_constraint", "?_offending", "?_about"] {
            if body.contains(projected) {
                return unsupported(format!(
                    "{node_}: a select body binds {projected}, which the report projects"
                ));
            }
        }
        let mut parts = Vec::new();
        let targets = self.g.objects(node_, &sh("targetNode"));
        if !targets.is_empty() {
            let named: Vec<String> = targets.iter().map(|t| self.term(t)).collect::<Result<_>>()?;
            parts.push(format!("VALUES ?this {{ {} }}", named.join(" ")));
        }
        parts.push(body);
        parts.push("BIND(0 AS ?_constraint)".to_string());
        if VALUE_PROJECTED.is_match(text.split('{').next().unwrap_or("")) {
            parts.push("BIND(?value AS ?_offending)".to_string());
        }
        match self.g.value(node_, &format!("{PLANNING}about")) {
            Some(a) if a == node(&sh("this")) => parts.push("BIND(?this AS ?_about)".to_string()),
            Some(a) => parts.push(format!("BIND({} AS ?_about)", self.term(&a)?)),
            None => {}
        }
        Ok(format!(
            "{}SELECT DISTINCT ?this ?_constraint ?_offending ?_about WHERE {{ {} }}",
            self.preamble(),
            parts.join(" ")
        ))
    }

    fn target(&mut self, shape: &Term) -> Result<String> {
        let nodes = self.g.objects(shape, &sh("targetNode"));
        let classes = self.g.objects(shape, &sh("targetClass"));
        let subjects_of = self.g.objects(shape, &sh("targetSubjectsOf"));
        let objects_of = self.g.objects(shape, &sh("targetObjectsOf"));
        let mut parts = Vec::new();
        for t in self.g.objects(shape, &sh("target")) {
            if !self.g.holds(&t, RDF_TYPE, &node(&sh("SPARQLTarget"))) {
                return unsupported(format!("{shape}: a sh:target that is not a sh:SPARQLTarget"));
            }
            let text = self.g.value(&t, &sh("select")).map(|s| lexical(&s)).unwrap_or_default();
            parts.push(format!("{{ {} }}", self.body_of(&text, &t, "?this")?));
        }
        if nodes.is_empty() && classes.is_empty() && subjects_of.is_empty() && objects_of.is_empty() && parts.is_empty()
        {
            return unsupported(format!("{shape} targets nothing — whose state is it about?"));
        }
        if !nodes.is_empty() {
            let named: Vec<String> = nodes.iter().map(|n| self.term(n)).collect::<Result<_>>()?;
            parts.push(format!("VALUES ?this {{ {} }}", named.join(" ")));
        }
        for cls in &classes {
            parts.push(format!("?this a {} .", self.term(cls)?));
        }
        for p in &subjects_of {
            let v = self.fresh();
            parts.push(format!("?this {} {v} .", self.term(p)?));
        }
        for p in &objects_of {
            let v = self.fresh();
            parts.push(format!("{v} {} ?this .", self.term(p)?));
        }
        Ok(parts.join(" "))
    }

    // --- a node shape's violations, each an alternative -------------------------------------------------------------

    fn violations(&mut self, shape: &Term, focus: &str) -> Result<Vec<String>> {
        Ok(self
            .alternatives(shape, focus, None, None)?
            .into_iter()
            .map(|(text, _, _)| text)
            .collect())
    }

    /// Each way `focus` can violate `shape`: the pattern, the offending value's variable, and what the block says
    /// it is about. With `only`, an alternative whose severity is not `only` is left out.
    fn alternatives(
        &mut self,
        shape: &Term,
        focus: &str,
        severity: Option<&Term>,
        only: Option<&Term>,
    ) -> Result<Vec<Alternative>> {
        if self.g.has(shape, &sh("path")) {
            let found = self.property_violations(shape, focus)?;
            return Ok(self.about_each(shape, found));
        }
        for (p, _) in self.g.predicate_objects(shape) {
            if is_shacl(p.as_str()) && !NODE_ANNOTATIONS.iter().any(|w| sh(w) == p.as_str()) {
                return unsupported(format!("{shape}: <{}> on a node shape is not compiled", p.as_str()));
            }
        }
        let violation = node(&sh("Violation"));
        let mut out = Vec::new();
        let own = only.is_none() || severity == only;
        for prop in self.g.objects(shape, &sh("property")) {
            let stated = self
                .g
                .value(&prop, &sh("severity"))
                .unwrap_or_else(|| violation.clone());
            if only.is_none() || Some(&stated) == only {
                let found = self.property_violations(&prop, focus)?;
                out.extend(self.about_each(&prop, found));
            }
        }
        if own {
            for constraint in self.g.objects(shape, &sh("sparql")) {
                let body = self.sparql_body(&constraint, focus)?;
                out.push((body, None, self.g.value(&constraint, &format!("{PLANNING}about"))));
            }
            for (text, value) in self.value_violations(shape, focus)? {
                out.push((text, value, None));
            }
            for negated in self.g.objects(shape, &sh("not")) {
                out.push((self.conforms(&negated, focus)?, None, None));
            }
            for members in self.g.objects(shape, &sh("or")) {
                let mut filters = Vec::new();
                for m in self.g.list(&members) {
                    filters.push(format!("FILTER({})", self.violated(&m, focus)?));
                }
                out.push((filters.join(" "), None, None));
            }
            for members in self.g.objects(shape, &sh("xone")) {
                let shapes = self.g.list(&members);
                if shapes.len() != 2 {
                    return unsupported(format!("{shape}: sh:xone over {} shapes — only two", shapes.len()));
                }
                let (a, b) = (self.violated(&shapes[0], focus)?, self.violated(&shapes[1], focus)?);
                out.push((format!("FILTER(({a} && {b}) || (!({a}) && !({b})))"), None, None));
            }
        }
        Ok(out)
    }

    fn value_violations(&mut self, shape: &Term, focus: &str) -> Result<Vec<(String, Option<String>)>> {
        let mut out = Vec::new();
        for (p, o) in self.g.predicate_objects(shape) {
            let Some(local) = p.as_str().strip_prefix(SH) else {
                continue;
            };
            if !NODE_VALUE_CONSTRAINTS.contains(&local) {
                continue;
            }
            let text = match local {
                "class" => format!("FILTER NOT EXISTS {{ {focus} a {} }}", self.term(&o)?),
                "datatype" => format!("FILTER(!isLiteral({focus}) || datatype({focus}) != {})", self.term(&o)?),
                "nodeKind" => format!("FILTER({})", node_kind_violated(&o, focus, shape)?),
                "in" => format!("FILTER({focus} NOT IN ({}))", self.members(&o)?),
                "hasValue" => format!("FILTER({focus} != {})", self.term(&o)?),
                bound => format!("FILTER(!({focus} {} {}))", comparison(bound), self.term(&o)?),
            };
            out.push((text, None));
        }
        Ok(out)
    }

    fn violated(&mut self, shape: &Term, focus: &str) -> Result<String> {
        let alternatives = self.violations(shape, focus)?;
        if alternatives.is_empty() {
            return unsupported(format!("{shape} states no constraint this compiler knows"));
        }
        Ok(format!(
            "({})",
            alternatives
                .iter()
                .map(|a| format!("EXISTS {{ {a} }}"))
                .collect::<Vec<_>>()
                .join(" || ")
        ))
    }

    fn conforms(&mut self, shape: &Term, focus: &str) -> Result<String> {
        Ok(self
            .violations(shape, focus)?
            .into_iter()
            .map(|alt| match alt.strip_prefix("FILTER NOT EXISTS ") {
                Some(rest) => format!("FILTER EXISTS {rest}"),
                None => format!("FILTER NOT EXISTS {{ {alt} }}"),
            })
            .collect::<Vec<_>>()
            .join(" "))
    }

    fn about_each(&self, block: &Term, alternatives: Vec<(String, Option<String>)>) -> Vec<Alternative> {
        let about = self.g.value(block, &format!("{PLANNING}about"));
        alternatives.into_iter().map(|(t, v)| (t, v, about.clone())).collect()
    }

    fn property_violations(&mut self, prop: &Term, focus: &str) -> Result<Vec<(String, Option<String>)>> {
        let path_term = self.g.value(prop, &sh("path"));
        let path = self.path(path_term.as_ref())?;
        let mut out = Vec::new();
        for (p, o) in self.g.predicate_objects(prop) {
            let v = self.fresh();
            let p = p.as_str();
            let Some(local) = p.strip_prefix(SH) else {
                continue;
            };
            if PROPERTY_ANNOTATIONS.contains(&local) {
                continue;
            }
            match local {
                "hasValue" => out.push((
                    format!("FILTER NOT EXISTS {{ {focus} {path} {} }}", self.term(&o)?),
                    None,
                )),
                "minCount" => {
                    let n = count(&o)?;
                    out.push((
                        format!("FILTER NOT EXISTS {{ {} }}", self.distinct(focus, &path, n, None)?),
                        None,
                    ));
                }
                "maxCount" => {
                    let n = count(&o)?;
                    out.push((self.distinct(focus, &path, n + 1, None)?, None));
                }
                "class" => out.push((
                    format!("{focus} {path} {v} . FILTER NOT EXISTS {{ {v} a {} }}", self.term(&o)?),
                    Some(v),
                )),
                "datatype" => out.push((
                    format!(
                        "{focus} {path} {v} . FILTER(!isLiteral({v}) || datatype({v}) != {})",
                        self.term(&o)?
                    ),
                    Some(v),
                )),
                "nodeKind" => {
                    let filter = node_kind_violated(&o, &v, prop)?;
                    out.push((format!("{focus} {path} {v} . FILTER({filter})"), Some(v)));
                }
                "in" => {
                    let allowed = self.members(&o)?;
                    out.push((format!("{focus} {path} {v} . FILTER({v} NOT IN ({allowed}))"), Some(v)));
                }
                "node" => {
                    let violated = self.violated(&o, &v)?;
                    out.push((format!("{focus} {path} {v} . FILTER({violated})"), Some(v)));
                }
                "equals" => {
                    let other = self.path(Some(&o))?;
                    out.push((
                        format!("{focus} {path} {v} . FILTER NOT EXISTS {{ {focus} {other} {v} }}"),
                        Some(v.clone()),
                    ));
                    out.push((
                        format!("{focus} {other} {v} . FILTER NOT EXISTS {{ {focus} {path} {v} }}"),
                        Some(v),
                    ));
                }
                "lessThan" | "lessThanOrEquals" => {
                    let w = self.fresh();
                    let op = if local == "lessThan" { "<" } else { "<=" };
                    let other = self.path(Some(&o))?;
                    out.push((
                        format!("{focus} {path} {v} . {focus} {other} {w} . FILTER(!({v} {op} {w}))"),
                        Some(v),
                    ));
                }
                "minExclusive" | "maxExclusive" | "minInclusive" | "maxInclusive" => out.push((
                    format!(
                        "{focus} {path} {v} . FILTER(!({v} {} {}))",
                        comparison(local),
                        self.term(&o)?
                    ),
                    Some(v),
                )),
                "qualifiedValueShape" => {
                    let n_min = self.g.value(prop, &sh("qualifiedMinCount"));
                    let n_max = self.g.value(prop, &sh("qualifiedMaxCount"));
                    if let Some(n) = &n_min {
                        let n = count(n)?;
                        out.push((
                            format!("FILTER NOT EXISTS {{ {} }}", self.distinct(focus, &path, n, Some(&o))?),
                            None,
                        ));
                    }
                    if let Some(n) = &n_max {
                        if count(n)? != 0 {
                            return unsupported(format!("{prop}: sh:qualifiedMaxCount {} — only 0", lexical(n)));
                        }
                        let conforms = self.conforms(&o, &v)?;
                        out.push((format!("{focus} {path} {v} . {conforms}"), Some(v)));
                    }
                    if n_min.is_none() && n_max.is_none() {
                        return unsupported(format!("{prop}: a qualified value shape with no count"));
                    }
                }
                "qualifiedMinCount" | "qualifiedMaxCount" => continue,
                _ => return unsupported(format!("{prop}: <{p}> is not a constraint this compiles")),
            }
        }
        Ok(out)
    }

    fn distinct(&mut self, focus: &str, path: &str, n: i64, conforming: Option<&Term>) -> Result<String> {
        if n < 1 {
            return unsupported(format!("a count of {n} values is not a constraint"));
        }
        let vs: Vec<String> = (0..n).map(|_| self.fresh()).collect();
        let mut parts: Vec<String> = vs.iter().map(|v| format!("{focus} {path} {v} .")).collect();
        if let Some(shape) = conforming {
            for v in &vs {
                parts.push(self.conforms(shape, v)?);
            }
        }
        for (i, a) in vs.iter().enumerate() {
            for b in &vs[i + 1..] {
                parts.push(format!("FILTER({a} != {b})"));
            }
        }
        Ok(parts.join(" "))
    }

    fn sparql_body(&mut self, constraint: &Term, focus: &str) -> Result<String> {
        let text = self
            .g
            .value(constraint, &sh("select"))
            .map(|s| lexical(&s))
            .unwrap_or_default();
        self.body_of(&text, constraint, focus)
    }

    /// The WHERE body of a `SELECT … WHERE { … }` text, `$this` and `?this` both bound to `focus`.
    fn body_of(&mut self, text: &str, node_: &Term, focus: &str) -> Result<String> {
        let Some((head, rest)) = text.split_once('{') else {
            return unsupported(format!("{node_}: a select must be SELECT … WHERE {{ … }}"));
        };
        let upper = head.to_uppercase();
        if !upper.contains("SELECT") || !upper.contains("WHERE") {
            return unsupported(format!("{node_}: a select must be SELECT … WHERE {{ … }}"));
        }
        let declared: Vec<(String, String)> = PREFIX_LINE
            .captures_iter(head)
            .map(|c| (c.get(1).map_or("", |m| m.as_str()).to_string(), c[2].to_string()))
            .collect();
        for (name, iri) in declared {
            self.declare(&name, &iri)?;
        }
        //  `rest[:rest.rfind("}")]`, as the Python copy cuts it: a body with no closing brace loses its last
        //  character, since `rfind` answers -1.
        let body = match rest.rfind('}') {
            Some(end) => &rest[..end],
            None => &rest[..rest.char_indices().last().map_or(0, |(i, _)| i)],
        };
        for forbidden in ["$PATH", "$value", "$currentShape", "$shapesGraph"] {
            if body.contains(forbidden) {
                return unsupported(format!("{node_}: {forbidden} is not compiled"));
            }
        }
        let bound = bind(body, &[("this", Value::raw(focus))])?;
        Ok(THIS.replace_all(&bound, focus).trim().to_string())
    }

    // --- terms and paths ------------------------------------------------------------------------------------------

    fn term(&self, t: &Term) -> Result<String> {
        match t {
            Term::NamedNode(n) => Ok(format!("<{}>", n.as_str())),
            Term::Literal(l) => Ok(l.to_string()),
            Term::BlankNode(b) => unsupported(format!(
                "a blank node ({}) cannot be named in a compiled select",
                b.as_str()
            )),
        }
    }

    fn members(&self, list: &Term) -> Result<String> {
        let named: Vec<String> = self.g.list(list).iter().map(|m| self.term(m)).collect::<Result<_>>()?;
        Ok(named.join(", "))
    }

    fn path(&self, t: Option<&Term>) -> Result<String> {
        let Some(t) = t else {
            return unsupported("a property shape with no sh:path");
        };
        if let Term::NamedNode(n) = t {
            return Ok(format!("<{}>", n.as_str()));
        }
        if self.g.has(t, RDF_FIRST) {
            let steps: Vec<String> = self
                .g
                .list(t)
                .iter()
                .map(|p| self.path(Some(p)))
                .collect::<Result<_>>()?;
            return Ok(format!("({})", steps.join("/")));
        }
        for (pred, open, close) in [
            ("inversePath", "^(", ")"),
            ("oneOrMorePath", "(", ")+"),
            ("zeroOrMorePath", "(", ")*"),
            ("zeroOrOnePath", "(", ")?"),
        ] {
            if let Some(inner) = self.g.value(t, &sh(pred)) {
                return Ok(format!("{open}{}{close}", self.path(Some(&inner))?));
            }
        }
        if let Some(alternatives) = self.g.value(t, &sh("alternativePath")) {
            let steps: Vec<String> = self
                .g
                .list(&alternatives)
                .iter()
                .map(|p| self.path(Some(p)))
                .collect::<Result<_>>()?;
            return Ok(format!("({})", steps.join("|")));
        }
        unsupported(format!("a path this compiler does not know: {t}"))
    }
}

/// What a `sh:nodeKind` refuses, as the filter that finds the offending value — at the border's semantics, where
/// a blank node crossed into the judge as an IRI.
fn node_kind_violated(kind: &Term, v: &str, at: &Term) -> Result<String> {
    let local = match kind {
        Term::NamedNode(n) => n.as_str().strip_prefix(SH).unwrap_or(""),
        _ => "",
    };
    Ok(match local {
        "IRI" | "BlankNodeOrIRI" => format!("isLiteral({v})"),
        "Literal" => format!("!isLiteral({v})"),
        "BlankNodeOrLiteral" => format!("isIRI({v}) || isBlank({v})"),
        _ => return unsupported(format!("{at}: sh:nodeKind {kind} means nothing at the border")),
    })
}

fn comparison(local: &str) -> &'static str {
    match local {
        "minExclusive" => ">",
        "maxExclusive" => "<",
        "minInclusive" => ">=",
        _ => "<=",
    }
}

fn count(t: &Term) -> Result<i64> {
    lexical(t)
        .trim()
        .parse()
        .map_err(|_| Compiled::Unsupported(Unsupported(format!("a count that is no integer: {t}"))))
}

fn is_true(t: &Term) -> bool {
    matches!(t, Term::Literal(l) if l.datatype().as_str().ends_with("#boolean") && matches!(l.value(), "true" | "1"))
}

fn is_shacl(iri: &str) -> bool {
    iri.starts_with(SH)
}

fn lexical(t: &Term) -> String {
    match t {
        Term::Literal(l) => l.value().to_string(),
        Term::NamedNode(n) => n.as_str().to_string(),
        Term::BlankNode(b) => b.as_str().to_string(),
    }
}

#[cfg(test)]
mod tests {
    //! The met-test compiler, held as `agent/planning/tests/test_violation.py` holds the Python copy.

    use oxigraph::model::NamedNode;

    use orexis::snapshots;
    use orexis::store::{Store, iri, value};

    use super::*;

    const T: &str = "http://example.org/test#";
    const PREFIXES: &str =
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n@prefix planning: <http://example.org/orexis/planning#> .\n";

    fn shape() -> String {
        format!(
            "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ;
    sh:property [ sh:path <{T}level> ; sh:minInclusive 10 ; planning:about <{T}level> ] .
<{T}wanted> planning:metWhen <{T}full> .\n"
        )
    }

    fn avoided() -> String {
        format!(
            "<{T}low_tank> planning:about sh:this ;
    sh:select \"SELECT $this ?value WHERE {{ $this a <{T}Tank> ; <{T}level> ?value . FILTER(?value < 10) }}\" .
<{T}averse> planning:unmetWhen <{T}low_tank> .\n"
        )
    }

    /// A store of two tanks, the shapes in a graph of their own.
    fn store(shapes: &str) -> Store {
        let store = Store::new(snapshots::namespaces()).unwrap();
        store
            .put_trig(
                &format!("{T}default"),
                &format!(
            "{PREFIXES}<{T}world> {{ <{T}low> a <{T}Tank> ; <{T}level> 5 . <{T}high> a <{T}Tank> ; <{T}level> 12 . }}
<{T}shapes> {{ {shapes} }}"
        ),
            )
            .unwrap();
        store
    }

    fn compiled(store: &Store, subject: &str) -> Result<Option<String>> {
        let shapes = Shapes::of(store, &[format!("{T}shapes")]).unwrap();
        select_of(
            &shapes,
            &NamedNode::new(format!("{T}{subject}")).unwrap().into(),
            &snapshots::namespaces(),
        )
    }

    fn rows(store: &Store, select: &str) -> Vec<orexis::store::Row> {
        store.rows(select, &[&format!("{T}world")]).unwrap()
    }

    fn refusal(found: Result<Option<String>>) -> String {
        match found {
            Err(Compiled::Unsupported(u)) => u.0,
            other => panic!("refused nothing: {other:?}"),
        }
    }

    #[test]
    fn the_report_answers_the_focus_nodes_that_violate_and_what_each_is_about() {
        let store = store(&shape());
        let found = rows(&store, &compiled(&store, "wanted").unwrap().unwrap());
        assert_eq!(found.len(), 1);
        assert_eq!(iri(&found[0], "this"), Some(format!("{T}low")));
        assert_eq!(iri(&found[0], "_about"), Some(format!("{T}level")));
        assert_eq!(value(&found[0], "_constraint").as_deref(), Some("0"));
        assert_eq!(value(&found[0], "_offending").as_deref(), Some("5"));
    }

    #[test]
    fn the_entered_select_answers_one_row_per_instance_in_the_avoided_state_with_its_offending_value() {
        let store = store(&avoided());
        let found = rows(&store, &compiled(&store, "averse").unwrap().unwrap());
        assert_eq!(found.len(), 1);
        let row = &found[0];
        assert_eq!(
            (
                iri(row, "this"),
                value(row, "_constraint"),
                value(row, "_offending"),
                iri(row, "_about")
            ),
            (
                Some(format!("{T}low")),
                Some("0".into()),
                Some("5".into()),
                Some(format!("{T}low"))
            )
        );
    }

    #[test]
    fn an_avoided_state_narrowed_by_a_target_node_answers_for_that_instance_alone() {
        let high = store(&format!("{} <{T}low_tank> sh:targetNode <{T}high> .", avoided()));
        assert!(rows(&high, &compiled(&high, "averse").unwrap().unwrap()).is_empty());
        let low = store(&format!("{} <{T}low_tank> sh:targetNode <{T}low> .", avoided()));
        assert_eq!(rows(&low, &compiled(&low, "averse").unwrap().unwrap()).len(), 1);
    }

    #[test]
    fn select_of_reads_either_polarity_and_refuses_both() {
        let store = store(&format!("{}{}", shape(), avoided()));
        assert!(compiled(&store, "bare").unwrap().is_none());
        let both = self::store(&format!(
            "{}{} <{T}wanted> planning:unmetWhen <{T}low_tank> .",
            shape(),
            avoided()
        ));
        assert!(refusal(compiled(&both, "wanted")).contains("both"));
    }

    #[test]
    fn an_avoided_state_that_is_not_one_select_refuses() {
        let two = store(&format!(
            "{} <{T}low_tank> sh:select \"SELECT $this WHERE {{ $this a <urn:x> }}\" .",
            avoided()
        ));
        assert!(refusal(compiled(&two, "averse")).contains("one sh:select"));
        let none = store(&format!(
            "<{T}low_tank> planning:about sh:this . <{T}averse> planning:unmetWhen <{T}low_tank> ."
        ));
        assert!(refusal(compiled(&none, "averse")).contains("one sh:select"));
        let a_shape = store(&format!("{} <{T}averse> planning:unmetWhen <{T}full> .", shape()));
        assert!(refusal(compiled(&a_shape, "averse")).contains("not a shape"));
    }

    #[test]
    fn a_constraint_this_does_not_compile_refuses_and_names_itself() {
        let store = store(&format!(
        "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ; sh:property [ sh:path <{T}level> ; sh:pattern \"x\" ] .
<{T}wanted> planning:metWhen <{T}full> ."
    ));
        assert!(refusal(compiled(&store, "wanted")).contains("is not a constraint this compiles"));
    }

    #[test]
    fn constraints_are_numbered_in_the_order_the_shapes_graph_hands_them() {
        let store = store(&format!(
            "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ;
    sh:property [ sh:path <{T}level> ; sh:minInclusive 10 ; planning:about <{T}level> ] ;
    sh:property [ sh:path <{T}level> ; sh:maxInclusive 8 ; planning:about <{T}top> ] .
<{T}wanted> planning:metWhen <{T}full> ."
        ));
        let found = rows(&store, &compiled(&store, "wanted").unwrap().unwrap());
        let numbered: std::collections::BTreeSet<(String, String, String)> = found
            .iter()
            .map(|r| {
                (
                    iri(r, "this").unwrap(),
                    value(r, "_constraint").unwrap(),
                    iri(r, "_about").unwrap(),
                )
            })
            .collect();
        assert_eq!(
            numbered,
            [
                (format!("{T}low"), "0".into(), format!("{T}level")),
                (format!("{T}high"), "1".into(), format!("{T}top")),
            ]
            .into()
        );
    }
}
