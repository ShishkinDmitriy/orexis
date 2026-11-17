//! WHAT A GRAPH IS BUILT OF, as every package writes it: a node, a triple, a typed literal, a fresh name — and THE
//! ONE SPELLING OF A NUMBER. A number is rounded to six places and spelled as the shortest digits that read back
//! (`round6`, `repr`), by every writer alike, since a literal is compared as a term and the hash reads a number by
//! its text: two spellings of one value are two worlds.

use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hasher};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use oxigraph::model::vocab::{rdf, xsd};
use oxigraph::model::{Literal, NamedNode, NamedOrBlankNode, Term, Triple};
use oxsdatatypes::DateTime;

use crate::clock::isoformat;

pub const RDF_TYPE: &str = rdf::TYPE.as_str();

/// How far a number is trusted: two worlds whose readings agree to six decimals are one place.
const ROUND: usize = 6;

/// A figure correctly rounded to six places and read back, as every derived number here is written. A tie is never
/// met, since no binary fraction ends in a five at the seventh decimal: a figure is rounded by its binary value.
///
/// ```
/// use orexis::rdf::round6;
/// assert_eq!(round6(1.0000001), 1.0);
/// assert_eq!(round6(0.1234565), 0.123456);
/// assert_eq!(round6(2.5e-7), 0.0);
/// assert!(round6(f64::NAN).is_nan());
/// ```
pub fn round6(x: f64) -> f64 {
    if !x.is_finite() {
        return x;
    }
    format!("{x:.ROUND$}").parse().unwrap_or(x)
}

/// A float as the shortest digits that read back: fixed between 1e-4 and 1e16 with a `.0` where it has no fraction,
/// and an exponent of two digits at least outside.
///
/// ```
/// use orexis::rdf::repr;
/// assert_eq!(repr(0.0), "0.0");
/// assert_eq!(repr(-0.0), "-0.0");
/// assert_eq!(repr(21.0), "21.0");
/// assert_eq!(repr(0.3), "0.3");
/// assert_eq!(repr(123.456), "123.456");
/// assert_eq!(repr(0.0001), "0.0001");
/// assert_eq!(repr(1e-5), "1e-05");
/// assert_eq!(repr(1.5e-6), "1.5e-06");
/// assert_eq!(repr(1e15), "1000000000000000.0");
/// assert_eq!(repr(1e16), "1e+16");
/// assert_eq!(repr(1.2345e20), "1.2345e+20");
/// assert_eq!(repr(f64::INFINITY), "inf");
/// ```
pub fn repr(x: f64) -> String {
    if x.is_nan() {
        return "nan".to_string();
    }
    if x.is_infinite() {
        return if x > 0.0 { "inf" } else { "-inf" }.to_string();
    }
    let sci = format!("{:e}", x.abs());
    let (mantissa, exponent) = sci.split_once('e').expect("Rust's exponent form has an e");
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let point: i32 = exponent.parse::<i32>().expect("an exponent") + 1;
    let sign = if x.is_sign_negative() { "-" } else { "" };
    let n = digits.len() as i32;
    let body = if (-4 < point) && (point <= 16) {
        if point <= 0 {
            format!("0.{}{digits}", "0".repeat((-point) as usize))
        } else if point >= n {
            format!("{digits}{}.0", "0".repeat((point - n) as usize))
        } else {
            format!("{}.{}", &digits[..point as usize], &digits[point as usize..])
        }
    } else {
        let mantissa = if n == 1 {
            digits.clone()
        } else {
            format!("{}.{}", &digits[..1], &digits[1..])
        };
        let e = point - 1;
        format!("{mantissa}e{}{:02}", if e < 0 { '-' } else { '+' }, e.abs())
    };
    format!("{sign}{body}")
}

/// A fresh name: a UUID's URN, unique across every agent.
pub fn mint() -> NamedNode {
    static COUNT: AtomicU64 = AtomicU64::new(0);
    let state = RandomState::new();
    let mut high = state.build_hasher();
    high.write_u64(COUNT.fetch_add(1, Ordering::Relaxed));
    let mut low = RandomState::new().build_hasher();
    low.write_u128(Instant::now().elapsed().as_nanos() ^ u128::from(high.finish()));
    let (a, b) = (high.finish(), low.finish());
    //  A VERSION-4 UUID's shape: the version nibble 4 and the variant bits 10.
    let a = (a & 0xffff_ffff_ffff_0fff) | 0x0000_0000_0000_4000;
    let b = (b & 0x3fff_ffff_ffff_ffff) | 0x8000_0000_0000_0000;
    NamedNode::new_unchecked(format!(
        "urn:uuid:{:08x}-{:04x}-{:04x}-{:04x}-{:012x}",
        a >> 32,
        (a >> 16) & 0xffff,
        a & 0xffff,
        b >> 48,
        b & 0xffff_ffff_ffff
    ))
}

/// An IRI as a node.
pub fn node(iri: &str) -> NamedNode {
    NamedNode::new_unchecked(iri)
}

/// A triple of `subject`, `predicate` and `object`.
pub fn triple(subject: impl Into<NamedOrBlankNode>, predicate: &str, object: impl Into<Term>) -> Triple {
    Triple::new(subject, node(predicate), object)
}

/// `subject` a `class`.
pub fn typed(subject: impl Into<NamedOrBlankNode>, class: &str) -> Triple {
    triple(subject, RDF_TYPE, node(class))
}

/// An instant as the literal it is: an `xsd:dateTime`, with its zone (`clock::isoformat`).
pub fn instant(at: DateTime) -> Literal {
    Literal::new_typed_literal(isoformat(at), xsd::DATE_TIME)
}

/// A truth as the literal it is.
///
/// ```
/// assert_eq!(orexis::rdf::boolean(false).value(), "false");
/// ```
pub fn boolean(value: bool) -> Literal {
    Literal::new_typed_literal(if value { "true" } else { "false" }, xsd::BOOLEAN)
}

/// An integer as the literal it is.
///
/// ```
/// assert_eq!(orexis::rdf::integer(7).value(), "7");
/// ```
pub fn integer(value: i64) -> Literal {
    Literal::new_typed_literal(value.to_string(), xsd::INTEGER)
}

/// A text as the literal it is.
pub fn text(value: &str) -> Literal {
    Literal::new_simple_literal(value)
}

/// A double as the literal it is, spelled by `repr`.
///
/// ```
/// assert_eq!(orexis::rdf::double(3.0).value(), "3.0");
/// assert_eq!(orexis::rdf::double(0.25).value(), "0.25");
/// ```
pub fn double(value: f64) -> Literal {
    Literal::new_typed_literal(repr(value), xsd::DOUBLE)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_entry_is_named_by_a_uuid_urn_and_never_twice() {
        let (a, b) = (mint(), mint());
        assert_ne!(a, b);
        let re = regex::Regex::new("^urn:uuid:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
            .unwrap();
        assert!(re.is_match(a.as_str()), "{a}");
    }
}
