---
type: Decision
title: A person states what the chat allows in the world's words, and is believed as the world
status: accepted
timestamp: 2026-11-03T12:00:00Z
description: >-
  The sovereign's ruling of 2026-11-03 that sayables and askables are hardcoding - a shape per thing a
  person may say, a select per thing they may ask - when the ontologies already say what may be said of
  what. Decided - a question is the model's query over what the chat reads, and a statement is triples in
  the properties the chat allows, each held to its property's domain and range, kept as a statement per
  subject and property and believed as the world's word. Refused - a sayable per statement, an askable per
  question, and a person's word in a graph kind of its own read beside the world.
---

# The question

Telling the terrace that its probe shows strange numbers took, on the branch that first did it, a
`speech:Sayable` with two fields, a `sensing:DefectReport` class to be the statement's node, a
`sensing:defective` property to name the sensor, a `speech:keyedBy` so a report said again replaced the
last, a `speech:Extraction` with a `speech:believedAs` to turn the report into `sensing:defect`, a
`sensing:DefectGraph` kind for that belief, and a `beside` argument on revision so sensing would read it.
Seven declarations to say one triple the ontology already had a word for, `?sensor sensing:defect ?why`.
The sovereign: *can we eliminate Sayable and Askable? Otherwise we have to hardcode them. We have
ontologies and shapes; they should define the bounds of what is possible.*

The askables had already lost the argument once. [The model queries what its chat may
read](/decisions/the-model-queries-what-its-chat-may-read.md) refused an askable per question as a
hardcoded list, and what was left of them was `/status` and two selects, sensing's and execution's, each
a question the model's own query now answers.

# What was decided

**A question is a query.** The model loads the vocabularies the chat reads and queries a copy of its
graphs. No package ships a select for it, and `/status` went with the askables, since it was the rows
of the askables that take no field.

**A statement is triples in the words the chat allows.** `speech:allows` on a chat names properties, or
`rdf:Property` for every property a vocabulary the agent holds declares, which is what the sovereign's
chat allows. A chat allowing none hears questions alone, so a chat that may only ask is a chat that
allows nothing. The model hands the `state` tool Turtle in those words, and each triple is held to what
its property's vocabulary declares. Its subject is a thing the world states of the `rdfs:domain`, and its
object is a thing of the `rdfs:range` or a literal of that datatype. A word with no domain or range is
bounded by nothing more. Outside the bounds, the statement is refused whole and the model is told why:
`seeker is no Listing, which viewingAt is said of`.

**One statement per subject and property.** The graph is named by the two, so a word said again of a
subject replaces what was said of it, and the model unsays a word by naming the subject and property
with no object. This is how a prediction supersedes by key. Speech's `heard` keeps the statement as it
keeps any peer's document, with the prose it was made from and who said it.

**What a person states is believed as the world's word.** A person a chat allows a word speaks for the
world in it, so the triples are written into a belief graph no agent owns. That graph is derived from
the statement and holds from when it was said, and revision reads it beside the world's documents as
it reads theirs. So `<probe> sensing:defect "it shows strange numbers"` said by the sovereign is what
the same line in a world document would be. No extraction runs, since no extraction has anything to
decide: translation checked the bounds, and it writes the belief because it decided it. Speech hears
every peer's document alike, so a peer's document claiming a person said something is believed of
nothing.

# What was refused

**A sayable per statement.** A shape per thing a person may say is a second declaration of what the
property already declares: its fields restate the property's domain and range, and its extraction
restates the property. Each new thing to be said cost a shape, a class to be the statement, an
extraction and often a graph kind. It was the hardcoding the sovereign named.

**An askable per question.** [Refused already](/decisions/the-model-queries-what-its-chat-may-read.md)
as the account's list of questions, and kept only for `/status`. A status that costs no model call was
worth something, but not a second reader of the store that every package had to feed.

**A person's word in a graph kind of its own, read beside the world.** The defect branch made
`sensing:DefectGraph` and taught sensing's revision to read it `beside` the common beliefs. [Revision
reads what the world states alone](/domain/belief/revision.md), and
this kept that rule by adding an exception per kind, one for every word a person might say. A person
the chat allows the word IS the world's voice in it, so their word is believed as the world's and needs
no exception. Revision reading every extracted belief was refused for the same reason it was refused
before: one peer's word would be judged beside another's.

**The model proposing a document edit.** A person's word could become a change to a world document,
proposed and ratified. That would be the right path for a standing change to the world. A sensor that
shows strange numbers today is testimony, not authorship, so it is kept as a statement and can be unsaid.

# Seams left open

- **SHACL shapes beyond domain and range.** A word whose bounds are a count, a pattern or a value set is
  bounded today by its domain and range alone. The shapes that say more are onboarding's requirements,
  which no agent loads, and pyshacl is onboarding's dependency. A word that needs more brings the
  shape, and the dependency comes with translation's extra.
- **A person cannot unsay what a document says.** Unsaying takes back the person's own statement. A
  defect stated in a world document stays until the document changes.
- **Who may state is the chat, not the person.** Everyone in a chat that allows a word may state it.
  Allowing a word per participant is a seam, since no group chat has yet needed it.
