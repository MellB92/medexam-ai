#!/usr/bin/env python3
"""
MedExamAI Leitlinien-Fetcher
============================

Automatisierter Downloader für deutsche medizinische Leitlinien.

Unterstützte Quellen:
- AWMF (Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen Fachgesellschaften)
- DGIM (Deutsche Gesellschaft für Innere Medizin)
- ESC (European Society of Cardiology)
- DGU (Deutsche Gesellschaft für Urologie)
- DGOU (Deutsche Gesellschaft für Orthopädie und Unfallchirurgie)
- DRG (Deutsche Röntgengesellschaft)
- DGI (Deutsche Gesellschaft für Infektiologie)
- und weitere...

Features:
- Automatische Theme-Erkennung aus medizinischem Text
- Mapping von Themen zu relevanten Fachgesellschaften
- Paralleles Herunterladen mit Connection Pooling
- Caching und Versionierung
- Qualitäts-Scoring

Autor: MedExamAI Team
"""

import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


# Theme-zu-Fachgesellschaft Mapping
THEME_TO_SOCIETY = {
    # Kardiologie
    "Kardiologie": ["ESC", "DGIM", "AWMF"],
    "Herzinsuffizienz": ["ESC", "DGIM"],
    "Myokardinfarkt": ["ESC", "DGIM"],
    "Koronare Herzkrankheit": ["ESC", "DGIM"],
    "Hypertonie": ["ESC", "DGIM", "AWMF"],
    "Arrhythmie": ["ESC", "DGIM"],
    "Vorhofflimmern": ["ESC", "DGIM"],

    # Innere Medizin
    "Diabetes": ["DGIM", "AWMF"],
    "Pneumonie": ["DGIM", "AWMF", "DGI"],
    "COPD": ["DGIM", "AWMF"],
    "Asthma": ["DGIM", "AWMF"],
    "Gastroenterologie": ["DGIM", "AWMF"],
    "Nephrologie": ["DGIM", "AWMF"],

    # Urologie
    "Urologie": ["DGU", "AWMF"],
    "Prostatakarzinom": ["DGU", "AWMF"],
    "Harnsteinleiden": ["DGU"],
    "Blasenkarzinom": ["DGU", "AWMF"],

    # Orthopädie/Unfallchirurgie
    "Orthopädie": ["DGOU", "AWMF"],
    "Unfallchirurgie": ["DGOU", "AWMF"],
    "Fraktur": ["DGOU", "AWMF"],
    "Polytrauma": ["DGOU", "AWMF"],
    "Endoprothetik": ["DGOU", "AWMF"],
    "Wirbelsäule": ["DGOU", "AWMF"],

    # Radiologie
    "Radiologie": ["DRG", "AWMF"],
    "Bildgebung": ["DRG", "AWMF"],
    "CT": ["DRG"],
    "MRT": ["DRG"],
    "Röntgen": ["DRG", "AWMF"],

    # Infektiologie
    "Infektiologie": ["DGI", "AWMF"],
    "Sepsis": ["DGI", "AWMF", "DGIM"],
    "HIV": ["DGI", "AWMF"],
    "Hepatitis": ["DGI", "DGIM", "AWMF"],
    "Meningitis": ["DGI", "AWMF"],
    "Antibiotika": ["DGI", "AWMF"],

    # Chirurgie
    "Chirurgie": ["DGCH", "AWMF"],
    "Viszeralchirurgie": ["DGAV", "AWMF"],
    "Appendizitis": ["DGCH", "AWMF"],
    "Kolorektales Karzinom": ["DGAV", "AWMF"],

    # Neurologie
    "Neurologie": ["DGN", "AWMF"],
    "Schlaganfall": ["DGN", "AWMF"],
    "Epilepsie": ["DGN", "AWMF"],

    # Notfallmedizin
    "Notfall": ["AWMF", "DGIM"],
    "Reanimation": ["AWMF"],
    "Schock": ["AWMF", "DGIM"],
}

