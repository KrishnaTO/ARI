"""Editable disease-data item schema.

Each entry in ``CATEGORIES`` describes one editable category of disease-data
items. It drives both the add/edit forms in the UI and the generic field-setter
in :mod:`app.ontology_service`. For a field, ``read`` is the key in the
disease-detail item object returned by the API, while ``key`` is the OWL
property suffix (or a special ``kind``) used when writing the value back.
"""

SEEALSO_IRI = "http://www.w3.org/2000/01/rdf-schema#seeAlso"


def _field(key, label_, type_, read, kind, options=None):
    f = {"key": key, "label": label_, "type": type_, "read": read, "kind": kind}
    if options:
        f["options"] = options
    return f


_NAME = _field("name", "Label", "text", "name", "label")
_OBS = _field("obsolete", "Obsolete", "checkbox", "obsolete", "obsolete")
_SRC = _field("sourcePMID", "Source URL", "text", "source", "data")


def _immune(cls, link, prefix, label_, desc_suffix="mediatorDescription"):
    """Build a category spec for the immune/molecular components, which all
    share the same three editable fields (label, description, relevance)."""
    return {
        "label": label_, "cls": cls, "link": link, "id_prefix": prefix,
        "fields": [
            _NAME,
            _field(desc_suffix, "Description", "area", "description", "data"),
            _field("componentRelevance", "Relevance", "text", "relevance", "data"),
            _SRC,
            _OBS,
        ],
    }


CATEGORIES = {
    "symptoms": {"label": "Symptom", "cls": "Symptom", "link": "hasSymptom", "id_prefix": "Sym", "fields": [
        _NAME,
        _field("likelihood", "Likelihood", "text", "likelihood", "data"),
        _field("symptomDescription", "Description", "area", "description", "data"),
        _field("seeAlso", "HPO id", "text", "seeAlso", "seeAlso"),
        _SRC, _OBS]},
    "environmental": {"label": "Environmental factor", "cls": "EnvironmentalFactor", "link": "hasEnvironmentalTrigger", "id_prefix": "Env", "fields": [
        _NAME,
        _field("triggerDescription", "Description", "area", "description", "data"),
        _field("likelihood", "Likelihood", "text", "likelihood", "data"),
        _SRC, _OBS]},
    "antibodies": {"label": "Autoantibody", "cls": "Autoantibody", "link": "hasAntibody", "id_prefix": "Ab", "fields": [
        _NAME,
        _field("antibodyFrequency", "Frequency", "text", "frequency", "data"),
        _field("antibodyDiagnosticValue", "Diagnostic value", "text", "diagnostic_value", "data"),
        _SRC, _OBS]},
    "genetic": {"label": "Genetic association", "cls": "GeneVariant", "link": "hasGeneticAssociation", "id_prefix": "Gene", "fields": [
        _NAME,
        _field("chromosomalLocus", "Locus", "text", "locus", "data"),
        _field("geneticProduct", "Product", "text", "product", "data"),
        _field("geneticRiskEffect", "Risk effect", "text", "risk_effect", "data"),
        _field("geneticOddsRatio", "Odds ratio", "text", "odds_ratio", "data"),
        _field("hlaEffect", "HLA effect", "text", "hla_effect", "data"),
        _field("hlaMechanism", "HLA mechanism", "area", "hla_mechanism", "data"),
        _SRC, _OBS]},
    "treatments": {"label": "Treatment", "cls": "Treatment", "link": "hasTreatment", "id_prefix": "Tx", "fields": [
        _NAME,
        _field("treatmentType", "Type", "text", "type", "data"),
        _field("treatmentDescription", "Description", "area", "description", "data"),
        _field("treatmentFdaStatus", "FDA status", "text", "fda_status", "data"),
        _SRC, _OBS]},
    "etiology": {"label": "Etiology origin", "cls": "EtiologyOrigin", "link": "hasEtiologyFactor", "id_prefix": "Et", "fields": [
        _NAME,
        _field("etiologyOriginType", "Origin type", "select", "origin_type", "data", ["Genetic", "External", "Idiopathic"]),
        _field("etiologyDescription", "Description", "area", "description", "data"),
        _field("etiologyExcerpt", "Study excerpt", "area", "excerpt", "data"),
        _SRC, _OBS]},
    "biomarkers": {"label": "Biochemical marker", "cls": "BiochemicalMarker", "link": "hasBiomarker", "id_prefix": "Mark", "fields": [
        _NAME,
        _field("definition", "Description", "area", "description", "comment"),
        _field("markerDiagnosticUse", "Diagnostic use", "text", "diagnostic_use", "data"),
        _SRC, _OBS]},
    "pathophysiology": {"label": "Pathway step", "cls": "PathwayStep", "link": "hasPathwayStep", "id_prefix": "Path", "fields": [
        _NAME,
        _field("stepOrder", "Order", "number", "order", "intdata"),
        _field("stepCategory", "Category", "select", "category", "data", ["Genetic", "Trigger", "Immune", "Antibody", "TissueDamage", "Outcome"]),
        _field("stepDescription", "Description", "area", "description", "data"),
        _SRC]},
    "cytokines": _immune("Cytokine", "involvesCytokine", "Cyto", "Cytokine"),
    "tcells": _immune("TCellSubset", "involvesTCell", "T", "T-cell subset", "tCellRole"),
    "apcs": _immune("APC", "involvesAPC", "APC", "Antigen presenting cell"),
    "transcription": _immune("TranscriptionFactor", "involvesTranscriptionFactor", "TF", "Transcription factor"),
    "innate": _immune("InnateComponent", "involvesInnateComponent", "Innate", "Innate component"),
    "complement": _immune("ComplementComponent", "involvesComplement", "Comp", "Complement component"),
    "receptors": _immune("Receptor", "involvesReceptor", "Rec", "Receptor"),
    "netosis": _immune("NETosisComponent", "involvesNETosis", "NET", "NETosis component"),
    "inflammasome": _immune("Inflammasome", "involvesInflammasome", "Inf", "Inflammasome component"),
    "apr": _immune("AcutePhaseReactant", "involvesAcutePhaseReactant", "APR", "Acute phase reactant"),
    "antigens": _immune("Antigen", "involvesAntigen", "Antigen", "Antigen"),
}
