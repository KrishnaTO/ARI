# Changelog

## claude/restore-curator-mappings-1092-1116 (PR #114)

An audit of the history of `ARI:0001092` to `ARI:0001116` across every branch and PR head
found curator mappings that were lost or never written to the mapping set. This adds 25 rows
to both mapping exports.

- **Restored MONDO `0017287` on `ARI:0001109`** (IgG4-related disease). AnjaliRH entered it on
  2026-08-03 at 18:07 UTC. Her stale editor save at 18:43 (`e9919b5`) removed it, along with
  MONDO on eight other diseases and six IPEX ids. The others came back (re-entered on 08-07,
  or restored in `1ccffdf`), but this one did not. The id is stored again and has its mapping
  row, credited to AnjaliRH.
- **Recorded 23 ids that AnjaliRH entered through the field editor between 2026-08-07 and
  2026-08-10.** They were stored on the diseases (`ARI_*`), but no review ever wrote a mapping
  row for them. They cover MONDO, Orphanet, OMIM, MeSH, ICD-10 and UMLS on `ARI:0001102` and
  `ARI:0001107` to `ARI:0001116`. Each row is credited to AnjaliRH and dated by the
  `Edited: <field>` changelog entry that stored it.
- **Reversed the rejection of DOID `0080356` on `ARI:0001109`.** DOID labels it
  "IgG4-related disease", and MONDO `0017287` cross-references it. The curator's `Not` row is
  marked superseded, and a confirmation credited to `github:KrishnaTO` is added.
