#!/usr/bin/env python3
"""
Quellenanreicherungs-Script für MedExamAI Anki-Karten (v2)

Zwei-Quellen-Format:
- Intern: Ursprüngliche Quelle (Prüfungsprotokoll, Dateiname) BEIBEHALTEN + normalisiert
- Extern: Offizielle Leitlinie HINZUFÜGEN (AWMF/S3/ESC) oder "Recherche ausstehend"

POLICY: "Keine spezifische Leitlinie" NUR nach vollständiger 6-Schritt-Prüfung!
        Wenn automatische Prüfung nicht möglich: "Recherche ausstehend" + extern::pending Tag

Autor: Dagoberto (mit Claude Code)
Stand: 2025-12-29 (v2)
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# ============================================================================
# QUELLENTYPEN
# ============================================================================

class SourceType:
    LEITLINIE = 'leitlinie'       # AWMF S1/S2k/S2e/S3
    GESETZ = 'gesetz'             # BtMG, TPG, IfSG, StrlSchV
    ESC_GUIDELINE = 'esc'         # ESC Guidelines
    NVL = 'nvl'                   # Nationale VersorgungsLeitlinien
    FACHGESELLSCHAFT = 'fachges'  # DGK, DEGAM, etc.
    PENDING = 'pending'           # Recherche ausstehend


# ============================================================================
# LEITLINIEN-DATENBANK
# ============================================================================

class LeitlinienDB:
    """Datenbank für Leitlinien-Zuordnung basierend auf Keywords."""

    def __init__(self, manifest_path: Path):
        self.leitlinien = []
        self.keyword_index = defaultdict(list)
        self.rechtsquellen = {}
        self._load_manifest(manifest_path)
        self._build_keyword_index()
        self._add_rechtsquellen()

    def _load_manifest(self, path: Path):
        """Lädt das Leitlinien-Manifest."""
        if not path.exists():
            print(f"WARNUNG: Manifest nicht gefunden: {path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data.get('files', []):
            ll = {
                'name': entry.get('name', ''),
                'file': entry.get('file', ''),
                'awmf_number': entry.get('awmf_number'),
                'search_ref': entry.get('search_ref'),
                'fachgebiet': self._extract_fachgebiet(entry.get('file', '')),
            }
            self.leitlinien.append(ll)

    def _extract_fachgebiet(self, file_path: str) -> str:
        """Extrahiert das Fachgebiet aus dem Dateipfad."""
        parts = file_path.split('/')
        if len(parts) >= 2:
            return parts[1] if parts[0] in ('Leitlinien', '_BIBLIOTHEK') else parts[0]
        return 'Sonstige'

    def _add_rechtsquellen(self):
        """Fügt Rechtsquellen hinzu (keine AWMF-Leitlinien)."""
        self.rechtsquellen = {
            # BtM
            'btmg': ('Betäubungsmittelgesetz (BtMG) & BtMVV – BfArM/Bundesopiumstelle', SourceType.GESETZ),
            'btmvv': ('Betäubungsmittel-Verschreibungsverordnung (BtMVV) – BfArM', SourceType.GESETZ),
            'betäubungsmittel': ('Betäubungsmittelgesetz (BtMG) – BfArM/Bundesopiumstelle', SourceType.GESETZ),
            'opiat': ('BtMG/BtMVV – Opioidverschreibung; S3-LL LONTS (AWMF 145-003)', SourceType.LEITLINIE),

            # Transplantation/Organspende
            'tpg': ('Transplantationsgesetz (TPG) – Bundesgesetzblatt; BÄK-Richtlinien', SourceType.GESETZ),
            'organspende': ('Transplantationsgesetz (TPG) – Bundesgesetzblatt; BÄK-Richtlinien', SourceType.GESETZ),
            'hirntod': ('BÄK-Richtlinie Hirntoddiagnostik; TPG', SourceType.GESETZ),

            # Infektionsschutz
            'ifsg': ('Infektionsschutzgesetz (IfSG) §§ 6-9 – RKI/Bundesgesetzblatt', SourceType.GESETZ),
            'meldepflicht': ('Infektionsschutzgesetz (IfSG) §§ 6-9 – RKI', SourceType.GESETZ),
            'meldepflichtig': ('Infektionsschutzgesetz (IfSG) §§ 6-9 – RKI', SourceType.GESETZ),
            'rki': ('RKI-Empfehlungen / Infektionsschutzgesetz (IfSG)', SourceType.GESETZ),

            # Ärztliches Recht
            'schweigepflicht': ('StGB § 203, MBO-Ä § 9 – ärztliche Schweigepflicht', SourceType.GESETZ),
            'berufsordnung': ('Muster-Berufsordnung (MBO-Ä) – Bundesärztekammer', SourceType.GESETZ),
            'aufklärung': ('BGB § 630e (Patientenrechtegesetz) – Aufklärungspflicht', SourceType.GESETZ),
            'aufklärungspflicht': ('BGB § 630e (Patientenrechtegesetz)', SourceType.GESETZ),
            'behandlungsfehler': ('BGB §§ 630a-h (Patientenrechtegesetz) – Behandlungsvertrag', SourceType.GESETZ),
            'patientenrecht': ('BGB §§ 630a-h (Patientenrechtegesetz)', SourceType.GESETZ),

            # Strahlenschutz
            'strahlenschutz': ('Strahlenschutzverordnung (StrlSchV) / StrlSchG – EURATOM/ALARA', SourceType.GESETZ),
            'strlschv': ('Strahlenschutzverordnung (StrlSchV) – amtliche Fassung', SourceType.GESETZ),
            'alara': ('Strahlenschutzverordnung (StrlSchV) – ALARA-Prinzip', SourceType.GESETZ),
            'röntgen': ('Strahlenschutzverordnung (StrlSchV) – Röntgendiagnostik', SourceType.GESETZ),
            'kontrastmittel': ('ESUR-Leitlinie Kontrastmittel; StrlSchV bei CT', SourceType.LEITLINIE),

            # Sonstige Rechtsquellen
            'leichenschau': ('Landesbestattungsgesetze; AWMF S1-LL Leichenschau (054-002)', SourceType.GESETZ),
            'patientenverfügung': ('BGB §§ 1827-1828 (Patientenverfügung)', SourceType.GESETZ),
            'vorsorgevollmacht': ('BGB §§ 1827-1828', SourceType.GESETZ),
            'notstand': ('StGB § 34 (Rechtfertigender Notstand)', SourceType.GESETZ),
            'notwehr': ('StGB § 32 (Notwehr)', SourceType.GESETZ),
            'stgb': ('Strafgesetzbuch (StGB)', SourceType.GESETZ),
        }

    def _build_keyword_index(self):
        """Baut den Keyword-Index für schnelle Suche."""
        # Medizinische Keywords -> Leitlinien
        keyword_mappings = {
            # Kardiologie
            'herzinsuffizienz': ['herzinsuffizienz', 'hfref', 'hfpef', 'chronische herzinsuffizienz', 'herzschw'],
            'hypertonie': ['hypertonie', 'bluthochdruck', 'antihypertensiv'],
            'khk': ['koronare herzkrankheit', 'khk', 'angina', 'herzinfarkt', 'myokardinfarkt', 'stemi', 'nstemi', 'acs'],
            'vorhofflimmern': ['vorhofflimmern', 'vhf', 'afib', 'chads', 'chadvasc', 'antikoagulation'],
            'synkope': ['synkope', 'ohnmacht', 'kollaps'],
            'dyslipidämie': ['dyslipid', 'cholesterin', 'ldl', 'statin'],

            # Pneumologie
            'pneumonie': ['pneumonie', 'lungenentzündung', 'cap', 'hap', 'nosokomiale pneumonie'],
            'copd': ['copd', 'chronisch obstruktiv', 'gold-stadium'],
            'asthma': ['asthma', 'bronchial', 'peak flow'],
            'lungenembolie': ['lungenembolie', 'lae', 'thromboembolie', 'wells-score', 'genfer'],
            'tuberkulose': ['tuberkulose', 'tbc', 'mykobakter'],
            'pneumothorax': ['pneumothorax', 'spannungspneumo'],

            # Gastroenterologie
            'gerd': ['gerd', 'reflux', 'sodbrennen', 'ösophagitis', 'barrett'],
            'pankreatitis': ['pankreatitis', 'pankreas', 'lipase', 'amylase'],
            'leberzirrhose': ['zirrhose', 'leberzirrhose', 'aszites', 'child-pugh', 'hepatisch'],
            'gi_blutung': ['gi-blutung', 'meläna', 'hämatemesis', 'gastrointestinal blutung'],
            'hepatitis': ['hepatitis', 'hbv', 'hcv', 'hepatitis b', 'hepatitis c'],
            'gallensteine': ['gallenstein', 'choledocholithiasis', 'cholezystitis', 'mrcp', 'ercp'],
            'colitis': ['colitis ulcerosa', 'morbus crohn', 'ced', 'extraintestinal'],

            # Nephrologie
            'ckd': ['nierenerkrankung', 'ckd', 'niereninsuffizienz', 'dialyse', 'hämodialyse', 'gfr'],
            'harnwegsinfekt': ['harnwegsinfektion', 'hwi', 'zystitis', 'pyelonephritis'],

            # Neurologie
            'schlaganfall': ['schlaganfall', 'apoplex', 'tia', 'hirninfarkt', 'nihss'],
            'meningitis': ['meningitis', 'meningoenzephalitis', 'liquor', 'nackensteif'],
            'epilepsie': ['epilepsie', 'anfall', 'krampfanfall', 'antikonvulsiv'],
            'migräne': ['migräne', 'kopfschmerz', 'triptan'],

            # Onkologie
            'lungenkarzinom': ['lungenkarzinom', 'bronchialkarzinom', 'sclc', 'nsclc'],
            'kolorektales_karzinom': ['kolonkarzinom', 'rektumkarzinom', 'kolorektal', 'darmkrebs'],
            'mammakarzinom': ['mammakarzinom', 'brustkrebs', 'brca'],
            'prostatakarzinom': ['prostatakarzinom', 'prostatakrebs', 'psa'],
            'magenkarzinom': ['magenkarzinom', 'magenkrebs'],

            # Infektiologie
            'sepsis': ['sepsis', 'septisch', 'qsofa', 'multiorganversagen', 'sirs'],
            'antibiotika': ['antibiotika', 'antibiose', 'resistenz', 'mrsa'],

            # Notfallmedizin
            'reanimation': ['reanimation', 'cpr', 'herzdruckmassage', 'rosc', 'defibrillation'],
            'anaphylaxie': ['anaphylaxie', 'anaphylaktisch', 'allergische reaktion', 'adrenalin'],
            'polytrauma': ['polytrauma', 'schwerverletzt', 'schockraum', 'trauma'],

            # Orthopädie/Unfallchirurgie
            'arthrose': ['arthrose', 'gonarthrose', 'koxarthrose', 'hüft-tep', 'knie-tep'],
            'osteoporose': ['osteoporose', 'knochendichte', 'dxa', 'bisphosphonat'],
            'kreuzschmerz': ['kreuzschmerz', 'rückenschmerz', 'lumbal', 'lws'],
            'fraktur': ['fraktur', 'clavicula', 'radius', 'schenkelhal', 'monteggia', 'galeazzi'],

            # Psychiatrie
            'depression': ['depression', 'depressiv', 'antidepressiv', 'ssri', 'suizid'],
            'sucht': ['sucht', 'abhängigkeit', 'entzug', 'alkohol', 'substitution'],

            # Diabetologie
            'diabetes': ['diabetes', 'hba1c', 'metformin', 'insulin', 'diabetisch'],
            'diabetes_typ1': ['diabetes typ 1', 'typ-1-diabetes', 'ketoazidose'],
            'diabetes_typ2': ['diabetes typ 2', 'typ-2-diabetes'],

            # Hämatologie
            'thrombose': ['thrombose', 'vte', 'tvt', 'antikoagulation', 'heparin', 'noak'],
            'leukämie': ['leukämie', 'aml', 'all', 'cml', 'cll', 'blasten'],
            'myelom': ['myelom', 'plasmozytom', 'monoklonal'],

            # Pharmakologie
            'pharmako': ['pharmakologie', 'wirkstoff', 'nebenwirkung', 'interaktion'],
            'spironolacton': ['spironolacton', 'aldosteron', 'hyperkaliämie'],
            'diuretika': ['diuretika', 'furosemid', 'thiazid', 'schleifendiuretik'],
        }

        # Baue Index
        for ll in self.leitlinien:
            name_lower = ll['name'].lower()
            search_ref = (ll.get('search_ref') or '').lower()

            for topic, keywords in keyword_mappings.items():
                for kw in keywords:
                    if kw in name_lower or kw in search_ref:
                        if ll not in self.keyword_index[topic]:
                            self.keyword_index[topic].append(ll)
                        break

    def find_external_source(self, question: str, answer: str) -> tuple[Optional[str], str]:
        """
        Findet passende externe Quelle für eine Karte.
        Returns: (source_text, source_type)
        """
        combined = (question + ' ' + answer).lower()

        # 1. Prüfe Rechtsquellen zuerst (höhere Priorität für Rechtsfragen)
        for key, (source, stype) in self.rechtsquellen.items():
            if key in combined:
                return (source, stype)

        # 2. Prüfe medizinische Leitlinien
        found = []
        checked_topics = []

        topic_keywords = {
            'herzinsuffizienz': ['herzinsuffizienz', 'herzschw', 'hfref', 'hfpef'],
            'hypertonie': ['hypertonie', 'blutdruck', 'antihypertensiv'],
            'khk': ['khk', 'koronar', 'infarkt', 'acs', 'stemi', 'nstemi'],
            'vorhofflimmern': ['vorhofflimmern', 'vhf', 'antikoagulation'],
            'pneumonie': ['pneumonie', 'lungenentz'],
            'copd': ['copd', 'gold-stadium'],
            'asthma': ['asthma', 'bronchial'],
            'sepsis': ['sepsis', 'septisch', 'qsofa'],
            'diabetes': ['diabetes', 'hba1c', 'metformin', 'diabetisch'],
            'depression': ['depression', 'depressiv', 'antidepressiv'],
            'schlaganfall': ['schlaganfall', 'apoplex', 'tia'],
            'reanimation': ['reanimation', 'cpr', 'rosc'],
            'anaphylaxie': ['anaphylaxie', 'anaphylaktisch'],
            'polytrauma': ['polytrauma', 'schwerverletzt', 'schockraum'],
            'fraktur': ['fraktur', 'clavicula', 'monteggia', 'galeazzi'],
            'dialyse': ['dialyse', 'hämodialyse', 'shunt', 'nierenersatz'],
            'thrombose': ['thrombose', 'tvt', 'lungenembolie', 'lae'],
            'colitis': ['colitis', 'crohn', 'extraintestinal'],
            'leukämie': ['leukämie', 'aml', 'all', 'cml', 'cll'],
            'hepatitis': ['hepatitis', 'hbv', 'hcv'],
            'meningitis': ['meningitis', 'meningoenzephalitis'],
            'epilepsie': ['epilepsie', 'krampf', 'anfall'],
            'migräne': ['migräne', 'kopfschmerz'],
            'osteoporose': ['osteoporose', 'knochendichte'],
            'arthrose': ['arthrose', 'gonarthrose', 'koxarthrose', 'hüft-tep'],
            'pankreatitis': ['pankreatitis', 'pankreas', 'lipase'],
            'gerd': ['gerd', 'reflux', 'barrett'],
            'gallensteine': ['gallenstein', 'cholezystitis', 'ercp'],
            'leberzirrhose': ['zirrhose', 'aszites', 'child-pugh'],
        }

        for topic, kws in topic_keywords.items():
            for kw in kws:
                if kw in combined:
                    checked_topics.append(topic)
                    lls = self.keyword_index.get(topic, [])
                    if lls:
                        found.extend(lls[:2])
                    break

        if found:
            # Deduplizieren und formatieren
            seen = set()
            refs = []
            for ll in found:
                if ll['file'] not in seen:
                    seen.add(ll['file'])
                    refs.append(self._format_leitlinie(ll))
                if len(refs) >= 2:
                    break
            return ('; '.join(refs), SourceType.LEITLINIE)

        # 3. Kein Match -> Recherche ausstehend (NICHT "Keine Leitlinie"!)
        return (None, SourceType.PENDING)

    def _format_leitlinie(self, ll: dict) -> str:
        """Formatiert eine Leitlinie als Quellenangabe."""
        name = ll['name']
        awmf = ll.get('awmf_number')

        # Name bereinigen
        for prefix in ['AWMF_', 'ESC_', 'DGK_', 'DGVS_', 'OTHER_', 'STIKO_', 'KDIGO_',
                       'DGE_', 'DGIM_', 'DGHO_', 'GRC_']:
            if name.startswith(prefix):
                name = name[len(prefix):]
        name = re.sub(r'_[a-f0-9]{6}$', '', name)  # Hash-Suffix
        name = re.sub(r'_\d{4}-\d{2}.*$', '', name)  # Datums-Suffix
        name = name.replace('_', ' ')

        # Level erkennen
        if awmf and awmf.lower().startswith('nvl'):
            return f"NVL {name}"
        elif 'esc' in ll['name'].lower():
            return f"ESC-Leitlinie {name}"
        elif 'stiko' in ll['name'].lower():
            return f"STIKO-Empfehlung {name}"
        elif 'kdigo' in ll['name'].lower():
            return f"KDIGO-Leitlinie {name}"
        elif 'grc' in ll['name'].lower():
            return f"GRC-Leitlinie {name}"

        level = 'S2k'
        if 's3' in ll['name'].lower():
            level = 'S3'
        elif 's2e' in ll['name'].lower():
            level = 'S2e'
        elif 's1' in ll['name'].lower():
            level = 'S1'

        if awmf:
            return f"AWMF {level}-Leitlinie (Reg.-Nr. {awmf}) – {name}"
        return f"Fachgesellschafts-Empfehlung – {name}"


# ============================================================================
# QUELLENVERARBEITUNG
# ============================================================================

def normalize_internal_source(raw_source: str) -> str:
    """
    Normalisiert die interne Quelle, behält aber Original in Klammern.
    """
    if not raw_source:
        return 'Prüfungsprotokoll (Ursprung nicht dokumentiert)'

    normalized = raw_source
    original = raw_source

    # Normalisierungsregeln
    replacements = [
        # _OUTPUT/ Pfade
        (r'_OUTPUT/anki_ready_\d+\.tsv', 'MedExamAI-Export'),
        (r'_OUTPUT/evidenz_antworten[^|]*', 'MedExamAI-Antworten'),
        (r'_OUTPUT/[^\s|]+', 'MedExamAI-Export'),

        # Protokolle normalisieren
        (r'Kenntnisprüfung\s+Münster\s+Protokolle?\s*\d*\.pdf', 'KP Münster'),
        (r'Rechtsmedizin\s*\(\d+\)\.pdf', 'Rechtsmedizin (Prüfungsprotokoll)'),

        # Generische PDFs
        (r'([A-Za-zäöüÄÖÜ]+)\s*\(\d+\)\.pdf', r'\1 (Prüfungsprotokoll)'),
    ]

    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    # Bereinige Pipes und Leerzeichen
    normalized = re.sub(r'\s*\|\s*', ' | ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip(' |')

    # Falls KP Münster nicht drin ist aber Münster erwähnt wird
    if 'münster' in original.lower() and 'KP Münster' not in normalized:
        normalized = normalized + ' | KP Münster'

    # Original in Klammern nur wenn signifikant anders
    if normalized != original and len(original) > 10:
        # Kürze Original wenn zu lang
        if len(original) > 50:
            original_short = original[:47] + '...'
        else:
            original_short = original
        return f"{normalized} (Orig: {original_short})"

    return normalized


def extract_internal_source(answer: str) -> tuple[str, str]:
    """
    Extrahiert die interne Quelle aus der Antwort.
    Gibt zurück: (bereinigte_antwort, interne_quelle)
    """
    internal = ''
    cleaned = answer

    # Pattern für existierende Quellenangaben
    patterns = [
        r'<small>Quelle:\s*(.+?)</small>',
        r'<small>\[Quelle:\s*(.+?)\]</small>',
        r'\[Quelle:\s*(.+?)\]',
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            internal = match.group(1).strip()
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
            break

    # Entferne trailing HTML
    cleaned = re.sub(r'(<hr>|<br>)+\s*$', '', cleaned)
    cleaned = cleaned.strip()

    return cleaned, internal


def format_two_source_block(internal: str, external: Optional[str], source_type: str) -> str:
    """Formatiert den Zwei-Quellen-Block."""
    # Normalisiere interne Quelle
    int_normalized = normalize_internal_source(internal)

    # Externe Quelle formatieren
    if external and source_type != SourceType.PENDING:
        ext_line = f'<i>Extern:</i> {external}'
    else:
        ext_line = ('<i>Extern:</i> Recherche ausstehend – AWMF/Perplexity/Fachgesellschaften '
                    '(6-Schritt-Prüfung erforderlich)')

    return f'''<hr>
<b>Quellen:</b><br>
• <i>Intern:</i> {int_normalized}<br>
• {ext_line}'''


def process_card(question: str, answer: str, tags: str, db: LeitlinienDB) -> tuple[str, str, dict]:
    """
    Verarbeitet eine einzelne Karte.
    Returns: (new_answer, new_tags, metadata)
    """
    # Extrahiere interne Quelle
    cleaned_answer, internal = extract_internal_source(answer)

    # Finde externe Quelle
    external, source_type = db.find_external_source(question, cleaned_answer)

    # Formatiere neuen Quellenblock
    source_block = format_two_source_block(internal, external, source_type)

    # Neue Antwort
    new_answer = cleaned_answer + '<br><br>' + source_block

    # Tags aktualisieren
    new_tags = tags
    if source_type == SourceType.PENDING:
        if 'extern::pending' not in tags:
            new_tags = (tags + ' extern::pending').strip()

    # Metadata für Report/Queue
    metadata = {
        'question': question[:100],
        'internal_source': internal,
        'external_source': external,
        'source_type': source_type,
        'needs_research': source_type == SourceType.PENDING,
    }

    return new_answer, new_tags, metadata


def process_tsv(input_path: Path, output_path: Path, db: LeitlinienDB,
                pending_queue_path: Path, dry_run: bool = False) -> dict:
    """Verarbeitet eine TSV-Datei."""
    stats = {
        'total': 0,
        'with_leitlinie': 0,
        'with_gesetz': 0,
        'with_esc': 0,
        'with_nvl': 0,
        'pending': 0,
        'examples': [],
        'pending_cards': [],
    }

    rows = []

    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) < 2:
                rows.append(row)
                continue

            stats['total'] += 1
            question = row[0]
            answer = row[1]
            tags = row[2] if len(row) > 2 else ''

            # Verarbeite Karte
            new_answer, new_tags, metadata = process_card(question, answer, tags, db)

            # Statistik
            stype = metadata['source_type']
            if stype == SourceType.LEITLINIE:
                stats['with_leitlinie'] += 1
            elif stype == SourceType.GESETZ:
                stats['with_gesetz'] += 1
            elif stype == SourceType.ESC_GUIDELINE:
                stats['with_esc'] += 1
            elif stype == SourceType.NVL:
                stats['with_nvl'] += 1
            elif stype == SourceType.PENDING:
                stats['pending'] += 1
                stats['pending_cards'].append({
                    'id': stats['total'],
                    'question': question,
                    'internal_source': metadata['internal_source'],
                    'tags': new_tags,
                })

            # Speichere Beispiele (verschiedene Kategorien)
            if len(stats['examples']) < 20:
                stats['examples'].append({
                    'id': stats['total'],
                    'question': question[:120],
                    'source_type': stype,
                    'internal': metadata['internal_source'],
                    'external': metadata['external_source'],
                    'new_answer_tail': new_answer[-500:] if len(new_answer) > 500 else new_answer,
                })

            rows.append([question, new_answer, new_tags])

    if not dry_run:
        # Schreibe Output
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerows(rows)

        # Schreibe Pending-Queue
        if stats['pending_cards']:
            with open(pending_queue_path, 'w', encoding='utf-8') as f:
                for card in stats['pending_cards']:
                    f.write(json.dumps(card, ensure_ascii=False) + '\n')

    return stats


def print_report(stats: dict, output_path: Path, pending_path: Path):
    """Gibt einen detaillierten Report aus."""
    print(f"\n{'='*60}")
    print(f"QUELLENANREICHERUNG - REPORT")
    print(f"{'='*60}\n")

    total = stats['total']
    with_ext = stats['with_leitlinie'] + stats['with_gesetz'] + stats['with_esc'] + stats['with_nvl']

    print(f"Gesamt verarbeitet:    {total}")
    print(f"\nMit externer Quelle:   {with_ext} ({with_ext/total*100:.1f}%)")
    print(f"  - AWMF-Leitlinien:   {stats['with_leitlinie']}")
    print(f"  - Gesetze/Richtl.:   {stats['with_gesetz']}")
    print(f"  - ESC-Guidelines:    {stats['with_esc']}")
    print(f"  - NVL:               {stats['with_nvl']}")
    print(f"\nRecherche ausstehend:  {stats['pending']} ({stats['pending']/total*100:.1f}%)")
    print(f"  (Tag: extern::pending)")

    print(f"\nOutput-Dateien:")
    print(f"  - Angereicherte TSV: {output_path}")
    print(f"  - Pending-Queue:     {pending_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Reichert Anki-Karten mit Zwei-Quellen-Format an (v2)'
    )
    parser.add_argument('--input', type=Path, required=True,
                        help='Input TSV-Datei')
    parser.add_argument('--output', type=Path,
                        help='Output TSV-Datei')
    parser.add_argument('--manifest', type=Path,
                        default=Path('_BIBLIOTHEK/leitlinien_manifest.json'),
                        help='Pfad zum Leitlinien-Manifest')
    parser.add_argument('--pending-queue', type=Path,
                        default=Path('_OUTPUT/external_source_pending.jsonl'),
                        help='Pfad für Pending-Queue')
    parser.add_argument('--dry-run', action='store_true',
                        help='Nur analysieren, nicht schreiben')
    parser.add_argument('--show-examples', type=int, default=10,
                        help='Anzahl Beispiele anzeigen')

    args = parser.parse_args()

    if not args.output:
        args.output = args.input.with_stem(args.input.stem + '_enriched')

    print(f"=== Quellenanreicherung v2 (Zwei-Quellen-Format) ===\n")

    # Lade Leitlinien-DB
    print(f"Lade Leitlinien-Manifest: {args.manifest}")
    db = LeitlinienDB(args.manifest)
    print(f"  -> {len(db.leitlinien)} Leitlinien geladen")
    print(f"  -> {len(db.rechtsquellen)} Rechtsquellen definiert")
    print(f"  -> {len(db.keyword_index)} Themen indexiert\n")

    # Verarbeite TSV
    print(f"Verarbeite: {args.input}")
    if args.dry_run:
        print("  (Dry-Run: keine Dateien werden geschrieben)\n")

    stats = process_tsv(args.input, args.output, db, args.pending_queue, dry_run=args.dry_run)

    # Report
    print_report(stats, args.output, args.pending_queue)

    # Beispiele anzeigen
    if args.show_examples and stats['examples']:
        print(f"\n{'='*60}")
        print(f"{args.show_examples} BEISPIEL-KARTEN (gemischt)")
        print(f"{'='*60}\n")

        # Wähle diverse Beispiele
        shown = []
        for stype in [SourceType.GESETZ, SourceType.LEITLINIE, SourceType.PENDING]:
            for ex in stats['examples']:
                if ex['source_type'] == stype and len(shown) < args.show_examples:
                    if ex not in shown:
                        shown.append(ex)

        for i, ex in enumerate(shown[:args.show_examples], 1):
            print(f"--- Karte {ex['id']} [{ex['source_type'].upper()}] ---")
            print(f"Frage: {ex['question']}...")
            print(f"Quellenblock:")
            # Extrahiere nur den Quellenblock
            if '<hr>' in ex['new_answer_tail']:
                source_part = ex['new_answer_tail'].split('<hr>')[-1]
                # Formatiere für Lesbarkeit
                source_part = source_part.replace('<br>', '\n').replace('<b>', '').replace('</b>', '')
                source_part = source_part.replace('<i>', '').replace('</i>', '')
                source_part = re.sub(r'<[^>]+>', '', source_part)
                print(source_part)
            print()


if __name__ == '__main__':
    main()
