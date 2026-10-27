import pytest

import names
from names import Antibody, Family, noisy, normalise, parse_antibody, parse_family, sentence_like, split_bundle


# --- normalise ---------------------------------------------------------------------------------

def test_normalise_does_not_fix_spelling_slips():
    # The slip is caught by fuzzy grouping in Task 6; nobody should widen normalise to hide it.
    assert normalise("Type VII Colagen", "antigens") != normalise("Type VII collagen", "antigens")


def test_normalise_drops_antibody_words_for_antibodies():
    assert normalise("Anti-GAD65 autoantibodies", "antibodies") == normalise("Anti-GAD65", "antibodies")
    assert normalise("Anti MOG", "antibodies") == normalise("Anti-MOG autoantibodies", "antibodies")
    assert normalise("Anti-GQ1b IgG antibody", "antibodies") == normalise("Anti-GQ1b IgG", "antibodies")


def test_normalise_keeps_antibody_words_for_other_kinds():
    assert normalise("Anti-GAD65", "tests") != normalise("GAD65", "tests")


def test_normalise_only_removes_whole_words():
    # "Antinuclear" and "Antiphospholipid" are different words from "anti".
    assert normalise("Antinuclear antibodies (ANA)", "antibodies") == "antinuclear ana"
    assert normalise("Antiphospholipid antibodies", "antibodies") == "antiphospholipid"


def test_normalise_lowercases_collapses_and_drops_punctuation():
    assert normalise("  Anti-IA-2   (IA-2A) ", "antibodies") == "ia2 ia2a"
    assert normalise("Ro/SSA", "antigens") == normalise("Ro SSA", "antigens")
    assert normalise("GABA_B receptor", "antigens") == "gabab receptor"
    assert normalise("Cytosolic 5'-nucleotidase 1A", "antigens") == "cytosolic 5nucleotidase 1a"


def test_normalise_rejects_unknown_kind():
    with pytest.raises(ValueError):
        normalise("ANA", "proteins")


# --- parse_antibody ----------------------------------------------------------------------------

def test_parse_antibody_isotype():
    assert parse_antibody("Anti-CNTN1 IgG4") == Antibody("CNTN1", "IgG4")


def test_parse_antibody_functional_phrase_and_isotype():
    assert parse_antibody("Anti-ADAMTS13 neutralizing IgG").qualifier == "neutralizing IgG"
    assert parse_antibody("Anti-ADAMTS13 neutralizing IgG autoantibodies") == Antibody("ADAMTS13", "neutralizing IgG")


def test_parse_antibody_without_qualifier():
    assert parse_antibody("Anti-GAD65 autoantibodies") == Antibody("GAD65", None)
    assert parse_antibody("Anti MOG") == Antibody("MOG", None)
    assert parse_antibody("Anti-GQ1b IgG antibody") == Antibody("GQ1b", "IgG")


def test_parse_antibody_keeps_trailing_parenthetical_in_stem():
    assert parse_antibody("Anti-GAD65 (GADA)") == Antibody("GAD65 (GADA)", None)
    assert parse_antibody("Anti-aquaporin-4 (anti-AQP4) IgG") == Antibody("aquaporin-4 (anti-AQP4)", "IgG")


def test_parse_antibody_target_that_is_an_isotype_stays_the_stem():
    # Anti-IgE is an antibody against IgE, not an "IgE" qualifier on an unnamed target.
    assert parse_antibody("Anti-IgE autoantibodies") == Antibody("IgE", None)


def test_parse_antibody_only_reads_qualifiers_on_anti_labels():
    # "Elevated IgG4" is a finding about IgG4, not an antibody with an isotype.
    assert parse_antibody("Elevated IgG4") == Antibody("Elevated IgG4", None)
    assert parse_antibody("Rheumatoid factor (RF)") == Antibody("Rheumatoid factor (RF)", None)


def test_parse_antibody_matches_whole_words_only():
    assert parse_antibody("Anti-IgGlike") == Antibody("IgGlike", None)


def test_parse_antibody_without_anti_prefix_still_drops_trailing_antibody_words():
    assert parse_antibody("Antinuclear antibodies") == Antibody("Antinuclear", None)


# --- split_bundle ------------------------------------------------------------------------------

def test_split_bundle_brief_example():
    assert split_bundle("ANA, anti-dsDNA and anti-Sm") == ["ANA", "anti-dsDNA", "anti-Sm"]


def test_split_bundle_other_separators():
    assert split_bundle("Anti-Ro/SSA & Anti-La/SSB") == ["Anti-Ro/SSA", "Anti-La/SSB"]
    assert split_bundle("Anti-gliadin / anti-TG6 autoantibodies") == ["Anti-gliadin", "anti-TG6 autoantibodies"]
    assert split_bundle("A, B, and C") == ["A", "B", "C"]


def test_split_bundle_leaves_single_markers_alone():
    for label in ["Anti-Ro/SSA autoantibodies", "Anti-dopamine D1/D2 receptor autoantibodies", "Anti-GAD65 (GADA)"]:
        assert split_bundle(label) == [label]


def test_split_bundle_ignores_separators_inside_parentheses():
    for label in [
        "Anti-erythrocyte autoantibodies (warm IgG / cold agglutinins)",
        "Anti-neutrophil cytoplasmic antibodies (PR3-ANCA, MPO-ANCA)",
        "Myositis-specific antibodies (anti-Jo-1, anti-MDA5)",
        "(MAG, CNPase, MOBP)",
    ]:
        assert split_bundle(label) == [label]


