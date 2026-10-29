import pytest

import sources

HP_OBO = """format-version: 1.2
data-version: hp/releases/2026-02-16
ontology: hp.obo

[Term]
id: HP:0000001
name: All

[Term]
id: HP:0000118
name: Phenotypic abnormality
synonym: "Organ abnormality" EXACT []
synonym: "A \\"quoted\\" one" RELATED layperson []
is_a: HP:0000001 ! All

[Term]
id: HP:0000002
name: Child with qualifier
is_a: HP:0000118 {source="x"} ! Phenotypic abnormality
is_a: HP:0000001

[Term]
id: HP:0000003
name: Gone
is_obsolete: true

[Typedef]
id: part_of
name: part of
"""

PR_OBO = """format-version: 1.2
data-version: 73.1
ontology: pr

[Term]
id: PR:000000001
name: protein

[Term]
id: PR:000000002
name: family
is_a: PR:000000001 ! protein

[Term]
id: PR:000001001
name: human protein category
is_a: PR:000000002 ! family
relationship: only_in_taxon NCBITaxon:9606 ! Homo sapiens

[Term]
id: PR:000009999
name: mouse protein category
is_a: PR:000000001 ! protein
relationship: only_in_taxon NCBITaxon:10090 ! Mus musculus

[Term]
id: PR:Q05329
name: Glutamate decarboxylase 2 (human)
synonym: "GAD65" EXACT []
is_a: PR:000001001 ! human protein category
intersection_of: PR:000001001 ! human protein category
intersection_of: in_taxon NCBITaxon:9606 ! Homo sapiens

[Term]
id: PR:P48321
name: Glutamate decarboxylase 2 (mouse)
is_a: PR:000009999 ! mouse protein category
relationship: only_in_taxon NCBITaxon:10090 ! Mus musculus

[Term]
id: PR:Q05329-1
name: GAD2 isoform 1 (human)
is_a: PR:Q05329
relationship: in_taxon NCBITaxon:9606 ! Homo sapiens

[Term]
id: PR:000009998
name: obsolete human
is_obsolete: true
relationship: only_in_taxon NCBITaxon:9606 ! Homo sapiens
"""

CHEBI_OBO = """format-version: 1.2
data-version: chebi/256
date: 06:10:2026 11:26

[Term]
id: CHEBI:24431
name: chemical entity

[Term]
id: CHEBI:15377
name: water
synonym: "H2O" RELATED [ChEBI]
synonym: "oxidane" RELATED IUPAC_NAME [IUPAC]
is_a: CHEBI:24431 ! chemical entity

[Term]
id: CHEBI:99999
name: obsolete thing
is_obsolete: true
"""

HGNC_TSV = (
    "hgnc_id\tsymbol\tname\tlocus_group\tstatus\talias_symbol\tprev_symbol\tuniprot_ids\n"
    "HGNC:4093\tGAD2\tglutamate decarboxylase 2\tprotein-coding gene\tApproved\tGAD65|GAD-2\tGAD\tQ05329\n"
    "HGNC:1\tTWOP\ttwo proteins\tprotein-coding gene\tApproved\t\t\tP00001|P00002\n"
    "HGNC:2\tNOPROT\tno protein\tpseudogene\tApproved\t\t\t\n"
    "HGNC:3\tGONE\twithdrawn gene\tprotein-coding gene\tSymbol Withdrawn\t\t\tP00003\n"
)

LOINC_CSV = (
    "LOINC_NUM,COMPONENT,LONG_COMMON_NAME,SHORTNAME,RELATEDNAMES2,STATUS\n"
    '4548-4,Hemoglobin A1c/Hemoglobin.total,Hemoglobin A1c/Hemoglobin.total in Blood,HbA1c MFr Bld,"A1C; Glycohemoglobin;;Glycated hemoglobin ",ACTIVE\n'
    "1-1,Old,Old test,Old SN,,DEPRECATED\n"
)

IEDB_CSV = (
    "Reference,,Epitope,,,,Assay,,1st in vivo Process,\n"
    "IEDB IRI,Title,Name,Source Molecule,Source Molecule IRI,Source Organism,Assay IRI,Type,Disease,Process Type\n"
    "http://iedb.org/r/1,T,SLYNTVATL,Glutamate decarboxylase 2,http://www.uniprot.org/uniprot/Q05329,Homo sapiens,"
    "http://iedb.org/a/1,ELISA,Type 1 diabetes,Occurrence of disease\n"
)


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_read_hp_keeps_label_synonyms_parents_release(tmp_path):
    terms = sources.read_hp(write(tmp_path, "hp.obo", HP_OBO))
    t = terms["HP:0000118"]
    assert t == sources.Term(
        "HP:0000118", "Phenotypic abnormality", ["Organ abnormality", 'A "quoted" one'], ["HP:0000001"], "hp/releases/2026-02-16"
    )
    assert terms["HP:0000002"].parents == ["HP:0000118", "HP:0000001"]