- **Rejected MeSH `D003320` and NCIt `C50515` on `ARI:0001131`** (Mooren's ulcer). Both are
  "Corneal Ulcer", which is broader than the disease. They were entered in the field editor on
  2026-09-07 but never confirmed. Both are removed from the record. Neither vocabulary has a
  Mooren's ulcer term, so each gets a `sssom:NoTermFound` row.
- **Confirmed ICD-10 `G35`, MeSH `D009103` and UMLS `C0026769` on `ARI:0001135`** (Multiple
  sclerosis). They were stored at import and the ARI#76 review did not cover them.
- A second audit, of `ARI:0001117` to `ARI:0001141`, found no lost mappings. Every other
  removal there came from the ICD-9 cleanup or a documented PR review.
- Each touched record gains an `ARI_ChangeLog` line. Predictions, target labels and report 8
  are regenerated. They had not been rerun since ARI#108, so `ARI:0001019` and `ARI:0001177`
  also change.
- Not changed, and needing a curator: the five "no term" judgments deleted as `null` rows in
  `1cad398` (`ARI:0001094` DOID, `ARI:0001105` MeSH, `ARI:0001108` OMIM, `ARI:0001110` and
  `ARI:0001113` MeSH), and the never-reviewed `ARI:0001099` to `ARI:0001101` and `ARI:0001105`.
  The #49 suggestion of MeSH `C580192` for `ARI:0001105` is not restored. It is the IPEX
  descriptor, which belongs to `ARI:0001106`.

## claude/disease-mapping-gaps-prs-cd484c

Records "no term in database" for the 146 diseases reviewed in the curator mappings reviews
ARI#88, #89 and #92-#96. A disease gets a no-term row wherever a vocabulary has no confirmed
mapping, no id stored on the record, and no existing no-term row. Counted after ARI#108, that
is 173 rows across 54 diseases. 74 are in vocabularies where the review rejected every
candidate (Anti-CASPR2 autoimmune encephalitis, Autoimmune cerebellar ataxia and Autoimmune
diabetes insipidus had no mapping left at all). The other 99 are in vocabularies where no
candidate was ever offered. OMIM is left out, because it is a Mendelian catalogue these
diseases mostly have no entry in.

- Each row is `sssom:NoTermFound` / `manual-absent`, credited to `github:KrishnaTO`, with the
  comment `No term confirmed in the ARI#<n> mappings review.` Rows are added to
  `mappings/ari.sssom.tsv` and `mappings/ari.equivalencies.tsv`.
- Each of the 54 records gains one `ARI_ChangeLog` line in the editor's format
  (`Cross-reference review: no term in DOID; no term in NCI; ...`).
- `ARI:0002` from ARI#88 is counted under its current id, `ARI:0001214` (LADA). Ids stored on a
  record without an SSSOM row (e.g. LADA's SNOMED, DOID, MONDO and UMLS) count as mappings.

## edit/KrishnaTO/mappings-review-1791133633 (PR #108)

Editor mappings review covering 16 diseases. It adds 51 "no term" markers, confirms UMLS
`C2609059` and `C5959873` plus MeSH `C537778` on `ARI:0001019` and NCIt `C128332` on
`ARI:0001177`, and rejects 10 predicted ids on `ARI:0001046`. Repairs before merge:

- **Blank-subject flags dropped:** the editor's parked field removals published `Not` rows
  for MONDO `0005623` and MeSH `C567049` with no subject (app defect, see ARI#88). MeSH
  `C567049` was already rejected on `ARI:0001045`.
- **Autoimmune thyroiditis (`ARI:0001048`) kept as on main:** the review session predates
  PR #107 and PR #109, so it removed MONDO `0005623` again and confirmed NCIt `C27191`, which
  #109 moved to the subtype `ARI:0001216`. Both edits are reverted.
- **Merged `main`:** the ontology is main plus this PR's per-record line changes, so the
  editor's synonym, subtype and element reordering is dropped.

## claude/hashimotos-thyroiditis-mappings-d13221

Adds `ARI:0001216` Hashimoto's thyroiditis as a subtype (`hasParentDisease`) of `ARI:0001048`
Autoimmune thyroiditis. The cross-references on the parent that name Hashimoto thyroiditis
move to it. The parent keeps its own terms: SNOMED `66944004`, OMOP `4281109`, DOID `7188`,
MONDO `0005623`, ICD-10 `E06.3`, UMLS `C0920350` and MeSH `D013967`.

- **Moved off the parent:** ORPHA `855` and NCIt `C27191` are both Hashimoto thyroiditis. The
  parent now rejects them (`manual-negative` / `Not`, with the earlier ORPHA confirmation
  marked superseded) and stores neither.
- **Confirmed on the subtype:** MONDO `0007699`, ORPHA `855`, NCIt `C27191`, SNOMED `21983002`
  (also the DXCODE) and OMOP `135215`. The first, fourth and fifth were already rejected on the
  parent as "the subtype", and those rejections stand.
- **Synonyms:** "Hashimoto thyroiditis", "Hashimoto's disease", "Hashimoto's thyroiditis" and
  "Chronic lymphocytic thyroiditis" are withdrawn from the parent (`subtype`). The subtype
  lists all of them except its own label. `9_Synonym_Review.tsv` records the new verdicts.
- **Prediction engine** (`notebook/ari-grounding/predict_target_matches.py`):
  - SSSOM rows marked `Superseded by the …` are ignored. The old ORPHA `855` confirmation on
    the parent had still been anchoring predictions, and 10 other diseases carry such rows.
  - A term confirmed for a disease's parent or subtype (`hasParentDisease`, read by the new
    `ari_diseases.parents()`) is no longer predicted for it, unless the disease confirms it
    too. A hub term the disease rejected, or one its relative claims, is no longer expanded.
    As a result, the parent no longer gets OMIM `140300`, MeSH `D050031` or UMLS `C0677607`
    (through the rejected MONDO `0007699`), and the subtype no longer gets the parent's
    DOID `7188`, ICD-10 `E06.3`, MeSH `D013967`, NCIt `C38766` or UMLS `C0920350`.
  - `build_disease_target_matrix.py` drops superseded rows too, so report 8 shows only live
    judgements.
  - Grounding, predictions, labels and reports 5-8 are regenerated. This also picks up every
    mapping change since #104.

## claude/autoimmune-thyroiditis-mondo-mapping-1b8434

Reverses the ARI#93 line-review rejection of `ARI:0001048` Autoimmune thyroiditis -> MONDO
`0005623` autoimmune thyroid disease. The review comment on that row ("Specific subtype")
described the Hashimoto row below it (MONDO `0007699`, which stays rejected). The row goes back
to `manual` with medinatinajeropablo-dot's attribution, and `0005623` is stored on the record
again with a dated `ARI_ChangeLog` line.

## validator-typed-node-elements

The validator now recognises a disease written as a typed node element
(`<AutoimmuneDisease rdf:about=...>`) as well as `<owl:NamedIndividual>`. Both are the same
individual in RDF/XML, but the line parser only matched `owl:NamedIndividual`/`owl:Class`, so
when the editor app wrote `ARI:0001013` the typed way (ARI#105) the disease looked deleted and
the build failed with `disease-deleted`. An entity is now any top-level element with an
`rdf:about`, and a disease is whichever of those carries an `ARI_ID`. Results on `main` are
unchanged (214 diseases, identical annotations).

## edit/Ari2215/mappings-review-1790388580

Applies the line review of ARI#96 (`mappings/ari.equivalencies.tsv`). Each marked row is
re-judged in both mapping exports with its original attribution kept, and the disease record
and its `ARI_ChangeLog` follow.

- **Rejected (confirmation -> `manual-negative` / `Not`), id removed from the record:**
  - `ARI:0001002` Acquired hemophilia: ORPHA `599480` (acquired hemophilia A, a subtype; the
    existing ORPHA "no term" row stands)
  - `ARI:0001029` Anti-NMDA receptor encephalitis: SNOMED `716684004`, OMOP `37399546` (SNOMED
    `452281000124106` and OMOP `764228` map the disease)
  - `ARI:0001121` Limbic encephalitis: ORPHA `163892` (obsolete)
- **Rejected and recorded as "no term":** `ARI:0001005` Acute lichenoid pityriasis MeSH
  `D017514` (pityriasis lichenoides, broader); `ARI:0001027` Autoimmune disorder of inner ear
  MeSH `D008575` (Meniere disease).
- **Replaced:** `ARI:0001027` ICD-10 `H81.0` -> `H83.8X9` and UMLS `C0025281` -> `C0395947`
  (the old ids are Meniere disease).
- **Rejections reversed (`manual-negative` -> `manual`), id restored to the record:**
  - `ARI:0001007` Adult-onset immunodeficiency due to anti-IFN-gamma autoantibodies: MONDO
    `0017617`, ORPHA `306431`, UMLS `C5191336`
  - `ARI:0001029`: SNOMED `452281000124106`, NCIt `C94853`
  - `ARI:0001042` Autoimmune optic neuropathy: MONDO `0044685`, ORPHA `499047`, UMLS `C5681239`
  - `ARI:0001055` Bickerstaff's brainstem encephalitis: MONDO `0019208`, ORPHA `79138`
- **Rejections reversed where KrishnaTO's June confirmation already exists:** the rejection rows
  are dropped and the older rows' "Superseded" notes cleared, ids restored: `ARI:0001001` NCIt
  `C84690`, MeSH `D016107`; `ARI:0001007` SNOMED `784393004`, OMOP `37205096`.
- **Rejections kept, reason recorded:** `ARI:0001013` Anti-CASPR2 autoimmune encephalitis:
  SNOMED `763803004`, OMOP `35622356`, MONDO `0017179`, ORPHA `83467`, UMLS `C3854373`,
  `C4706582` (subtypes: Morvan syndrome, CASPR2 limbic encephalitis); ORPHA `276402` (obsolete).

## edit/maffersi/mappings-review-1790310362

Applies the line review of ARI#95 (`mappings/ari.equivalencies.tsv`). Each marked row is
re-judged in both mapping exports with its original attribution kept, and the disease record
and its `ARI_ChangeLog` follow.

- **ICD-9 codes removed** (rows dropped, values taken off `ARI_ICD10`): `617` Endometriosis,
  `710.3` Dermatomyositis, `701.0` Morphea, `345.9` Epilepsy, `709.01` Vitiligo, `710.0`
  Systemic lupus erythematosus, `360.11` Sympathetic uveitis, `333.91` Stiff-person syndrome,
  `379.00` Scleritis, `390` and the rejected `390-392.99` Rheumatic fever, `710.1` Systemic
  sclerosis.
- **Rejected (confirmation -> `manual-negative` / `Not`), id removed from the record:**
  - `ARI:0001043` Autoimmune pancreatitis: SNOMED `722872000`, OMOP `36716715`, ORPHA `280302`
    (the existing codes `448542008`, `40490446` and `103919` map the disease)
  - `ARI:0001132` Morphea: SNOMED `201049004`, OMOP `4066845` (duplicates of the "Localized
    scleroderma" concept, which is kept)
  - `ARI:0001196` Systemic lupus erythematosus: OMOP `255891` (broader)
  - `ARI:0001193` Stiff-person syndrome: ORPHA `3198` (the spectrum disorder)
  - `ARI:0001120` Ligneous conjunctivitis: MONDO `0009009` (hypoplasminogenemia; MONDO
    `0100560` stays confirmed)
- **Rejection reversed, id stored:** `ARI:0001090` Essential mixed cryoglobulinemia: UMLS
  `C1852456` (target label matches a synonym).
- **"No term" rows replaced with a confirmed id:** `ARI:0001133` DOID `683`, `ARI:0001183`
  UMLS `C0265017`, `ARI:0001137` ICD-10 `G37.81`, `ARI:0001034` ICD-10 `E20.812`,
  `ARI:0001124` ICD-10 `L13.8`. The Enthesitis MeSH comment named `D001171`, which is
  "Arthritis, Juvenile"; that row stays "no term".
- **ICD-10 range replaced:** `ARI:0001182` Rheumatic fever: `I00-I02` -> `I01`, since ICD-10
  ranges are not used. `I00` stays confirmed alongside it.
- **Confirmations added:** `ARI:0001193` ORPHA `443192` (replaces `3198`); `ARI:0001198`
  ICD-10 `M34` (the rejected `M34.0` stays rejected).

## edit/JoshuaCorona-Sa/mappings-review-1790310013

Applies the line review of ARI#94 (`mappings/ari.equivalencies.tsv`). Each marked row is
re-judged in both mapping exports with its original attribution kept, and the disease record
and its `ARI_ChangeLog` follow.

- **Rejected (confirmation -> `manual-negative` / `Not`), id removed from the record:**
  `ARI:0001038` Autoimmune lymphoproliferative syndrome: MONDO `0011158` (ALPS type 1, a subtype).
- **ICD-9 code removed:** `279.41` on `ARI:0001038` (row dropped, value taken off `ARI_ICD10`).
- **Rejections reversed (`manual-negative` -> `manual`), id restored to the record:**
  - `ARI:0001039` Autoimmune necrotizing myopathy: MONDO `0016098`, ORPHA `206569` (synonym match)
  - `ARI:0001057` Bullous pemphigoid: DOID `8506`, MeSH `D010391`
  - `ARI:0001081` Eaton-Lambert syndrome: NCI `C3155`, ICD-10 `G70.80`, ORPHA `43393`
  - `ARI:0001212` CREST Syndrome: OMOP `3469412`
- **"No term" rows replaced with a confirmed id:**
  - `ARI:0001039` Autoimmune necrotizing myopathy: NCI `C206531`, ICD-10 `G72.89`
  - `ARI:0001040` Autoimmune neutropenia: NCI `C176730`, UMLS `C0340971`
  - `ARI:0001049` Autoimmune urticaria: MeSH `D000080223`
  - `ARI:0001050` Autoimmune urticaria and/or angioedema: UMLS `C1304196`
  - `ARI:0001075` CTLA4 haploinsufficiency: SNOMED `1197361002`, OMOP `37162742`
  - `ARI:0001083` Encephalopathy caused by anti-IgLON5 antibody: SNOMED `765751002`, OMOP
    `35623409`, ORPHA `420789`, UMLS `C4707562` (the NCIt row stays "no term")
  - `ARI:0001093` Felty syndrome: UMLS `C0015773`, ICD-10 `M05.00`
- **Superseded:** the older rejections of MeSH `D000080223` (`ARI:0001049`, KrishnaTO) and UMLS
  `C0015773` (`ARI:0001093`, Jennyzeng25) are marked superseded by the new confirmations.

## edit/medinatinajeropablo-dot/mappings-review-1790308984

Applies the line review of ARI#93 (`mappings/ari.equivalencies.tsv`). Each marked row is
re-judged in both mapping exports with its original attribution kept, and the disease record
and its `ARI_ChangeLog` follow.

- **Rejected (confirmation -> `manual-negative` / `Not`), id removed from the record:**
  - `ARI:0001031` Autoimmune gastritis: MeSH `D005757` (broader)
  - `ARI:0001048` Autoimmune thyroiditis: MONDO `0005623` autoimmune thyroid disease (broader)
    and MONDO `0007699` Hashimoto thyroiditis (subtype). No MONDO id remains on the record.
  - `ARI:0001119` Lichen sclerosus: DOID `13477`, MONDO `0001725`, NCI `C3523`, MeSH `D052798`,
    UMLS `C0152460` (balanitis xerotica obliterans, the male-only subtype)
- **Replaced:** Lichen sclerosus NCI `C3523` -> `C26817` and UMLS `C0152460` -> `C0023652`
  (lichen sclerosus et atrophicus), both confirmed and stored.
- **"No term" rows replaced with a confirmed id:** Autoimmune hemolytic anemia ICD-10 `D59.1`;
  Systemic sclerosis with limited cutaneous involvement NCI `C70646` (CREST syndrome).
- **Rejections reversed (`manual-negative` -> `manual`), id restored to the record:** Lichen
  sclerosus ICD-10 `L90.0`; Lipomatosis dolorosa ICD-10 `E88.2`; Vogt-Koyanagi-Harada UMLS
  `C0042170`.
- **ICD-9 codes removed** (rows dropped, values taken off `ARI_ICD10`): `571.42` autoimmune
  hepatitis, `697.0` lichen planus, `607.81` lichen sclerosus, `725` polymyalgia rheumatica.
- **Editor-save repairs surfaced by the main merge:**
  - `ari.sssom.tsv`: the save rewrote nine of KrishnaTO's confirmations (Uveitis, limited SSc,
    autoimmune thyroiditis, Balo, benign mucous membrane pemphigoid) as this curator's in the
    SSSOM export only. Restored to main's rows, matching `ari.equivalencies.tsv`.
  - Two field-edit removals were published with a blank subject (app defect, ARI#88). Filled
    in: NCI `C27778` on autoimmune hepatitis and NCI `C38766` on autoimmune thyroiditis.
  - Reversals keep both rows: KrishnaTO's 2026-07 rejection of NCI `C70646` (limited SSc) and
    confirmation of NCI `C38766` (autoimmune thyroiditis) are marked superseded.
    `validate_mappings.py` now skips superseded rows when checking them against the ontology,
    as it already did for confirmations. Before this, a superseded rejection still counted as
    live and failed with `flagged-still-stored`.
  - Rejected ICD-9 candidates dropped from both exports: `556.5` and `556` (ulcerative
    colitis), `364.24` (Vogt-Koyanagi-Harada).
  - `ARI_DXCODE`: dropped the SNOMED ids this review flagged that were still served through
    DXCODE, on ARI:0001031, 0001032, 0001033 and 0001119.

## claude/mappings-updated-synonyms-0ea6bd

- **Predicted mappings redetermined from the current synonyms.** The DOID and SNOMED
  grounders read names and synonyms from `1_Core_ARI_Diseases.xlsx`, a master-list snapshot
  that still carried 148 synonyms the synonym review withdrew (PR #84, #101) and lacked 157
  added since. They now read `ontologies/ari_t1d.owl` through a new
  `notebook/ari-grounding/ari_diseases.py`: the 213 non-retired diseases, their live
  `ARI_Synonym` values and their `ARI_SNOMED` codes. Report 8's Synonyms column uses the same
  source.
- Reran the whole pipeline (`ground_doid` → `ground_snomed` → `make_match_reports` →
  `predict_target_matches` → `resolve_target_labels` → `build_disease_target_matrix`);
  reports 5–8 and the CSV/JSON intermediates are regenerated. The top prediction changed
  for 93 (disease, database) pairs. Some changes also pick up PR #102's corrected mappings.
- Against the 713 curated confirmed mappings, the top prediction now reproduces the curated
  term for 649 (was 641). 28 name a different term (was 38) and 36 produce none (was 34).
- Regenerated again after merging #104 (Sjögren's MeSH/UMLS fix). The top predictions are
  unchanged, and Sjögren's candidates roughly double in support now that its ids agree. Of 715
  confirmed mappings, 651 are reproduced.
- Withdrawn synonyms no longer drive matches. Examples: Sjögren's disease no longer lands
  on keratoconjunctivitis sicca, Lichen sclerosus on balanitis xerotica obliterans, or
  Secondary Raynaud's on primary Raynaud disease. Polyglandular autoimmune syndrome type 2
  no longer lands on Carpenter syndrome (acrocephalopolysyndactyly).
- Disease set: ARI:0001212–0001215 (in the ontology, not in the core report) are now
  grounded. ARI:0001026 "Autoimmune disease" (report-only umbrella, not in the ontology) is
  no longer grounded.
- New false candidate (second in the DOID list, behind the curated-anchor term): ARI:0001069 Cold agglutinin disease → DOID:0111275
  speech-language disorder-1, via the abbreviation "CAS" (Gilda 0.556).
## edit/dileryfuentes/mappings-review-1790308227

Applies the line review of ARI#92 (`mappings/ari.equivalencies.tsv`). Each marked row is
re-judged in both mapping exports with its original attribution kept, and the disease record
and its `ARI_ChangeLog` follow.

- **Rejected (confirmation -> `manual-negative` / `Not`), id removed from the record:**
  - `ARI:0001117` Juvenile rheumatoid arthritis: DOID `676` (subtype); NCI `C61279` (different disease)
  - `ARI:0001138` Myocarditis due to autoimmune disease: SNOMED `37217002`, DOID `0040095`,
    MONDO `0030701` (different disease)
  - `ARI:0001189` Sjögren's disease: NCI `C70647`, UMLS `C0022575`, MeSH `D007638` (different disease)
  - `ARI:0001176` Secondary Raynaud's phenomenon: SNOMED `266261006`, DOID `10300`, MONDO
    `0008364`, ICD-10 `I73.0`, UMLS `C0034734`, MeSH `D011928` (broader)
  - `ARI:0001169` Primary sclerosing cholangitis: Orphanet `447771` (broader)
  - `ARI:0001177` Reactive arthritis: SNOMED `67224007`, OMOP `78357`, NCI `C34975`, ICD-10
    `M02.3`, UMLS `C0035012` (subtype)
- **Rejections reversed (`manual-negative` -> `manual`), id restored to the record:**
  Myasthenia gravis OMOP `76685` and UMLS `C1260409`; Reactive arthritis UMLS `C0152085`;
  Polymyositis OMOP `80800`. Polymyositis already had alexlazcano248's confirmation of
  `80800`, so its rejection row is dropped and that row's "Superseded" note is cleared.
- Removed SNOMED ids are also dropped from `ARI_DXCODE`, which mirrors `ARI_SNOMED`.
- **Merged `main`.** The editor re-serialised this PR's 21 diseases (and 312 symptoms) as
  `<AutoimmuneDisease>` / `<Symptom>` typed nodes and reordered the file. The ontology is
  rebuilt from `main`'s copy with this PR's per-disease additions and removals applied, so
  `main`'s layout and its #102 / #104 corrections are kept. Four of this PR's rejections were
  already recorded on `main` (Sjögren's DOID `12895`, UMLS `C0022575`, MeSH `D007638`;
  Secondary Raynaud's DOID `10300`); their duplicate rows are dropped here.
- **Editor-save repairs.** The save rewrote alexlazcano248's eight Polymyositis confirmations
  in `ari.sssom.tsv` as dileryfuentes's, so the two exports disagreed (16 `cross-file-drift`);
  restored to match `ari.equivalencies.tsv`. Rejected SNOMED ids that survived in
  `ARI_DXCODE` are removed: `239796000` on `ARI:0001117`, `238676008` and `72470008` on
  `ARI:0001186` (3 `flagged-still-stored`).

## claude/sjogren-mesh-umls

- **ARI:0001189 Sjögren's disease: MeSH D007638 → D012859 and UMLS C0022575 → C1527336.**
  The old ids are both keratoconjunctivitis sicca (NLM MeSH; MedGen 9620). This is the same
  mix-up that PR #102 fixed for DOID 12895. D012859 "Sjogren's Syndrome" and C1527336 "Sjogren
  syndrome" are the exact equivalents that MONDO:0010030 lists, and DOID:12894 lists D012859. The
  new predictions review in PR #103 surfaced this. Each old id is flagged
  (`Not` / `manual-negative`) and each new id is confirmed in both mapping exports, with a dated
  `ARI_ChangeLog` line per id.

## claude/fix-wrong-ontology-mappings

- **Fixed seven wrong MONDO/DOID cross-references** (six below, narcolepsy further down), found during the synonym review (PR #101).
  Each fix updates the disease record and records the judgment in both mapping exports,
  with a dated `ARI_ChangeLog` line:
  - ARI:0001018 Antiphospholipid syndrome: MONDO 0017278 (autoimmune polyendocrinopathy)
    → 8000010 (antiphospholipid syndrome).
  - ARI:0001189 Sjögren's disease: DOID 12895 (keratoconjunctivitis sicca) → 12894
    (Sjogren's syndrome).
  - ARI:0001208 Uveitis: MONDO 0000554 (endocervical adenocarcinoma) → 0020283 (uveitis).
  - ARI:0001074 Cryptogenic organizing pneumonia: DOID 2797 (idiopathic interstitial
    pneumonia, the parent) → 0050157 (cryptogenic organizing pneumonia). The earlier
    confirmation is kept and annotated as superseded.
  - ARI:0001002 Acquired hemophilia: removed DOID 12134 (factor VIII deficiency). DOID has
    no acquired-haemophilia term; this was already recorded as NoTermFound.
  - ARI:0001176 Secondary Raynaud's phenomenon: removed DOID 10300 (primary Raynaud
    disease). DOID has no term for the secondary form, so it is now recorded as NoTermFound.
- Each wrong id is flagged in the mapping exports (`Not` / `manual-negative`) and each new id
  is confirmed.
- **Not changed:**
  - ARI:0001117 JRA → DOID 676. The term's label says "systemic", but its definition and
    exact synonyms (JRA, JIA) cover the whole disease.
  - Addison's (0001006) stays on MONDO:0100480 autoimmune primary adrenal insufficiency.
    MONDO lists "Addison's disease" as an exact synonym of that term and has no separate
    all-cause Addison's term. The only wider option, MONDO:0015128 primary adrenal
    insufficiency, also covers CAH and adrenoleukodystrophy.
- **ARI:0001060 Cataplexy and narcolepsy: MONDO 0016158 → 0021107.** 0016158 is
  narcolepsy-cataplexy syndrome, which is narcolepsy type 1 only. This entry's definition
  covers narcolepsy in general, and it lists types 1 and 2 as subtypes, so 0021107
  (narcolepsy) is the right term. The earlier confirmation of 0016158 is annotated as
  superseded. The move also makes the entry's synonyms consistent: the type-1 names were
  withdrawn as subtypes on 2026-09-07, and *narcolepsy*, *paroxysmal sleep* and *narcolepsy
  with or without cataplexy* are exact synonyms of 0021107.

## claude/ari-disease-synonyms-acd0f7

- **Second pass of the synonym-vs-subtype review. 66 more synonyms withdrawn across 35
  diseases.** All 557 synonyms kept by the first pass (PR #84) were checked again against
  their disease's mapped MONDO/DOID terms via EBI OLS4: label, synonym scope
  (exact/related/narrow/broad), ancestors and descendants. Clinical judgement decided the
  259 that matched nothing and the 42 on unmapped diseases. Results: 25 `broader`,
  23 `subtype`, 12 `distinct`, 6 `non-disease`. Each uses the existing
  `ARI_SynonymWithdrawn` marker plus a dated `ARI_ChangeLog` line. `ARI_ClinicalSubtype` is
  untouched. No synonyms were added since PR #84, so the first pass had nothing new to cover.
- Withdrawn, main groups: the CRPS type 1 names (*Reflex sympathetic dystrophy*,
  *Sudeck's atrophy*, *Algodystrophy*, ...); the seven *inflammatory bowel disease 1* / NOD2
  strings on Crohn's (MONDO:0009960); cold-type AIHA terms on cold agglutinin disease; the
  acquired/adult PRCA forms; *Raynaud's disease* on **secondary** Raynaud's (distinct: it
  names primary Raynaud's); *Carpenter syndrome* on APS-2 (name collision with ACPS2);
  *Acute-onset type 1 diabetes* on fulminant T1D (a separate Japanese subtype); bare
  *Lupus*, *NMOSD*, *LCV*, *Juvenile arthritis*, *Atrophic gastritis* and
  *Interstitial pulmonary fibrosis* (broader); *MOG* and the sympathetic-ophthalmia eye
  labels (non-disease).
- **New report `data/4-reports/9_Synonym_Review.tsv`.** It has one row for each of the 708
  synonym strings ever recorded, with the verdict, reason, OLS evidence and a note. It covers
  both passes. 36 kept synonyms carry a curator note.
- **Noted for a curator, not fixed here:** wrong ontology mappings on ARI:0001002
  (DOID → factor VIII deficiency), 0001018 (MONDO → autoimmune polyendocrinopathy),
  0001189 (DOID → keratoconjunctivitis sicca), 0001208 (MONDO → endocervical
  adenocarcinoma), 0001176 (DOID → primary Raynaud disease), 0001117 (DOID → systemic JRA
  only), 0001074 (DOID → parent idiopathic interstitial pneumonia). There are also
  mapping-vs-concept conflicts on Addison's (0001006) and narcolepsy (0001060). *Sprue* on
  celiac disease is broader but can't be withdrawn: `validate_mappings.py` comma-splits
  values, so *Sprue, Celiac* keeps the token present.

## claude/remove-ari-0001168-term-6422bf

- **Retired Primary immune deficiency (`ARI:0001168`).** Set `ARI_Obsolete` to `true` and
  added an `ARI_ChangeLog` line. The individual stays in the ontology because
  `validate_mappings.py` fails on a deleted disease (`disease-deleted`); retirement is by
  `ARI_Obsolete`. It had no mapping rows, subtypes, or other ontology references.
- **Dropped it from the reports and regenerated everything downstream.** Its row is removed
  from `1_Core_ARI_Diseases.xlsx` and `4_Additional_Info_Index.xlsx`, which have no generator
  here; hyperlinks are shifted with their rows, and every other cell and link is unchanged.
  The grounding pipeline was then rerun: `doid_matches_all.csv`, `snomed_matches_all.csv` and
  reports 5-7 now cover 210 diseases. Each CSV loses only the one row.
- **Reports 6 and 8 also pick up earlier changes that were never regenerated.** Report 6's
  detail sheet now files ICD-9 xrefs under "Other xrefs", as the script has done since the
  ICD-9 retirement. Report 8 is rebuilt from the current mapping set, 845 curated mappings
  where the old snapshot had 501, and replaces the stale `ARI:0003` with `ARI:0001214` and
  `ARI:0001215`. The README counts are updated to match.
- **The four older grounding scripts now resolve paths from the repo.** They hardcoded a
  `/sessions/...` sandbox path. Repo files now resolve relative to the script, and
  `data/2-databases` follows the fixed path the newer scripts use.
- The master list (`data/1-master/ARI Master List V 2.1 - 2026-06-04.xlsx`) still lists the
  disease. It is a dated source release and is left as issued.

## t1d-registry-ids

- **Gave LADA and Fulminant type 1 diabetes registry ids.** They were the only diseases
  left with ids from the editor's seed data. The editor started with three demo records
  (`#T1D_0001`-`0003`, `ARI:0001`-`0003`). When the core reports were imported, Type 1
  diabetes matched the report's record and took `ARI:0001080`, but the other two appear in
  no report or master list, so they kept four-digit ids on an IRI outside the registry
  namespace. Renumbered with the next free ids:
  - `ARI:0002` -> `ARI:0001214`, Latent autoimmune diabetes in adults (LADA)
  - `ARI:0003` -> `ARI:0001215`, Fulminant type 1 diabetes

  Each individual moves to `https://diseases.autoimmuneregistry.org/disease/ARI_…`, carries
  the old id in a new `ARI_FormerID` annotation, and gets a changelog line. Their mapping rows are rewritten to the new ids in both files: four
  for `ARI:0003`, and the ten `ARI:0002` rows that #88 added.
- **`validate_mappings.py` now requires seven-digit ids.** The SSSOM subject pattern was
  `ARI:\d{4,7}` to let these two through; it is `ARI:\d{7}`, and a new `ari-id-shape`
  check applies the same rule to the ontology's own `ARI_ID`s. The deletion check follows
  `ARI_FormerID` to the renumbered record, so a renumbering is not reported as
  `disease-deleted`. `ARI_FormerID` is append-only, and `former-id-in-use` rejects a former
  id that another disease still uses.
- `data/4-reports/8_Disease_Target_Mappings.xlsx` still lists `ARI:0003`. It is a
  formatted snapshot from 2026-08-22 that is already behind the mapping set, and is left
  for its next regeneration.

## edit/alexlazcano248/mappings-review-1790253647

Fixes the 32 `validate` errors on ARI#88. All come from editor-app defects
(KrishnaTO/ARI-metadata-manager#171), not from the curator's judgments.

- **Four negative rows had no subject.** The editor now parks ids removed in the field
  editor and publishes them as flagged, but the parked entry carries only the disease IRI,
  so the export wrote an empty `subject_id` / `source_id`. Filled in from the ontology's own
  changelog, which recorded the removals correctly: umls `C2987933`, DOID `9744` and MONDO
  `0011027` belong to `ARI:0002` (LADA); SNOMED `195353004` to `ARI:0001017` (ANCA
  vasculitis). The LADA replacements (DOID `0080846`, MONDO `0850306`) are the correct
  terms on OLS; the removed ones name type 1 and type 2 diabetes.
- **SNOMED `195353004` on `ARI:0001017` is a reversal.** KrishnaTO had confirmed it on
  2026-07-10. The removal stands, so the earlier positive SSSOM row is annotated
  `Superseded by the negative judgment of github:alexlazcano248 …`, as the app does for a
  reversal made on the review page.
- **Flagged SNOMED codes survived in `ARI_DXCODE`.** The editor removed them from
  `ARI_SNOMED` only. Dropped from the DXCODE mirror: `82275008`, `195353004`
  (ARI:0001017); `715863001`, `722991004`, `702380008` (ARI:0001139); `3548001`
  (ARI:0001142).
## skip-superseded-confirmed-not-stored

- **`confirmed-not-stored` no longer fires for superseded rows.** A positive SSSOM row whose
  `comment` starts with "Superseded by the " has been withdrawn by a later negative judgment,
  so the id being absent from the ontology is correct. `check_against_ontology` now treats
  such rows as not live, matching the `contradiction` check (e.g. ARI:0001017 ->
  SNOMEDCT:195353004, superseded in #88).

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
- **Batch 7 — 20 diseases (ARI:0001176–0001199), 70 synonym strings.** 41 kept, 16 kept with
  a note, **13 withdrawn across 9 diseases**: 4 `non-disease`, 3 `broader`, 3 `distinct`,
  3 `subtype`.
- Batch 7 withdrawn: Relapsing polychondritis — *Relapsing polyneuropathy* (a nerve disease);
  Retinocochleocerebral vasculopathy — *retinal and encephalic tissue* / *Small infarctions
  of cochlear* (one term split on a comma); Rheumatic fever — *Acute rheumatic myocarditis*;
  Rheumatoid aortitis — *non-vasculitic)* / *Autoimmune aortitis (isolated* (one term split
  on a comma); Secondary Raynaud's phenomenon — bare *Raynaud's phenomenon*; Sjögren's
  disease — *Sicca syndrome*, *Keratoconjunctivitis sicca* (broader), *SJS* (Stevens-Johnson
  collision); Subacute bacterial endocarditis — *Subacute native valve endocarditis*;
  Systemic sclerosis — *Diffuse Systemic sclerosis*; SSc with limited cutaneous involvement —
  *dcSSc* (the diffuse form).
- **Pre-existing notes for a curator:** the comma-split imports on ARI:0001180 and ARI:0001183
  (the whole terms should be re-added); ARI:0001176 conflates primary and secondary Raynaud's;
  ARI:0001194 (subacute bacterial endocarditis, an infection) sits oddly in an autoimmune
  registry.
- **Batch 8 — 10 diseases (ARI:0001080, 0001200–0001211), 31 synonym strings.** 18 kept, 6 kept
  with a note, **7 withdrawn across 5 diseases**: 5 `broader`, 2 `subtype`.
- Batch 8 withdrawn: TIF1-gamma positive dermatomyositis — *Cancer-associated myositis*
  (broader); Transverse myelitis — *Secondary acute transverse myelitis*; Uveitis —
  *Idiopathic intermediate uveitis*; Vitiligo — *Leukoderma* (broader); Warm autoimmune
  haemolytic anaemia — *Immune hemolytic anemia*, *Acquired autoimmune hemolytic anemia*,
  *Immunohemolytic anemia* (broader — the whole AIHA / immune-haemolysis family, mirroring the
  cold-agglutinin-disease finding in batch 3).

### Review complete — all 146 diseases with synonyms

- **708 `ARI_Synonym` strings reviewed. 450 kept, 107 kept with a curator note,
  151 withdrawn across 56 diseases** — 63 name an existing or clear clinical subtype
  (`subtype`), 45 a broader parent (`broader`), 23 a different disease (`distinct`),
  20 an import artefact / downstream finding / split fragment (`non-disease`).
- `ARI_Synonym` 708 → 557; every removal carries an `ARI_SynonymWithdrawn` marker and its
  disease a dated `ARI_ChangeLog` line. No `ARI_ClinicalSubtype` line was added or rewritten —
  every `subtype`-reason withdrawal already had a matching subtype (or a clearly narrower
  clinical form) on the disease. `validate_mappings.py --since main` is clean.
- The 107 "kept (noted)" strings are left in place with a rationale in the findings tables for
  a curator: ambiguous broader/near-synonymous terms, historical eponyms, misspellings kept
  pending a spelling pass, and dangerous homonyms (e.g. *SJS*, *Carpenter syndrome*).
- Pre-existing issues surfaced but not fixed: label/definition mismatches (ARI:0001031,
  0001065, 0001076), comma-split imports (ARI:0001180, 0001183), and mis-imported sibling
  diseases in some `ARI_ClinicalSubtype` lists (ARI:0001069, 0001074).

## edit/KrishnaTO/mappings-review-1788817126

Fixes the 19 `validate` errors the review batch raised. Both were pre-existing gaps this
batch was the first to expose; neither is a fault in the judgments the curator recorded.

- **Morvan syndrome had no ARI id.** It was created on 2026-07-02, before the metadata
  manager started allocating sequential ids, so it kept a placeholder
  `#ARI_new_5199ce2a` IRI and carried no `ARI_ID` at all — the only such record left in the
  ontology. It went unnoticed until this batch exported the first mapping rows for it, and
  the empty subject reached both files spelled differently (`ARI:` in the equivalencies,
  empty in the SSSOM), so each file also reported the other as missing the row. Assigned
  `ARI:0001213` and moved the individual onto the registry namespace, matching every other
  disease. The number is the ontology's highest plus one, which is the same floor the
  manager's own allocator uses.
- **Recorded four judgments that were never written.** `ARI:0001158` (Polyglandular
  autoimmune syndrome type 2) lost DOID `0060234`, umls `C1275078`, ncit `C98873` and mesh
  `C563187`. Its changelog shows all four went through the disease record's field editor
  (`Edited: doid`, `Edited: nci`, `Edited: umls`, `Edited: mesh`) half an hour before the
  review was submitted. That path writes the ontology and nothing else, so the ids were
  dropped with no decision behind them — exactly what `xref-deleted` exists to catch. The
  replacements are right, so the four are now flagged wrong in both exports rather than
  restored. Note that the `mesh` `NoTermFound` row the review did write does not stand in
  for this: an absent-database verdict says nothing about the specific id that was there.

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