def test_split_bundle_refuses_when_a_part_is_not_a_marker_name():
    sentence = "autoantibodies target the NMDA receptor, the AMPA receptor, or a growing list of synaptic protein"
    assert split_bundle(sentence) == [sentence]
    assert split_bundle("Anti-GAD65, ") == ["Anti-GAD65, "]
    assert split_bundle("Antibody combinations (more than one subtype are common) and more") == [
        "Antibody combinations (more than one subtype are common) and more"
    ]


# --- parse_family ------------------------------------------------------------------------------

def test_parse_family_brief_example():
    family = parse_family("Sperm surface antigens (SP-10, YLP-12, Izumo1)")
    assert family == Family("Sperm surface antigens", ["SP-10", "YLP-12", "Izumo1"])


def test_parse_family_antibody_labels():
    family = parse_family("Anti-neutrophil autoantibodies (anti-HNA-1a, anti-HNA-1b, anti-HNA-2)")
    assert family.name == "Anti-neutrophil autoantibodies"
    assert family.members == ["anti-HNA-1a", "anti-HNA-1b", "anti-HNA-2"]


def test_parse_family_drops_abbreviation_prefix_and_example_markers():
    assert parse_family("Anti-centromere antibodies (ACA: CENP-A, CENP-B, CENP-C)").members == ["CENP-A", "CENP-B", "CENP-C"]
    assert parse_family("Organ-specific autoantibodies (e.g. anti-TPO, anti-GAD65, anti-myositis)").members == [
        "anti-TPO", "anti-GAD65", "anti-myositis"
    ]


def test_parse_family_needs_a_plural_name_and_two_members():
    assert parse_family("Anti-GAD65 (GADA)") is None
    assert parse_family("Anti-erythrocyte autoantibodies (warm IgG / cold agglutinins)") is None
    assert parse_family("Rh blood group antigens (Rh polypeptide complex)") is None
    assert parse_family("Anti-IA-2 (IA-2A)") is None
    # An alias list for one antigen, not a family: the name is singular.
    assert parse_family("BP180 (LAD-1, 120 kDa / 97 kDa fragments)") is None
    assert parse_family("Histones") is None
    # A synonym plus a description of the antibody, not two members.
    assert parse_family("Anti-insulin autoantibodies (IAA, high-titer polyclonal IgG)") is None


def test_parse_family_parenthetical_must_close_the_label():
    assert parse_family("Anti-endothelial cell antibodies (AECA, others) in serum") is None


# --- noisy -------------------------------------------------------------------------------------

def test_noisy_strips_stray_numbers():
    assert noisy("Anti-GAD65  25") == "Anti-GAD65"
    assert noisy("anti-enterocyte (AE)   85") == "anti-enterocyte (AE)"
    assert noisy("anti-villin 40") == "anti-villin"
    assert noisy("anti-AE75 90") == "anti-AE75"


def test_noisy_strips_percentages():
    assert noisy("Anti-ACSL5 (…)  <50%") is not None
    assert noisy("Anti-HNF4A (Hepatic Nuclear Factor 4 Alpha)  <50%") == "Anti-HNF4A (Hepatic Nuclear Factor 4 Alpha)"
    assert noisy("Anti-X 12%") == "Anti-X"


def test_noisy_leaves_names_that_contain_numbers():
    for label in [
        "Anti-IA-2",
        "Anti-GAD65",
        "Anti-Mi-2 autoantibodies",
        "Anti-TIF1-γ",
        "Glutamic acid decarboxylase 65 (GAD65)",
        "Neurofascin-155",
        "Contactin 1",
        "Phospholipase A2 receptor (PLA2R)",
        "Anti-glutamic acid decarboxylase 65 (anti-GAD65) autoantibodies",
    ]:
        assert noisy(label) is None


# --- sentence_like -----------------------------------------------------------------------------

def test_sentence_like_long_labels():
    assert sentence_like("Examples are autoantibodies against aromatic L-amino acid decarboxylase (AADC)")
    assert sentence_like("74% of patients show reactivity to cocktails of MBP/PLP/MOG peptides.")


def test_sentence_like_verb_phrases():
    assert sentence_like("DEP1/CD148 is the relevant autoantigen")
    assert sentence_like("Associated with Autoimmune Enteropathy:")
    assert sentence_like("No single antigen explains all cases")
    assert sentence_like("Tissue specific antibodies/tcells not found")
    assert sentence_like("Antibody combinations (more than one subtype are extremly common in this disease)")
    assert sentence_like("Not associated with diet (unlike celiac disease)")


def test_sentence_like_headings_urls_and_trailing_descriptions():
    assert sentence_like("IPEX specific antibodies:")
    assert sentence_like("https://ard.bmj.com/content/58/10/656")
    assert sentence_like("Mucins (predominantly MUC2) - present in Goblet Cells")


def test_sentence_like_counts_words_outside_parentheses_only():
    assert not sentence_like("U1-small nuclear ribonucleoprotein (U1-snRNP, 68/70 kDa, A, C)")
    assert not sentence_like("Anti-tryptophan hydroxylase  (enzyme in enterochromaphin cells in the gastrointestinal tract)")


def test_sentence_like_accepts_marker_names():
    for label in [
        "Anti-GAD65 autoantibodies",
        "Contactin-associated protein-like 2 (CASPR2)",
        "Melanocyte-associated antigens (tyrosinase family, TRP-1, TRP-2)",
        "Skin punch biopsy: intraepidermal nerve fiber density",
        "Anti-erythrocyte autoantibodies (warm IgG targeting Rh complex antigens)",
        "Elevated serum IgG4",
    ]:
        assert not sentence_like(label)


def test_qualifiers_are_the_agreed_list():
    assert names.QUALIFIERS == ("IgG4", "IgG", "IgA", "IgM", "IgE", "neutralizing", "blocking", "stimulating")