def test_obsolete_terms_are_skipped(tmp_path):
    assert "HP:0000003" not in sources.read_hp(write(tmp_path, "hp.obo", HP_OBO))
    assert "PR:000009998" not in sources.read_pr(write(tmp_path, "pr.obo", PR_OBO))
    assert "CHEBI:99999" not in sources.read_chebi(write(tmp_path, "chebi.obo", CHEBI_OBO))


def test_release_falls_back_to_date(tmp_path):
    terms = sources.read_hp(write(tmp_path, "hp.obo", HP_OBO.replace("data-version: hp/releases/2026-02-16", "date: 01:02:2026")))
    assert terms["HP:0000001"].release == "01:02:2026"


def test_read_pr_keeps_human_ancestors_and_uniprot_terms(tmp_path):
    terms = sources.read_pr(write(tmp_path, "pr.obo", PR_OBO))
    assert set(terms) == {
        "PR:000000001", "PR:000000002", "PR:000001001",  # human category and its ancestors
        "PR:Q05329", "PR:Q05329-1",  # human
        "PR:P48321",  # non-human UniProt accession
    }
    assert terms["PR:Q05329"].parents == ["PR:000001001"]
    assert terms["PR:Q05329"].synonyms == ["GAD65"]
    assert terms["PR:Q05329"].release == "73.1"


def test_read_chebi_keeps_synonyms(tmp_path):
    t = sources.read_chebi(write(tmp_path, "chebi.obo", CHEBI_OBO))["CHEBI:15377"]
    assert (t.label, t.synonyms, t.parents, t.release) == ("water", ["H2O", "oxidane"], ["CHEBI:24431"], "chebi/256")


def test_read_hgnc_maps_symbol_to_uniprot(tmp_path):
    genes = sources.read_hgnc(write(tmp_path, "hgnc.txt", HGNC_TSV))
    g = genes["HGNC:4093"]
    assert (g.hgnc_id, g.symbol, g.name) == ("HGNC:4093", "GAD2", "glutamate decarboxylase 2")
    assert g.uniprot == ["Q05329"]
    assert g.aliases == ["GAD65", "GAD-2", "GAD"]
    assert genes["HGNC:1"].uniprot == ["P00001", "P00002"]
    assert genes["HGNC:2"].uniprot == [] and genes["HGNC:2"].aliases == []


def test_read_hgnc_skips_withdrawn(tmp_path):
    assert "HGNC:3" not in sources.read_hgnc(write(tmp_path, "hgnc.txt", HGNC_TSV))


def test_read_loinc_active_only_with_split_synonyms(tmp_path):
    terms = sources.read_loinc(write(tmp_path, "Loinc.csv", LOINC_CSV))
    assert set(terms) == {"4548-4"}
    t = terms["4548-4"]
    assert t.label == "Hemoglobin A1c/Hemoglobin.total in Blood"
    assert t.synonyms == ["HbA1c MFr Bld", "Hemoglobin A1c/Hemoglobin.total", "A1C", "Glycohemoglobin", "Glycated hemoglobin"]
    assert (t.parents, t.release) == ([], "")


def test_read_iedb_bcell_two_line_header(tmp_path):
    assays = sources.read_iedb_bcell(write(tmp_path, "bcell_full_v3.csv", IEDB_CSV))
    assert assays == [
        sources.Assay("Glutamate decarboxylase 2", "http://www.uniprot.org/uniprot/Q05329", "Homo sapiens", "Type 1 diabetes")
    ]


@pytest.mark.parametrize(
    "reader,name",
    [
        (sources.read_hp, "hp.obo"),
        (sources.read_pr, "pro_nonreasoned.obo"),
        (sources.read_chebi, "chebi_lite.obo"),
        (sources.read_hgnc, "hgnc_complete_set.txt"),
        (sources.read_loinc, "Loinc.csv"),
        (sources.read_iedb_bcell, "bcell_full_v3.csv"),
    ],
)
def test_missing_file_names_the_expected_file(tmp_path, reader, name):
    with pytest.raises(FileNotFoundError, match=name):
        reader(tmp_path / name)


def test_intersection_of_genus_is_a_parent_and_kept_by_read_pr(tmp_path):
    obo = """data-version: 73.1

[Term]
id: PR:000000001
name: protein

[Term]
id: PR:000007786
name: glutamate decarboxylase 2
is_a: PR:000000001 ! protein

[Term]
id: PR:000050001
name: gene-level human term
intersection_of: PR:000007786 ! glutamate decarboxylase 2
intersection_of: in_taxon NCBITaxon:9606 ! Homo sapiens
intersection_of: has_gene_template HGNC:4093 ! GAD2

[Term]
id: PR:000060001
name: unrelated
is_a: PR:000000001
"""
    terms = sources.read_pr(write(tmp_path, "pr.obo", obo))
    assert terms["PR:000050001"].parents == ["PR:000007786"]
    assert set(terms) == {"PR:000000001", "PR:000007786", "PR:000050001"}
