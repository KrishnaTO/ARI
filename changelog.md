# Changelog

## disease-synonyms-subtypes

- **Reviews `ARI_Synonym` strings against the disease's own concept and retires the ones
  that are not synonyms.** Each disease's synonyms were checked against the exact-synonym
  list and subclass hierarchy of the MONDO / DOID term it maps to (via EBI OLS), with
  clinical judgement where no mapping exists. A string that names a narrower form, a
  broader parent, a different disease, or a downstream finding is not a synonym.
- **New retirement mechanism.** `ARI_Synonym` stays append-only. A synonym is now retired
  by removing its line **and** adding an `ARI_SynonymWithdrawn` marker on the same disease,
  shaped `<synonym> | <reason> | <note>` with `<reason>` in
  `subtype` / `broader` / `distinct` / `non-disease`. `validate_mappings.py` accepts a
  synonym removal that carries a matching marker and still fails an unexplained one; it
  also shape-checks the markers (`withdrawn-synonym-shape`, `-reason`, `-still-present`)
  and treats `ARI_SynonymWithdrawn` as append-only itself. `ARI_ClinicalSubtype` and
  `ARI_ChangeLog` are untouched — still strictly append-only.
- **Batch 1 — 25 diseases (ARI:0001001–0001044), 69 synonym strings.** 37 kept, 13 kept
  with a note for a curator, **19 withdrawn across 9 diseases**: 9 name an existing
  `ARI_ClinicalSubtype` (`subtype`), 4 a broader parent (`broader`), 4 a different disease
  (`distinct`), 2 a downstream haematologic finding (`non-disease`). Every withdrawn
  synonym maps to a subtype already listed on the disease, so no `ARI_ClinicalSubtype`
  lines were added or rewritten. Each edited disease carries a dated `ARI_ChangeLog` line.
- Withdrawn: ADEM — *Nonvasculitic autoimmune inflammatory meningoencephalitis*,
  *Hurst's disease*, *Weston-Hurst syndrome*; Addison's disease — *Adrenal Insufficiency*,
  *Adrenal cortical hypofunction*; Ankylosing spondylitis — *Axial spondyloarthritis*,
  *Spondyloarthritis*; Anti-CASPR2 encephalitis — *Morvan syndrome*; ANCA-associated
  vasculitis — *Churg Strauss syndrome*, *Wegener's Granulomatosis*; Autoimmune inner-ear
  disease — *Ménière's disease*; Autoimmune gastritis — *Megaloblastic Anemia*,
  *Macrocytic Anemia*, *Eosinophilic gastritis*, *Autoimmune enteropathy*; Autoimmune
  neutropenia — *Autoimmune neutropenia of infancy*, *Primary autoimmune neutropenia*;
  Autoimmune pancreatitis — *Lymphoplasmocytic sclerosing pancreatitis*, *Nonalcoholic
  destructive pancreatitis*.
- **Batch 2 — 16 diseases (ARI:0001036, 0001048–0001067), 181 synonym strings.** 129 kept,
  21 kept with a note, **31 withdrawn across 8 diseases**: 12 name an existing
  `ARI_ClinicalSubtype` (`subtype`), 12 are `NON RARE IN EUROPE: …` Orphanet
  epidemiological-classification labels that leaked in as synonyms (`non-disease`), 4 name a
  different disease (`distinct`), 3 a broader parent (`broader`). No `ARI_ClinicalSubtype`
  lines added or rewritten.
- Batch 2 withdrawn: Autoimmune urticaria — *Chronic idiopathic urticaria*,
  *Chronic urticaria* (broader), *Physical urticaria* (distinct); Behçet's syndrome —
  *Hughes-Stovin syndrome* ×2 (a rare vascular variant); Benign mucous membrane pemphigoid —
  *Ocular pemphigoid*; Cataplexy and narcolepsy — 8 NT1 / NT2 / HCRT-locus / *narcolepsy 1*
  strings; Celiac disease — 9 *NON RARE IN EUROPE: …* strings; Chronic Fatigue Syndrome —
  3 *NON RARE IN EUROPE: …* strings; Chronic interstitial cystitis — *ulcerative cystitis*;
  Chronic Lyme disease — *Lyme Borreliosis*, *Lyme Arthritis*, *Erythema Migrans with
  Polyarthritis* (the active infection), *Lyme disease* (broader).
