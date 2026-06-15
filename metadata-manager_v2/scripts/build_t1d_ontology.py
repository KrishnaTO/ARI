#!/usr/bin/env python3
"""
Build a standalone Protege-compatible OWL ontology for Type 1 Diabetes (T1D)
and its autoimmune subtypes. No external schema dependencies.

Usage:
    python scripts/build_t1d_ontology.py [--output ontologies/ari_t1d.owl]

Dependencies: owlready2
"""
import argparse
from pathlib import Path
from owlready2 import (
    World, Thing, ObjectProperty, DataProperty, AnnotationProperty,
    label, comment, seeAlso,
)

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
BASE_IRI = "http://www.aurint.org/ontologies/ari-disease#"


def build_ontology(output_path: str):
    world = World()
    onto = world.get_ontology(BASE_IRI.rstrip("#"))

    with onto:
        # ============================================================
        # ANNOTATION PROPERTIES
        # ============================================================
        class ARI_ID(AnnotationProperty):             namespace = onto
        class ARI_Synonym(AnnotationProperty):        namespace = onto
        class ARI_Version(AnnotationProperty):        namespace = onto
        class ARI_ChangeLog(AnnotationProperty):      namespace = onto
        class ARI_SNOMED(AnnotationProperty):         namespace = onto
        class ARI_DOID(AnnotationProperty):           namespace = onto
        class ARI_UMLS(AnnotationProperty):           namespace = onto
        class ARI_MONDO(AnnotationProperty):          namespace = onto
        class ARI_ICD10(AnnotationProperty):          namespace = onto
        class ARI_PrevalenceDesc(AnnotationProperty): namespace = onto
        class ARI_Pubmed(AnnotationProperty):         namespace = onto
        class ARI_DefSource(AnnotationProperty):      namespace = onto
        class ARI_Obsolete(AnnotationProperty):       namespace = onto

        # ============================================================
        # DATA PROPERTIES
        # ============================================================
        class evidenceQuality(DataProperty):           namespace = onto; range = [str]
        class diseaseCategory(DataProperty):           namespace = onto; range = [str]
        class prevalencePer100k(DataProperty):         namespace = onto; range = [float]
        class prevalenceValue(DataProperty):           namespace = onto; range = [float]
        class incidenceRate(DataProperty):             namespace = onto; range = [str]
        class demographicBias(DataProperty):           namespace = onto; range = [str]
        class ageRange(DataProperty):                  namespace = onto; range = [str]
        class sourcePMID(DataProperty):                namespace = onto; range = [str]
        class likelihood(DataProperty):                namespace = onto; range = [str]
        class symptomDescription(DataProperty):        namespace = onto; range = [str]
        class triggerDescription(DataProperty):        namespace = onto; range = [str]
        class antibodyFrequency(DataProperty):         namespace = onto; range = [str]
        class antibodyDiagnosticValue(DataProperty):   namespace = onto; range = [str]
        class geneticProduct(DataProperty):            namespace = onto; range = [str]
        class geneticRiskEffect(DataProperty):         namespace = onto; range = [str]
        class geneticOddsRatio(DataProperty):          namespace = onto; range = [str]
        class chromosomalLocus(DataProperty):          namespace = onto; range = [str]
        class hlaEffect(DataProperty):                 namespace = onto; range = [str]
        class hlaMechanism(DataProperty):              namespace = onto; range = [str]
        class treatmentType(DataProperty):             namespace = onto; range = [str]
        class treatmentDescription(DataProperty):      namespace = onto; range = [str]
        class treatmentFdaStatus(DataProperty):        namespace = onto; range = [str]
        class etiologyDescription(DataProperty):       namespace = onto; range = [str]
        class etiologyOriginType(DataProperty):        namespace = onto; range = [str]
        class etiologyExcerpt(DataProperty):           namespace = onto; range = [str]
        class markerDiagnosticUse(DataProperty):       namespace = onto; range = [str]
        class mediatorDescription(DataProperty):       namespace = onto; range = [str]
        class componentRelevance(DataProperty):        namespace = onto; range = [str]
        class tCellRole(DataProperty):                 namespace = onto; range = [str]
        class stepOrder(DataProperty):                 namespace = onto; range = [int]
        class stepCategory(DataProperty):              namespace = onto; range = [str]
        class stepDescription(DataProperty):           namespace = onto; range = [str]

        # ============================================================
        # OBJECT PROPERTIES
        # ============================================================
        class hasParentDisease(ObjectProperty):           namespace = onto
        class hasSymptom(ObjectProperty):                 namespace = onto
        class hasEnvironmentalTrigger(ObjectProperty):    namespace = onto
        class hasAntibody(ObjectProperty):                namespace = onto
        class hasGeneticAssociation(ObjectProperty):      namespace = onto
        class hasTreatment(ObjectProperty):               namespace = onto
        class hasEtiologyFactor(ObjectProperty):          namespace = onto
        class hasBiomarker(ObjectProperty):               namespace = onto
        class hasPathwayStep(ObjectProperty):             namespace = onto
        class targetsTissue(ObjectProperty):              namespace = onto
        class hasParentCategory(ObjectProperty):          namespace = onto
        class involvesCytokine(ObjectProperty):           namespace = onto
        class involvesTCell(ObjectProperty):              namespace = onto
        class involvesAPC(ObjectProperty):                namespace = onto
        class involvesTranscriptionFactor(ObjectProperty):namespace = onto
        class involvesInnateComponent(ObjectProperty):    namespace = onto
        class involvesComplement(ObjectProperty):         namespace = onto
        class involvesReceptor(ObjectProperty):           namespace = onto
        class involvesNETosis(ObjectProperty):            namespace = onto
        class involvesInflammasome(ObjectProperty):       namespace = onto
        class involvesAcutePhaseReactant(ObjectProperty): namespace = onto
        class involvesAntigen(ObjectProperty):            namespace = onto

        # ============================================================
        # CLASSES (Thing subclasses = OWL classes)
        # ============================================================
        # Tissue hierarchy rooted at multicellular anatomical structure
        # (UBERON_0010000) per the ARI specification.
        class MulticellularAnatomicalStructure(Thing): namespace = onto
        class AnatomicalSystem(MulticellularAnatomicalStructure): namespace = onto
        class EndocrineSystem(AnatomicalSystem): namespace = onto
        class Pancreas(EndocrineSystem):    namespace = onto
        class IsletOfLangerhans(Pancreas):  namespace = onto
        class BetaCell(IsletOfLangerhans):  namespace = onto

        # Categories
        class DiseaseCategory(Thing):       namespace = onto
        class EndocrineDisease(DiseaseCategory): namespace = onto

        # Main disease type
        class AutoimmuneDisease(Thing):     namespace = onto

        # Association types
        class Symptom(Thing):                namespace = onto
        class EnvironmentalFactor(Thing):    namespace = onto
        class Autoantibody(Thing):           namespace = onto
        class GeneticFactor(Thing):          namespace = onto
        class HLAAssociation(GeneticFactor): namespace = onto
        class GeneVariant(GeneticFactor):    namespace = onto
        class Treatment(Thing):              namespace = onto
        class EtiologyOrigin(Thing):         namespace = onto
        class BiochemicalMarker(Thing):      namespace = onto
        class PathwayStep(Thing):            namespace = onto
        class Cytokine(Thing):               namespace = onto
        class TCellSubset(Thing):            namespace = onto
        class APC(Thing):                    namespace = onto
        class TranscriptionFactor(Thing):    namespace = onto
        class InnateComponent(Thing):        namespace = onto
        class ComplementComponent(Thing):    namespace = onto
        class Receptor(Thing):               namespace = onto
        class NETosisComponent(Thing):       namespace = onto
        class Inflammasome(Thing):           namespace = onto
        class AcutePhaseReactant(Thing):     namespace = onto
        class Antigen(Thing):                namespace = onto

        # Tag the root tissue class with its source UBERON identifier
        ARI_ID[MulticellularAnatomicalStructure] = ["UBERON:0010000"]

        # Human-readable labels for the tissue hierarchy classes
        label[MulticellularAnatomicalStructure] = ["Multicellular anatomical structure"]
        label[AnatomicalSystem] = ["Anatomical system"]
        label[EndocrineSystem] = ["Endocrine system"]
        label[Pancreas] = ["Pancreas"]
        label[IsletOfLangerhans] = ["Islet of Langerhans"]
        label[BetaCell] = ["Pancreatic beta cell"]

        # ============================================================
        # TISSUE TARGET INDIVIDUALS
        # ============================================================
        ti_beta  = BetaCell("Tissue_BetaCell")
        label[ti_beta] = ["Pancreatic beta cell"]
        ARI_ID[ti_beta] = ["CL:0000169"]
        ti_islet = IsletOfLangerhans("Tissue_Islet")
        label[ti_islet] = ["Islet of Langerhans"]
        ARI_ID[ti_islet] = ["UBERON:0000006"]
        ti_panc  = Pancreas("Tissue_Pancreas")
        label[ti_panc] = ["Pancreas"]
        ARI_ID[ti_panc] = ["UBERON:0001264"]

        # Category individual
        cat_endo = EndocrineDisease("Category_Endocrine")
        label[cat_endo] = ["Endocrine disease"]

        # ============================================================
        # MAIN DISEASE: TYPE 1 DIABETES
        # ============================================================
        t1d = AutoimmuneDisease("T1D_0001")
        label[t1d] = ["Type 1 diabetes mellitus"]
        ARI_ID[t1d] = ["ARI:0001"]
        comment[t1d] = [
            "Type 1 diabetes is a chronic autoimmune disease characterized by the "
            "destruction of pancreatic beta cells in the islets of Langerhans, leading "
            "to absolute insulin deficiency and hyperglycemia. The autoimmune attack is "
            "mediated by autoreactive T-cells targeting beta-cell antigens including "
            "insulin, GAD65, IA-2, and ZnT8."
        ]
        ARI_Obsolete[t1d] = ["false"]

        # Synonyms
        for s in ["T1D", "Type 1 diabetes", "Insulin-dependent diabetes mellitus",
                   "IDDM", "Juvenile-onset diabetes", "Diabetes mellitus type 1",
                   "Juvenile diabetes"]:
            ARI_Synonym[t1d].append(s)

        # Identifiers
        ARI_SNOMED[t1d] = ["46635009"]
        ARI_DOID[t1d]   = ["9744"]
        ARI_UMLS[t1d]   = ["C0011854"]
        ARI_MONDO[t1d]  = ["MONDO:0005147"]
        ARI_ICD10[t1d]  = ["E10"]

        # Metadata
        ARI_Version[t1d] = ["1.0"]
        ARI_PrevalenceDesc[t1d] = ["~0.5% global, ~1.6M US. ~500/100k globally."]
        ARI_Pubmed[t1d] = ["https://pubmed.ncbi.nlm.nih.gov/?term=type+1+diabetes+epidemiology"]
        ARI_DefSource[t1d] = ["ADA Standards of Care 2025; PMID: 38393374"]

        # Data properties
        evidenceQuality[t1d] = ["High"]
        diseaseCategory[t1d] = ["Autoimmune"]
        prevalencePer100k[t1d] = [500.0]
        prevalenceValue[t1d]   = [1600000.0]
        incidenceRate[t1d] = ["12-15/100k/yr in US"]
        demographicBias[t1d] = ["Male predominance 1.3:1; highest in Scandinavia (~60/100k/yr), lowest in East Asia (~1/100k/yr)"]
        ageRange[t1d] = ["Bimodal: 4-7y and 10-14y peaks; adult-onset LADA form"]

        # Object property links
        targetsTissue[t1d].append(ti_beta)
        targetsTissue[t1d].append(ti_islet)
        targetsTissue[t1d].append(ti_panc)
        hasParentCategory[t1d].append(cat_endo)

        # ============================================================
        # SYMPTOMS
        # ============================================================
        def add_symptom(name, lbl, lik, desc, hpo, src, obsolete=False):
            s = Symptom(name)
            label[s] = [lbl]
            likelihood[s] = [lik]
            symptomDescription[s] = [desc]
            seeAlso[s] = [hpo]
            sourcePMID[s] = [src]
            ARI_Obsolete[s] = ["true" if obsolete else "false"]
            hasSymptom[t1d].append(s)

        add_symptom("Sym_Polyuria", "Polyuria", "Very common (>=90%)",
            "Excessive urination due to osmotic diuresis from hyperglycemia",
            "HP:0100626", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_symptom("Sym_Polydipsia", "Polydipsia", "Very common (>=90%)",
            "Excessive thirst caused by dehydration from osmotic diuresis",
            "HP:0100627", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_symptom("Sym_WeightLoss", "Unintended weight loss", "Common (60-80%)",
            "Weight loss despite normal/increased appetite",
            "HP:0001824", "https://pubmed.ncbi.nlm.nih.gov/27063042/")
        add_symptom("Sym_Fatigue", "Fatigue", "Common (60-80%)",
            "Chronic tiredness from metabolic dysregulation",
            "HP:0012378", "https://pubmed.ncbi.nlm.nih.gov/28734308/")
        add_symptom("Sym_BlurredVision", "Blurred vision", "Moderate (20-40%)",
            "Lens swelling due to hyperglycemia",
            "HP:0025147", "https://pubmed.ncbi.nlm.nih.gov/17514992/")
        add_symptom("Sym_DKA", "Diabetic ketoacidosis (DKA)", "Variable (25-40%)",
            "Metabolic decompensation with ketone production",
            "HP:0001953", "https://pubmed.ncbi.nlm.nih.gov/30229690/")
        add_symptom("Sym_RecInfections", "Recurrent infections", "Moderate",
            "Increased susceptibility to skin, UT, and yeast infections",
            "HP:0002718", "https://pubmed.ncbi.nlm.nih.gov/29987771/")
        add_symptom("Sym_Nocturia", "Nocturia", "Moderate (30-50%)",
            "Nighttime urination from impaired renal concentrating ability",
            "HP:0000017", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_symptom("Sym_Irritability", "Irritability / mood changes", "Common (40-60%)",
            "Behavioral changes from hyperglycemia",
            "HP:0000737", "https://pubmed.ncbi.nlm.nih.gov/29570362/")
        add_symptom("Sym_Polyphagia", "Increased appetite (polyphagia)", "Common (50-70%)",
            "Excessive hunger despite high blood glucose",
            "HP:0002591", "https://pubmed.ncbi.nlm.nih.gov/30609683/")

        # ============================================================
        # ENVIRONMENTAL TRIGGERS
        # ============================================================
        def add_trigger(name, lbl, desc, lik, src):
            t = EnvironmentalFactor(name)
            label[t] = [lbl]
            triggerDescription[t] = [desc]
            likelihood[t] = [lik]
            sourcePMID[t] = [src]
            ARI_Obsolete[t] = ["false"]
            hasEnvironmentalTrigger[t1d].append(t)

        add_trigger("Env_Enterovirus", "Enterovirus (Coxsackie B)",
            "Viral molecular mimicry triggers beta-cell autoimmunity; viral RNA in pancreatic islets",
            "Moderate", "https://pubmed.ncbi.nlm.nih.gov/28958587/")
        add_trigger("Env_CowMilk", "Early cow's milk exposure",
            "Hypothesized antigen mimicry between bovine and human insulin",
            "Low-Moderate", "https://pubmed.ncbi.nlm.nih.gov/32484217/")
        add_trigger("Env_VitaminD", "Vitamin D deficiency",
            "Immunomodulatory role in T-cell regulation",
            "Low-Moderate", "https://pubmed.ncbi.nlm.nih.gov/25573198/")
        add_trigger("Env_MaternalAge", "Advanced maternal age",
            "Modest increase in T1D risk in offspring",
            "Weak", "https://pubmed.ncbi.nlm.nih.gov/30095980/")
        add_trigger("Env_CSection", "C-section delivery",
            "Altered microbiome may influence immune programming",
            "Weak", "https://pubmed.ncbi.nlm.nih.gov/29977825/")
        add_trigger("Env_InfantWeight", "Rapid weight gain in infancy",
            "Increased metabolic demand on beta-cells",
            "Moderate", "https://pubmed.ncbi.nlm.nih.gov/25489210/")
        add_trigger("Env_Gluten", "Early gluten exposure",
            "May modulate gut permeability and immune response",
            "Low", "https://pubmed.ncbi.nlm.nih.gov/30531442/")

        # ============================================================
        # ANTIBODIES
        # ============================================================
        antibodies = {}
        def add_antibody(name, lbl, freq, diag_val, src, obsolete=False):
            ab = Autoantibody(name)
            label[ab] = [lbl]
            antibodyFrequency[ab] = [freq]
            antibodyDiagnosticValue[ab] = [diag_val]
            sourcePMID[ab] = [src]
            ARI_Obsolete[ab] = ["true" if obsolete else "false"]
            hasAntibody[t1d].append(ab)
            antibodies[name] = ab
            return ab

        add_antibody("Ab_GAD65", "Anti-GAD65 (GADA)", "70-80%",
            "Persistent marker; slower progression in adults",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_antibody("Ab_IA2", "Anti-IA-2 (IA-2A)", "50-70%",
            "Predictive of rapid progression",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_antibody("Ab_IAA", "Anti-insulin (IAA)", "50-70% child, 10-30% adult",
            "Earliest predictor in young children",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_antibody("Ab_ZnT8", "Anti-ZnT8 (ZnT8A)", "60-80%",
            "Increases diagnostic sensitivity in combination",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        # Islet Cell Antibodies: classic marker superseded by specific assays -> obsolete
        add_antibody("Ab_ICA", "Islet Cell Antibodies (ICA)", "70-80%",
            "Classic marker; replaced by specific antigen assays",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/", obsolete=True)

        # ============================================================
        # GENETIC ASSOCIATIONS
        # ============================================================
        def add_gene(name, lbl, locus, product, effect, or_val, src):
            g = GeneVariant(name)
            label[g] = [lbl]
            chromosomalLocus[g] = [locus]
            geneticProduct[g] = [product]
            geneticRiskEffect[g] = [effect]
            geneticOddsRatio[g] = [or_val]
            sourcePMID[g] = [src]
            ARI_Obsolete[g] = ["false"]
            hasGeneticAssociation[t1d].append(g)

        add_gene("Gene_HLA_DR3", "HLA-DR3-DQ2 (DRB1*03:01-DQA1*05:01-DQB1*02:01)",
            "6p21.32", "MHC class II molecules",
            "Strongest risk; DR3/DR4 heterozygotes highest", "~5-7",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_HLA_DR4", "HLA-DR4-DQ8 (DRB1*04:01-DQA1*03:01-DQB1*03:02)",
            "6p21.32", "MHC class II molecules",
            "Strongest risk; DR3/DR4 heterozygotes highest", "~5-7",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_INS", "INS VNTR", "11p15.5", "Insulin regulatory region",
            "VNTR affects thymic insulin expression", "~2-3",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_PTPN22", "PTPN22 R620W (C1858T)", "1p13.2",
            "Protein tyrosine phosphatase N22",
            "LOF impairs TCR signalling and tolerance", "~1.5-2",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_CTLA4", "CTLA4", "2q33.2", "CTLA-4 checkpoint protein",
            "Impaired Treg function from reduced expression", "~1.2-1.5",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_IL2RA", "IL2RA (CD25)", "10p15.1", "IL-2R alpha chain",
            "Affects Treg development", "~1.1-1.3",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_IFIH1", "IFIH1 (MDA5)", "2q24.2", "Viral RNA helicase",
            "Innate antiviral sensor; LOF variants protective", "~1.2-1.4",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_gene("Gene_PTPN2", "PTPN2", "18p11.21", "TC-PTP phosphatase",
            "Beta-cell apoptosis susceptibility", "~1.1-1.3",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")

        # HLA associations
        def add_hla(name, lbl, effect, mechanism, src):
            h = HLAAssociation(name)
            label[h] = [lbl]
            hlaEffect[h] = [effect]
            hlaMechanism[h] = [mechanism]
            sourcePMID[h] = [src]
            ARI_Obsolete[h] = ["false"]
            hasGeneticAssociation[t1d].append(h)

        add_hla("HLA_DR3DQ2", "DRB1*03:01-DQA1*05:01-DQB1*02:01",
            "Strong susceptibility",
            "Presents proinsulin and GAD65 to CD4+ T-cells",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_hla("HLA_DR4DQ8", "DRB1*04:01-DQA1*03:01-DQB1*03:02",
            "Strong susceptibility",
            "Enhanced insulin B:9-23 epitope presentation",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_hla("HLA_DR2DQ6", "DRB1*15:01-DQA1*01:02-DQB1*06:02",
            "Strong protection",
            "Negative selection of autoreactive T-cells",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_hla("HLA_DR4_0403", "DRB1*04:03-DQB1*03:02",
            "Dominant protection",
            "Position 57 alters antigen binding pocket",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")

        # ============================================================
        # TREATMENTS
        # ============================================================
        def add_tx(name, lbl, tx_type, desc, fda, src):
            t = Treatment(name)
            label[t] = [lbl]
            treatmentType[t] = [tx_type]
            treatmentDescription[t] = [desc]
            treatmentFdaStatus[t] = [fda]
            sourcePMID[t] = [src]
            ARI_Obsolete[t] = ["false"]
            hasTreatment[t1d].append(t)

        add_tx("Tx_Insulin", "Exogenous insulin therapy", "Pharmacotherapy",
            "Basal-bolus: rapid-acting (lispro, aspart, glulisine) + long-acting (glargine, detemir, degludec)",
            "Approved", "https://pubmed.ncbi.nlm.nih.gov/29595638/")
        add_tx("Tx_Pump", "CSII (insulin pump)", "Medical device",
            "Continuous subcutaneous insulin infusion; improves HbA1c",
            "Approved", "https://pubmed.ncbi.nlm.nih.gov/29595638/")
        add_tx("Tx_CGM", "Continuous glucose monitor", "Medical device",
            "Real-time interstitial glucose: Dexcom G7, Libre 3, Guardian 4",
            "Approved", "https://pubmed.ncbi.nlm.nih.gov/29595638/")
        add_tx("Tx_Teplizumab", "Teplizumab (anti-CD3)", "Immunotherapy",
            "Delays T1D onset in stage 2 at-risk individuals",
            "FDA 2022", "https://pubmed.ncbi.nlm.nih.gov/31167052/")
        add_tx("Tx_ClosedLoop", "Hybrid closed-loop system", "Medical device",
            "Algorithm-driven CGM+pump; artificial pancreas",
            "Approved", "https://pubmed.ncbi.nlm.nih.gov/31163012/")
        add_tx("Tx_Transplant", "Pancreatic/islet transplant", "Surgical",
            "For severe T1D with hypoglycemia unawareness",
            "Select cases", "https://pubmed.ncbi.nlm.nih.gov/28686848/")
        add_tx("Tx_Pramlintide", "Pramlintide (amylin analog)", "Pharmacotherapy",
            "Slows gastric emptying; adjunctive to insulin",
            "Approved", "https://pubmed.ncbi.nlm.nih.gov/26612240/")

        # ============================================================
        # ETIOLOGY  (classified as Genetic / External / Idiopathic)
        # ============================================================
        def add_etio(name, lbl, origin_type, desc, excerpt, src):
            e = EtiologyOrigin(name)
            label[e] = [lbl]
            etiologyOriginType[e] = [origin_type]
            etiologyDescription[e] = [desc]
            etiologyExcerpt[e] = [excerpt]
            sourcePMID[e] = [src]
            ARI_Obsolete[e] = ["false"]
            hasEtiologyFactor[t1d].append(e)

        add_etio("Et_Genetic", "Genetic susceptibility", "Genetic",
            "~50% MZ twin concordance; polygenic risk (HLA, INS, PTPN22, CTLA4, IL2RA, IFIH1)",
            "\"The HLA region accounts for approximately 50% of the genetic risk of type 1 diabetes.\"",
            "https://pubmed.ncbi.nlm.nih.gov/21447697/")
        add_etio("Et_Viral", "Viral trigger", "External",
            "Enterovirus precedes seroconversion; viral RNA detected in islets",
            "\"Enteroviral infection is associated with the appearance of islet autoimmunity and clinical type 1 diabetes.\"",
            "https://pubmed.ncbi.nlm.nih.gov/28958587/")
        add_etio("Et_Tolerance", "Loss of immune tolerance", "Idiopathic",
            "Defective central/peripheral tolerance; impaired Treg function",
            "\"Breakdown of self-tolerance to beta-cell antigens underlies disease initiation.\"",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_etio("Et_Mimicry", "Molecular mimicry", "External",
            "Coxsackie P2-C / GAD65 homology drives cross-reactive T-cells",
            "\"Sequence homology between Coxsackievirus P2-C and GAD65 may elicit cross-reactive responses.\"",
            "https://pubmed.ncbi.nlm.nih.gov/24814487/")
        add_etio("Et_ERStress", "Beta-cell ER stress", "Idiopathic",
            "Unfolded protein response increases beta-cell immunogenicity",
            "\"ER stress in beta cells generates neoantigens that promote autoimmunity.\"",
            "https://pubmed.ncbi.nlm.nih.gov/30269450/")

        # ============================================================
        # BIOCHEMICAL MARKERS
        # ============================================================
        def add_marker(name, lbl, desc, use, src):
            m = BiochemicalMarker(name)
            label[m] = [lbl]
            comment[m] = [desc]
            markerDiagnosticUse[m] = [use]
            sourcePMID[m] = [src]
            ARI_Obsolete[m] = ["false"]
            hasBiomarker[t1d].append(m)

        add_marker("Mark_Cpeptide", "C-peptide",
            "Endogenous insulin measure; low/undetectable in T1D",
            "Diagnosis, staging", "https://pubmed.ncbi.nlm.nih.gov/27062967/")
        add_marker("Mark_HbA1c", "HbA1c",
            "3-month glucose average; diagnosis >=6.5%",
            "Diagnosis, monitoring", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_marker("Mark_FastingGlucose", "Fasting plasma glucose",
            ">=126 mg/dL after >=8h fast",
            "Diagnosis", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_marker("Mark_RandomGlucose", "Random plasma glucose",
            ">=200 mg/dL with symptoms",
            "Diagnosis", "https://pubmed.ncbi.nlm.nih.gov/30609683/")
        add_marker("Mark_Ketones", "Ketones (beta-hydroxybutyrate)",
            "Elevated in DKA",
            "DKA detection", "https://pubmed.ncbi.nlm.nih.gov/30229690/")
        add_marker("Mark_OGTT", "OGTT",
            "75g load; 2h >=200 mg/dL",
            "Diagnosis, screening", "https://pubmed.ncbi.nlm.nih.gov/30609683/")

        # ============================================================
        # PATHOPHYSIOLOGY  (ordered pathograph steps)
        # ============================================================
        def add_step(name, lbl, order, category, desc, src=""):
            p = PathwayStep(name)
            label[p] = [lbl]
            stepOrder[p] = [order]
            stepCategory[p] = [category]
            stepDescription[p] = [desc]
            if src:
                sourcePMID[p] = [src]
            hasPathwayStep[t1d].append(p)

        add_step("Path_1_Genetic", "Genetic susceptibility", 1, "Genetic",
            "HLA-DR3/DR4-DQ, INS VNTR, PTPN22, CTLA4 establish a permissive genetic background.",
            "https://pubmed.ncbi.nlm.nih.gov/25471517/")
        add_step("Path_2_Trigger", "Environmental trigger", 2, "Trigger",
            "Enteroviral infection or dietary antigens precipitate islet autoimmunity in genetically susceptible hosts.",
            "https://pubmed.ncbi.nlm.nih.gov/28958587/")
        add_step("Path_3_Tolerance", "Loss of immune tolerance", 3, "Immune",
            "Impaired central/peripheral tolerance and defective Treg function permit autoreactive clones.",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_step("Path_4_Presentation", "Antigen presentation", 4, "Immune",
            "Dendritic cells and macrophages present beta-cell antigens in pancreatic lymph nodes.",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_step("Path_5_Autoantibodies", "Autoantibody production", 5, "Antibody",
            "B-cells produce GADA, IA-2A, IAA and ZnT8A, the serological hallmark of islet autoimmunity.",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_step("Path_6_Insulitis", "T-cell insulitis", 6, "Immune",
            "CD8+ cytotoxic and CD4+ Th1 cells infiltrate the islets (insulitis).",
            "https://pubmed.ncbi.nlm.nih.gov/25614315/")
        add_step("Path_7_BetaDeath", "Beta-cell destruction", 7, "TissueDamage",
            "Perforin/granzyme, Fas-FasL and cytokine (IL-1B, IFN-g, TNF) toxicity destroy beta cells.",
            "https://pubmed.ncbi.nlm.nih.gov/30269450/")
        add_step("Path_8_Insulin", "Insulin deficiency & hyperglycemia", 8, "Outcome",
            "Loss of >80-90% beta-cell mass yields absolute insulin deficiency and clinical hyperglycemia.",
            "https://pubmed.ncbi.nlm.nih.gov/30609683/")

        # ============================================================
        # IMMUNE COMPONENTS
        # ============================================================
        def add_cytokine(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            c = Cytokine(name)
            label[c] = [lbl]
            mediatorDescription[c] = [desc]
            componentRelevance[c] = [relevance]
            sourcePMID[c] = [src]
            involvesCytokine[t1d].append(c)

        add_cytokine("Cyto_IL1B", "IL-1B",
            "Pro-inflammatory; beta-cell apoptosis via NF-kB and NO", "Beta-cell toxicity")
        add_cytokine("Cyto_IFNG", "IFN-g",
            "Macrophage activation; MHC-I upregulation", "Pro-inflammatory")
        add_cytokine("Cyto_TNF", "TNF-a",
            "Insulitis and beta-cell damage", "Pro-inflammatory")
        add_cytokine("Cyto_IL10", "IL-10",
            "Regulatory; impaired in T1D", "Regulatory (dysregulated)")
        add_cytokine("Cyto_IL21", "IL-21",
            "Tfh-derived B-cell differentiation", "Pro-inflammatory")
        add_cytokine("Cyto_IL17", "IL-17A",
            "Neutrophil recruitment to islets", "Pro-inflammatory")

        # T-Cells
        def add_tcell(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            t = TCellSubset(name)
            label[t] = [lbl]
            tCellRole[t] = [desc]
            componentRelevance[t] = [relevance]
            sourcePMID[t] = [src]
            involvesTCell[t1d].append(t)

        add_tcell("T_Th1", "CD4+ Th1 cells",
            "IFN-g mediated; dominant pathogenic subset", "Dominant pathogenic")
        add_tcell("T_Th17", "CD4+ Th17 cells",
            "IL-17; neutrophil recruitment", "Contributory")
        add_tcell("T_Treg", "CD4+ Treg cells",
            "Impaired FoxP3 and suppressive function", "Defective regulation")
        add_tcell("T_Tfh", "CD4+ Tfh cells",
            "B-cell maturation and autoantibody production", "Drive autoantibodies")
        add_tcell("T_CD8", "CD8+ cytotoxic T-cells",
            "Beta-cell destruction via perforin/granzyme, Fas-FasL", "Primary effector")

        # APC
        def add_apc(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            a = APC(name)
            label[a] = [lbl]
            mediatorDescription[a] = [desc]
            componentRelevance[a] = [relevance]
            sourcePMID[a] = [src]
            involvesAPC[t1d].append(a)

        add_apc("APC_DC", "Dendritic cells",
            "Present antigens in pancreatic lymph nodes", "Initiation")
        add_apc("APC_Macro", "Macrophages",
            "Pro-inflammatory cytokines in islets", "Inflammation")
        add_apc("APC_BCell", "B-cells",
            "APC in lymph nodes; autoantibody production", "Autoantibodies")

        # Transcription Factors
        def add_tf(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25471517/"):
            t = TranscriptionFactor(name)
            label[t] = [lbl]
            mediatorDescription[t] = [desc]
            componentRelevance[t] = [relevance]
            sourcePMID[t] = [src]
            involvesTranscriptionFactor[t1d].append(t)

        add_tf("TF_STAT4", "STAT4", "Th1 differentiation; GWAS locus", "Th1 diff")
        add_tf("TF_Tbet", "T-bet (TBX21)", "Master Th1 regulator", "Th1 lineage")
        add_tf("TF_FoxP3", "FoxP3", "Master Treg regulator; reduced in T1D", "Treg")
        add_tf("TF_RORgt", "RORgt (RORC)", "Master Th17 regulator", "Th17 lineage")

        # Innate Components
        def add_innate(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/28958587/"):
            i = InnateComponent(name)
            label[i] = [lbl]
            mediatorDescription[i] = [desc]
            componentRelevance[i] = [relevance]
            sourcePMID[i] = [src]
            involvesInnateComponent[t1d].append(i)

        add_innate("Innate_TLR2", "TLR2", "DAMPs from stressed beta-cells", "DAMP")
        add_innate("Innate_TLR4", "TLR4", "HMGB1 from necrotic beta-cells", "DAMP")
        add_innate("Innate_IFIH1", "IFIH1/MDA5", "Viral RNA sensor; GWAS", "Viral sensing")

        # Complement
        def add_comp(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            c = ComplementComponent(name)
            label[c] = [lbl]
            mediatorDescription[c] = [desc]
            componentRelevance[c] = [relevance]
            sourcePMID[c] = [src]
            involvesComplement[t1d].append(c)
        add_comp("Comp_C3", "Complement C3", "Central complement; elevated in T1D", "Islet inflammation")
        add_comp("Comp_C4", "Complement C4", "C4d deposition in islets", "Classical pathway")

        # Receptors
        def add_receptor(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25471517/"):
            r = Receptor(name)
            label[r] = [lbl]
            mediatorDescription[r] = [desc]
            componentRelevance[r] = [relevance]
            sourcePMID[r] = [src]
            involvesReceptor[t1d].append(r)

        add_receptor("Rec_IL2R", "IL-2R (CD25)", "Treg maintenance; GWAS locus", "Treg")
        add_receptor("Rec_CTLA4", "CTLA-4 (CD152)", "Checkpoint; reduced in T1D", "Checkpoint")
        add_receptor("Rec_PD1", "PD-1 (CD279)", "Inhibitory; T1D polymorphisms", "Exhaustion")
        add_receptor("Rec_Fas", "Fas (CD95)", "Death receptor on beta-cells", "Apoptosis")

        # NETosis
        def add_netosis(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            n = NETosisComponent(name)
            label[n] = [lbl]
            mediatorDescription[n] = [desc]
            componentRelevance[n] = [relevance]
            sourcePMID[n] = [src]
            involvesNETosis[t1d].append(n)

        add_netosis("NET_NETs", "Neutrophil extracellular traps (NETs)",
            "Increased NETosis precedes T1D onset; NET components deposit in islets", "Early autoimmunity")
        add_netosis("NET_PAD4", "PAD4 (citrullination)",
            "Peptidylarginine deiminase 4 drives NET formation and neoantigen citrullination", "Neoantigen generation")
        add_netosis("NET_MPO", "Myeloperoxidase (MPO)",
            "NET-associated enzyme; elevated neutrophil activity in new-onset T1D", "Inflammatory marker")

        # Inflammasome
        def add_inflammasome(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/30269450/"):
            i = Inflammasome(name)
            label[i] = [lbl]
            mediatorDescription[i] = [desc]
            componentRelevance[i] = [relevance]
            sourcePMID[i] = [src]
            involvesInflammasome[t1d].append(i)

        add_inflammasome("Inf_NLRP3", "NLRP3 inflammasome",
            "Activated by beta-cell DAMPs; drives caspase-1 cleavage and IL-1B maturation", "IL-1B activation")
        add_inflammasome("Inf_Caspase1", "Caspase-1",
            "Effector protease converting pro-IL-1B/pro-IL-18 to active cytokines", "Cytokine maturation")
        add_inflammasome("Inf_ASC", "ASC (PYCARD)",
            "Adaptor protein nucleating inflammasome assembly", "Inflammasome scaffold")

        # Acute Phase Reactants
        def add_apr(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            a = AcutePhaseReactant(name)
            label[a] = [lbl]
            mediatorDescription[a] = [desc]
            componentRelevance[a] = [relevance]
            sourcePMID[a] = [src]
            involvesAcutePhaseReactant[t1d].append(a)

        add_apr("APR_CRP", "C-reactive protein (CRP)",
            "Low-grade elevation reflects subclinical inflammation in T1D", "Inflammation marker")
        add_apr("APR_SAA", "Serum amyloid A (SAA)",
            "Acute-phase protein raised during islet inflammation", "Inflammation marker")
        add_apr("APR_Fibrinogen", "Fibrinogen",
            "Elevated in T1D; contributes to vascular complication risk", "Vascular risk")

        # Antigens
        def add_antigen(name, lbl, desc, relevance, src="https://pubmed.ncbi.nlm.nih.gov/25614315/"):
            a = Antigen(name)
            label[a] = [lbl]
            mediatorDescription[a] = [desc]
            componentRelevance[a] = [relevance]
            sourcePMID[a] = [src]
            involvesAntigen[t1d].append(a)

        add_antigen("Antigen_Insulin", "(Pro)insulin",
            "Primary autoantigen; B:9-23 epitope central to disease initiation", "Primary autoantigen")
        add_antigen("Antigen_GAD65", "GAD65 (glutamic acid decarboxylase 65)",
            "Major islet autoantigen targeted by GADA", "Major autoantigen")
        add_antigen("Antigen_IA2", "IA-2 (tyrosine phosphatase)",
            "Islet autoantigen; target of IA-2A", "Autoantigen")
        add_antigen("Antigen_ZnT8", "ZnT8 (zinc transporter 8)",
            "Beta-cell zinc transporter; target of ZnT8A", "Autoantigen")

        # ============================================================
        # SUBTYPE DISEASES (children of T1D for the parent/child view)
        # ============================================================
        def add_subtype(name, lbl, ari_id, definition, synonyms, identifiers,
                        prevalence_per_100k, prevalence_desc, evidence, age,
                        symptoms_spec, antibodies_spec, def_source):
            d = AutoimmuneDisease(name)
            label[d] = [lbl]
            ARI_ID[d] = [ari_id]
            comment[d] = [definition]
            ARI_Obsolete[d] = ["false"]
            ARI_Version[d] = ["1.0"]
            diseaseCategory[d] = ["Autoimmune"]
            evidenceQuality[d] = [evidence]
            ageRange[d] = [age]
            prevalencePer100k[d] = [prevalence_per_100k]
            ARI_PrevalenceDesc[d] = [prevalence_desc]
            ARI_DefSource[d] = [def_source]
            for s in synonyms:
                ARI_Synonym[d].append(s)
            for k, v in identifiers.items():
                {"snomed": ARI_SNOMED, "doid": ARI_DOID, "umls": ARI_UMLS,
                 "mondo": ARI_MONDO, "icd10": ARI_ICD10}[k][d] = [v]
            # parent / shared structure
            hasParentDisease[d].append(t1d)
            hasParentCategory[d].append(cat_endo)
            targetsTissue[d].append(ti_beta)
            targetsTissue[d].append(ti_islet)
            # a few symptoms
            for sname, slbl, slik, sdesc, shpo, ssrc in symptoms_spec:
                s = Symptom(sname)
                label[s] = [slbl]; likelihood[s] = [slik]
                symptomDescription[s] = [sdesc]; seeAlso[s] = [shpo]
                sourcePMID[s] = [ssrc]; ARI_Obsolete[s] = ["false"]
                hasSymptom[d].append(s)
            # a couple antibodies (reuse existing antibody individuals where given)
            for abname, ablbl, abfreq, abdiag, absrc in antibodies_spec:
                ab = Autoantibody(abname)
                label[ab] = [ablbl]; antibodyFrequency[ab] = [abfreq]
                antibodyDiagnosticValue[ab] = [abdiag]; sourcePMID[ab] = [absrc]
                ARI_Obsolete[ab] = ["false"]
                hasAntibody[d].append(ab)
            ARI_ChangeLog[d] = ["2026-06-12 | System | Initial subtype entry"]
            return d

        add_subtype(
            "T1D_0002", "Latent autoimmune diabetes in adults (LADA)", "ARI:0002",
            "LADA is a slowly progressive form of autoimmune diabetes presenting in adulthood, "
            "characterized by GAD65 autoantibodies and gradual beta-cell failure that initially "
            "does not require insulin, bridging type 1 and type 2 diabetes phenotypes.",
            ["LADA", "Type 1.5 diabetes", "Slowly progressive IDDM", "Latent autoimmune diabetes"],
            {"doid": "9744", "umls": "C2987933", "mondo": "MONDO:0011027", "icd10": "E10"},
            8.0, "~5-10% of adult-onset diabetes; ~8/100k.", "Moderate",
            "Adult-onset, typically >30 years",
            [("Sym_LADA_Thirst", "Polydipsia", "Common (50-70%)",
              "Gradual onset thirst as beta-cell function declines", "HP:0100627",
              "https://pubmed.ncbi.nlm.nih.gov/26494507/"),
             ("Sym_LADA_WeightLoss", "Gradual weight loss", "Moderate",
              "Slow weight loss over months to years", "HP:0001824",
              "https://pubmed.ncbi.nlm.nih.gov/26494507/")],
            [("Ab_LADA_GAD65", "Anti-GAD65 (GADA)", "90-100%",
              "Defining serological marker of LADA",
              "https://pubmed.ncbi.nlm.nih.gov/26494507/")],
            "Diabetes Care LADA consensus; PMID: 32086290")

        add_subtype(
            "T1D_0003", "Fulminant type 1 diabetes", "ARI:0003",
            "Fulminant T1D is a rare, abrupt-onset subtype characterized by very rapid beta-cell "
            "destruction over days, near-normal HbA1c at presentation despite severe hyperglycemia, "
            "and frequent absence of islet autoantibodies. Most cases are reported in East Asia.",
            ["Fulminant diabetes", "Acute-onset type 1 diabetes"],
            {"umls": "C2349037", "mondo": "MONDO:0014523", "icd10": "E10"},
            0.5, "Rare; predominantly East Asian populations. <1/100k.", "Moderate",
            "Any age; often associated with pregnancy",
            [("Sym_Ful_DKA", "Fulminant ketoacidosis", "Very common (>=90%)",
              "Severe DKA within days of symptom onset", "HP:0001953",
              "https://pubmed.ncbi.nlm.nih.gov/17456842/"),
             ("Sym_Ful_Flu", "Flu-like prodrome", "Common (70%)",
              "Preceding viral-like illness before abrupt onset", "HP:0033273",
              "https://pubmed.ncbi.nlm.nih.gov/17456842/")],
            [("Ab_Ful_GAD65", "Anti-GAD65 (GADA)", "<5%",
              "Usually negative, distinguishing it from classic T1D",
              "https://pubmed.ncbi.nlm.nih.gov/17456842/")],
            "Japan Diabetes Society criteria; PMID: 22912766")

        # ============================================================
        # CHANGE LOG (parent disease)
        # ============================================================
        ARI_ChangeLog[t1d] = ["2026-06-12 | System | Initial T1D entry creation"]
        ARI_ChangeLog[t1d].append(
            "2026-06-12 | System | 10 symptoms, 7 triggers, 5 antibodies, 12 genetic, "
            "7 treatments, 5 etiology, 6 markers, 8 pathway steps, immune components, "
            "NETosis/inflammasome/APR/antigens, 2 subtypes")

    # ================================================================ #
    # SAVE
    # ================================================================ #
    onto.save(file=output_path, format="rdfxml")
    print(f"OK Ontology saved to: {output_path}")
    print(f"  Disease: Type 1 Diabetes mellitus (T1D_0001) + 2 subtypes")
    print(f"  Classes: {len(list(onto.classes()))}")
    print(f"  Individuals: {len(list(onto.individuals()))}")
    print(f"  Object props: {len(list(onto.object_properties()))}")
    print(f"  Data props: {len(list(onto.data_properties()))}")
    print(f"  Annotation props: {len(list(onto.annotation_properties()))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build T1D OWL ontology")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "ontologies" / "ari_t1d.owl"),
                        help="Output OWL file path")
    args = parser.parse_args()
    build_ontology(args.output)
