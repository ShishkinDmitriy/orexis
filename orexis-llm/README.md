# orexis-llm

The language model family: the client a package asks a model through, and the words of a model and of asking one,
`llm:`, which every asking package shares and nothing else reads.

- **Loaded for:** no role. It is no package: it registers nothing, starts nothing and runs no task; a package asking
  a model depends on it and brings its words beside its own as it joins (`Handed::joins_with(&DOCUMENTS, &[&orexis_llm::DOCUMENTS])`).
- **Words:** `ontology.ttl` (`llm:`): `llm:Model`, and `llm:calledWithinS` and `llm:retries`, which any role asking a
  model may state. **Dictionary:** `knowledge/domain/llm/model.md`.
- **Asked by:** `orexis-translation/`, whose role names its model (`translation:translatedBy`) and what it is told.

## What it gives a package

| A package | by |
|---|---|
| asks a model a conversation's turn, with tools, or one call | `model::Model` (`converse`, `ask`) |
| reaches Anthropic's Messages API, paced by its role's figures | `model::Anthropic` (`from_environ`, `paced`) |
| says why a model would not answer, in a person's terms | `model::Failure`, `model::why_not` |
| counts what a call spent | `model::TOKENS` |