# Medizinische Keyword-Pattern für Theme-Erkennung
MEDICAL_KEYWORDS = {
    "Kardiologie": [
        r"\b(Herz|kardial|Myokard|Koronar|Arrhythmi|EKG|Echokardiographie)\w*\b",
        r"\b(Herzinsuffizienz|Myokardinfarkt|KHK|Angina\s+pectoris)\b",
    ],
    "Diabetes": [
        r"\b(Diabetes|diabetisch|Blutzucker|Glukose|HbA1c|Insulin)\w*\b",
        r"\b(Typ-[12]-Diabetes|Hyperglykämie|Hypoglykämie)\b",
    ],
    "Pneumonie": [
        r"\b(Pneumonie|Lungenentzündung|pulmon|Lunge)\w*\b",
        r"\b(Atemweg|respiratorisch|Bronchitis)\w*\b",
    ],
    "Orthopädie": [
        r"\b(Orthopädie|orthopädisch|Knochen|Gelenk|Skelett)\w*\b",
        r"\b(Fraktur|Bruch|Endoprothese|Arthrose|Osteoporose)\w*\b",
        r"\b(Wirbelsäule|Bandscheibe|Hüfte|Knie|Schulter)\w*\b",
    ],
    "Unfallchirurgie": [
        r"\b(Unfall|Trauma|Polytrauma|Verletzung)\w*\b",
        r"\b(Frakturversorgung|Osteosynthese|Fixateur)\w*\b",
    ],
    "Infektiologie": [
        r"\b(Infektion|infektiös|Sepsis|bakteriell|viral)\w*\b",
        r"\b(Antibiotika|Erreger|Pathogen|HIV|Hepatitis)\w*\b",
    ],
    "Urologie": [
        r"\b(Prostata|Harn|Blase|Niere|urolog)\w*\b",
        r"\b(PSA|Harnstein|Inkontinenz|Urethra)\b",
    ],
    "Chirurgie": [
        r"\b(Chirurgie|chirurgisch|Operation|OP|operativ)\w*\b",
        r"\b(Eingriff|Resektion|Laparoskopie)\w*\b",
    ],
    "Radiologie": [
        r"\b(Radiologie|Bildgebung|CT|MRT|Röntgen|Sonographie)\b",
        r"\b(radiologisch|bildgebend|Tomographie)\w*\b",
    ],
}


@dataclass
class GuidelineMetadata:
    """Metadaten für eine medizinische Leitlinie."""
    title: str
    source: str  # AWMF, DGIM, ESC, etc.
    registry_number: Optional[str]
    version: str
    publication_date: str
    valid_until: Optional[str]
    specialty: str
    url: str
    local_path: Optional[str] = None
    downloaded_at: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str = "valid"  # valid, expired, updated
    quality_score: float = 0.0  # 0.0-1.0 basierend auf S-Level, Aktualität
    relevance_score: float = 0.0  # 0.0-1.0 basierend auf Theme-Matching
    detected_themes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "registry_number": self.registry_number,
            "version": self.version,
            "publication_date": self.publication_date,
            "valid_until": self.valid_until,
            "specialty": self.specialty,
            "url": self.url,
            "local_path": self.local_path,
            "downloaded_at": self.downloaded_at,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status,
            "quality_score": self.quality_score,
            "relevance_score": self.relevance_score,
            "detected_themes": self.detected_themes,
        }


def detect_medical_themes(text: str, top_n: int = 5) -> List[Tuple[str, float]]:
    """
    Erkennt medizinische Themen aus Text mittels Keyword-Matching.

    Args:
        text: Medizinischer Text zur Analyse
        top_n: Anzahl der Top-Themen

    Returns:
        Liste von (theme, confidence_score) Tupeln, sortiert nach Konfidenz
    """
    if not text or len(text) < 50:
        return []

    theme_scores: Dict[str, float] = defaultdict(float)

    # Score für jedes Theme basierend auf Keyword-Matches
    for theme, patterns in MEDICAL_KEYWORDS.items():
        matches = 0
        for pattern in patterns:
            matches += len(re.findall(pattern, text, re.IGNORECASE))

        if matches > 0:
            # Normalisieren nach Textlänge (Matches pro 1000 Zeichen)
            score = (matches / len(text)) * 1000
            theme_scores[theme] = min(1.0, score)

    # Auch direkte Theme-Erwähnungen prüfen
    text_lower = text.lower()
    for theme_key in THEME_TO_SOCIETY.keys():
        if theme_key.lower() in text_lower:
            theme_scores[theme_key] = max(theme_scores.get(theme_key, 0.0), 0.5)

    # Sortieren nach Score
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)

    logger.debug(f"Erkannte Themen: {sorted_themes[:top_n]}")
    return sorted_themes[:top_n]


