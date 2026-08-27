# Third-party fixtures — W3C SSN worked examples

**These two `.ttl` files are not ours.** They are worked examples published alongside the
[Semantic Sensor Network Ontology](https://www.w3.org/TR/vocab-ssn/), the 2017 W3C
Recommendation, and they describe a **DHT22** — the KY-015's sibling and the part
`packages/orexis-part-dht11/` was modelled against.

They are here as evidence rather than as documentation. `tests/test_w3c_descriptions.py` drops
them into a world and holds them to every shape this project owns, which answers a question no
amount of reading the spec could: *can a description written by the people who wrote the
vocabulary be deployed without editing it?*

## Provenance

| | |
|---|---|
| repository | [`w3c/sdw`](https://github.com/w3c/sdw) |
| path | `ssn/integrated/examples/` |
| retrieved | 2026-08-11 |
| last upstream change | `cb31ee9de636`, 2022-10-10 (`dht22.ttl`) |

Both files are **byte-identical to upstream**, and that is checkable rather than claimed — the
git blob hash of each file here equals the blob SHA GitHub reports for it:

| file | blob SHA |
|---|---|
| `dht22.ttl` | `03f0d5bf30003373d341abb34f24c6351bd8f8a2` |
| `dht22-deployment.ttl` | `a9417ac7cc54a82b798f831d32bf5074fcd7b896` |

```
git hash-object tests/fixtures/w3c-ssn/dht22.ttl
```

`deploy-dht22.ttl` in this directory is **ours** — the deployment half, written here to show
what a vendor's description is missing and why it is right to be missing it.

## Copyright and licence — what is declared, and what is not

The specification these examples accompany carries **Copyright © 2017 [OGC](https://www.ogc.org/)
& [W3C](https://www.w3.org/)** and links W3C's
[document use](https://www.w3.org/Consortium/Legal/copyright-documents) rules, its
[liability](https://www.w3.org/Consortium/Legal/ipr-notice#Legal_Disclaimer) disclaimer and its
[trademark](https://www.w3.org/Consortium/Legal/ipr-notice#W3C_Trademarks) notices.

**The `w3c/sdw` repository itself declares no licence.** There is no `LICENSE` file, GitHub
reports no SPDX licence for it, and neither `.ttl` carries a copyright header. W3C's usual terms
for material of this kind are the [W3C Software and Document
License](https://www.w3.org/Consortium/Legal/2015/copyright-software-and-document), but that is
**not stated in this repository**, so it is recorded here as context and not as a claim about
these files.

What is recorded above is what is actually declared. Anyone redistributing this project should
check the current notices rather than trust this table.

## `dht22.ttl` does not parse, and we did not fix the file

Its `<observation/1087>` statement ends with `;` and never receives its `.`, so the next subject
begins mid-statement:

```turtle
<observation/1087> rdf:type sosa:Observation ;
  sosa:madeBySensor <DHT22/4578#TemperatureSensor> ;
  sosa:usedProcedure <DHT22#Procedure> ;
  ssn-system:qualityOfObservation <observation/1087#quality> ;    # <- no terminating dot
```

Every Turtle parser rejects it; ours is not being strict.

**The file here is left exactly as published.** The one-character repair lives in
`tests/test_w3c_descriptions.py`, as an explicit string replacement, so that our change is
visible as ours and cannot be mistaken for theirs. It is also self-invalidating: the test
asserts the malformed statement is still present, so if W3C ever fixes it upstream the test
fails and tells us to drop the patch, rather than silently applying a no-op forever.

## What these files taught us

- **A standard description can deploy untouched.** `dht22-deployment.ttl` — rooms, walls, boards
  and deployments — satisfies every shape we own with no overlay and no relaxation.
- **A device description needs a deployment half, and correctly so.** Their sensors state no
  name on our wire, no sense mode, no subject and no topic, because a vendor cannot know any of
  it. That is the part/deployment boundary, and it is the whole reason "use their descriptions
  as-is" is a coherent goal rather than a wish.
- **They write schema.org in the legacy `http:` form.** Ours is the canonical `https:`, and RDF
  treats the two as different IRIs — so a figure their file plainly states was invisible to a
  shape written against ours. That is bridged in `capabilities/sensing/ontology.ttl`.
- **Their frequency is 2 seconds**, which is the figure the KY-015 declares in
  `packages/orexis-part-dht11/`. Independent corroboration of a number nobody here measured.
- **One in four of the published examples does not parse.** `IBS-TH2-PLUS.ttl` is deliberately
  not vendored: it comes from the successor draft
  [`w3c/sdw-sosa-ssn`](https://github.com/w3c/sdw-sosa-ssn), which models a datasheet a different
  way. See `knowledge/decisions/their-descriptions-are-our-fixtures.md` for why that is a
  warning rather than a fixture.
