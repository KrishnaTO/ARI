"""Add the review of every listed symptom to report 13 (data/4-reports/13_Non_Symptom_Review.tsv).

Report 13 began as the review of entries already judged "not a symptom". This pass reviews the
other side: every Symptom individual a disease lists with hasSymptom in ontologies/ari_disease.owl
(2,227 listings of 817 distinct strings over 218 diseases on 2026-11-05). Each string was read and
judged; most are symptoms and need nothing. The ones that do are in JUDGMENTS below:

  - compound: several symptoms in one entry ("Fluctuating neurological symptoms (confusion,
    transient focal deficits, seizure, coma)"). `proposed` lists the parts it splits into, each with
    the ARIS class whose label or synonym matches it, or "(new)" when ari_symptoms.owl has none.
    A part that is a test result or a disease is named with the field it belongs in instead.
  - finding: a test, imaging or examination result, not something the patient experiences or
    sees ("Microangiopathic hemolytic anemia with schistocytes on blood smear"). A laboratory value
    is proposed as hasBiomarker; an examination, imaging or biopsy finding has no field
    ("no field: diagnostic finding"), as in the first pass.
  - related condition: a disease or syndrome of its own listed as a symptom ("Carpal tunnel
    syndrome"). Proposed as ARI_AssociatedDisease, with the ARI disease when ARI has one.
  - trigger, onset or course, too general: as in the first pass.

Each row carries the entry's context the way build_non_symptom_review.py writes it: the individual,
its likelihood, and its seq and neighbours in report 4's Symptoms sheet. A row already in the table
(same disease and entry) is left as it is, so the script can be rerun. build_non_symptom_review.py
keeps these rows on a rebuild, as it keeps any reviewed row.

Usage: python review_listed_symptoms.py
"""
import collections, csv, re
import xml.etree.ElementTree as ET

import openpyxl

from build_non_symptom_review import COLUMNS, REVIEW as REVIEW_PATH
from build_symptom_report import ARI, ARI_BASE, DISEASE, OBOINOWL, OWL, RDF, RDFS, REPORT, SKOS, SYMPTOMS

BIO = "hasBiomarker: "
EXAM = "no field: "
ASSOC = "ARI_AssociatedDisease: "

