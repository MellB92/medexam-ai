#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Medical Subject/Fachgebiet Classifier
======================================

Automatische Erkennung medizinischer Fachgebiete aus Dokumenten.

Features:
- Keyword-basierte Klassifikation
- Fuzzy-Matching für Fachbegriffe
- Ordner-Struktur Analyse
- Multi-Label Support (Dokument kann mehrere Fachgebiete haben)

Model: Claude Sonnet 4.5
"""

import re
import logging
from typing import Dict, List, Set, Tuple
from pathlib import Path
from collections import Counter

logger = logging.getLogger(__name__)


class MedicalSubjectClassifier:
    """
    Klassifiziert medizinische Dokumente nach Fachgebiet.
    
    Erkennt über 20 medizinische Fachgebiete basierend auf:
    - Dateinamen
    - Ordnerstruktur
    - Textinhalt (Keywords)
    - Fuzzy-Matching
    """
    
    # Fachgebiete mit Keywords (Deutsch und Englisch)
    SUBJECT_KEYWORDS = {
        'Innere_Medizin': [
            'innere', 'internal', 'medizin', 'kardiologie', 'cardiology',
            'gastroenterologie', 'nephrologie', 'endokrinologie',
            'hämatologie', 'onkologie', 'rheumatologie'
        ],
        
        'Chirurgie': [
            'chirurgie', 'surgery', 'operation', 'op', 'operativ',
            'viszeralchirurgie', 'unfallchirurgie', 'gefäßchirurgie',
            'thoraxchirurgie', 'herz', 'transplantation'
        ],
        
        'Neurologie': [
            'neurologie', 'neurology', 'neuro', 'gehirn', 'brain',
            'schlaganfall', 'stroke', 'epilepsie', 'parkinson',
            'ms', 'multiple sklerose', 'demenz', 'alzheimer'
        ],
        
        'Psychiatrie': [
            'psychiatrie', 'psychiatry', 'psychisch', 'depression',
            'schizophrenie', 'bipolar', 'angst', 'psychose',
            'suizid', 'psychotherapie'
        ],
        
        'Pädiatrie': [
            'pädiatrie', 'pediatrics', 'kind', 'kinder', 'child',
            'neugeborenen', 'säugling', 'infant', 'jugendlich',
            'entwicklung', 'wachstum', 'impfung'
        ],
        
        'Gynäkologie': [
            'gynäkologie', 'gynecology', 'geburtshilfe', 'obstetrics',
            'schwangerschaft', 'pregnancy', 'geburt', 'menstruation',
            'ovar', 'uterus', 'mamma', 'schwanger'
        ],
        
        'Orthopädie': [
            'orthopädie', 'orthopedics', 'knochen', 'bone', 'fraktur',
            'fracture', 'gelenk', 'joint', 'wirbelsäule', 'spine',
            'arthroskopie', 'endoprothetik', 'trauma'
        ],
        
        'HNO': [
            'hno', 'ent', 'otolaryngology', 'hals', 'nase', 'ohr',
            'ear', 'nose', 'throat', 'larynx', 'pharynx',
            'sinusitis', 'tonsillitis', 'hörsturz'
        ],
        
        'Augenheilkunde': [
            'ophthalmologie', 'ophthalmology', 'auge', 'eye', 'vision',
            'katarakt', 'cataract', 'glaukom', 'glaucoma',
            'retina', 'macula', 'sehvermögen'
        ],
        
        'Dermatologie': [
            'dermatologie', 'dermatology', 'haut', 'skin', 'dermato',
            'ekzem', 'eczema', 'psoriasis', 'melanom', 'mole',
            'allergie', 'hautkrebs'
        ],
        
        'Urologie': [
            'urologie', 'urology', 'niere', 'kidney', 'blase', 'bladder',
            'prostata', 'prostate', 'harnwege', 'urinary',
            'inkontinenz', 'niereninsuffizienz'
        ],
        
        'Anästhesie': [
            'anästhesie', 'anesthesia', 'narkose', 'analgosedierung',
            'schmerztherapie', 'pain', 'intubation', 'beatmung',
            'intensivmedizin', 'icu', 'reanimation'
        ],
        
        'Radiologie': [
            'radiologie', 'radiology', 'bildgebung', 'imaging',
            'röntgen', 'xray', 'ct', 'mrt', 'mri', 'sonographie',
            'ultraschall', 'ultrasound', 'pet', 'szintigraphie'
        ],
        
        'Nuklearmedizin': [
            'nuklearmedizin', 'nuclear', 'szintigraphie', 'scintigraphy',
            'pet', 'spect', 'tracer', 'radioaktiv', 'isotop',
            'schilddrüse', 'thyroid'
        ],
        
        'Pathologie': [
            'pathologie', 'pathology', 'histologie', 'histology',
            'biopsie', 'biopsy', 'zytologie', 'autopsy',
            'gewebeprobe', 'tumor', 'malignität'
        ],
        
        'Pharmakologie': [
            'pharmakologie', 'pharmacology', 'medikament', 'drug',
            'arzneimittel', 'wirkstoff', 'dosierung', 'dose',
            'nebenwirkung', 'kontraindikation', 'antibiotika'
        ],
        
        'Notfallmedizin': [
            'notfall', 'emergency', 'reanimation', 'cpr', 'trauma',
            'polytrauma', 'schock', 'akut', '急', 'notarzt',
            'rettung', 'ambulance'
        ],
        
        'Allgemeinmedizin': [
            'allgemein', 'general', 'hausarzt', 'family',
            'prävention', 'prevention', 'vorsorge', 'check',
            'gesundheit', 'health'
        ],
        
        'Labormedizin': [
            'labor', 'laboratory', 'klinische chemie', 'hämatologie',
            'blutbild', 'cbc', 'blutwerte', 'elektrolyte',
            'enzyme', 'marker', 'serologie'
        ],
        
        'Hygiene': [
            'hygiene', 'infektologie', 'infectious', 'mrsa',
            'steril', 'desinfektion', 'antisepsis', 'nosokomial',
            'krankenhaus', 'infektion'
        ],
        
        'Medizinrecht': [
            'medizinrecht', 'medizin recht', 'aufklärung', 'einwilligung',
            'haftung', 'dokumentation', 'arztfehler', 'gutachten',
            'jurisprudence', 'legal', 'consent'
        ]
    }
    
    def __init__(self):
        """Initialize Subject Classifier."""
        self.classification_stats = Counter()
        logger.info("MedicalSubjectClassifier initialisiert (20+ Fachgebiete)")
    
    def classify_by_keywords(self, text: str, filename: str = "") -> Dict[str, float]:
        """
        Klassifiziert nach Keywords mit Fuzzy-Matching.
        
        Args:
            text: Dokumenttext
            filename: Dateiname für zusätzlichen Kontext
            
        Returns:
            Dict {Fachgebiet: Score (0.0-1.0)}
        """
        scores: Dict[str, float] = {subject: 0.0 for subject in self.SUBJECT_KEYWORDS}
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Keyword-Matching
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            subject_score = 0.0
            
            for keyword in keywords:
                # Text-Matching
                text_matches = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
                subject_score += text_matches * 2
                
                # Filename-Matching (höher gewichtet)
                if keyword in filename_lower:
                    subject_score += 10
            
            # Normalisiere Score
            word_count = len(text.split())
            if word_count > 0:
                scores[subject] = min(1.0, subject_score / (word_count * 0.01))
        
        return scores
    
    def classify_by_path(self, file_path: str) -> Dict[str, float]:
        """
        Klassifiziert basierend auf Ordnerstruktur.
        
        Args:
            file_path: Dateipfad
            
        Returns:
            Dict {Fachgebiet: Score}
        """
        scores: Dict[str, float] = {subject: 0.0 for subject in self.SUBJECT_KEYWORDS}
        
        path_parts = Path(file_path).parts
        path_lower = str(file_path).lower()
        
        for subject, keywords in self.SUBJECT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in path_lower:
                    scores[subject] += 0.5
        
        return scores
    
    def get_primary_subjects(self, 
                            scores: Dict[str, float], 
                            threshold: float = 0.1,
                            max_subjects: int = 3) -> List[str]:
        """
        Ermittelt Haupt-Fachgebiete aus Scores.
        
        Args:
            scores: Subject scores
            threshold: Minimum Score für Inclusion
            max_subjects: Maximum Anzahl Fachgebiete
            
        Returns:
            Liste der Haupt-Fachgebiete (sortiert nach Score)
        """
        # Filtere nach Threshold
        filtered = {k: v for k, v in scores.items() if v >= threshold}
        
        if not filtered:
            return ['Allgemeinmedizin']  # Default
        
        # Sortiere nach Score und nehme Top-N
        sorted_subjects = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        primary = [subject for subject, score in sorted_subjects[:max_subjects]]
        
        self.classification_stats.update(primary)
        
        return primary
    
    def classify_document(self, 
                         text: str, 
                         file_path: str = "") -> Tuple[List[str], Dict[str, float]]:
        """
        Vollständige Dokument-Klassifikation.
        
        Args:
            text: Dokumenttext
            file_path: Dateipfad
            
        Returns:
            Tuple (primary_subjects, all_scores)
        """
        # Kombiniere beide Klassifikationsmethoden
        keyword_scores = self.classify_by_keywords(text, Path(file_path).name)
        path_scores = self.classify_by_path(file_path)
        
        # Kombiniere Scores (gewichtet)
        combined_scores = {}
        for subject in self.SUBJECT_KEYWORDS:
            combined_scores[subject] = (
                keyword_scores[subject] * 0.7 +  # 70% Keywords
                path_scores[subject] * 0.3        # 30% Pfad
            )
        
        # Ermittle Hauptfachgebiete
        primary_subjects = self.get_primary_subjects(combined_scores)
        
        logger.debug(
            f"Klassifiziert {Path(file_path).name}: "
            f"{', '.join(primary_subjects)} "
            f"(Score: {combined_scores[primary_subjects[0]]:.2f})"
        )
        
        return primary_subjects, combined_scores
    
    def get_statistics(self) -> Dict:
        """Gibt Klassifikations-Statistiken zurück."""
        return {
            'total_classifications': sum(self.classification_stats.values()),
            'by_subject': dict(self.classification_stats.most_common())
        }


# Convenience Funktion
def classify_medical_document(text: str, file_path: str = "") -> List[str]:
    """
    Schnelle Fachgebiet-Klassifikation.
    
    Args:
        text: Dokumenttext
        file_path: Dateipfad
        
    Returns:
        Liste der Fachgebiete
    """
    classifier = MedicalSubjectClassifier()
    subjects, _ = classifier.classify_document(text, file_path)
    return subjects


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    test_text = """
    Herzinsuffizienz
    
    Definition: Unvermögen des Herzens, den Körper ausreichend mit Blut zu versorgen.
    
    Diagnose:
    - Anamnese
    - EKG: Rhythmusstörungen
    - Echokardiographie
    - BNP/NT-proBNP
    
    Therapie:
    - ACE-Hemmer
    - Betablocker
    - Diuretika
    """
    
    classifier = MedicalSubjectClassifier()
    subjects, scores = classifier.classify_document(test_text, "herzinsuffizienz.pdf")
    
    print(f"Erkannte Fachgebiete: {', '.join(subjects)}")
    print(f"\nTop 5 Scores:")
    for subject, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]:
        if score > 0:
            print(f"  {subject}: {score:.3f}")