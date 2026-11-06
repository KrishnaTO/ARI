"""Write data/4-reports/14_Sign_Or_Symptom.tsv: every shared symptom class, judged a sign or a symptom.

Every ARIS class in ontologies/ari_symptoms.owl gets one row, with the judgment in JUDGMENTS below:

  - symptom: known only from the patient's account. A sensation, a perception, a mood or thought, a
    general feeling, or a change in function the patient reports.
  - sign: another person can observe or measure it, with their own senses or a test. It can be seen on
    the body, seen or heard as an event or behaviour, measured, found on examination, or established
    by a test or a diagnosis. A sign is still a sign when the patient also notices it (a rash).

Some faculties can go either way. There, the entry's wording decides: a loss that an examiner measures
(vision on an eye chart, strength in a named muscle group, memory) is a sign, and the experience the
patient describes (blurred vision, numbness, general weakness, brain fog) is a symptom. A qualifier
does not change what an entry names: a painful rash is a rash, and "X with Y" is X. An entry that lists
separate items (A, B and C; A / B; examples in brackets) takes the class most of its items have, and the
first-named item breaks a tie. Its explanation starts "Mixed:".

Each JUDGMENTS line is `ARIS number|class|basis|explanation`. basis says which kind of evidence
decided it, from BASES. The script stops when a class has no judgment, a judgment names no class, or a
class or basis is not one of these.

`decision` is the review column: a rebuild keeps the value a row has, so the table can be rebuilt while
the review is open. The file is tab-separated, UTF-8 with no byte-order mark and LF line ends, written
with the csv module's excel-tab dialect, so a reviewer can fill `decision` in a spreadsheet and save it
as tab-delimited text.

Usage: python build_sign_symptom_report.py
"""
import collections, csv, os
import xml.etree.ElementTree as ET

from build_symptom_report import ARI, ARIS, DISEASE, OBOINOWL, OWL, RDF, RDFS, ROOT, SYMPTOMS

REPORT = os.path.join(ROOT, "data", "4-reports", "14_Sign_Or_Symptom.tsv")
COLUMNS = ["aris_id", "entry", "parent", "diseases", "classification", "basis", "explanation", "decision"]
BASES = {
    "symptom": ("sensation", "perception", "mood or thought", "general feeling", "reported function"),
    "sign": ("appearance", "observed event or behaviour", "measurement", "examination", "test or diagnosis"),
}