def map_themes_to_societies(themes: List[Tuple[str, float]]) -> Dict[str, float]:
    """
    Mappt erkannte Themen auf relevante Fachgesellschaften.

    Args:
        themes: Liste von (theme, confidence) Tupeln

    Returns:
        Dictionary {society: relevance_score}
    """
    society_scores: Dict[str, float] = defaultdict(float)

    for theme, confidence in themes:
        societies = THEME_TO_SOCIETY.get(theme, [])
        for society in societies:
            society_scores[society] += confidence / len(societies) if societies else 0

    # Normalisieren
    if society_scores:
        max_score = max(society_scores.values())
        if max_score > 0:
            society_scores = {
                soc: score / max_score
                for soc, score in society_scores.items()
            }

    return dict(sorted(society_scores.items(), key=lambda x: x[1], reverse=True))


class GuidelineFetcher:
    """Fetcher für deutsche medizinische Leitlinien."""

    # Basis-URLs der Fachgesellschaften
    SOURCES = {
        "AWMF": "https://www.awmf.org",
        "DGIM": "https://www.dgim.de",
        "ESC": "https://www.escardio.org",
        "DGU": "https://www.dgu.de",
        "DGOU": "https://www.dgou.de",
        "DRG": "https://www.drg.de",
        "DGI": "https://www.dgi-net.de",
        "DGCH": "https://www.dgch.de",
        "DGAV": "https://www.dgav.de",
        "DGN": "https://www.dgn.org",
    }

    def __init__(
        self,
        download_dir: str = "_BIBLIOTHEK/Leitlinien",
        cache_file: str = "guideline_cache.json",
        max_parallel: int = 4
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.download_dir / cache_file
        self.cache: Dict[str, GuidelineMetadata] = {}
        self._load_cache()

        self.max_parallel = max_parallel

        # Session für Connection Pooling
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        })

        logger.info(f"GuidelineFetcher initialisiert: {self.download_dir}")

    def _load_cache(self) -> None:
        """Lädt Cache aus Datei."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.cache[k] = GuidelineMetadata(**v)
                logger.info(f"Cache geladen: {len(self.cache)} Leitlinien")
            except Exception as e:
                logger.error(f"Cache-Ladefehler: {e}")

    def _save_cache(self) -> None:
        """Speichert Cache in Datei."""
        try:
            data = {k: v.to_dict() for k, v in self.cache.items()}
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Cache-Speicherfehler: {e}")

    def get_curated_guidelines(
        self,
        specialty: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 50
    ) -> List[GuidelineMetadata]:
        """
        Gibt kuratierte Liste wichtiger Leitlinien für Kenntnisprüfung zurück.

        Basiert auf den häufigsten Themen in den Gold-Standard-Prüfungsprotokollen:
        - Infektiologie, Chirurgie, Diabetes, Pneumonie, Unfallchirurgie
        - Kardiologie, COPD/Asthma, Orthopädie, Neurologie, Notfallmedizin

        Args:
            specialty: Filter nach Fachgebiet
            search_term: Suchbegriff
            limit: Maximale Anzahl

        Returns:
            Liste von GuidelineMetadata
        """
        # Umfassende kuratierte Leitlinien für Kenntnisprüfung (50+ Leitlinien)
        curated = [
            # === KARDIOLOGIE (häufig in KP) ===
            GuidelineMetadata(
                title="S3-Leitlinie Herzinsuffizienz",
                source="AWMF", registry_number="nvl-006", version="2023-03",
                publication_date="2023-03-01", valid_until="2028-03-01",
                specialty="Kardiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-006.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Arterielle Hypertonie",
                source="AWMF", registry_number="046-001", version="2023-06",
                publication_date="2023-06-01", valid_until="2028-06-01",
                specialty="Kardiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/046-001.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Infarkt-bedingter kardiogener Schock",
                source="AWMF", registry_number="019-013", version="2020-03",
                publication_date="2020-03-01", valid_until="2025-03-01",
                specialty="Kardiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/019-013.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="ESC Guidelines Acute Coronary Syndromes",
                source="ESC", registry_number="ESC-ACS-2023", version="2023",
                publication_date="2023-08-01", valid_until="2028-08-01",
                specialty="Kardiologie",
                url="https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/Acute-Coronary-Syndromes",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="ESC Guidelines Atrial Fibrillation",
                source="ESC", registry_number="ESC-AF-2024", version="2024",
                publication_date="2024-01-01", valid_until="2029-01-01",
                specialty="Kardiologie",
                url="https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/Atrial-Fibrillation",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Koronare Herzkrankheit",
                source="AWMF", registry_number="nvl-004", version="2022-09",
                publication_date="2022-09-01", valid_until="2027-09-01",
                specialty="Kardiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-004.html",
                quality_score=0.95
            ),

            # === INFEKTIOLOGIE (Top-Thema) ===
            GuidelineMetadata(
                title="S3-Leitlinie Sepsis - Prävention, Diagnose, Therapie",
                source="AWMF", registry_number="079-001", version="2020-02",
                publication_date="2020-02-01", valid_until="2025-02-01",
                specialty="Intensivmedizin, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/079-001.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Ambulant erworbene Pneumonie",
                source="AWMF", registry_number="020-020", version="2021-04",
                publication_date="2021-04-01", valid_until="2026-04-01",
                specialty="Pneumologie, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/020-020.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Nosokomiale Pneumonie",
                source="AWMF", registry_number="020-013", version="2017-09",
                publication_date="2017-09-01", valid_until="2022-09-01",
                specialty="Pneumologie, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/020-013.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Bakterielle Meningitis",
                source="AWMF", registry_number="030-089", version="2015-10",
                publication_date="2015-10-01", valid_until="2020-10-01",
                specialty="Neurologie, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/030-089.html",
                quality_score=0.8
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Antibiotic Stewardship",
                source="AWMF", registry_number="092-001", version="2018-12",
                publication_date="2018-12-01", valid_until="2023-12-01",
                specialty="Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/092-001.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S3-Leitlinie HIV-Infektion",
                source="AWMF", registry_number="055-001", version="2020-06",
                publication_date="2020-06-01", valid_until="2025-06-01",
                specialty="Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/055-001.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Hepatitis B",
                source="AWMF", registry_number="021-011", version="2021-06",
                publication_date="2021-06-01", valid_until="2026-06-01",
                specialty="Gastroenterologie, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-011.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Hepatitis C",
                source="AWMF", registry_number="021-012", version="2020-05",
                publication_date="2020-05-01", valid_until="2025-05-01",
                specialty="Gastroenterologie, Infektiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-012.html",
                quality_score=0.9
            ),

            # === CHIRURGIE / UNFALLCHIRURGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Polytrauma / Schwerverletzten-Behandlung",
                source="AWMF", registry_number="187-023", version="2022-12",
                publication_date="2022-12-01", valid_until="2027-12-01",
                specialty="Unfallchirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/187-023.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Appendizitis",
                source="AWMF", registry_number="088-007", version="2020-01",
                publication_date="2020-01-01", valid_until="2025-01-01",
                specialty="Chirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/088-007.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Schenkelhalsfraktur",
                source="AWMF", registry_number="187-015", version="2020-10",
                publication_date="2020-10-01", valid_until="2025-10-01",
                specialty="Unfallchirurgie, Orthopädie",
                url="https://www.awmf.org/leitlinien/detail/ll/187-015.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S2e-Leitlinie Distale Radiusfraktur",
                source="AWMF", registry_number="012-015", version="2021-02",
                publication_date="2021-02-01", valid_until="2026-02-01",
                specialty="Unfallchirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/012-015.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Akutes Abdomen",
                source="AWMF", registry_number="088-001", version="2019-05",
                publication_date="2019-05-01", valid_until="2024-05-01",
                specialty="Chirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/088-001.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Hernien",
                source="AWMF", registry_number="010-079", version="2019-12",
                publication_date="2019-12-01", valid_until="2024-12-01",
                specialty="Chirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/010-079.html",
                quality_score=0.9
            ),

            # === INNERE MEDIZIN / DIABETES ===
            GuidelineMetadata(
                title="S3-Leitlinie Typ-2-Diabetes",
                source="AWMF", registry_number="nvl-001", version="2023-06",
                publication_date="2023-06-01", valid_until="2028-06-01",
                specialty="Innere Medizin, Diabetologie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-001.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Typ-1-Diabetes",
                source="AWMF", registry_number="057-013", version="2023-04",
                publication_date="2023-04-01", valid_until="2028-04-01",
                specialty="Innere Medizin, Diabetologie",
                url="https://www.awmf.org/leitlinien/detail/ll/057-013.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Akute und chronische Pankreatitis",
                source="AWMF", registry_number="021-003", version="2021-09",
                publication_date="2021-09-01", valid_until="2026-09-01",
                specialty="Gastroenterologie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-003.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Gastroösophageale Refluxkrankheit",
                source="AWMF", registry_number="021-013", version="2022-04",
                publication_date="2022-04-01", valid_until="2027-04-01",
                specialty="Gastroenterologie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-013.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Leberzirrhose",
                source="AWMF", registry_number="021-017", version="2019-11",
                publication_date="2019-11-01", valid_until="2024-11-01",
                specialty="Gastroenterologie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-017.html",
                quality_score=0.9
            ),

            # === PNEUMOLOGIE / COPD / ASTHMA ===
            GuidelineMetadata(
                title="S2k-Leitlinie COPD",
                source="AWMF", registry_number="020-006", version="2018-01",
                publication_date="2018-01-01", valid_until="2023-01-01",
                specialty="Pneumologie",
                url="https://www.awmf.org/leitlinien/detail/ll/020-006.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Asthma bronchiale",
                source="AWMF", registry_number="nvl-002", version="2023-03",
                publication_date="2023-03-01", valid_until="2028-03-01",
                specialty="Pneumologie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-002.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Lungenembolie",
                source="AWMF", registry_number="065-002", version="2015-06",
                publication_date="2015-06-01", valid_until="2020-06-01",
                specialty="Pneumologie, Kardiologie",
                url="https://www.awmf.org/leitlinien/detail/ll/065-002.html",
                quality_score=0.85
            ),

            # === NEUROLOGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Schlaganfall",
                source="AWMF", registry_number="030-140", version="2021-05",
                publication_date="2021-05-01", valid_until="2026-05-01",
                specialty="Neurologie",
                url="https://www.awmf.org/leitlinien/detail/ll/030-140.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S1-Leitlinie Epilepsie",
                source="AWMF", registry_number="030-041", version="2023-05",
                publication_date="2023-05-01", valid_until="2028-05-01",
                specialty="Neurologie",
                url="https://www.awmf.org/leitlinien/detail/ll/030-041.html",
                quality_score=0.8
            ),
            GuidelineMetadata(
                title="S1-Leitlinie Kopfschmerzen",
                source="AWMF", registry_number="030-057", version="2022-01",
                publication_date="2022-01-01", valid_until="2027-01-01",
                specialty="Neurologie",
                url="https://www.awmf.org/leitlinien/detail/ll/030-057.html",
                quality_score=0.8
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Schädel-Hirn-Trauma",
                source="AWMF", registry_number="024-018", version="2015-12",
                publication_date="2015-12-01", valid_until="2020-12-01",
                specialty="Neurologie, Unfallchirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/024-018.html",
                quality_score=0.85
            ),

            # === UROLOGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Prostatakarzinom",
                source="AWMF", registry_number="043-022", version="2021-10",
                publication_date="2021-10-01", valid_until="2026-10-01",
                specialty="Urologie",
                url="https://www.awmf.org/leitlinien/detail/ll/043-022.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Harnwegsinfektionen",
                source="AWMF", registry_number="043-044", version="2017-04",
                publication_date="2017-04-01", valid_until="2022-04-01",
                specialty="Urologie",
                url="https://www.awmf.org/leitlinien/detail/ll/043-044.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Urolithiasis",
                source="AWMF", registry_number="043-025", version="2019-02",
                publication_date="2019-02-01", valid_until="2024-02-01",
                specialty="Urologie",
                url="https://www.awmf.org/leitlinien/detail/ll/043-025.html",
                quality_score=0.85
            ),

            # === ORTHOPÄDIE ===
            GuidelineMetadata(
                title="S2k-Leitlinie Gonarthrose",
                source="AWMF", registry_number="187-050", version="2018-01",
                publication_date="2018-01-01", valid_until="2023-01-01",
                specialty="Orthopädie",
                url="https://www.awmf.org/leitlinien/detail/ll/187-050.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Coxarthrose",
                source="AWMF", registry_number="187-049", version="2019-07",
                publication_date="2019-07-01", valid_until="2024-07-01",
                specialty="Orthopädie",
                url="https://www.awmf.org/leitlinien/detail/ll/187-049.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Spezifischer Kreuzschmerz",
                source="AWMF", registry_number="nvl-007", version="2017-11",
                publication_date="2017-11-01", valid_until="2022-11-01",
                specialty="Orthopädie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-007.html",
                quality_score=0.85
            ),

            # === ONKOLOGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Kolorektales Karzinom",
                source="AWMF", registry_number="021-007", version="2019-01",
                publication_date="2019-01-01", valid_until="2024-01-01",
                specialty="Onkologie, Chirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/021-007.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Lungenkarzinom",
                source="AWMF", registry_number="020-007", version="2018-02",
                publication_date="2018-02-01", valid_until="2023-02-01",
                specialty="Onkologie, Pneumologie",
                url="https://www.awmf.org/leitlinien/detail/ll/020-007.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Mammakarzinom",
                source="AWMF", registry_number="032-045", version="2021-06",
                publication_date="2021-06-01", valid_until="2026-06-01",
                specialty="Onkologie, Gynäkologie",
                url="https://www.awmf.org/leitlinien/detail/ll/032-045.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Magenkarzinom",
                source="AWMF", registry_number="032-009", version="2019-08",
                publication_date="2019-08-01", valid_until="2024-08-01",
                specialty="Onkologie, Chirurgie",
                url="https://www.awmf.org/leitlinien/detail/ll/032-009.html",
                quality_score=0.9
            ),

            # === NOTFALLMEDIZIN / REANIMATION ===
            GuidelineMetadata(
                title="S3-Leitlinie Reanimation",
                source="AWMF", registry_number="001-006", version="2021-03",
                publication_date="2021-03-01", valid_until="2026-03-01",
                specialty="Notfallmedizin",
                url="https://www.awmf.org/leitlinien/detail/ll/001-006.html",
                quality_score=0.95
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Analgesie und Sedierung in der Notfallmedizin",
                source="AWMF", registry_number="001-039", version="2019-02",
                publication_date="2019-02-01", valid_until="2024-02-01",
                specialty="Notfallmedizin",
                url="https://www.awmf.org/leitlinien/detail/ll/001-039.html",
                quality_score=0.85
            ),
            GuidelineMetadata(
                title="S3-Leitlinie Anaphylaxie",
                source="AWMF", registry_number="061-025", version="2021-12",
                publication_date="2021-12-01", valid_until="2026-12-01",
                specialty="Notfallmedizin, Allergologie",
                url="https://www.awmf.org/leitlinien/detail/ll/061-025.html",
                quality_score=0.9
            ),

            # === RADIOLOGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Kontrastmittel",
                source="DRG", registry_number="DRG-KM-2018", version="2018-05",
                publication_date="2018-05-01", valid_until="2023-05-01",
                specialty="Radiologie",
                url="https://www.drg.de/de-DE/Publikationen/Leitlinien",
                quality_score=0.85
            ),

            # === NEPHROLOGIE ===
            GuidelineMetadata(
                title="S3-Leitlinie Chronische Nierenerkrankung",
                source="AWMF", registry_number="053-015", version="2019-09",
                publication_date="2019-09-01", valid_until="2024-09-01",
                specialty="Nephrologie",
                url="https://www.awmf.org/leitlinien/detail/ll/053-015.html",
                quality_score=0.9
            ),
            GuidelineMetadata(
                title="S2k-Leitlinie Akutes Nierenversagen",
                source="AWMF", registry_number="053-012", version="2019-08",
                publication_date="2019-08-01", valid_until="2024-08-01",
                specialty="Nephrologie",
                url="https://www.awmf.org/leitlinien/detail/ll/053-012.html",
                quality_score=0.85
            ),

            # === PSYCHIATRIE (falls relevant) ===
            GuidelineMetadata(
                title="S3-Leitlinie Depression",
                source="AWMF", registry_number="nvl-005", version="2022-09",
                publication_date="2022-09-01", valid_until="2027-09-01",
                specialty="Psychiatrie",
                url="https://www.awmf.org/leitlinien/detail/ll/nvl-005.html",
                quality_score=0.9
            ),
        ]

        # Filter anwenden
        if specialty:
            curated = [g for g in curated if specialty.lower() in g.specialty.lower()]
        if search_term:
            term_lower = search_term.lower()
            curated = [g for g in curated if term_lower in g.title.lower() or term_lower in g.specialty.lower()]

        return curated[:limit]

    def search_guidelines(
        self,
        specialty: Optional[str] = None,
        search_term: Optional[str] = None,
        sources: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[GuidelineMetadata]:
        """
        Sucht nach Leitlinien.

        Args:
            specialty: Fachgebiet
            search_term: Suchbegriff
            sources: Zu durchsuchende Quellen
            limit: Maximum

        Returns:
            Liste von GuidelineMetadata
        """
        # Für MVP: Kuratierte Liste verwenden
        # In Produktion: Echte Web-Scraping-Implementierung
        return self.get_curated_guidelines(specialty, search_term, limit)

    def download_guideline(
        self,
        guideline: GuidelineMetadata,
        force: bool = False
    ) -> Optional[Path]:
        """
        Lädt eine Leitlinie herunter.

        Args:
            guideline: Leitlinien-Metadaten
            force: Download erzwingen

        Returns:
            Pfad zur heruntergeladenen Datei oder None
        """
        if guideline.local_path and not force:
            local = Path(guideline.local_path)
            if local.exists():
                logger.info(f"Bereits heruntergeladen: {local}")
                return local

        try:
            # Dateiname erstellen
            safe_title = re.sub(r"[^\w\s-]", "", guideline.title)[:80]
            safe_title = re.sub(r"\s+", "_", safe_title)
            filename = f"{guideline.source}_{guideline.registry_number or 'unknown'}_{safe_title}.pdf"

            output_path = self.download_dir / guideline.source / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Lade herunter: {guideline.title}")

            # Download mit Retry
            for attempt in range(3):
                try:
                    response = self.session.get(
                        guideline.url,
                        timeout=60,
                        stream=True
                    )
                    response.raise_for_status()

                    with open(output_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # Metadaten aktualisieren
                    guideline.local_path = str(output_path)
                    guideline.downloaded_at = datetime.now().isoformat()
                    guideline.file_size_bytes = output_path.stat().st_size

                    # Cache aktualisieren
                    cache_key = f"{guideline.source}_{guideline.registry_number}"
                    self.cache[cache_key] = guideline
                    self._save_cache()

                    logger.info(f"Download erfolgreich: {output_path}")
                    return output_path

                except requests.RequestException as e:
                    logger.warning(f"Versuch {attempt + 1} fehlgeschlagen: {e}")
                    if attempt < 2:
                        time.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Download fehlgeschlagen: {e}")

        return None

    def batch_download(
        self,
        guidelines: List[GuidelineMetadata],
        progress_callback: Optional[Callable] = None,
        parallel: bool = True
    ) -> List[Tuple[GuidelineMetadata, Optional[Path]]]:
        """
        Lädt mehrere Leitlinien herunter.

        Args:
            guidelines: Liste von Leitlinien
            progress_callback: Callback(current, total)
            parallel: Parallel herunterladen

        Returns:
            Liste von (guideline, path) Tupeln
        """
        results = []

        if parallel and len(guidelines) > 1:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                futures = {
                    executor.submit(self.download_guideline, g): g
                    for g in guidelines
                }

                completed = 0
                for future in as_completed(futures):
                    guideline = futures[future]
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, len(guidelines))

                    try:
                        path = future.result()
                        results.append((guideline, path))
                    except Exception as e:
                        logger.error(f"Download-Fehler: {e}")
                        results.append((guideline, None))
        else:
            for i, guideline in enumerate(guidelines):
                if progress_callback:
                    progress_callback(i + 1, len(guidelines))
                path = self.download_guideline(guideline)
                results.append((guideline, path))
                time.sleep(1)  # Rate limiting

        successful = sum(1 for _, p in results if p)
        logger.info(f"Batch-Download: {successful}/{len(guidelines)} erfolgreich")

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        by_source = defaultdict(int)
        by_specialty = defaultdict(int)

        for g in self.cache.values():
            by_source[g.source] += 1
            by_specialty[g.specialty] += 1

        return {
            "total_cached": len(self.cache),
            "by_source": dict(by_source),
            "by_specialty": dict(by_specialty),
        }


def fetch_guidelines_for_text(
    text: str,
    download_dir: str = "_BIBLIOTHEK/Leitlinien",
    download: bool = False,
    min_relevance: float = 0.3
) -> Dict[str, Any]:
    """
    Hauptfunktion: Erkennt Themen aus Text und holt relevante Leitlinien.

    Args:
        text: Medizinischer Text
        download_dir: Download-Verzeichnis
        download: Tatsächlich herunterladen
        min_relevance: Minimum Relevanz-Score

    Returns:
        Dictionary mit Themen, Gesellschaften und Leitlinien
    """
    start_time = time.time()

    logger.info("=== INTELLIGENTE LEITLINIEN-SUCHE ===")

    # 1. Themen erkennen
    themes = detect_medical_themes(text, top_n=10)
    if not themes:
        return {
            "detected_themes": [],
            "relevant_societies": {},
            "guidelines": [],
            "stats": {"processing_time": time.time() - start_time}
        }

    # 2. Fachgesellschaften mappen
    societies = map_themes_to_societies(themes)
    relevant = {s: score for s, score in societies.items() if score >= min_relevance}

    # 3. Leitlinien suchen
    fetcher = GuidelineFetcher(download_dir)
    all_guidelines = []

    for theme, _ in themes[:3]:
        guidelines = fetcher.search_guidelines(search_term=theme, limit=5)
        for g in guidelines:
            g.detected_themes = [t[0] for t in themes[:5]]
        all_guidelines.extend(guidelines)

    # 4. Optional herunterladen
    download_results = []
    if download and all_guidelines:
        download_results = fetcher.batch_download(all_guidelines)

    return {
        "detected_themes": themes,
        "relevant_societies": relevant,
        "guidelines": [g.to_dict() for g in all_guidelines],
        "download_results": [(g.title, str(p) if p else None) for g, p in download_results],
        "stats": {
            "processing_time": round(time.time() - start_time, 2),
            "themes_detected": len(themes),
            "societies_identified": len(relevant),
            "guidelines_found": len(all_guidelines),
        }
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test
    test_text = """
    Der Patient zeigt Symptome einer akuten Pankreatitis mit
    gürtelförmigen Oberbauchschmerzen und erhöhter Lipase.
    Differentialdiagnostisch ist auch an einen Myokardinfarkt zu denken.
    """

    result = fetch_guidelines_for_text(test_text, download=False)

    print("\n=== Erkannte Themen ===")
    for theme, score in result["detected_themes"]:
        print(f"  {theme}: {score:.2f}")

    print("\n=== Relevante Gesellschaften ===")
    for soc, score in result["relevant_societies"].items():
        print(f"  {soc}: {score:.2f}")

    print("\n=== Gefundene Leitlinien ===")
    for g in result["guidelines"][:5]:
        print(f"  {g['title']}")
