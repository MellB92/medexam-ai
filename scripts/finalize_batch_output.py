import json
import os

# Data from my manual reconstruction above
reconstructed_questions_data = [
    {"index": 0, "new_question": "Nennen Sie die Muskeln, die vom N. axillaris, N. radialis, N. medianus und N. ulnaris innerviert werden."},
    {"index": 1, "new_question": "Was ist ein D-Arzt (Durchgangsarzt) und wann wird er eingeschaltet?"},
    {"index": 2, "new_question": "Was ist die Berufsgenossenschaft und welche Aufgaben hat sie?"},
    {"index": 3, "new_question": "Wie ist vorzugehen bei Fällen, bei denen eine Impfschädigung vermutet wird?"},
    {"index": 4, "new_question": "Welche Strafe gibt es, wenn man der Bundeswehr oder einer Behörde angehört und sich nicht impfen lässt?"},
    {"index": 5, "new_question": "Was sind Betäubungsmittel (BtM) gemäß Betäubungsmittelgesetz?"},
    {"index": 6, "new_question": "Was sind Medizinprodukte?"},
    {"index": 7, "new_question": "Was versteht man unter Organspende und welche Formen gibt es?"},
    {"index": 8, "new_question": "Was ist Eurotransplant und welche Aufgaben hat es?"},
    {"index": 9, "new_question": "Was passiert, wenn die Eltern eines minderjährigen Patienten sich gegen einen lebensrettenden Eingriff widersetzen?"},
    {"index": 10, "new_question": "Wie wird mit einem suizidalen Patienten umgegangen, der eine lebensrettende Behandlung ablehnt?"},
    {"index": 11, "new_question": "Wem gehören die Krankenunterlagen und welche Rechte hat der Patient in Bezug auf diese?"},
    {"index": 12, "new_question": "Wie sieht das weitere diagnostische Vorgehen bei Verdacht auf chronisch entzündliche Darmerkrankung (CED) aus?"},
    {"index": 13, "new_question": "Welche Laborwerte sollten bei Verdacht auf CED bestimmt werden?"},
    {"index": 14, "new_question": "Welche Dosis Prednisolon wird bei einem schweren Schub einer Colitis ulcerosa systemisch verabreicht?"},
    {"index": 15, "new_question": "Was ist die Funktion des Zwerchfells und welche Lücken gibt es, durch die Hernien entstehen können?"},
    {"index": 16, "new_question": "Was ist der Unterschied zwischen einem Strahlenschutzverantwortlichen und einem Strahlenschutzbeauftragten?"},
    {"index": 17, "new_question": "Wo ist die ärztliche Schweigepflicht gesetzlich geregelt?"},
    {"index": 18, "new_question": "Was sind sichere Todeszeichen?"},
    {"index": 19, "new_question": "Wen stellt der Richter als Betreuer auf, wenn keine Patientenverfügung vorliegt? Müssen es unbedingt Angehörige sein?"},
    {"index": 20, "new_question": "Was bedeutet der englische Begriff 'flail chest' auf Deutsch?"},
    {"index": 21, "new_question": "Nennen Sie die verschiedenen Schockformen, ihre Ursachen und Therapieansätze."}, # Manual reconstruction for the unanswerable one
    {"index": 22, "new_question": "Welche Differentialdiagnosen (z.B. Sprunggelenksverletzung) kommen bei den beschriebenen Symptomen in Betracht?"},
    {"index": 23, "new_question": "Wie entsteht Röntgenstrahlung?"},
    {"index": 24, "new_question": "Welche Diuretika kennen Sie und welche darf man wann kombinieren?"},
    {"index": 25, "new_question": "Bei welchem Unfallmechanismus tritt eine Kreuzbandruptur typischerweise auf?"},
    {"index": 26, "new_question": "Was sind die Ursachen für maligne Lebertumoren, insbesondere bei vorbestehender Leberzirrhose?"},
    {"index": 27, "new_question": "Worauf müssen wir während der Cholezystektomie achten (Calot-Dreieck) und warum ist es wichtig, den Ductus choledochus nicht zu verletzen?"},
    {"index": 28, "new_question": "Welches Medikament würden Sie der Mutter telefonisch für das Kind empfehlen?"},
    {"index": 29, "new_question": "Welche Körperteile sind bei Röntgenuntersuchungen der Strahlenbelastung ausgesetzt, aber oft nicht geschützt (neben den Augenlinsen)?"},
    {"index": 30, "new_question": "Welche Therapiemöglichkeiten gibt es beim Pleuramesotheliom?"},
    {"index": 31, "new_question": "Wie sind Diagnostik (Labor, Sono, Szintigrafie/TC-Uptake) und Behandlung bei Schilddrüsenerkrankungen (Hashimoto, Basedow, Karzinom)?"},
    {"index": 32, "new_question": "Wie antikoagulieren Sie einen Patienten mit Vorhofflimmern, der einen Stent bekommen hat?"},
    {"index": 33, "new_question": "Was ist eine typische Verletzung bei einem Verdrehtrauma im Kniegelenk?"},
    {"index": 34, "new_question": "Welche Impfungen empfehlen Sie vor einer Reise nach Zentralafrika?"},
    {"index": 35, "new_question": "Welche Art von Prophylaxe gegen Infektionskrankheiten würden Sie vornehmen?"},
    {"index": 36, "new_question": "Gegen welche weiteren Krankheiten (neben HAV) sollte geimpft werden?"},
    {"index": 37, "new_question": "Wie sind Sie versichert, wenn Sie als Arzt im Rettungswagen bei einem Unfall verletzt werden?"},
    {"index": 38, "new_question": "Durch wen sind Sie im Fall eines Arbeitsunfalls (z.B. im Rettungswagen) versichert?"},
    {"index": 39, "new_question": "Welche Antikörper sind bei Diabetes Mellitus Typ 1 positiv?"}
]

# Read the results from fragmente_rekon_text.json (which contains original, source_file, block_id, context)
# and merge with the new_question field.
output_file = "_OUTPUT/fragmente_reconstructed_batches.json"
rekon_text_file = "_OUTPUT/fragmente_rekon_text.json"

final_output = []

if os.path.exists(rekon_text_file):
    with open(rekon_text_file, "r") as f:
        rekon_data = json.load(f)

    # Create a dictionary for quick lookup of new_question by index
    new_questions_map = {item["index"]: item["new_question"] for item in reconstructed_questions_data}

    for item in rekon_data:
        if item["index"] < 40 and item["status"] == "reconstructable":
            new_q = new_questions_map.get(item["index"])
            if new_q:
                final_output.append({
                    "index": item["index"],
                    "original": item["original"],
                    "new_question": new_q,
                    "source_file": item["source_file"],
                    "block_id": item["block_id"]
                })

# Sort by index
final_output.sort(key=lambda x: x["index"])

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(final_output)} reconstructed fragments to {output_file}")