JUDGMENTS = """
597|sign|appearance|Streaky red marks on the skin that others can see.
001|symptom|sensation|Fullness and pressure are felt; only the patient can report them.
002|sign|appearance|A rash others can see; the fever it comes with is measured.
003|symptom|sensation|Cramping pain is felt, not seen.
004|symptom|sensation|Discomfort is felt; others cannot observe it.
005|symptom|sensation|Pain is known only from the patient's account.
006|sign|observed event or behaviour|Leaks or retained urine can be seen and measured, so poor bladder control is observable.
007|sign|appearance|Growths on the skin are seen; that they may hurt describes them.
008|sign|examination|Lumps under the skin are seen or felt by an examiner.
009|sign|observed event or behaviour|Abnormal movements are seen by others.
010|sign|appearance|Abnormal blood vessels show on the skin.
598|sign|observed event or behaviour|Mixed: shaking chills (rigors) are seen and high fever is measured (signs); the back or abdominal pain is felt (symptom). Two of three items are signs.
011|sign|observed event or behaviour|Missed periods are an observable fact, not a sensation.
012|sign|examination|Fluid in the abdomen (ascites) shows as swelling and is found on examination or imaging.
013|symptom|sensation|Heartburn is a burning felt behind the breastbone.
599|sign|test or diagnosis|Kidney failure and azotemia are established by urine output and blood tests.
600|sign|examination|Weakness of the eye muscles is seen when an examiner tests eye movements.
601|symptom|mood or thought|Mixed: anxiety and psychosis are reported experiences (symptoms); affective changes are observed (sign). Two of three items are symptoms.
602|sign|test or diagnosis|Anemia is a blood-test result, and pallor and jaundice are seen.
014|sign|examination|Amnesia and confusion are seen by others and found on mental-status testing.
603|sign|measurement|Loss of vision is measured with an eye chart; that it is painful describes it.
015|sign|observed event or behaviour|Aggressive behaviour is seen by others.
604|symptom|sensation|Allodynia, dysesthesias and hyperalgesia are abnormal pain and touch sensations only the patient feels.
605|sign|examination|Level of consciousness is judged by an observer (e.g. the Glasgow Coma Scale).
016|sign|examination|Level of consciousness is judged by an observer (e.g. the Glasgow Coma Scale).
606|symptom|sensation|Angina is chest pain felt on exertion.
607|sign|measurement|Absent sweating can be seen and measured with a sweat test.
017|symptom|general feeling|Loss of appetite is felt; the weight loss it causes would be a sign.
018|symptom|mood or thought|Anxiety is a feeling the patient reports.
019|symptom|mood or thought|Anxiety is a felt state, reported by the child or described by carers.
020|symptom|sensation|Pain is known only from the patient's account.
021|symptom|sensation|Pain is felt; exertion is when it comes on.
022|sign|examination|Weakness in a named limb is graded on strength testing (unlike general "Weakness", a felt lack of strength).
608|symptom|sensation|Mixed: arthralgia is joint pain (symptom); inflammatory arthritis shows as swollen, tender joints (sign). Tie broken by the first item.
609|sign|examination|Reflexes are tested with a reflex hammer.
610|sign|examination|Wrist and finger drop are seen, and weakness is graded on strength testing.
023|symptom|mood or thought|Trouble keeping attention, as the patient reports it; attention measured on cognitive testing would be a sign.
611|sign|test or diagnosis|Low blood counts are blood-test results.
024|sign|test or diagnosis|Low blood counts are blood-test results.
612|sign|test or diagnosis|Low blood counts are blood-test results.
613|sign|test or diagnosis|Autoimmune hepatitis is diagnosed from liver enzymes and biopsy.
614|sign|test or diagnosis|Hypophysitis is diagnosed on imaging and hormone tests; the headache and fatigue it comes with describe it.
615|sign|test or diagnosis|Thyroid disease is diagnosed on thyroid blood tests.
616|sign|test or diagnosis|Thyrotoxicosis and hypothyroidism are diagnosed on thyroid blood tests.
025|sign|test or diagnosis|Both are diagnoses established by examination and testing (blood pressure, bladder studies).
617|sign|test or diagnosis|Mixed: altered sweating can be measured and dysmotility is shown by tests (signs); dry mouth and eyes are felt (symptom). Two of three items are signs.
026|symptom|sensation|Pain is known only from the patient's account.
027|sign|appearance|A sunken eye is seen and can be measured.
028|sign|appearance|Bald patches are seen.
029|sign|appearance|Hair loss is seen.
030|sign|observed event or behaviour|A wet bed is evidence others can see.
031|sign|observed event or behaviour|Changes in behaviour are noticed by others.
032|sign|observed event or behaviour|Mixed: behavioural changes and confusion are observed (signs); psychosis is known from what the patient reports (symptom). Two of three items are signs.
618|sign|examination|Enlarged lymph nodes and spleen are felt on examination.
619|sign|examination|Crackles are heard with a stethoscope.
620|sign|examination|Crackles are heard with a stethoscope.
621|symptom|perception|Mixed: blurred vision is what the patient sees (symptom); reduced acuity is measured on an eye chart (sign). Tie broken by the first item.
622|sign|examination|Enlarged tear glands are seen and felt.
033|symptom|reported function|A general change in bladder habits, known from the patient's account.
034|symptom|sensation|Pain is known only from the patient's account.
035|sign|appearance|Bleeding is seen.
036|sign|appearance|Blood-filled blisters are seen.
037|sign|appearance|Bleeding gums are seen.
038|sign|measurement|Loss of sight is measured with eye charts and field tests, and others can see it.
039|sign|appearance|A blister is seen.
040|sign|appearance|A blister in the throat is seen on examination.
041|sign|appearance|A blister is seen.
042|sign|appearance|Blisters are seen.
043|sign|appearance|The blisters are seen; that they hurt but do not itch describes them.
044|sign|appearance|Blisters are seen.
045|sign|appearance|Blisters are seen.
046|sign|appearance|Blisters are seen.
047|sign|appearance|Blisters are seen.
048|sign|appearance|Blisters and open sores are seen.
049|symptom|sensation|Bloating is a felt fullness; visible distension would be a sign.
050|symptom|sensation|Bloating is a felt fullness; visible distension would be a sign.
051|sign|appearance|Blood in the stool is seen or found on a stool test.
052|sign|appearance|Blood in the urine is seen or found on a dipstick.
053|sign|appearance|A blue tint to the skin is seen.
054|symptom|perception|Only the patient sees the blur; reduced acuity on an eye chart would be its sign.
055|sign|appearance|Hair loss is seen.
056|symptom|sensation|Pain is known only from the patient's account.
057|symptom|reported function|A general change in bowel habits, known from the patient's account.
058|symptom|sensation|Urgency is a felt need to empty the bowel.
059|symptom|mood or thought|A felt clouding of thought, known only from the patient's account.
060|sign|appearance|Brittle nails are seen.
623|sign|test or diagnosis|Diagnosed on lung function tests and imaging.
624|sign|examination|Mixed: slurred speech and vocal cord palsy are found on examination (signs); difficulty swallowing is felt (symptom). Two of three items are signs.
061|sign|appearance|Bulging eyes are seen and can be measured.
062|sign|appearance|Skin bumps are seen.
063|sign|appearance|Skin bumps are seen.
064|symptom|sensation|Pain is known only from the patient's account.
065|sign|appearance|The rash is seen; the burning describes how it feels.
066|symptom|sensation|A burning feeling only the patient can report.
067|symptom|sensation|A burning feeling only the patient can report.
068|symptom|sensation|A burning feeling only the patient can report.
069|symptom|sensation|A burning feeling only the patient can report.
070|symptom|sensation|A burning feeling only the patient can report.
071|symptom|sensation|A burning or gritty feeling only the patient can report.
072|sign|appearance|The rash is seen.
073|sign|appearance|Mouth ulcers are seen.
074|sign|test or diagnosis|A named condition, confirmed by examination and nerve conduction studies; its numbness and tingling are symptoms.
075|sign|appearance|Blisters are seen.
625|sign|observed event or behaviour|Slurred, scanning speech is heard by others.
076|sign|appearance|A changed facial expression is seen by others.
077|sign|examination|Mental status is assessed by an observer.
078|sign|observed event or behaviour|A changed voice is heard by others.
079|sign|appearance|Changes in hair are seen.
080|sign|appearance|Changes in nails are seen.
081|symptom|perception|Altered smell, taste, sight or hearing (as in a seizure aura) is perceived only by the patient.
082|sign|test or diagnosis|An infection is diagnosed by examination, imaging and cultures.
083|symptom|sensation|Pain is known only from the patient's account.
084|symptom|sensation|A felt sense of cold; visible shaking (rigors) would be a sign.
626|sign|observed event or behaviour|Abnormal movements of the body and eyes are seen.
627|symptom|general feeling|Fatigue and unrefreshing sleep are felt and reported.
628|symptom|general feeling|Fatigue and exhaustion are felt and reported.
085|sign|examination|Enlarged lymph nodes, liver and spleen are felt on examination.
629|sign|examination|Inflamed joints are swollen and tender on examination; non-erosive is an X-ray finding.
630|sign|examination|Swollen, draining lymph nodes are seen and felt.
631|sign|observed event or behaviour|A cough is heard by others.
632|sign|observed event or behaviour|A cough is heard by others.
633|sign|observed event or behaviour|Loose, frequent stools can be seen and measured.
086|symptom|sensation|A churning feeling only the patient can report.
087|sign|appearance|The rash is seen.
088|sign|observed event or behaviour|Clumsy movements are seen by others.
634|sign|observed event or behaviour|Exaggerated startle, myoclonus and tremor are seen.
089|symptom|perception|Mixed: derealization and altered perception are experiences only the patient has (symptoms); apathy is observed (sign). Two of three items are symptoms.
090|sign|examination|Measured on cognitive testing.
635|sign|examination|Mixed: cognitive impairment and memory loss are measured on testing (signs); brain fog is felt (symptom). Two of three items are signs.
091|sign|examination|Cold skin can be felt by an examiner.
092|sign|examination|Cold skin can be felt by an examiner.
093|symptom|sensation|Feeling unusually cold is reported by the patient.
094|symptom|sensation|A felt sense of cold; skin cold to the touch would be a sign.
095|sign|examination|Coma is judged by an observer.
636|sign|test or diagnosis|Found on fetal ultrasound and ECG.
096|sign|observed event or behaviour|Compulsive acts are seen by others.
097|sign|observed event or behaviour|Binge eating is behaviour others can see.
637|sign|observed event or behaviour|Mixed: compulsive drinking is seen (sign); the craving is felt (symptom). Tie broken by the first item.
098|sign|examination|Confusion is seen by others and found on mental-status testing.
099|symptom|sensation|Pain is known only from the patient's account.
100|symptom|reported function|Defined largely by what the patient feels: straining, hard stools, incomplete emptying.
101|sign|examination|A corneal ulcer is seen on eye examination.
102|sign|observed event or behaviour|A cough is heard by others.
103|sign|appearance|Blood is seen.
638|symptom|sensation|Mixed: abdominal pain is felt (symptom); tenderness is found when an examiner presses (sign). Tie broken by the first item.
104|symptom|sensation|Cramps are felt.
639|sign|examination|Seen on examination of the back of the eye.
105|sign|appearance|Ulcers are seen.
106|sign|appearance|Seen on the face.
107|sign|appearance|Damaged enamel is seen.
108|symptom|perception|Only the patient sees the spots.
109|sign|appearance|Dark urine is seen.
110|sign|observed event or behaviour|Reduced movement is seen by others.
111|sign|measurement|Reduced sweating can be seen and measured with a sweat test.
112|symptom|sensation|Pain is known only from the patient's account.
113|sign|test or diagnosis|A clot diagnosed by ultrasound.
114|sign|examination|Found on examination (dry mouth, low blood pressure) and blood tests.
115|sign|measurement|Growth is measured.
116|sign|examination|Slow release after a grip is seen and recorded on EMG (myotonia).
117|sign|measurement|Pubertal stage is assessed on examination.
118|sign|examination|Diagnosed on cognitive testing and seen by others.
119|symptom|mood or thought|Low mood is felt and reported.
120|sign|observed event or behaviour|Shown by grades and seen by teachers.
121|sign|observed event or behaviour|Loss of skills is seen by carers and on developmental assessment.
640|sign|test or diagnosis|Mixed: polyuria is measured (sign); thirst is felt (symptom). Tie broken by the first item; the condition itself is diagnosed by tests.
122|sign|test or diagnosis|Diagnosed on blood tests.
123|sign|observed event or behaviour|Loose, frequent stools can be seen and measured.
124|sign|appearance|Eye colour is seen.
125|sign|appearance|Pupil size is seen.
126|symptom|reported function|Felt as tiring of the jaw or effort while eating.
127|sign|observed event or behaviour|An examiner can watch the patient struggle; it is how hip and thigh weakness shows.
128|symptom|mood or thought|An inner difficulty the patient reports.
129|symptom|reported function|A difficulty the patient reports.
130|symptom|reported function|Reduced exercise tolerance is known from the patient's account.
131|sign|observed event or behaviour|Word-finding pauses are heard in conversation and tested on examination.
132|sign|observed event or behaviour|An examiner can watch the patient rise; it is how hip and thigh weakness shows.
133|sign|examination|Limited jaw movement can be seen and measured.
134|sign|measurement|Colour vision is measured with colour plates.
135|sign|observed event or behaviour|Impaired speech is heard by others.
136|symptom|reported function|Felt as food sticking or effort to swallow; a swallow study would show it as a sign.
137|sign|examination|Comprehension is assessed by others and on testing.
138|sign|examination|Comprehension of speech is tested on examination.
139|symptom|reported function|Felt as hesitancy or straining.
140|sign|observed event or behaviour|Walking difficulty is seen.
641|symptom|sensation|Mixed: myalgias are felt (symptom); muscle weakness is graded on strength testing (sign). Tie broken by the first item.
642|sign|appearance|Clubbing is seen.
643|symptom|perception|Only the patient sees double; the muscle enlargement behind it is an imaging finding.
141|symptom|sensation|Discomfort is felt.
142|symptom|sensation|Discomfort is felt.
143|sign|appearance|Nail changes are seen.
144|sign|examination|Disorientation is found on mental-status testing.
644|sign|observed event or behaviour|Sleep timing can be seen by others and recorded.
645|sign|measurement|The number of times the patient passes urine at night can be counted.
646|sign|test or diagnosis|Diagnosed by cultures.
647|symptom|sensation|Pain is known only from the patient's account.
648|symptom|sensation|Numbness, tingling and pain are all felt.
145|sign|examination|Level of consciousness is judged by an observer.
146|symptom|sensation|Dizziness is felt.
147|symptom|perception|Only the patient sees double; misaligned eyes found on examination would be the sign.
148|symptom|perception|Only the patient sees double; the detail on closing one eye is the patient's report.
149|symptom|general feeling|Sleepiness is felt; reduced alertness seen by others would be a sign.
150|sign|observed event or behaviour|A cough is heard by others.
151|symptom|sensation|Dryness is felt as grittiness; reduced tears on a Schirmer test would be its sign.
152|symptom|sensation|Dryness is felt; reduced saliva flow would be measured as a sign.
153|sign|appearance|Dry, flaky skin is seen and felt by others.
154|sign|appearance|Cracked, bleeding skin is seen.
155|sign|appearance|A dull expression is seen by others.
156|sign|examination|Pupil reactions are tested with a light.
157|symptom|sensation|Pain is known only from the patient's account.
158|sign|observed event or behaviour|Seizures are seen by others and recorded on EEG.
649|sign|test or diagnosis|Diagnosed on imaging and lung tests.
159|sign|test or diagnosis|A disease course established by tests, not something felt.
650|sign|test or diagnosis|Enteropathy is a biopsy diagnosis; the watery diarrhea it comes with describes it.
160|sign|test or diagnosis|Diagnosed on blood glucose and antibody tests.
651|sign|test or diagnosis|Diagnosed on blood glucose and antibody tests.
161|sign|appearance|Bruises are seen.
162|sign|appearance|The rash is seen.
163|sign|examination|Fluid swelling is seen and pits when pressed.
164|symptom|sensation|Pain is known only from the patient's account.
165|symptom|sensation|Lhermitte's sign: despite its name, a sensation only the patient feels.
166|symptom|sensation|An empty feeling only the patient can report.
167|sign|examination|Encephalopathy, confusion and delirium are seen by others and found on examination.
168|sign|observed event or behaviour|Seizures are seen by others and recorded on EEG.
169|symptom|reported function|Known from the patient's account.
652|sign|appearance|Xanthomas are seen.
170|symptom|mood or thought|An elevated mood the patient feels.
171|sign|appearance|Bleeding is seen.
172|sign|appearance|Sweating is seen.
653|symptom|sensation|Mixed: presyncope is a felt faintness (symptom); syncope is a loss of consciousness others see (sign). Tie broken by the first item.
654|sign|appearance|Dermatitis is seen.
655|sign|examination|Calcium deposits are felt under the skin and seen on X-ray.
656|sign|examination|Arthritis, uveitis and mouth ulcers are all found on examination.
173|sign|appearance|Discharge is seen.
174|sign|examination|Inflammation shows as redness and on slit-lamp examination.
175|symptom|sensation|Irritation is felt.
176|sign|appearance|Lesions are seen.
177|symptom|sensation|Pain is known only from the patient's account.
178|symptom|sensation|Discomfort from light or touch is felt.
179|sign|appearance|Hair loss is seen.
180|sign|appearance|A drooping eyelid is seen.
181|sign|appearance|A drooping face is seen.
182|sign|appearance|Flushing is seen.
183|symptom|sensation|Pain is known only from the patient's account.
184|sign|examination|Facial weakness is seen and tested on examination.
185|sign|measurement|Weight and growth are measured.
186|sign|observed event or behaviour|Loss of consciousness is seen by others.
187|sign|observed event or behaviour|Falls are seen.
188|sign|measurement|Breathing rate is counted.
189|sign|observed event or behaviour|Eye movements are seen.
190|symptom|general feeling|Tiredness is felt and reported.
191|sign|appearance|Fatty deposits are seen.
192|symptom|mood or thought|Fear is felt.
193|symptom|sensation|Fullness is felt.
194|symptom|sensation|Fullness is felt.
195|sign|observed event or behaviour|Spasms are visible muscle contractions.
196|sign|measurement|Body temperature is measured with a thermometer.
197|symptom|sensation|Pain is known only from the patient's account.
198|sign|observed event or behaviour|Tremor is seen.
199|sign|appearance|Nail changes are seen.
200|sign|examination|Bumps under the skin are felt.
201|sign|appearance|The rash is seen; that it is painless describes it.
202|symptom|perception|Only the patient sees floaters.
203|symptom|general feeling|Aches, tiredness and feeling unwell are felt.
204|sign|examination|Confusion, focal deficits, seizures and coma are all observed.
205|sign|appearance|Foamy urine is seen.
657|sign|examination|Wasted muscle is seen and felt.
206|symptom|sensation|Food sticking is felt.
207|symptom|sensation|Pain is known only from the patient's account.
208|sign|measurement|Bowel movements can be counted.
209|sign|test or diagnosis|Diagnosed on blood tests.
210|sign|appearance|Milky discharge from the nipple is seen.
211|sign|appearance|Gangrene is seen.
212|symptom|sensation|Gassiness and bloating are felt.
213|sign|examination|Reflexes are tested with a reflex hammer.
658|sign|examination|Reflexes are tested with a reflex hammer.
214|sign|appearance|Blisters are seen.
215|symptom|sensation|An ache is felt.
659|sign|appearance|Gottron's papules are seen.
216|sign|measurement|Weight is measured.
217|sign|appearance|Enlarged gums are seen.
218|sign|appearance|Hair loss is seen.
219|symptom|perception|Only the patient perceives hallucinations.
220|symptom|sensation|Pain is known only from the patient's account.
221|sign|observed event or behaviour|Spasms are visible muscle contractions.
222|sign|observed event or behaviour|Tremor is seen.
223|sign|measurement|Describes loss of central vision in everyday terms; central acuity is measured with an eye chart.
660|sign|examination|A murmur is heard with a stethoscope.
224|symptom|sensation|Pain is known only from the patient's account.
225|sign|measurement|Hearing is measured with an audiogram.
226|sign|measurement|Hearing is measured with an audiogram.
227|sign|examination|A murmur is heard with a stethoscope.
228|symptom|sensation|An awareness of the heartbeat; a fast or irregular pulse measured by others is the sign.
229|symptom|sensation|Heaviness is felt.
230|sign|measurement|Menstrual blood loss can be seen and measured.
661|sign|test or diagnosis|Proteinuria is measured in the urine; the foamy urine it comes with describes it.
231|sign|appearance|Discharge is seen and its odour noticed by others.
232|symptom|sensation|Pain is known only from the patient's account.
233|symptom|sensation|Stiffness is felt.
234|sign|observed event or behaviour|Hiccups are seen and heard.
662|sign|test or diagnosis|Clots are diagnosed by ultrasound.
235|sign|appearance|A raised shoulder blade is seen.
236|sign|observed event or behaviour|Stridor is heard by others.
237|symptom|sensation|Pain is known only from the patient's account.
238|symptom|sensation|Stiffness is felt.
239|sign|appearance|Hives are seen.
240|sign|observed event or behaviour|A hoarse voice is heard by others.
241|sign|appearance|Posture is seen.
242|symptom|general feeling|Hunger is felt.
663|sign|test or diagnosis|Blood and urine test results.
664|sign|test or diagnosis|Diagnosed on blood sodium.
243|sign|appearance|Darkened skin is seen.
244|sign|observed event or behaviour|Behaviour others see.
665|sign|observed event or behaviour|Seizures are seen by others; low calcium is a blood-test result.
666|sign|test or diagnosis|Low antibody levels are a blood-test result; the infections it comes with describe it.
667|sign|test or diagnosis|Low blood glucose is a measured value.
668|sign|test or diagnosis|Diagnosed on hormone tests.
669|sign|test or diagnosis|Diagnosed on urine tests and biopsy.
670|sign|test or diagnosis|Colitis is diagnosed on colonoscopy; the diarrhea and cramps it comes with describe it.
671|sign|appearance|Rash and depigmentation are seen.
245|sign|examination|Coordination is tested on examination.
246|sign|appearance|Blisters are seen.
247|symptom|general feeling|Appetite is felt; the extra eating would be its sign.
248|sign|appearance|Enlarged calves are seen.
249|sign|measurement|The number of times the patient passes urine can be counted.
250|symptom|sensation|Indigestion is felt.
251|sign|test or diagnosis|Established by failure to conceive and fertility tests, not felt.
252|sign|appearance|Inflamed gums are seen.
672|symptom|sensation|Breathlessness is felt.
673|sign|observed event or behaviour|Tremor is seen.
253|sign|test or diagnosis|Diagnosed on imaging.
254|sign|observed event or behaviour|Involuntary movements are seen.
674|sign|measurement|Mixed: weight loss is measured and malabsorption shown by tests (signs); fatigue is felt (symptom). Two of three items are signs.
255|sign|measurement|Found on taking the pulse or on an ECG; feeling it is "Heart palpitations".
256|symptom|mood or thought|Irritable mood is felt and reported.
257|symptom|mood or thought|Irritability and mood changes are felt and reported.
258|symptom|mood or thought|Irritable mood, as with "Irritability"; in young children carers report it.
259|symptom|sensation|Itching is felt.
260|sign|appearance|The blisters are seen; the itch describes them.
261|sign|appearance|The rash is seen; the itch describes it.
262|symptom|sensation|Pain is known only from the patient's account.
263|symptom|sensation|Pain is known only from the patient's account.
264|symptom|sensation|Stiffness is felt; limited movement measured by an examiner would be a sign.
265|sign|examination|Tenderness is pain an examiner provokes by pressing the joint.
266|symptom|sensation|Pain is known only from the patient's account.
267|symptom|sensation|Stiffness is felt.
268|symptom|reported function|Known from the symptoms the patient reports after eating dairy.
269|sign|appearance|Blisters are seen.
270|sign|appearance|Blisters are seen.
675|sign|observed event or behaviour|Laryngospasm and stridor are heard by others.
676|sign|examination|Chvostek's and Trousseau's signs are provoked by an examiner.
271|sign|appearance|Sores are seen.
272|sign|test or diagnosis|Assessed by educational and cognitive testing.
273|symptom|sensation|Pain is known only from the patient's account.
274|symptom|sensation|Stiffness is felt.
275|sign|appearance|Lesions are seen.
276|symptom|sensation|Lightheadedness is felt.
677|sign|test or diagnosis|Encephalitis is diagnosed on MRI, CSF and antibody tests; cognitive decline is measured.
277|sign|examination|Range of motion is measured.
278|sign|observed event or behaviour|A limp is seen.
279|sign|examination|A floppy ear is seen and felt.
280|sign|appearance|Ulcers are seen.
678|sign|examination|Seen on examination of the back of the eye.
281|sign|appearance|Fatty stools are seen.
282|sign|observed event or behaviour|Leaks of urine are seen.
283|sign|observed event or behaviour|Leaks of stool are seen.
284|sign|appearance|Pale lining of the mouth is seen.
285|sign|observed event or behaviour|Loss of consciousness is seen by others.
286|sign|appearance|Lost eyelashes are seen.
287|sign|examination|Lost sensation is mapped on examination with touch, pin and vibration; the felt numbness is "Numbness".
288|sign|examination|Lost sensation is mapped on examination with touch, pin and vibration; the felt numbness is "Numbness".
289|sign|measurement|Night vision can be measured with dark-adaptation testing.
290|sign|observed event or behaviour|Lost skills are seen.
291|sign|examination|Seen on eye examination.
292|sign|measurement|Measured on visual field testing.
293|sign|examination|Lost sensation is mapped on examination with touch, pin and vibration.
294|sign|appearance|Lost teeth are seen.
295|sign|test or diagnosis|Low blood counts are blood-test results.
296|sign|test or diagnosis|A blood-test result.
297|sign|test or diagnosis|A blood-test result.
298|sign|measurement|Body temperature is measured with a thermometer.
299|symptom|sensation|Stiffness is felt.
300|sign|appearance|Colour changes are seen.
679|sign|test or diagnosis|Diagnosed on imaging and biopsy.
301|symptom|general feeling|Feeling unwell is felt and reported.
680|sign|examination|Pitting swelling is seen and pressed on examination.
302|sign|observed event or behaviour|Tremor is seen.
681|sign|observed event or behaviour|Tremor is seen.
303|sign|observed event or behaviour|Mixed: agitation is seen (sign); psychosis is known from what the patient reports (symptom). Tie broken by the first item.
304|sign|examination|Memory loss is noticed by others and measured on cognitive testing.
305|sign|measurement|Mixed: fever is measured and neck stiffness is found on examination (signs); headache is felt (symptom). Two of three items are signs.
306|sign|examination|Decline is seen by others and measured on cognitive testing.
307|symptom|mood or thought|Too general to place closely; mental disorders show mainly in mood and thought the patient reports.
308|sign|test or diagnosis|Blood-test and blood-smear results.
309|symptom|sensation|Pain is known only from the patient's account.
310|symptom|sensation|Pain is known only from the patient's account.
682|sign|examination|Foot drop is seen, and weakness is graded on strength testing.
311|sign|appearance|Skin patches are seen.
312|sign|appearance|Misalignment is seen.
313|sign|appearance|Misalignment is seen.
314|sign|observed event or behaviour|A pregnancy loss is a clinical event, confirmed by examination or ultrasound.
315|symptom|mood or thought|Mood is felt and reported.
316|sign|appearance|The rash is seen.
317|sign|appearance|Sores are seen.
683|sign|observed event or behaviour|Chorea, catatonia and opsoclonus are seen.
318|sign|observed event or behaviour|Movement difficulty is seen.
319|sign|appearance|Bleeding is seen.
684|sign|appearance|Blisters and erosions are seen.
320|sign|appearance|Blisters are seen.
321|symptom|sensation|Felt as sudden painful tightening.
685|sign|observed event or behaviour|Mixed: fasciculations and myokymia are visible twitches (signs); cramps are felt (symptom). Two of three items are signs.
322|sign|appearance|Wasting is seen and measured.
323|symptom|sensation|Pain is known only from the patient's account.
324|symptom|sensation|Soreness is felt.
325|sign|observed event or behaviour|Spasms are visible muscle contractions.
326|symptom|sensation|Tightness is felt; rigidity an examiner feels when moving the limb would be a sign.
327|sign|examination|Tenderness is pain an examiner provokes by pressing the muscle.
328|sign|examination|Paraparesis and sensory loss are found on neurological examination.
329|sign|appearance|Lost nails are seen.
330|symptom|sensation|A blocked nose is felt.
331|symptom|sensation|Nausea is felt.
332|symptom|sensation|Nausea is felt.
333|symptom|sensation|Pain is known only from the patient's account.
686|sign|measurement|Retained urine is measured by bladder scan or catheter.
334|sign|appearance|Drenching sweats soak bedclothes, which others can see, though the patient usually reports them.
335|sign|measurement|The number of times the patient passes urine at night can be counted.
336|sign|observed event or behaviour|Coughing is heard and aspiration is shown on imaging.
337|sign|examination|Nodules are seen and felt.
338|sign|examination|Nodules are seen and felt.
339|sign|examination|Nodules are seen and felt.
340|sign|appearance|The rash is seen.
341|sign|appearance|Ulcers are seen.
342|sign|appearance|Bleeding is seen.
343|symptom|sensation|Numbness is felt; sensory loss mapped on examination would be its sign.
344|symptom|sensation|Numbness is felt.
687|sign|measurement|Night vision and colour discrimination are measured with vision tests.
688|sign|examination|Abnormal eye movements are seen on examination.
345|symptom|mood or thought|Obsessions are thoughts the patient reports.
346|symptom|mood or thought|Obsessions are thoughts only the patient reports; the compulsions they drive are seen.
689|sign|test or diagnosis|Diagnosed by cultures.
347|sign|appearance|Skin texture is seen.
348|sign|appearance|Patches are seen.
349|sign|examination|Reflexes are tested with a reflex hammer.
350|symptom|sensation|Pain is known only from the patient's account.
351|symptom|sensation|Pain is known only from the patient's account.
352|symptom|sensation|Pain and cramps are felt.
353|symptom|sensation|Pain is known only from the patient's account.
354|symptom|sensation|Pain is known only from the patient's account.
355|symptom|sensation|Pain is known only from the patient's account.
356|symptom|sensation|Pain is known only from the patient's account.
357|symptom|sensation|Pain is known only from the patient's account.
358|symptom|sensation|Pain is known only from the patient's account.
359|symptom|sensation|Pain is known only from the patient's account.
360|symptom|sensation|Pain is known only from the patient's account.
361|symptom|sensation|Pain and discomfort are felt.
362|symptom|sensation|Pain and relief are felt.
363|symptom|sensation|Pain is known only from the patient's account.
364|symptom|sensation|Pain is known only from the patient's account.
365|symptom|sensation|Pain is known only from the patient's account.
366|symptom|sensation|Mixed: pain on eye movement is felt (symptom); reduced eye movement is seen on examination (sign). Tie broken by the first item.
367|sign|appearance|The blisters are seen; pain and sensitivity describe them.
368|symptom|sensation|Pain is known only from the patient's account.
690|sign|observed event or behaviour|Mixed: carpopedal spasms are visible (sign); cramps are felt (symptom). Tie broken by the first item.
369|symptom|sensation|Pain is known only from the patient's account.
691|sign|appearance|Ulcers are seen; that they hurt describes them.
370|sign|appearance|Sores are seen; that they hurt describes them.
371|symptom|sensation|Pain is known only from the patient's account.
372|sign|appearance|The rash is seen; that it hurts describes it.
373|sign|appearance|Bumps and pus are seen.
374|sign|appearance|Sores are seen; that they hurt describes them.
375|sign|examination|Lumps are seen and felt; that they hurt describes them.
376|sign|examination|Lumps are seen and felt; that they hurt describes them.
692|symptom|perception|Mixed: blurriness is what the patient sees (symptom); reduced acuity is measured on an eye chart (sign). Tie broken by the first item.
693|sign|appearance|Bulging of the eye is seen, and the mass on imaging.
377|sign|appearance|Pallor is seen.
694|sign|appearance|Papules are seen.
695|sign|appearance|Papules are seen.
696|symptom|sensation|Palpitations and tremulousness (feeling shaky) are both felt.
378|symptom|mood or thought|Panic is felt.
379|sign|examination|Paralysis is seen and tested on examination.
380|sign|examination|Eye muscle paralysis is seen on examination.
381|symptom|perception|Sleep paralysis is experienced by the patient; others usually see nothing.
382|symptom|mood or thought|Delusions are beliefs known from what the patient says.
383|sign|examination|Paralysis is seen and tested on examination.
384|sign|appearance|Blisters are seen.
697|sign|observed event or behaviour|Seizures are seen by others.
385|sign|appearance|Peeling skin is seen.
386|symptom|sensation|Pain is known only from the patient's account.
387|symptom|sensation|Pain is known only from the patient's account.
698|symptom|sensation|Tingling is felt.
699|sign|examination|Swelling is seen and pits when pressed.
700|symptom|sensation|Pain is known only from the patient's account.
388|sign|observed event or behaviour|Personality changes are noticed by others.
701|sign|appearance|The rash is seen.
389|symptom|general feeling|Excessive thirst is felt; the amount drunk could be measured as a sign.
702|sign|appearance|Skin eruptions are seen.
390|sign|measurement|Urine volume is measured.
391|sign|examination|Reduced skin turgor is felt by an examiner.
392|sign|measurement|Weight is measured.
766|symptom|general feeling|Malaise after exertion is felt and reported.
393|sign|measurement|Growth and height are measured.
394|sign|appearance|Grey hair is seen.
703|symptom|sensation|Presyncope, lightheadedness and dizziness are all felt.
395|sign|test or diagnosis|Too general to place closely; metabolic problems are found on blood tests.
704|sign|observed event or behaviour|Diarrhea is seen and weight loss is measured.
396|sign|test or diagnosis|Low platelets are a blood-test result; the purpura and bleeding it comes with describe it.
705|sign|examination|Measured on cognitive testing.
397|symptom|reported function|Felt as food sticking; a swallow study would show it as a sign.
706|symptom|sensation|Breathlessness is felt.
707|sign|examination|Gait and limb coordination are tested on examination.
708|sign|examination|Gait and limb coordination are tested on examination.
398|sign|observed event or behaviour|Loss of speech is heard by others.
399|sign|examination|Muscle weakness is graded on strength testing.
400|sign|examination|Weakness in a named limb is graded on strength testing.
401|sign|examination|Weakness in a named limb is graded on strength testing.
402|sign|examination|Muscle weakness is graded on strength testing.
403|sign|appearance|Bleeding is seen.
404|sign|appearance|Bleeding is seen.
709|sign|appearance|Skin changes are seen.
405|sign|observed event or behaviour|Tremor is seen.
710|sign|test or diagnosis|Sleep architecture is recorded on polysomnography; parasomnias, apnoea and stridor are also seen or heard.
711|sign|examination|Mixed: muscle wasting is seen (sign); myalgias are felt (symptom). Tie broken by the first item.
406|sign|test or diagnosis|Diagnosed on blood tests; the anasarca it comes with describes it.
712|symptom|mood or thought|Mixed: paranoia and hallucinations are reported experiences (symptoms); confusion is observed (sign). Two of three items are symptoms.
407|symptom|mood or thought|Known from the hallucinations and delusions the patient reports.
408|sign|appearance|A puffy face is seen.
409|sign|appearance|Bruising is seen.
410|sign|appearance|The rash is seen.
411|sign|appearance|Bumps are seen.
713|sign|examination|The plantar response is tested on examination.
412|sign|observed event or behaviour|Rage attacks are seen by others.
413|sign|appearance|Nodules are seen; tenderness and pain describe them.
414|sign|appearance|Spots are seen.
714|sign|examination|Decline is seen by others and measured on testing.
415|sign|measurement|Heart rate is measured from the pulse; feeling it is "Heart palpitations".
715|sign|test or diagnosis|Diagnosed on imaging and blood oxygen.
716|sign|examination|Memory is measured on cognitive testing.
717|sign|appearance|Acanthosis nigricans is seen.
416|sign|test or diagnosis|Diagnosed on examination and nerve conduction studies.
718|sign|examination|Weakness is graded on strength testing.
417|sign|appearance|The rash is seen.
418|sign|appearance|The rash is seen.
419|sign|appearance|The rash is seen.
420|sign|appearance|The rash is seen; tenderness describes it.
719|sign|appearance|Skin lesions are seen.
421|sign|appearance|Bleeding is seen.
422|symptom|sensation|Pain is known only from the patient's account.
720|symptom|sensation|Mixed: urgency and tenesmus are felt (symptoms); incontinence is seen (sign). Two of three items are symptoms.
721|sign|test or diagnosis|Diagnosed on blood tests and imaging.
423|sign|observed event or behaviour|Prolonged sleep is seen by others and can be recorded.
722|sign|appearance|Blood coughed up is seen, and the cough heard.
424|sign|test or diagnosis|Infections are diagnosed by examination and cultures.
425|sign|test or diagnosis|A clinical diagnosis of brief neurological deficits that others can see.
723|sign|test or diagnosis|Low blood glucose is measured; its examples (confusion, coma, seizures) are all observed.
426|sign|appearance|Bumps are seen.
427|sign|appearance|Red eyes are seen.
428|sign|appearance|Patches are seen.
429|sign|appearance|Patches are seen.
430|sign|appearance|Patches are seen.
431|sign|appearance|Lip changes are seen.
432|sign|appearance|Redness is seen.
433|sign|appearance|Redness is seen.
434|symptom|general feeling|Sexual desire is felt and reported.
435|sign|examination|Reflexes are tested with a reflex hammer.
724|sign|test or diagnosis|Blood-test results.
725|sign|test or diagnosis|A blood-test result.
726|sign|observed event or behaviour|Seizures are seen by others and recorded on EEG.
436|sign|observed event or behaviour|Food coming back up is seen.
727|sign|examination|The pupil defect is tested with a light and the scotoma mapped on field testing.
437|sign|test or diagnosis|Blood and urine test results.
438|sign|observed event or behaviour|Repetitive movements are seen.
728|sign|examination|Seen on examination of the back of the eye.
729|symptom|sensation|Pain is known only from the patient's account.
439|symptom|sensation|Pain is known only from the patient's account.
440|symptom|sensation|Pain is known only from the patient's account.
441|symptom|perception|Only the patient hears the ringing.
442|sign|appearance|Blisters are seen.
443|symptom|general feeling|Craving is felt.
444|sign|appearance|Scaling is seen.
445|sign|appearance|Discoloration is seen.
446|sign|appearance|Hair loss is seen.
447|sign|examination|Tenderness is pain an examiner provokes by pressing the scalp.
448|sign|appearance|Scaly skin is seen.
449|sign|appearance|Scars are seen.
450|sign|examination|Corneal scars are seen on eye examination.
451|symptom|perception|Only the patient sees the flashes.
452|sign|observed event or behaviour|A seizure is an event others can see and an EEG can record; in an aware seizure the patient can also describe it.
453|sign|observed event or behaviour|A seizure is an event others can see and an EEG can record.
454|sign|observed event or behaviour|A seizure is an event others can see and an EEG can record.
455|symptom|sensation|Discomfort in heat is felt.
456|symptom|reported function|A reaction known from what the patient reports after eating gluten.
457|symptom|sensation|Discomfort from light is felt.
458|symptom|sensation|Discomfort from touch is felt.
730|sign|test or diagnosis|Mixed: agrypnia is loss of sleep recorded on polysomnography (sign); insomnia is the patient's complaint (symptom). Tie broken by the first item.
459|sign|test or diagnosis|Diagnosed on echocardiography; a murmur is heard.
731|sign|test or diagnosis|Diagnosed on biopsy; the diarrhea it comes with describes it.
732|sign|examination|Ataxia is tested on examination.
460|sign|test or diagnosis|Diagnosed on biopsy; the diarrhea it comes with describes it.
733|sign|test or diagnosis|A blood-test result.
734|symptom|reported function|Felt as food sticking; a swallow study would show it as a sign.
735|symptom|reported function|Mixed: difficulty swallowing is felt (symptom); neck flexor weakness is graded on strength testing (sign). Tie broken by the first item.
736|sign|measurement|Weight and growth are measured.
737|sign|test or diagnosis|Mixed: gastroparesis and pseudo-obstruction are shown by tests (signs); constipation is mostly what the patient feels (symptom). Two of three items are signs.
738|sign|test or diagnosis|A blood-test result.
461|symptom|sensation|Itching is felt.
462|sign|test or diagnosis|Malabsorption is shown by tests, and cachexia and weight loss are measured.
739|symptom|sensation|Pain is known only from the patient's account.
740|sign|measurement|Urine volume is measured.
463|sign|examination|Ataxia and the Romberg sign are tested on examination.
741|sign|examination|Weakness is graded on strength testing.
742|sign|appearance|Conjunctivitis and erosions are seen.
464|sign|examination|Weakness is graded on strength testing.
465|sign|examination|Ataxia and gait are tested on examination.
466|sign|examination|Memory is measured on cognitive testing.
743|sign|measurement|Blood pressure is measured lying and standing; fainting is seen by others.
744|sign|appearance|Skin lesions are seen.
467|sign|observed event or behaviour|Loose, frequent stools can be seen and measured.
745|sign|observed event or behaviour|Loose, frequent stools can be seen and measured.
746|sign|appearance|Mouth inflammation and erosions are seen.
747|sign|test or diagnosis|Blood glucose is measured.
468|symptom|reported function|Known from the patient's account.
469|sign|measurement|Height is measured.
470|symptom|sensation|Breathlessness is felt; a fast breathing rate or low oxygen would be its signs.
471|symptom|sensation|Breathlessness is felt.
472|symptom|sensation|Pain is known only from the patient's account.
748|symptom|sensation|Its examples are felt dryness of mouth and eyes; tear and saliva tests would make them signs.
473|sign|measurement|Weight is measured.
749|sign|appearance|Excess hair and virilization are seen, and missed periods are observable.
474|sign|test or diagnosis|An infection is diagnosed by examination and imaging.
475|sign|appearance|Discoloration is seen.
476|sign|appearance|Too general to place closely; skin disorders are seen.
477|sign|examination|Hardened skin is felt by an examiner.
478|sign|appearance|Skin lesions are seen.
479|symptom|sensation|Pain is known only from the patient's account.
480|sign|appearance|Loss of colour is seen.
481|sign|appearance|Sores are seen.
482|sign|measurement|Skin temperature can be felt and measured.
483|sign|examination|Texture is seen and felt.
484|sign|appearance|Depressions in the skull are seen and felt.
750|sign|examination|Ataxia is tested on examination.
485|symptom|reported function|Sleep trouble as the patient reports it.
486|symptom|general feeling|A felt lack of energy.
487|sign|appearance|Pitted skin is seen.
488|sign|appearance|Bumps are seen.
489|sign|appearance|Spots are seen.
490|sign|appearance|Spots are seen.
491|sign|observed event or behaviour|Withdrawal is behaviour others see.
492|sign|examination|Hematomas are seen and felt.
493|symptom|sensation|Pain is known only from the patient's account.
494|sign|examination|Sores and masses are seen when the eyelid is turned.
495|sign|examination|Bleeding into a joint shows as a swollen joint and is confirmed by aspiration or imaging.
496|sign|appearance|Hematomas are seen.
497|sign|appearance|Spots are seen.
498|symptom|sensation|Stiffness is felt.
499|symptom|sensation|Stiffness is felt.
500|sign|examination|Tight, thickened skin is felt by an examiner (sclerodactyly).
501|symptom|sensation|Stiffness is felt.
502|sign|observed event or behaviour|A stillbirth is a clinical event.
503|sign|appearance|The rash is seen; the stinging describes it.
751|sign|examination|Memory and orientation are measured on cognitive testing.
504|sign|examination|Weakness is graded on strength testing.
752|sign|appearance|Dark urine is seen.
505|sign|appearance|Swelling is seen.
506|sign|appearance|Swelling is seen.
507|sign|appearance|Swelling is seen and felt.
508|sign|appearance|Swelling is seen and felt.
509|sign|appearance|Swelling is seen and felt.
510|sign|appearance|Swelling is seen and felt.
511|sign|appearance|Swelling is seen.
512|sign|appearance|Swelling is seen.
513|sign|appearance|Swelling is seen.
514|sign|appearance|Swelling is seen.
515|sign|appearance|Swelling is seen.
516|sign|appearance|Swelling is seen.
517|sign|appearance|Swelling is seen.
518|sign|appearance|Swelling is seen and felt.
519|sign|appearance|Swelling is seen.
520|sign|appearance|Swelling is seen.
521|sign|appearance|Swelling is seen.
522|sign|appearance|Swelling is seen.
523|sign|appearance|Swelling is seen.
524|sign|appearance|Swelling is seen.
525|sign|appearance|Swelling is seen and felt.
526|sign|appearance|Swelling is seen.
527|sign|appearance|A swollen, red-spotted tongue is seen.
528|sign|appearance|Swelling is seen.
529|sign|examination|A nodule is seen and felt; that it hurts describes it.
753|sign|observed event or behaviour|Mixed: sweating and tremor are seen (signs); palpitations are felt (symptom). Two of three items are signs.
754|symptom|general feeling|Fatigue, asthenia and chest tightness are all felt.
755|sign|observed event or behaviour|Seizures are seen by others and recorded on EEG.
530|sign|examination|Tenderness is pain an examiner provokes by pressing.
531|sign|examination|Tenderness is pain an examiner provokes by pressing the tendon.
532|sign|appearance|Blisters are seen.
533|symptom|sensation|Pain is known only from the patient's account.
534|sign|appearance|Thickened skin is seen.
535|sign|examination|Thickened skin is felt by an examiner.
536|sign|examination|Thickened eyelid lining is seen and felt.
537|sign|appearance|Thin skin is seen.
538|sign|appearance|Facial wasting is seen.
539|sign|examination|Weakness of the throat muscles is seen on examination of the palate and swallow.
540|symptom|sensation|Pain is known only from the patient's account.
541|sign|observed event or behaviour|Tics are seen.
542|symptom|sensation|Tightness is felt.
543|symptom|sensation|Tingling is felt.
544|symptom|sensation|Tingling is felt.
545|symptom|sensation|Tingling is felt.
546|symptom|sensation|Tingling is felt.
547|symptom|sensation|Tingling is felt.
548|sign|appearance|Spots are seen.
549|symptom|general feeling|Tiredness is felt.
550|symptom|sensation|Pain is known only from the patient's account.
551|symptom|sensation|Pain is known only from the patient's account.
756|sign|examination|Pupil reactions are tested with a light.
552|sign|examination|Paralysis is seen and tested on examination.
757|sign|test or diagnosis|Blood-test results.
758|sign|test or diagnosis|Blood-test results.
553|sign|observed event or behaviour|Tremor is seen.
759|sign|measurement|Weight is measured.
554|sign|measurement|Weight is measured.
555|symptom|sensation|Felt unsteadiness; an unsteady gait seen by others is the sign ("Unsteady gait").
556|sign|observed event or behaviour|An unsteady gait is seen.
760|sign|appearance|Eyelid swelling and drooping are seen.
557|symptom|sensation|Urgency is felt.
558|sign|appearance|Bleeding is seen.
559|symptom|sensation|Dryness is felt.
560|symptom|sensation|Pain is known only from the patient's account.
561|sign|examination|Ulcers are seen on examination.
562|symptom|sensation|Vertigo is felt.
563|sign|appearance|The rash is seen.
564|sign|measurement|Vision is measured with an eye chart.
565|symptom|perception|A general complaint about sight (blur, doubling or loss), known from the patient's account.
761|sign|measurement|Measured on visual field testing.
762|sign|measurement|Measured on visual field testing.
566|sign|examination|Disc swelling is seen on examination of the back of the eye, and acuity measured.
763|symptom|perception|Mixed: floaters are what the patient sees (symptom); vitreous haze is seen on slit-lamp examination (sign). Tie broken by the first item.
567|symptom|perception|Only the patient has the experiences.
568|sign|observed event or behaviour|Vomiting is seen.
569|sign|appearance|Plaques are seen.
570|sign|appearance|Tears are seen.
571|symptom|general feeling|With no muscle named, it is the patient's sense of lacking strength; weakness of a named muscle group, graded on strength testing, is a sign.
572|sign|examination|Weakness is seen and graded on examination.
573|sign|examination|Weakness in a named part is graded on strength testing.
574|sign|examination|Weakness in a named part is graded on strength testing.
575|sign|examination|Weakness in a named part is graded on strength testing.
576|sign|examination|Weakness in a named part is graded on strength testing.
577|sign|examination|Read as weakness of the muscles that move the joints, which is graded on strength testing.
578|sign|examination|Weakness in a named part is graded on strength testing.
579|sign|examination|Weakness in a named part is graded on strength testing.
580|sign|examination|Weakness in a named part is graded on strength testing.
581|sign|measurement|Weight is measured.
582|sign|measurement|Weight is measured.
764|sign|measurement|Weight loss and fever are measured, and cyanosis is seen.
583|sign|observed event or behaviour|Wheezing is heard by others and with a stethoscope.
584|sign|appearance|Scars and bumps are seen.
585|symptom|sensation|Mixed: burning, throbbing, numbness and tingling are felt (symptoms); the red colour is seen (sign). Most items are symptoms.
586|sign|appearance|Patches are seen.
587|sign|appearance|Patches are seen.
588|sign|appearance|White hair is seen.
589|sign|appearance|Blisters are seen.
590|sign|appearance|Mixed: redness is seen (sign); itching is felt (symptom). Tie broken by the first item.
765|sign|appearance|Blisters are seen.
591|sign|appearance|A winged shoulder blade is seen.
592|symptom|sensation|Pain is known only from the patient's account.
593|symptom|sensation|Stiffness is felt.
594|sign|appearance|Yellow eyes are seen.
595|sign|appearance|Yellow skin is seen.
596|symptom|sensation|A fluttering feeling only the patient can report.
"""