- **Batch 3 — 17 diseases (ARI:0001068–0001093), 125 synonym strings.** 60 kept, 23 kept
  with a note, **42 withdrawn across 7 diseases**: 20 name a broader parent (`broader`),
  13 name an existing `ARI_ClinicalSubtype` (`subtype`), 7 name a different disease
  (`distinct`), 2 are `NON RARE IN EUROPE: …` / complication strings (`non-disease`).
- Batch 3 withdrawn: Cold agglutinin disease — 16 strings naming autoimmune haemolytic
  anaemia in general (CAD is its cold-agglutinin subtype); Complex regional pain syndrome —
  *Amplified musculoskeletal pain syndrome* (distinct) and the CRPS type-1/type-2 names
  (*Causalgia*, *CRPS I*, …); Crohn's disease — the location forms (*Crohn's colitis*,
  *Ileocolitis*, *Gastroduodenal Crohn's disease*, *Illeitis*), *Crohn disease-associated
  growth failure*, *NON RARE IN EUROPE: Crohn disease*; Cryptogenic organizing pneumonia —
  broader interstitial-pneumonia terms and two names for IPF (*Idiopathic fibrosing
  alveolitis*, *Diffuse idiopathic pulmonary fibrosis*); Cutaneous lupus erythematosus —
  the *Discoid lupus* strings (a subtype); Endometriosis — all four synonyms, which name
  *adenomyosis* (a separate diagnosis); Erythema nodosum — *Idiopathic erythema nodosum*.
- **Pre-existing bugs noted for a curator, not fixed here:** ARI:0001031 is labelled
  *Autoimmune gastritis* but its `rdfs:comment` describes autoimmune enteropathy; ARI:0001065
  *Chronic Lyme disease* has a definition describing the acute tick-borne infection;
  ARI:0001076 *Cutaneous lupus erythematosus* has a definition describing discoid lupus;
  ARI:0001069 and ARI:0001074 carry many mis-imported sibling diseases in their
  `ARI_ClinicalSubtype` lists (whole AIHA / interstitial-pneumonia families); several large
  synonym lists (celiac, CFS, CIDP, cold agglutinin) carry dozens of MeSH permuted forms
  that are kept but add little.
- **Batch 4 — 18 diseases (ARI:0003, 0001094–0001114), 64 synonym strings.** 40 kept, 4 kept
  with a note, **20 withdrawn across 5 diseases**: 17 name a manifestation/subtype
  (`subtype`), 2 a different disease (`distinct`), 1 a broader parent (`broader`).