# entry -> (kind, [parts] or proposal, note). A list is a split: each part is a symptom label,
# looked up in ari_symptoms.owl, or a proposal for another field (it starts with BIO, EXAM or ASSOC).
JUDGMENTS = {
    # --- compound: several symptoms in one entry -------------------------------------------------
    "Fluctuating neurological symptoms (confusion, transient focal deficits, seizure, coma)": (
        "compound", ["Confusion", "Transient focal neurological deficits", "Seizures", "Coma"],
        "'fluctuating' becomes the symptomDescription of each part"),
    "Abrupt shaking chills, high fever, and back/flank or abdominal pain": (
        "compound", ["Chills", "Fever", "Back pain", "Flank pain", "Abdominal pain"],
        "'abrupt' becomes the symptomDescription of each part"),
    "Acute psychiatric disturbances (affective changes, anxiety, psychosis)": (
        "compound", ["Mood changes", "Anxiety", "Psychosis"], ""),
    "Psychiatric disturbances (confusion, paranoia, hallucinations)": (
        "compound", ["Confusion", "Paranoid delusions", "Hallucinations"], ""),
    "Marked psychiatric and behavioral changes (agitation, psychosis)": (
        "compound", ["Agitation", "Psychosis"], ""),
    "Behavioral changes, confusion, and psychosis": (
        "compound", ["Behavioral changes", "Confusion", "Psychosis"], ""),
    "Encephalopathy, confusion, and delirium": (
        "compound", ["Confusion", "Delirium"], "encephalopathy is the syndrome the two make up"),
    "Altered consciousness / somnolence, stupor, or coma": (
        "compound", ["Drowsiness", "Stupor", "Coma"], ""),
    "Acute/subacute limbic amnesia and confusion": ("compound", ["Memory problems", "Confusion"], ""),
    "Allodynia, dysesthesias, and hyperalgesia": ("compound", ["Allodynia", "Dysesthesia", "Hyperalgesia"], ""),
    "Arthralgias or inflammatory arthritis": ("compound", ["Joint pain", "Swollen joints"], ""),
    "Autonomic symptoms (altered sweating, dry mouth/eyes, gastrointestinal dysmotility)": (
        "compound", ["Altered sweating", "Dry mouth", "Dry eyes", "Gastrointestinal dysmotility"], ""),
    "Autonomic dysregulation and neurogenic bladder": (
        "compound", ["Autonomic dysfunction", "Neurogenic urinary retention"], ""),
    "Severe gastrointestinal dysmotility (gastroparesis, pseudo-obstruction, constipation)": (
        "compound", ["Gastroparesis", "Intestinal pseudo-obstruction", "Constipation"], ""),
    "Sympathetic adrenergic symptoms (sweating, palpitations, tremors)": (
        "compound", ["Excessive sweating", "Heart palpitations", "Tremor"], ""),
    "CNS hyperexcitability: hyperekplexia (exaggerated startle), myoclonus, tremor": (
        "compound", ["Exaggerated startle", "Myoclonus", "Tremor"], ""),
    "Peripheral nerve hyperexcitability (myokymia, fasciculations, muscle cramps)": (
        "compound", ["Myokymia", "Muscle fasciculations", "Muscle cramps"], ""),
    "Muscle fasciculations, myokymia, and muscle cramps": (
        "compound", ["Muscle fasciculations", "Myokymia", "Muscle cramps"], ""),
    "Movement disorders (chorea, catatonia, opsoclonus)": ("compound", ["Chorea", "Catatonia", "Opsoclonus"], ""),
    "Chorea, dystonia, or abnormal ocular movements": (
        "compound", ["Chorea", "Dystonia", "Abnormal eye movements"], ""),
    "Bulbar dysfunction (dysphagia, dysarthria, vocal cord palsy)": (
        "compound", ["Difficulty swallowing", "Difficulty speaking", "Hoarseness"],
        "vocal cord palsy is seen on laryngoscopy; hoarseness is how it shows"),
    "Benign lymphadenopathy and splenomegaly": ("compound", ["Swollen lymph nodes", "Enlarged spleen"], ""),
    "Chronic lymphadenopathy and hepatosplenomegaly": (
        "compound", ["Swollen lymph nodes", "Enlarged liver", "Enlarged spleen"], ""),
    "Massive hepatosplenomegaly and chronic lymphadenopathy": (
        "compound", ["Enlarged liver", "Enlarged spleen", "Swollen lymph nodes"], ""),
    "Chronic disabling fatigue and unrefreshing sleep": ("compound", ["Fatigue", "Unrefreshing sleep"], ""),
    "Chronic fatigue and severe post-exertional exhaustion": (
        "compound", ["Fatigue", "Post-exertional malaise"], ""),
    "Cognitive derealization, apathy, and altered perception": (
        "compound", ["Derealization", "Apathy", "Altered perception"], ""),
    "Cognitive impairment, memory loss, and brain fog": (
        "compound", ["Cognitive impairment", "Memory problems", "Brain fog"], ""),
    "Progressive cognitive impairment and amnesia": ("compound", ["Cognitive impairment", "Memory problems"], ""),
    "Rapid cognitive and behavioral decline": ("compound", ["Mental decline", "Behavioral changes"], ""),
    "Subacute anterograde memory loss and spatial disorientation": (
        "compound", ["Memory problems", "Disorientation"], ""),
    "Cramping abdominal pain and lower abdominal tenderness": (
        "compound", ["Abdominal cramps", "Abdominal tenderness"], ""),
    "Diffuse myalgias and muscle weakness": ("compound", ["Muscle pain", "Weakness"], ""),
    "Pronounced muscle atrophy and myalgias": ("compound", ["Muscle loss", "Muscle pain"], ""),
    "Distal lower limb numbness, paresthesias, and pain": (
        "compound", ["Numbness", "Tingling", "Leg pain"], "'distal lower limb' becomes the symptomDescription"),
    "Hypersexuality and disinhibited behaviors": ("compound", ["Hypersexuality", "Disinhibition"], ""),
    "Involuntary weight loss, malabsorption, and chronic fatigue": (
        "compound", ["Weight loss", "Malabsorption", "Fatigue"], ""),
    "Severe malabsorption, cachexia, and involuntary weight loss": (
        "compound", ["Malabsorption", "Cachexia", "Weight loss"], ""),
    "Severe failure to thrive and cachexia": ("compound", ["Failure to thrive", "Cachexia"], ""),
    "Prodromal severe diarrhea and weight loss": (
        "compound", ["Diarrhea", "Weight loss"], "'prodromal' becomes the symptomDescription"),
    "Laryngospasm and stridor": ("compound", ["Laryngospasm", "High-pitched sound during breathing"], ""),
    "Mucocutaneous, hematuric, and gastrointestinal bleeding": (
        "compound", ["Excessive bleeding", "Blood in urine", "Blood in stool"], ""),
    "Mucosal blister formation and erosions": ("compound", ["Mucosal blisters", "Mucosal erosions"], ""),
    "Nocturnal cough and pulmonary aspiration": ("compound", ["Cough", "Pulmonary aspiration"], "'nocturnal' becomes the symptomDescription of Cough"),
    "Nyctalopia and diminished color discrimination": (
        "compound", ["Loss of low-light vision", "Difficulty seeing color"], ""),
    "Palpitations and tremulousness upon standing": (
        "compound", ["Heart palpitations", "Tremor"], "'upon standing' becomes the symptomDescription"),
    "Peripheral and periorbital subcutaneous edema": ("compound", ["Edema", "Swelling around eyes"], ""),
    "Marked bilateral dependent peripheral pitting edema and anasarca": (
        "compound", ["Edema", "Anasarca"], ""),
    "Perioral, lingual, and digital paresthesias / tingling": (
        "compound", ["Perioral tingling", "Tingling of tongue", "Tingling of extremities"], ""),
    "Presyncope, lightheadedness, and orthostatic dizziness": (
        "compound", ["Lightheadedness", "Dizziness"], "presyncope is lightheadedness; 'orthostatic' becomes the symptomDescription of Dizziness"),
    "Exertional presyncope or syncope": (
        "compound", ["Lightheadedness", "Fainting"], "'exertional' becomes the symptomDescription"),
    "Progressive exertional dyspnea and exercise limitation": (
        "compound", ["Shortness of breath with exertion", "Difficulty exercising"], ""),
    "Progressive gait instability and appendicular limb ataxia": ("compound", ["Unsteady gait", "Impaired coordination"], ""),
    "Progressive gait instability and ataxia": ("compound", ["Unsteady gait", "Impaired coordination"], ""),
    "Severe sensory ataxia with gait failure": ("compound", ["Sensory ataxia", "Difficulty walking"], ""),
    "Severe central cerebellar and sensory ataxia": ("compound", ["Cerebellar ataxia", "Sensory ataxia"], ""),
    "Prominent 'V-sign', 'shawl sign', and extensive poikiloderma": (
        "compound", ["V-sign rash", "Shawl sign rash", "Poikiloderma"], ""),
    "Rectal urgency, tenesmus, and fecal incontinence": (
        "compound", ["Bowel movement urgency", "Tenesmus", "Loss of bowel control"], ""),
    "Recurrent hemoptysis and chronic cough": ("compound", ["Coughing up blood", "Cough"], ""),
    "Severe dysphagia and neck flexor weakness": ("compound", ["Difficulty swallowing", "Weakness in neck"], ""),
    "Severe neck flexor weakness and prominent dysphagia": (
        "compound", ["Weakness in neck", "Difficulty swallowing"], ""),
    "Severe pseudomembranous conjunctivitis and genital erosions": (
        "compound", ["Conjunctivitis", "Painful genital sores"], ""),
    "Severe, painful, refractory polymorphous stomatitis and extensive oral mucosal erosions": (
        "compound", ["Mouth sores", "Oral mucosal erosions"], ""),
    "Systemic fatigue, asthenia, and chest tightness": ("compound", ["Fatigue", "Weakness", "Heaviness in chest"], ""),
    "Upper eyelid fullness, edema, and ptosis": ("compound", ["Swelling around eyes", "Eyelid drooping"], ""),
    "Vitreous floaters and hazy vision": ("compound", ["Floaters in vision", "Blurred vision"], ""),
    "Weight loss, low-grade fevers, and cyanosis in advanced disease": (
        "compound", ["Weight loss", "Low-grade fever", "Cyanosis"],
        "'in advanced disease' becomes the symptomDescription of each part"),
    "Extraintestinal manifestations (peripheral arthritis, uveitis, aphthae)": (
        "compound", ["Swollen joints", "Eye inflammation", "Mouth ulcers"], ""),
    "Immune-related maculopapular dermatitis and vitiligo-like depigmentation": (
        "compound", ["Maculopapular rash", "Skin pigmentation loss"], ""),
    "Polymorphic cutaneous eruptions: lichenoid, bullous, or targetoid lesions": (
        "compound", ["Lichenoid lesions", "Blisters", "Target lesions"], ""),
    "Extensive eczematous or psoriasiform dermatitis": ("compound", ["Eczema-like rash", "Psoriasis-like rash"], ""),
    "Signs of hyperandrogenism (severe hirsutism, virilization, amenorrhea) in women": (
        "compound", ["Excess hair growth", "Virilization", "Absent menstrual period"],
        "'in women' becomes the symptomDescription of each part"),
    "Postnatal growth failure and severe short stature": ("compound", ["Delayed growth", "Short stature"], ""),
    "Early intractable limbic seizures and temporal lobe status": ("compound", ["Seizures", "Status epilepticus"], ""),
    "Refractory status epilepticus / frequent multifocal seizures": ("compound", ["Status epilepticus", "Seizures"], ""),
    "Painful and decreased eye movements": ("compound", ["Eye pain", "Limited eye movement"], "'with eye movement' becomes the symptomDescription of Eye pain"),
    "Acute/subacute painful visual loss (unilateral or bilateral)": ("compound", ["Vision loss", "Eye pain"], ""),
    "Irritability / mood changes": ("compound", ["Irritability", "Mood changes"], ""),
    "An increase in perspiration or warm, moist skin": ("compound", ["Excessive sweating", "Warm, moist skin"], ""),
    "A feeling of fullness or pressure in the chest or abdomen that can cause difficulty breathing or eating": (
        "compound", ["Heaviness in chest", "Abdominal fullness", "Difficulty breathing", "Difficulty eating"], ""),
    "Red, dry, cracked, and swollen lips": ("compound", ["Red lips", "Dry, cracked lips", "Swollen lips"], ""),
    "Fingernails and toenails have dents, white spots, and roughness": (
        "compound", ["Nail pitting", "White spots on nails", "Rough nails"], ""),
    "When blood starts to return to these areas, fingers or toes that turn red, burn, throb, experience numbness, or tingle.": (
        "compound", ["Red fingers or toes", "Burning", "Throbbing pain in limbs", "Numbness", "Tingling"],
        "'when blood returns to the fingers or toes' becomes the symptomDescription of each part"),
    "Meningoencephalitis symptoms: subacute fever, severe headache, and neck stiffness": (
        "compound", ["Fever", "Headache", "Neck stiffness"], ""),
    "Myelopathy with spinal paraparesis and sensory deficit": (
        "compound", ["Partial paralysis of the legs", "Sensory impairment"], "myelopathy is the diagnosis"),
    "Sicca syndrome (severe dry mouth and dry eyes)": ("compound", ["Dry mouth", "Dry eyes"], ""),
    "Diabetes insipidus (polyuria, polydipsia)": (
        "compound", ["Polyuria", "Polydipsia", ASSOC + "Autoimmune diabetes insipidus (neurogenic) (ARI:0001025)"], ""),
    "Rapidly progressive, symmetric sensorimotor polyradiculoneuropathy": (
        "compound", ["Weakness", "Sensory impairment"],
        "polyradiculoneuropathy is the diagnosis (nerve conduction studies); 'rapidly progressive, symmetric' "
        "becomes the symptomDescription"),
    "Limbic encephalitis with cognitive decline": (
        "compound", ["Mental decline", ASSOC + "Limbic encephalitis (ARI:0001121)"], ""),
    "Autoimmune hypophysitis with severe headache and fatigue": (
        "compound", ["Headache", "Fatigue", ASSOC + "Autoimmune hypophysitis (ARI:0001035)"], ""),
    "Immune-mediated colitis with severe watery diarrhea and abdominal cramps": (
        "compound", ["Diarrhea", "Abdominal cramps", ASSOC + "colitis"], ""),
    "Early-onset refractory autoimmune enteropathy with chronic watery diarrhea": (
        "compound", ["Diarrhea", ASSOC + "Autoimmune enteropathy (ARI:0001220)"], ""),
    "Severe autoimmune enteropathy / lymphocytic colitis with chronic diarrhea": (
        "compound", ["Diarrhea", ASSOC + "Autoimmune enteropathy (ARI:0001220)", ASSOC + "Microscopic colitis (ARI:0001128)"],
        "lymphocytic colitis is a form of microscopic colitis"),
    "Severe chronic autoimmune enteropathy with intractable diarrhea": (
        "compound", ["Diarrhea", ASSOC + "Autoimmune enteropathy (ARI:0001220)"], ""),
    "Opportunistic fungal infections (cryptococcosis, penicilliosis)": (
        "related condition", [ASSOC + "cryptococcosis", ASSOC + "talaromycosis (penicilliosis)"], ""),

    # --- compound, with a test or examination result in it ------------------------------------
    "Profound consumptive thrombocytopenia with purpura and bleeding": (
        "compound", ["Purple skin where blood has collected just beneath the surface of the skin", "Excessive bleeding",
                     BIO + "low platelet count"], ""),
    "Acute severe intravascular hemolytic anemia, pallor, and jaundice": (
        "compound", ["Pale skin", "Yellow skin", BIO + "intravascular hemolysis"], ""),
    "Heavy nephrotic-range proteinuria (>3.5 g/24h) with foamy urine": (
        "compound", ["Foamy, frothy urine", BIO + "proteinuria >3.5 g/24h"], ""),
    "Hypogammaglobulinemia with recurrent severe sinopulmonary infections": (
        "compound", ["Frequent infections", BIO + "low serum immunoglobulins"], ""),
    "Hypogammaglobulinemia with recurrent sinopulmonary bacterial infections": (
        "compound", ["Recurrent sinopulmonary infections", BIO + "low serum immunoglobulins"], ""),
    "Severe polyuria (>3–5 L/24h) with dilute urine": (
        "compound", ["Polyuria", BIO + "low urine osmolality"], "'>3–5 L/24h' becomes the symptomDescription"),
    "Hypernatremic dehydration when fluid access is restricted": (
        "compound", ["Dehydration", BIO + "high serum sodium"],
        "'when fluid access is restricted' becomes the symptomDescription"),
    "Hypocalcemic generalized seizures": ("compound", ["Seizures", BIO + "low serum calcium"], ""),
    "Recurrent, severe spontaneous neuroglycopenic hypoglycemia (confusion, coma, seizures)": (
        "compound", ["Confusion", "Coma", "Seizures", BIO + "low blood glucose"], ""),
    "Acute oliguric renal failure / azotemia": (
        "compound", ["Reduced urine output", BIO + "high blood urea nitrogen and creatinine"], ""),
    "Protein-losing enteropathy with severe hypoalbuminemia and anasarca": (
        "compound", ["Anasarca", BIO + "low serum albumin", ASSOC + "protein-losing enteropathy"], ""),
    "Autoimmune hepatitis with marked transaminitis": (
        "related condition", [ASSOC + "Autoimmune hepatitis (ARI:0001033)", BIO + "high liver transaminases"], ""),
    "Rapidly progressive interstitial lung disease with hypoxemic respiratory failure": (
        "related condition", [ASSOC + "Interstitial lung disease (ARI:0001116)", "Shortness of breath",
                              BIO + "low blood oxygen"], ""),
    "Complete (third-degree) congenital heart block with severe fetal/neonatal bradycardia": (
        "compound", ["Slow heartbeat", EXAM + "complete heart block (ECG finding)"], ""),
    "Relative afferent pupillary defect (RAPD) and central scotoma": (
        "compound", ["Central scotoma", EXAM + "relative afferent pupillary defect (examination finding)"], ""),
    "Visual impairment / bilateral optic disc edema (papillitis)": (
        "compound", ["Vision problems", EXAM + "optic disc edema (fundoscopic finding)"], ""),
    "Painless proptosis and orbital pseudotumor mass": (
        "compound", ["Bulging eyes", EXAM + "orbital mass (imaging finding)"], ""),
    "Diplopia due to extraocular muscle enlargement": (
        "compound", ["Double vision", EXAM + "extraocular muscle enlargement (imaging finding)"], ""),
    "Visual field deficits / bitemporal hemianopia due to chiasmal compression": (
        "compound", ["Loss of peripheral vision", EXAM + "chiasmal compression (imaging finding)"],
        "bitemporal hemianopia is loss of the outer half of each eye's field"),
    "Severe proprioceptive sensory ataxia and positive Romberg sign": (
        "compound", ["Sensory ataxia", EXAM + "positive Romberg sign (examination finding)"], ""),
    "Nystagmus, saccadic intrusions, and ocular dysmetria": (
        "compound", ["Fast, irregular eye movements", EXAM + "saccadic intrusions and ocular dysmetria (examination findings)"],
        ""),
    "Vitreous floaters and haze": ("compound", ["Floaters in vision", EXAM + "vitreous haze (examination finding)"], ""),
    "Severe, disabling orthostatic hypotension and syncope": (
        "compound", ["Fainting", EXAM + "orthostatic hypotension (blood pressure measured on standing)"],
        "its symptoms on standing (lightheadedness, dizziness) are entries of their own where the source lists them"),
    "Prominent sleep architecture disruption (NREM parasomnia, sleep apnea, stridor)": (
        "compound", ["Abnormal behavior during sleep", "Sleep apnea", "High-pitched sound during breathing",
                     EXAM + "sleep architecture disruption (polysomnography finding)"], ""),

    # --- finding: a test, imaging or examination result -----------------------------------------
    "Microangiopathic hemolytic anemia with schistocytes on blood smear": (
        "finding", BIO + "microangiopathic hemolytic anemia (schistocytes on blood smear)",
        "a blood test result, not a symptom; the anemia's symptoms (pale skin, fatigue, yellow skin, dark urine) "
        "are entries of their own where the source lists them"),
    "Microangiopathic hemolytic anemia with fragmented schistocytes": (
        "finding", BIO + "microangiopathic hemolytic anemia (schistocytes on blood smear)",
        "a blood test result, not a symptom; the anemia's symptoms (pale skin, fatigue, yellow skin, dark urine) "
        "are entries of their own where the source lists them"),
    "Low blood counts": ("finding", BIO + "low blood cell counts", ""),
    "Severe consumptive thrombocytopenia": ("finding", BIO + "low platelet count", ""),
    "Transient neonatal thrombocytopenia or neutropenia": ("finding", BIO + "low platelet or neutrophil count", ""),
    "Transient neonatal cholestasis and elevated hepatic transaminases": (
        "finding", BIO + "cholestasis and high liver transaminases", ""),
    "Renal dysfunction (azotemia, proteinuria, hematuria)": (
        "finding", BIO + "azotemia; proteinuria; hematuria", "urine and blood test results"),
    "Hyperlipidemia and lipiduria": ("finding", BIO + "hyperlipidemia; lipiduria", ""),
    "Severe hypoalbuminemia (<3.0 g/dL)": ("finding", BIO + "serum albumin <3.0 g/dL", ""),
    "Refractory hyponatremia (SIADH-like)": ("finding", BIO + "low serum sodium", ""),
    "Refractory extreme hypertriglyceridemia (>1,000–2,000 mg/dL) with lactescent/milky serum": (
        "finding", BIO + "serum triglycerides >1,000–2,000 mg/dL", ""),
    "Severe, refractory hyperglycemia despite extreme doses of exogenous insulin (>1,000 U/day)": (
        "finding", BIO + "high blood glucose", "'despite >1,000 U/day of insulin' is a treatment response"),
    "Hypoglycemia occurring primarily postprandially (2–4 hours after meal) or post-exercise": (
        "finding", BIO + "low blood glucose",
        "the timing (2–4 hours after a meal or after exercise) goes with it; the source names no symptoms"),
    "Fulminant ketoacidosis": ("finding", BIO + "ketoacidosis",
                               "its symptoms (nausea, vomiting, abdominal pain, fast breathing) are entries of their own "
                               "where the source lists them"),
    "Lipemia retinalis on fundoscopic examination": ("finding", EXAM + "diagnostic finding", ""),
    "Creamy yellow-orange hypopigmented choroidal spots radiating from optic disc": (
        "finding", EXAM + "diagnostic finding", "seen on fundoscopy"),
    "Retinal arteriolar attenuation and vasculitis": ("finding", EXAM + "diagnostic finding", "seen on fundoscopy or angiography"),
    "Severe aortic valve regurgitation": ("finding", EXAM + "diagnostic finding", "seen on echocardiography"),
    "Harsh crescendo-decrescendo systolic murmur radiating to carotids": (
        "finding", EXAM + "diagnostic finding", "heard by stethoscope"),
    "Heart murmur": ("finding", EXAM + "diagnostic finding", "heard by stethoscope"),
    "Bibasilar inspiratory crackles": ("finding", EXAM + "diagnostic finding", "heard by stethoscope"),
    "Bibasilar inspiratory fine Velcro-like crackles": ("finding", EXAM + "diagnostic finding", "heard by stethoscope"),
    "Latent tetany: positive Chvostek's sign (60–75%) & Trousseau's sign": (
        "finding", EXAM + "diagnostic finding", "signs the examiner elicits"),
    "Pyramidal tract signs / extensor plantar responses (Babinski sign)": (
        "finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Asymmetric hyporeflexia confined to clinically weak muscles": (
        "finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Generalized areflexia": ("finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Generalized hypo- or areflexia": ("finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Reduced reflexes": ("finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Over-responsive reflexes": ("finding", EXAM + "diagnostic finding", "found on neurological examination"),
    "Tonic, unreactive, or poorly reactive pupils": ("finding", EXAM + "diagnostic finding", "found on examination"),
    "Dysfunction of pupils": ("finding", EXAM + "diagnostic finding", "found on examination"),
    "Immune complex-mediated glomerulonephritis": (
        "finding", EXAM + "diagnostic finding", "a kidney biopsy diagnosis; its signs (blood or protein in urine) are tests"),

    # --- related condition: a disease of its own ----------------------------------------------
    "Autoimmune cytopenias (autoimmune thrombocytopenia, AIHA)": (
        "related condition", [ASSOC + "Immune thrombocytopenia (ARI:0001107)", ASSOC + "Autoimmune hemolytic anemia (ARI:0001032)"], ""),
    "Autoimmune cytopenias (autoimmune thrombocytopenia, AIHA, neutropenia)": (
        "related condition", [ASSOC + "Immune thrombocytopenia (ARI:0001107)", ASSOC + "Autoimmune hemolytic anemia (ARI:0001032)",
                              ASSOC + "Autoimmune neutropenia (ARI:0001040)"], ""),
    "Autoimmune cytopenias (refractory ITP, AIHA)": (
        "related condition", [ASSOC + "Immune thrombocytopenia (ARI:0001107)", ASSOC + "Autoimmune hemolytic anemia (ARI:0001032)"], ""),
    "Autoimmune thyroid disease (hypo- or hyperthyroidism)": (
        "related condition", ASSOC + "Autoimmune thyroiditis (ARI:0001048)", "or Hashimoto's (ARI:0001216) / Graves' (ARI:0001096)"),
    "Autoimmune thyroid dysfunction: thyrotoxicosis followed by hypothyroidism": (
        "related condition", ASSOC + "Autoimmune thyroiditis (ARI:0001048)", "the course is the symptomDescription"),
    "Early-onset type 1 diabetes mellitus": ("related condition", ASSOC + "Type 1 diabetes mellitus (ARI:0001080)", ""),
    "Early-onset type 1 diabetes mellitus in male infants": (
        "related condition", ASSOC + "Type 1 diabetes mellitus (ARI:0001080)", ""),
    "Diabetic ketoacidosis (DKA)": (
        "related condition", "no field: complication",
        "a complication; its symptoms (nausea, vomiting, abdominal pain, fast breathing) are entries of their own "
        "where the source lists them"),
    "Hypopituitarism": (
        "related condition", BIO + "secondary adrenal insufficiency; secondary hypothyroidism; hypogonadism",
        "its likelihood names the hormone deficiencies, which are test results"),
    "Interstitial pneumonia": ("related condition", ASSOC + "Interstitial lung disease (ARI:0001116)", ""),
    "Lymphocytic interstitial lung disease": ("related condition", ASSOC + "Interstitial lung disease (ARI:0001116)", ""),
    "Early-onset interstitial lung disease / pulmonary hemorrhage": (
        "related condition", ASSOC + "Interstitial lung disease (ARI:0001116); pulmonary hemorrhage", ""),
    "Bronchiolitis obliterans leading to progressive, fatal respiratory failure": (
        "related condition", ASSOC + "bronchiolitis obliterans", "its symptom (shortness of breath) is an entry of its own"),
    "Recurrent episodes of acute pancreatitis": (
        "related condition", ASSOC + "acute pancreatitis", "its symptom (abdominal pain) is an entry of its own"),
    "Deep vein thrombosis": ("related condition", ASSOC + "deep vein thrombosis", "its symptoms are leg swelling and pain"),
    "High incidence of deep venous thrombosis or renal vein thrombosis": (
        "related condition", ASSOC + "deep vein thrombosis; renal vein thrombosis", ""),
    "Carpal tunnel syndrome": (
        "related condition", ASSOC + "carpal tunnel syndrome",
        "its symptoms are numbness, tingling and pain in the hand"),
    "Epilepsy": ("related condition", ASSOC + "Epilepsy (ARI:0001087)", "or restate as Seizures"),
    "Ocd": ("related condition", ASSOC + "obsessive-compulsive disorder",
            "its symptoms (obsessions, compulsive behavior) are entries of their own"),
    "Lactose intolerance": ("related condition", ASSOC + "lactose intolerance",
                            "its symptoms (bloating, diarrhea, gas after dairy) are entries of their own"),
    "Disseminated non-tuberculous mycobacterial (NTM) infections": (
        "related condition", ASSOC + "disseminated non-tuberculous mycobacterial infection", ""),
    "Early-onset multi-organ autoimmunity starting in infancy/childhood": (
        "onset or course", "disease definition (IAO_0000115)", "describes the disease, not a symptom"),

    # --- other ---------------------------------------------------------------------------------
    "Sensitivity to gluten": ("trigger", "hasEnvironmentalTrigger", "gluten triggers the rash"),
    "In childhood-onset bullous pemphigoid associated with vaccination, the bullous lesions predominantly affect the palms, soles, and face": (
        "body site", "qualifier: note it in symptomDescription of the blister entries", ""),
    "Problems with metabolism": ("too general", "check the source", ""),
    "Skin disorders": ("too general", "check the source", ""),
    "Mental disorders": ("too general", "check the source", ""),
}


def read_listed():
    """[(ARI ID, disease label, entry, individual id, likelihood)] for every hasSymptom listing."""
    root = ET.parse(DISEASE).getroot()
    names, listed = {}, collections.defaultdict(list)
    for el in root:
        ari_id = el.findtext(ARI + "ARI_ID")
        if ari_id:
            names[ari_id] = el.findtext(RDFS + "label").strip()
            for ref in el.findall(ARI + "hasSymptom"):
                listed[ref.get(RDF + "resource")].append(ari_id)
    out = []
    for ind in root.findall(OWL + "NamedIndividual"):
        iri = ind.get(RDF + "about")
        for ari_id in listed.get(iri, []):
            out.append((ari_id, names[ari_id], ind.findtext(RDFS + "label").strip(), iri[len(ARI_BASE):],
                        ind.findtext(ARI + "likelihood") or ""))
    return out


def read_classes():
    """Lower-cased label or synonym -> ARIS id."""
    index = {}
    for c in ET.parse(SYMPTOMS).getroot().findall(OWL + "Class"):
        cid = c.findtext(OBOINOWL + "id")
        if not cid:
            continue
        for el in [c.find(RDFS + "label")] + c.findall(SKOS + "altLabel"):
            if el is not None:
                index.setdefault(el.text.strip().lower(), cid)
    return index


def read_sheet():
    """(ARI ID, entry) -> (seq, before, after) from report 4's Symptoms sheet."""
    ws = openpyxl.load_workbook(REPORT, read_only=True)["Symptoms"]
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    col = {name: header.index(name) for name in ("ARI ID", "seq", "symptom")}
    by_disease = collections.defaultdict(list)
    for r in rows:
        if r[col["symptom"]]:
            by_disease[r[col["ARI ID"]]].append((r[col["symptom"]].strip(), r[col["seq"]]))
    context = {}
    for ari_id, items in by_disease.items():
        for i, (entry, seq) in enumerate(items):
            context[ari_id, entry] = (str(seq), items[i - 1][0] if i else "",
                                      items[i + 1][0] if i + 1 < len(items) else "")
    return context


def proposal(parts, classes):
    if isinstance(parts, str):
        return parts
    named = []
    for part in parts:
        if part.startswith((BIO, EXAM, ASSOC)):
            named.append(part)
        else:
            named.append(f"{part} ({classes.get(part.lower(), 'new')})")
    return "split: " + "; ".join(named)


def main():
    listed = read_listed()
    strings = {entry for _, _, entry, _, _ in listed}
    unknown = set(JUDGMENTS) - strings
    if unknown:
        raise SystemExit(f"Reviewed entries no disease lists: {sorted(unknown)}")
    classes, context = read_classes(), read_sheet()

    with open(REVIEW_PATH, encoding="utf-8", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if lines[0] != COLUMNS:
        raise SystemExit(f"{REVIEW_PATH}: the header is not {COLUMNS}")
    have = {(v[0], v[2]) for v in lines[1:]}

    added = 0
    for ari_id, disease, entry, individual, likelihood in listed:
        if entry not in JUDGMENTS or (ari_id, entry) in have:
            continue
        kind, parts, note = JUDGMENTS[entry]
        seq, before, after = context.get((ari_id, entry), ("", "", ""))
        lines.append([ari_id, disease, entry, individual, seq, likelihood, before, after,
                      kind, proposal(parts, classes), "", note])
        have.add((ari_id, entry))
        added += 1

    for v in lines[1:]:
        for value in v:
            if any(c in value for c in "\t\r\n"):
                raise SystemExit(f"{v[0]} {v[2]!r}: a value has a tab or a line break")
    with open(REVIEW_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerows(lines)
    print(f"{len(strings)} distinct listed entries reviewed, {len(JUDGMENTS)} need a change; "
          f"{added} rows added -> {REVIEW_PATH}")


if __name__ == "__main__":
    main()