def read_judgments():
    """ARIS id -> (classification, basis, explanation)."""
    judged = {}
    for line in JUDGMENTS.strip().splitlines():
        number, classification, basis, explanation = line.split("|")
        aris_id = f"ARIS:{int(number):07d}"
        if aris_id in judged:
            raise SystemExit(f"{aris_id} is judged twice")
        if basis not in BASES.get(classification, ()):
            raise SystemExit(f"{aris_id}: {basis!r} is not a basis for {classification!r}")
        judged[aris_id] = (classification, basis, explanation)
    return judged


def read_classes():
    """ARIS IRI -> (ARIS id, label, parent labels)."""
    root = ET.parse(SYMPTOMS).getroot()
    found = {}
    for el in root.findall(OWL + "Class"):
        iri = el.get(RDF + "about")
        if iri.startswith(ARIS):
            parents = [p.get(RDF + "resource") for p in el.findall(RDFS + "subClassOf")]
            found[iri] = (el.findtext(OBOINOWL + "id"), el.findtext(RDFS + "label").strip(), parents)
    return {iri: (aris_id, label, " | ".join(found[p][1] for p in parents if p in found))
            for iri, (aris_id, label, parents) in found.items()}


def count_diseases():
    """ARIS IRI -> number of diseases whose hasSymptom list links it."""
    root = ET.parse(DISEASE).getroot()
    concept = {}
    for ind in root.findall(OWL + "NamedIndividual"):
        ref = ind.find(ARI + "sharedConcept")
        if ref is not None:
            concept[ind.get(RDF + "about")] = ref.get(RDF + "resource")
    diseases = collections.defaultdict(set)
    for el in root:
        for ref in el.findall(ARI + "hasSymptom"):
            individual = ref.get(RDF + "resource")
            if individual in concept:
                diseases[concept[individual]].add(el.get(RDF + "about"))
    return {iri: len(listed) for iri, listed in diseases.items()}