- Batch 4 withdrawn: Graves' disease — *Thyrotoxicosis* (broader); Guillain-Barré syndrome —
  *Miller-Fisher syndrome* / *MFS* / *Fisher syndrome* (a variant, already a subtype);
  Hemophilia B Leyden — *Autoimmune hemophilia B* (acquired haemophilia B, a different
  disease); Immune thrombocytopenia — *Immune-mediated thrombotic thrombocytopenic purpura
  (iTTP)* (a different disease); Immunoglobulin G4 related disease — 14 organ-manifestation
  names (*Riedel's thyroiditis*, *Küttner's tumor*, *Mikulicz's syndrome*, *retroperitoneal
  fibrosis* / *Ormond's disease*, *periaortitis*, *inflammatory pseudotumor*, …).
- **Pre-existing note for a curator:** ARI:0001098 *Hemophilia B Leyden* is a genetic
  F9-promoter variant; its place in an autoimmune registry is questionable.
- **Batch 5 — 20 diseases (ARI:0002, 0001115–0001142), 70 synonym strings.** 48 kept, 11 kept
  with a note, **11 withdrawn across 9 diseases**: 5 `subtype`, 3 `broader`, 3 `distinct`.
- Batch 5 withdrawn: Juvenile RA — *Pediatric rheumatic disease* (broader); Lichen sclerosus —
  *Balanitis xerotica obliterans* (the male genital form); Linear IgA dermatosis —
  *Chronic bullous dermatosis of childhood* (the childhood form); Lipomatosis dolorosa —
  *Juxta-Articular adiposis dolorosa*; Mooren's ulcer — *Peripheral Ulcerative Keratitis*,
  *Corneal Ulcer* (broader); MOG antibody disease — *Anti-MAG disease* and its full name
  (anti-MAG neuropathy is a different disease — MAG vs MOG); Myocarditis due to autoimmune
  disease — *Coxsackie myocarditis* (viral); Myositis — *Juvenile myositis*; Neonatal lupus —
  *Congenital heart block due to maternal anti-Ro/SSA and anti-La/SSB* (the cardiac form).
- **Batch 6 — 20 diseases (ARI:0001143–0001173), 98 synonym strings.** 77 kept, 13 kept with
  a note, **8 withdrawn across 4 diseases**: 6 `broader`, 2 `subtype`.
- Batch 6 withdrawn: Opsoclonus-myoclonus syndrome — *Paraneoplastic opsoclonus-myoclonus*
  (×2, the cancer-associated subtype); Paraneoplastic cerebellar degeneration —
  *Paraneoplastic neurological syndrome* / *PNS* / *Paraneoplastic syndrome* (broader
  categories); PANDAS — *PANS* / *Pediatric Acute-onset Neuropsychiatric Syndrome* (the
  broader umbrella); Primary idiopathic dilated cardiomyopathy — bare *Dilated
  cardiomyopathy*.
- Batches 7+ (the remaining ~50 diseases with synonyms) follow in the same style.

## fix-ms-omop-and-lost-judgments

- **Corrects an error `restore-overwritten-curation` introduced.** OMOP `4027727` is
  "Systemic sclerosis, diffuse" (SNOMED 128460000); OMOP `374919` is "Multiple sclerosis"
  (SNOMED 24700007). The SSSOM rows for ARI:0001135 had the two verdicts swapped,
  `ari.equivalencies.tsv` had them the right way round, and the earlier branch resolved that
  disagreement in favour of the SSSOM side without checking either concept's label. So `main`
  stored the systemic sclerosis concept on Multiple sclerosis and had dropped the correct one.
  The curator's own SNOMED verdicts settle it: they confirmed 24700007 and flagged 128460000,
  which are exactly 374919 and 4027727. Both exports and `ARI_OMOP` now say 374919.
- The lesson generalises: a mapping row is not self-validating. Every stored OMOP concept was
  re-checked against the SNOMED code it carries and the SNOMED codes its disease stores. Five
  more diseases hold an OMOP concept broader or narrower than their SNOMED one — ARI:0001057
  (Pemphigoid vs Bullous pemphigoid), ARI:0001117 (Juvenile idiopathic vs Juvenile Rheumatoid
  Arthritis), ARI:0001138, ARI:0001144 and ARI:0001196 (Lupus erythematosus vs SLE). Those are
  pre-existing curation questions, not errors introduced here, and are **left for a curator**.
- **Restored six confirmations on ARI:0001106** (IPEX). AnjaliRH recorded nine judgments on
  2026-08-03; `02938dd` wiped every row for the disease on the 4th, and her next publish on the
  7th restored four. The six confirmations — MONDO:0010580, OMIM:304790, ORPHA:37042,
  mesh:C580192, ncit:C131009, umls:C0342288 — never came back, though every id is still stored
  on the disease and her changelog entry still names them. The review page therefore showed six
  cells as never reviewed when they had been.
- This is the first confirmed loss of *mapping rows*, as opposed to ontology records. The
  earlier branch checked only back to PR #69 and found the mapping set additive over that
  window; the loss is older, from the 2026-08-04 save.
- **Added `umls:C0398650` on ARI:0001107** (Immune thrombocytopenia). The id is stored and a
  changelog entry names AnjaliRH confirming it on 2026-08-10, but no row was ever written.
  This creates the record that entry implies rather than restoring a deleted one.
- Audited every disease for the same shape — an id stored, or a changelog entry naming it, with
  no judgment in the mapping set. What remains is deliberate: 11 ICD-9 codes whose rows the
  ICD-9 retirement removed on purpose, and one entry on ARI:0003 whose row exists under the
  repaired `MONDO:0014523` spelling.
- **One finding needs a curator, not a fix.** ARI:0001143 (Neuromyelitis optica) carries a
  changelog entry from 2026-08-27 confirming OMOP `4027727` — systemic sclerosis again, on a
  third disease. The mapping set holds the correct `omop:380995`, so the data is right and only
  the note is wrong; but the same wrong concept reaching two diseases in one session suggests a
  mis-click worth knowing about.

## restore-overwritten-curation

- Restores curation that the editor app's saves reverted, and re-applies the cleanups they
  undid. The audit goes from **66 errors** back to **0 errors, 6 warnings**, and every
  confirmed mapping is now stored on its disease — `confirmed-not-stored` is at zero for the
  first time since the check was written.
- **The cause is not curation.** An editor save writes the whole ontology from a copy loaded
  when the session started, so it reverts anything merged into the branch since. `0f03b91` is
  labelled a review of one disease, ARI:0001143, and changed 453 lines. `295fb23` deleted a
  confirmation three seconds after `17e616c` merged it in cleanly. Two curators' saves on
  17 August landed on byte-identical stale content, which points at a shared server-side copy
  rather than per-user browser state. **The fix for that belongs in
  [`KrishnaTO/ARI-metadata-manager`](https://github.com/KrishnaTO/ARI-metadata-manager) and is
  not in this change** — until a save applies a diff instead of a snapshot, the next publish
  can revert this one.
- **Restored 95 changelog entries, 10 synonyms and 17 clinical subtypes** from the merged
  history, plus **208 synonyms and 57 clinical subtypes** from PR #69, the last commit before
  the 17 August cliff. Only commits reachable from `main` were read, so nothing arrives from a
  branch that was never accepted. Synonyms 490 → 708, clinical subtypes 355 → 429, recorded
  cross-reference reviews 194 → 305. Verified afterwards: every distinct (disease, author,
  review) record that ever reached `main` is present, and none was invented — 603 of 603.
- **Stored 30 confirmed cross-references that had never been written to a disease**, across
  16 diseases — 12 MONDO, 10 Orphanet, 3 UMLS and one each of DOID, NCIt, MeSH, ICD-10 and
  OMIM. Confirming a term only ever affirmed an id the disease already held, so confirming one
  the registry lacked recorded a judgment with no data behind it. That skews to MONDO and
  Orphanet because the original ARI import carried almost nothing from either. Hemophilia B
  Leyden (ARI:0001098) now holds MONDO:0850054 and ORPHA:617930, confirmed by linikujp on
  21 August and absent ever since. **Writing the id at confirmation time is also an app-side
  fix and is not in this change.**
- **Re-applied the reverted cleanups**: 61 ICD-9 codes filed under `ARI_ICD10`, the two
  `MONDO:`-prefixed values on ARI:0001080 and ARI:0002, and the ranges `I00-I02` and
  `390-392.99` on Rheumatic fever. All three had landed on 16 August and were overwritten the
  next day. Cross-references are now derived from the mapping set rather than from either
  snapshot: a value flagged `predicate_modifier: Not` is dropped, a confirmed one is stored.
  That reproduces aaronabend's own correction in `1f18f16` — Multiple sclerosis keeps the
  single OMOP concept 4027727 and SNOMED 24700007 — without special-casing it.
- **Fixed three mapping-file errors that had been invisible.** `ari.equivalencies.tsv` and
  `ari.sssom.tsv` disagreed about which OMOP concept is Multiple sclerosis; the equivalencies
  rows for 374919 and 4027727 were the inverted pair and now match the SSSOM side and the
  ontology. Three judgments were recorded twice — a curator reviewed a pair, the record was
  wiped, the pair resurfaced as unreviewed, and a second curator confirmed the same terms
  again. The first judgment is kept in each case, so linikujp keeps the credit for
  ARI:0001019 that was taken once already.
- **`Validate mappings` can now fail on absence.** It ran with `--since BASE_SHA` and reported
  only rows a branch added or rewrote, so a save that deleted 385 lines passed clean. The new
  `check_deletions` compares the ontology against the pull request's base and reports
  `record-deleted`, `xref-deleted` and `disease-deleted`. A cross-reference may still go — that
  is what flagging one wrong on the review page does, and the judgment is in the mapping set —
  but a synonym, a subtype, a changelog entry or an id no curator ruled against may not.
  Removing a malformed value is exempt, so repairing an ICD-9 code or a doubled prefix is not
  mistaken for a reversal. Replayed against `0f03b91`, the commit that started this: **24
  errors**, where CI previously reported none.
- **Restored the weekly audit's sight.** The editor began writing a tenth `comment` column into
  `ari.sssom.tsv`; the header check rejected it, `split_rows` returned nothing, and every SSSOM
  row check was skipped in silence — including the two that exist to catch precisely this. Ports
  the header fix from `fix/sssom-comment-column` (validator only, none of that branch's data),
  and widens `mapping_date` to accept the ISO 8601 timestamp the app writes: all 548 rows carry
  one, and a timestamp sorts after the bare date it falls on, which made every row today read as
  tomorrow.
- **Judged the four OMOP concepts on Chronic Lyme disease (ARI:0001065)**, which the union had
  left unreviewed. The disease is Post-Treatment Lyme Disease Syndrome, not Lyme disease: its
  confirmed cross-references are MeSH D000077342 "Post-Lyme Disease Syndrome", MONDO:0700280,
  NCIt C119039 and UMLS C3890422, and the curator had already rejected DOID:11729 and
  icd10cm:A69.2 — both plain "Lyme disease" — and recorded no term in SNOMED. Resolved against
  the local Athena vocabulary in `data/2-databases`:
  - `omop:19137845` is MeSH D000077342, the same term already confirmed — **confirmed**.
  - `omop:440638` is SNOMED 23502006 "Lyme disease" and `omop:4141757` is SNOMED 33937009
    "Lyme arthritis" — the active infection and one of its manifestations, so both are
    **flagged wrong**. Storing them contradicted the curator's own "no term in SNOMED" finding.
  - `omop:37365579` appears in no local vocabulary file, in any column. It is left stored and
    unjudged: an id nobody can look up is not an id anybody can rule on. **Still needs
    Athena.**
  - `ARI_DXCODE` held 23502006 and 33937009 — the SNOMED codes behind the two rejected OMOP
    concepts. Flagging only the OMOP form would have left the same two concepts on the disease
    under a second property, so both SNOMED codes are flagged too and the property is now empty.
    That also clears one of the standing `dxcode-without-snomed` warnings, taking them from 6
    to 5.
- **Fixed a latent bug in the `date-future` check** found while recording the above. The app
  stamps `mapping_date` in UTC and the check compared it against `date.today()`, the local date,
  so an evening publish anywhere west of UTC read as tomorrow's work. CI runners are UTC and
  never saw it; a curator in Toronto running the validator after 20:00 would have.
- One thing is deliberately left alone. Some diseases now carry the same review recorded more
  than once under different timestamps, an artifact of the app re-recording a judgment whose
  record had been wiped; collapsing them is a curator's call and does not belong in a
  restoration, particularly one that adds a rule saying `ARI_ChangeLog` is append-only.
- The five remaining warnings are the standing `dxcode-without-snomed` debt.

## disease-target-mapping-sheet

- Added `data/4-reports/8_Disease_Target_Mappings.xlsx`: one row per (disease, target
  database) pair across all 213 mapping subjects and all 10 target databases in the ARI
  mapping set, so an unreviewed pair is as visible in the sheet as a curated one. Each row
  carries the disease ID, name and synonyms, the target database, and — where a mapping
  exists — its status (confirmed / rejected / no term found), SSSOM predicate and modifier,
  target ID, target label, and the curator and date. 2,216 rows covering all 501 mappings.
- Added `notebook/ari-grounding/resolve_target_labels.py`, which resolves a label for every
  `object_id` in `ari.sssom.tsv` (the mapping set stores no `object_label`). All 480 distinct
  object ids resolve. Local vocabulary copies cover SNOMED CT, OMOP, ICD-10-CM, MeSH, DOID,
  Mondo and OMIM; Orphanet and NCI Thesaurus come from the EBI OLS4 API because no usable
  local copy exists, and UMLS CUIs are labelled from the DOID or Mondo term that
  cross-references them. Every row records its label source.
- Added `notebook/ari-grounding/build_disease_target_matrix.py`, which builds the workbook.
- Added predicted matches to the report: 1,467 rows now carry a candidate, 1,022 of them on
  pairs no curator has reviewed. `notebook/ari-grounding/predict_target_matches.py` combines
  the existing Gilda lexical matches with cross-reference expansion through Mondo and DOID
  hub terms, which reaches the seven databases lexical grounding does not cover. Hubs are
  scored by how many of the disease's own identifiers reach them, so a candidate corroborated
  by several hubs outranks one reached through a single broad cross-reference.
- Two filters keep predictions from contradicting curation or the source vocabularies: a term
  already rejected for that disease and database is never predicted, and predicted SNOMED
  codes are restricted to standard, non-retired concepts — ontology xrefs still point at codes
  SNOMED has deprecated, which was the largest source of wrong predictions before the filter
  (top-1 agreement with curated mappings rose from 283/367 to 330/367).
- New columns: Predicted Mapping ID / Name, Prediction Method, Prediction Support, Prediction
  Evidence, Prediction vs Curated (colour-coded), Other Predicted IDs, Predicted URL. Where a
  curator recorded "no term in database" but a prediction still surfaced (5 rows), the verdict
  reads `Contradicts no-term finding` rather than being hidden.
- Flagged rather than dropped two mapping subjects that are not in
  `1_Core_ARI_Diseases.xlsx`: `ARI:0001212` (CREST Syndrome) and `ARI:0003` (Fulminant
  type 1 diabetes, whose ID does not follow the `ARI:0001XXX` format).

## fix-sssom-duplicate-key

- Fixed a false `duplicate-row` error in `.github/scripts/validate_mappings.py`. The
  SSSOM duplicate check keyed rows on `object_id`, but every `manual-absent` row carries
  the same literal `sssom:NoTermFound` object — the vocabulary that was searched lives in
  `object_source`. So five rows recording "no ORPHA term", "no DOID term", "no SNOMEDCT
  term", "no icd10cm term" and "no OMIM term" for one subject all collapsed to one key,
  and four of them were reported as duplicates of the first.
- The file already resolved this correctly in `sssom_key()` for the cross-file
  comparison; only the intra-file duplicate check missed it. Factored that resolution
  into `distinct_object_id()` and used it in both places, so the two cannot drift again.
- The same value now feeds the `contradiction` check, which likewise needs to compare
  per-vocabulary — and its message reads `ORPHA:NoTermFound` rather than a bare
  `sssom:NoTermFound` that names no vocabulary.
- No change to the counts on `main` (0 errors, 17 warnings before and after). PR #67,
  which added 24 `manual-absent` rows and tripped 7 of these false errors, goes to 0.

## port-icd9-retirement-to-main

- Ports #57 to `main`. That PR retired ICD-9 but merged into
  `feature/metadata-manager_v2/ARI`, so none of it reached this branch — `main` still
  listed ICD9/ICD9CM as active sources, still grouped ICD-9 into the report's ICD column,
  and still drew the ICD9 node in the ontology diagram.
- Removed the `ICD9` and `ICD9CM` rows from `data/3-meta-database-sources/meta-databases.csv`.
- Narrowed the xref grouping in `notebook/ari-grounding/make_match_reports.py` from
  `["ICD10", "ICD9", "ICD-10", "ICD-9"]` to `["ICD10", "ICD-10"]`, so the report's "ICD
  xrefs" column stops picking up ICD-9.
- Removed the ICD9 node and its edge from `connecting_ontologies.drawio`.
- Carries no data change. The ICD-9 codes themselves are removed separately.
## ci-workflows-mapping-files

- Added `.github/scripts/validate_mappings.py` and two workflows that run it. The checks
  were derived from problems that actually reached `main` — the `mesh:null` and
  `DOID:null` ids caught by hand in code review on #49 and #52, the ICD-9 codes #57
  retired from the source list but not from the data, the `MONDO:MONDO:0014523` double
  prefix, and the flagged-but-still-stored ids #60 had to clear out.
- **`Validate mappings`** gates pull requests that touch `mappings/` or `ontologies/`. It
  reports only rows the branch added or rewrote, so a curator submitting one disease is
  never blocked by debt they did not introduce. Findings appear as inline annotations on
  the changed line.
- **`Audit mappings`** runs the same checks over every row, weekly and on demand, so the
  standing backlog stays visible without turning every merge red.
- The validator is standard library only, so CI needs no install step, and it runs
  locally with `python .github/scripts/validate_mappings.py`.
- The first full audit against `main` reports **193 errors and 17 warnings**, all
  pre-existing and none corrected here. Two follow-up branches clear the bulk mechanically
  — `remove-icd9-codes-from-data` (88 ICD-9 codes filed under ICD-10 fields) and
  `fix-ari-id-padding` (69 rows whose ARI id is not padded the way the ontology spells
  it) — which takes the audit to **25 errors and 17 warnings**.
- What remains after those is the part that needs a curator, not a script: 18 literal
  `null` identifiers, the `MONDO:MONDO:0014523` double prefix, two MONDO values stored
  with their prefix where the other 55 are bare, the ICD-10 range `I00-I02`, and one
  cross-file drift where `ari.sssom.tsv` has `DOID:0111157` against the equivalencies
  export's `DOID:111157`.
## fix-remaining-mapping-errors

- Clears the last 25 validation errors. The audit is now **0 errors, 17 warnings**.
- **Removed 9 `null` cross-reference rows from each export.** Four were flagged-wrong rows,
  which recorded a curator rejecting nothing at all. Five were *confirmations* — a mapping
  asserted to exist against an identifier that was never written. The rows are removed
  rather than repaired: supplying the real id is a curation judgment, and asserting
  `NoTermFound` instead would claim the vocabulary has no term, which is demonstrably
  false in at least one case. The nine pairs need re-review: ARI:0001005 and ARI:0001010
  (NCIt), ARI:0001017, ARI:0001094 and ARI:0003 (DOID), ARI:0001105, ARI:0001110 and
  ARI:0001113 (MeSH), ARI:0001108 (OMIM).
- Worth noting on that last point: #49 supplied `mesh:C580192` for ARI:0001105 by review
  suggestion on 2026-08-03, and a `mesh:null` row dated 2026-08-07 has since replaced it.
  A hand-corrected value was overwritten by the same defect four days later, which is the
  regression the new CI check exists to stop.
- **`MONDO:MONDO:0014523` → `MONDO:0014523`** in both exports — the prefix had been
  concatenated onto a value that already carried it.
- **`DOID:111157` → `DOID:0111157`** in `ari.equivalencies.tsv`, resolving the last drift
  between the two exports. The ontology stores `0111157` for ARI:0001011, so the leading
  zeros were lost on the equivalencies side, not invented on the SSSOM side.
- **Two `ARI_MONDO` values de-prefixed** in the ontology — ARI:0001080 and ARI:0002 stored
  `MONDO:0005147` and `MONDO:0011027` where the other 55 MONDO values are bare digits.
- **Removed the ICD-10 range `I00-I02`** from Rheumatic fever (ARI:0001182). Nothing is
  lost: the disease already records `I00` as a single code alongside it, and a range is
  not an exact match.
- The 17 remaining warnings are unchanged and non-blocking: 11 confirmed mappings that are
  not stored on their disease, and 6 diseases holding a DXCODE with no SNOMED counterpart.

## fix-ari-id-padding

- Zero-padded the `source_id` column on **69 rows in `mappings/ari.equivalencies.tsv`**,
  covering 12 diseases that were written as `1001` where the ontology and
  `mappings/ari.sssom.tsv` both spell them `0001001`.
- The ontology's `ARI_ID` is the one spelling; the fix reads the correct form from
  `ontologies/ari_t1d.owl` rather than assuming a width, which matters because ARI:0002
  and ARI:0003 are genuinely four digits there and must not be re-padded to seven.
- Nothing else changed — only column 2 differs on every rewritten row, and no row was
  added or removed. The effect is that all three files now join on disease id without
  normalisation, which is what made the earlier drift between the two exports hard to see.

## remove-icd9-codes-from-data

- Removed **89 ICD-9-CM codes** filed under ICD-10 fields: 61 `ARI_ICD10` values in
  `ontologies/ari_t1d.owl` across 53 diseases, and the 14 matching rows in each of
  `mappings/ari.sssom.tsv` and `mappings/ari.equivalencies.tsv`.
- The rule is unambiguous: every ICD-10-CM code begins with a letter, so a digit-led value
  in an ICD-10 field is an ICD-9 code under the wrong vocabulary. `446.1`, `720.0` and
  `390-392.99` are ICD-9; `M30.3`, `M45` and `E10` are not. Letter-led values were left
  alone, including the range `I00-I02` on Rheumatic fever, which is a separate problem.
- **4 diseases now have no ICD-10 code at all** because every code they held was ICD-9:
  ARI:0001032, ARI:0001033, ARI:0001119 and ARI:0001201. Those cells now read as no term
  recorded, which is the honest state.
- Of the 14 mapping rows, 4 were confirmations and **10 were negative judgments** — a
  curator had already reviewed the code and rejected it. Dropping them removes a record,
  but a rejection of a code that cannot be represented in the target vocabulary carries no
  information forward; 9 of the 10 already had no stored id to guard. The affected
  diseases are ARI:0001012, 0001014, 0001061, 0001062, 0001063, 0001065, 0001068,
  0001073, 0001074 and 0001107.
- Three unrelated errors fall out of this. `ARI:0001012 -> icd10cm:720.0` was recorded as
  both confirmed and flagged wrong, and was the one id still stored after #60 despite
  being flagged; both rows and the stored value are ICD-9, so all three go together. Two
  of the six cross-file drifts (`362.50`/`362.5` and `720.0`/`720`) go with them.
- Note that #57 retired ICD-9 from `meta-databases.csv`, `make_match_reports.py` and the
  ontology diagram, but it merged into `feature/metadata-manager_v2/ARI` rather than
  `main`, so none of that reached this branch. This change covers the data only; porting
  #57 to `main` is still outstanding.

## remove-false-xref-mappings

- Removed **140 database cross-reference ids across 32 diseases** that curators had already flagged as wrong. Flagging a mapping on the [cross-reference review page](https://aurint.ca/ari-editor/ref-edits/) records the judgment in `mappings/ari.sssom.tsv` as an `skos:exactMatch` row with `predicate_modifier: Not`, but it never removed the id from the ontology — so 125 negative judgments had accumulated with the wrong ids still stored and still served.
- Scope is exactly the ids explicitly flagged negative; unreviewed ids were left alone. Verified before and after against the curated positives: no confirmed mapping was affected (the 25 confirmed-but-unstored ids all pre-date this change). Stored cross-reference ids: 1639 -> 1499.
- By database: SNOMED 36, DXCODE 38, OMOP 37, ICD-10 14, UMLS 4, DOID 4, MeSH 3, NCI 1, MONDO 1, Orphanet 1, OMIM 1. DXCODE is included because it shares SNOMED's CURIE prefix and mirrors its values, so a wrong SNOMED code would otherwise survive under a second property.
- **19 database/disease pairs are now empty** because every id they held was flagged — Chronic Lyme disease loses all its SNOMED, DOID and ICD-10 codes; Immune thrombocytopenia its only DOID and both ICD-10 codes. Those cells now read as "no term recorded", which is the honest state.
- Annotation values that pack several ids into one comma-separated string were filtered and rejoined in place, so the diff stays confined to the affected `ARI_*` properties. No changelog annotations were appended to the individual diseases — the SSSOM negatives already carry each judgment and its author.
- Advances #23 ("Remove multiple IDs in favour of exact matches to disease"); the remaining subtasks on that issue are untouched.

## docs/ari-editor-readme

- Added a root `README.md` focused on the public ARI Disease Metadata Manager at `https://aurint.ca/ari-editor/`.
- Documented the editor's visible workflow, project scope, key outputs, and local grounding process.
- Added this root `changelog.md` to track branch-level updates.
