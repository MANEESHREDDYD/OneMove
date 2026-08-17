# Provenance Model

> **Superseded.** The canonical evidence vocabulary lives in
> [`../EVIDENCE_MODEL.md`](../EVIDENCE_MODEL.md), and its single source of truth in code is
> `EvidenceClass` in `services/temporal/contracts.py`.

Every record carries an evidence class from **one** closed nine-value enum:

`OBSERVED` · `PUBLIC_OFFICIAL` · `PUBLIC_GEOGRAPHIC` · `PROVIDER_ESTIMATED` · `DERIVED` ·
`SIMULATED` · `ASSUMPTION` · `STAGING_DO_NOT_USE` · `TEST_ONLY`

`services/api/contracts/observatory.py` imports that enum rather than redefining it, and
`apps/observatory/src/lib/api/types.ts` mirrors it as a closed TypeScript union.

This file previously listed a different eight-value vocabulary (`ESTIMATED`, `PUBLIC_BENCHMARK`,
`MERCHANT_CONFIDENTIAL`, `DEMO_SYNTHETIC`) that **matched nothing in the codebase**. It was one of
several parallel taxonomies that drifted apart; the others — a `StrictStr`-typed API field emitting
`OFFICIAL_API_REAL` and `UNAVAILABLE`, and a dead fourth enum at `services/api/core/provenance.py` —
have been removed. Do not reintroduce a second list here.

Availability is **not** an evidence class. A record with nothing behind it carries
`state: "UNAVAILABLE"` and `evidence_class: null`.

Synthetic and legacy OneMove data must be strictly quarantined and, if ever stamped, carry
`STAGING_DO_NOT_USE` or `TEST_ONLY` — both of which are explicitly non-usable for decisions.

**Enforcement gap:** these classes are enforced by Pydantic and TypeScript contracts only. There is
no `evidence_class` column, `CHECK`, enum type, or trigger in any merged migration, so nothing at the
storage layer prevents an arbitrary string from being persisted.

> `generate_docs.py` still contains the old eight-value list as a template literal. If that generator
> is ever re-run it will overwrite this file with the stale vocabulary; fix the generator before
> running it.