def read_decisions():
    """ARIS id -> decision, from the table as it stands ({} before the first build)."""
    if not os.path.exists(REPORT):
        return {}
    with open(REPORT, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(f, dialect="excel-tab"))
    if not lines or lines[0] != COLUMNS:
        raise SystemExit(f"{REPORT}: the header is not {COLUMNS}")
    return {v[0]: v[COLUMNS.index("decision")] for v in lines[1:]}


def main():
    classes, judged, counts, decisions = read_classes(), read_judgments(), count_diseases(), read_decisions()
    unjudged = sorted(aris_id for aris_id, _, _ in classes.values() if aris_id not in judged)
    unknown = sorted(set(judged) - {aris_id for aris_id, _, _ in classes.values()})
    if unjudged or unknown:
        raise SystemExit(f"Classes with no judgment: {unjudged}; judgments for no class: {unknown}")

    rows = []
    for iri, (aris_id, label, parent) in classes.items():
        classification, basis, explanation = judged[aris_id]
        rows.append(dict(aris_id=aris_id, entry=label, parent=parent, diseases=str(counts.get(iri, 0)),
                         classification=classification, basis=basis, explanation=explanation,
                         decision=decisions.get(aris_id, "")))
    rows.sort(key=lambda r: (r["entry"].casefold(), r["aris_id"]))
    with open(REPORT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, dialect="excel-tab", lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            values = [row[c] for c in COLUMNS]
            if any(ch in value for value in values for ch in "\t\r\n"):
                raise SystemExit(f"{row['aris_id']}: a value has a tab or a line break")
            writer.writerow(values)

    tally = collections.Counter((r["classification"], r["basis"]) for r in rows)
    for classification in BASES:
        total = sum(n for (c, _), n in tally.items() if c == classification)
        listed = sum(1 for r in rows if r["classification"] == classification and r["diseases"] != "0")
        print(f"{classification}: {total} classes ({listed} listed by a disease)")
        for basis in BASES[classification]:
            print(f"  {basis}: {tally[classification, basis]}")
    mixed = sum(1 for r in rows if r["explanation"].startswith("Mixed:"))
    print(f"{len(rows)} classes, {mixed} mixed -> {os.path.relpath(REPORT, ROOT)}")


if __name__ == "__main__":
    main()
