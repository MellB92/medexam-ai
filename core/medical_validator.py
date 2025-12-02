#!/usr/bin/env python3
"""
MedExamAI Medical Validation Layer
==================================

Lokaler Pre-Validator für medizinische Extraktionen.
Prüft OHNE LLM-Calls:
- Dosierungen gegen bekannte Ranges
- ICD-10 Code Syntax und Existenz
- Laborwerte gegen Referenzbereiche
- Logische Inkonsistenzen
- Confidence Score Berechnung

Architektur:
    Extraktion -> MedicalValidationLayer -> [VALID] -> Pipeline
                        |
                        v
                   [INVALID/SUSPICIOUS] -> Quarantäne + Review

Autor: MedExamAI Team
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Schweregrad einer Validierungsmeldung."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Einzelnes Validierungsproblem."""
    code: str
    message: str
    severity: ValidationSeverity
    field: Optional[str] = None
    value: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "value": self.value,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationResult:
    """Ergebnis einer Validierung."""
    is_valid: bool
    confidence_score: float  # 0.0 - 1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)

    @property
    def has_errors(self) -> bool:
        return any(
            i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for i in self.issues
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "confidence_score": self.confidence_score,
            "has_critical_issues": self.has_critical_issues,
            "has_errors": self.has_errors,
            "has_warnings": len(self.warnings) > 0,
            "issues": [i.to_dict() for i in self.issues],
            "warnings": [w.to_dict() for w in self.warnings],
            "metadata": self.metadata
        }


# Eingebaute Referenzdaten für häufige Medikamente
DOSAGE_REFERENCE = {
    "Metformin": {"unit": "mg", "min_dose": 500, "max_dose": 1000, "max_daily": 3000, "fatal_above": 10000},
    "Ramipril": {"unit": "mg", "min_dose": 1.25, "max_dose": 10, "max_daily": 10, "fatal_above": 50},
    "Metoprolol": {"unit": "mg", "min_dose": 25, "max_dose": 200, "max_daily": 400, "fatal_above": 1000},
    "Amiodaron": {"unit": "mg", "min_dose": 100, "max_dose": 400, "max_daily": 800, "fatal_above": 2000},
    "Methylphenidat": {"unit": "mg", "min_dose": 5, "max_dose": 60, "max_daily": 80, "fatal_above": 200},
    "Ibuprofen": {"unit": "mg", "min_dose": 200, "max_dose": 800, "max_daily": 2400, "fatal_above": 10000},
    "Paracetamol": {"unit": "mg", "min_dose": 500, "max_dose": 1000, "max_daily": 4000, "fatal_above": 15000},
    "Prednisolon": {"unit": "mg", "min_dose": 5, "max_dose": 100, "max_daily": 250, "fatal_above": 1000},
    "Aspirin": {"unit": "mg", "min_dose": 75, "max_dose": 500, "max_daily": 3000, "fatal_above": 20000},
    "Heparin": {"unit": "IE", "min_dose": 5000, "max_dose": 35000, "max_daily": 35000, "fatal_above": 100000},
    "Insulin": {"unit": "IE", "min_dose": 2, "max_dose": 100, "max_daily": 200, "fatal_above": 500},
    "Morphin": {"unit": "mg", "min_dose": 5, "max_dose": 30, "max_daily": 200, "fatal_above": 500},
}

# Laborwert-Referenzbereiche
LAB_REFERENCE = {
    "Kalium": {"unit": "mmol/l", "normal_min": 3.5, "normal_max": 5.0, "critical_low": 2.5, "critical_high": 6.5},
    "Natrium": {"unit": "mmol/l", "normal_min": 135, "normal_max": 145, "critical_low": 120, "critical_high": 160},
    "Kreatinin": {"unit": "mg/dl", "normal_min": 0.7, "normal_max": 1.3, "critical_high": 10.0},
    "Hämoglobin": {"unit": "g/dl", "normal_min": 12.0, "normal_max": 17.0, "critical_low": 6.0},
    "Leukozyten": {"unit": "/µl", "normal_min": 4000, "normal_max": 11000, "critical_low": 1000, "critical_high": 50000},
    "Thrombozyten": {"unit": "/µl", "normal_min": 150000, "normal_max": 400000, "critical_low": 20000},
    "Glukose": {"unit": "mg/dl", "normal_min": 70, "normal_max": 100, "critical_low": 40, "critical_high": 500},
    "HbA1c": {"unit": "%", "normal_min": 4.0, "normal_max": 6.0, "critical_high": 15.0},
    "Troponin": {"unit": "ng/ml", "normal_max": 0.04, "critical_high": 10.0},
    "CRP": {"unit": "mg/l", "normal_max": 5.0, "critical_high": 200.0},
    "Lipase": {"unit": "U/l", "normal_max": 60, "critical_high": 1000},
    "TSH": {"unit": "mU/l", "normal_min": 0.4, "normal_max": 4.0, "critical_low": 0.01, "critical_high": 100},
}

# ICD-10 Geschlechtsspezifische Codes
ICD10_GENDER = {
    "male_only": ["C61", "N40", "N41", "N42", "N43", "N44", "N45", "N46", "N47", "N48", "N49", "N50"],
    "female_only": ["C50", "C51", "C52", "C53", "C54", "C55", "C56", "C57", "C58",
                    "N70", "N71", "N72", "N73", "N74", "N75", "N76", "N77",
                    "O00", "O01", "O02", "O03", "O04", "O05", "O06", "O07", "O08",
                    "O10", "O11", "O12", "O13", "O14", "O15", "O16"]
}

# Kontraindikationen
CONTRAINDICATIONS = [
    {"medication": ["Methotrexat", "MTX"], "contraindicated_with": ["Schwanger", "schwanger", "Gravidität"], "severity": "critical"},
    {"medication": ["ACE-Hemmer", "Ramipril", "Enalapril"], "contraindicated_with": ["Schwanger", "schwanger"], "severity": "critical"},
    {"medication": ["Metformin"], "contraindicated_with": ["Niereninsuffizienz", "GFR < 30"], "severity": "high"},
    {"medication": ["Aspirin", "ASS"], "contraindicated_with": ["Magen-Ulkus", "GI-Blutung"], "severity": "warning"},
    {"medication": ["Betablocker"], "contraindicated_with": ["Asthma bronchiale"], "severity": "warning"},
]


class DosageValidator:
    """Validiert Medikamentendosierungen."""

    DOSAGE_PATTERNS = [
        r"(?P<med>\b[A-Za-zäöüÄÖÜß]+(?:\s+[A-Za-zäöüÄÖÜß]+)?)\s+(?P<dose>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|µg|g|ml|l|IE|IU|mmol)",
        r"(?P<dose>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|µg|g|ml|l|IE|IU|mmol)\s+(?P<med>\b[A-Za-zäöüÄÖÜß]+)",
    ]

    # Applikationsrouten und kurze Wörter, die keine Medikamente sind
    ROUTE_ABBREVIATIONS = {
        "i", "v", "p", "o", "s", "c", "iv", "po", "sc", "im",
        "oral", "rektal", "nasal", "lokal", "sublingual",
        "einmalig", "täglich", "stündlich", "morgens", "abends",
        "vor", "nach", "bei", "zu", "mit", "alle", "pro"
    }

    # Mindestlänge für Medikamentennamen
    MIN_MED_NAME_LENGTH = 3

    def __init__(self, reference_data: Optional[Dict] = None):
        self.reference = reference_data or DOSAGE_REFERENCE
        self.aliases = self._build_aliases()

    def _build_aliases(self) -> Dict[str, str]:
        """Erstellt Alias-Mapping."""
        aliases = {}
        for med in self.reference.keys():
            aliases[med.lower()] = med
        return aliases

    def extract_dosages(self, text: str) -> List[Dict[str, Any]]:
        """Extrahiert Dosierungsangaben aus Text."""
        extractions = []
        for pattern in self.DOSAGE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groupdict()
                try:
                    med_name = groups["med"].strip()

                    # Filter: Mindestlänge für Medikamentennamen
                    if len(med_name) < self.MIN_MED_NAME_LENGTH:
                        continue

                    # Filter: Applikationsrouten und häufige Nicht-Medikamente
                    if med_name.lower() in self.ROUTE_ABBREVIATIONS:
                        continue

                    dose = float(groups["dose"].replace(",", "."))
                    extractions.append({
                        "medication": med_name,
                        "dose": dose,
                        "unit": groups["unit"].lower(),
                        "original": match.group(0)
                    })
                except (ValueError, KeyError):
                    continue
        return extractions

    def validate(self, text: str) -> Tuple[List[Dict], List[ValidationIssue]]:
        """Validiert alle Dosierungen im Text."""
        extractions = self.extract_dosages(text)
        issues = []

        for ext in extractions:
            med_lower = ext["medication"].lower()
            ref_med = self.aliases.get(med_lower)

            if not ref_med:
                issues.append(ValidationIssue(
                    code="DOSAGE_UNKNOWN_MED",
                    message=f"Medikament '{ext['medication']}' nicht in Referenzdatenbank",
                    severity=ValidationSeverity.INFO,
                    field="medication",
                    value=ext["medication"]
                ))
                continue

            ref = self.reference[ref_med]
            dose = ext["dose"]

            # Fatal Check
            if ref.get("fatal_above") and dose > ref["fatal_above"]:
                issues.append(ValidationIssue(
                    code="DOSAGE_FATAL",
                    message=f"KRITISCH: {ext['medication']} {dose}{ext['unit']} überschreitet potenziell tödliche Dosis ({ref['fatal_above']}{ref['unit']})",
                    severity=ValidationSeverity.CRITICAL,
                    field="dosage",
                    value=f"{dose}{ext['unit']}",
                    suggestion=f"Maximale Einzeldosis: {ref['max_dose']}{ref['unit']}"
                ))
                continue

            # Überdosierung
            if ref.get("max_dose") and dose > ref["max_dose"]:
                max_daily = ref.get("max_daily", ref["max_dose"])
                if dose <= max_daily:
                    issues.append(ValidationIssue(
                        code="DOSAGE_HIGH",
                        message=f"{ext['medication']} {dose}{ext['unit']} überschreitet Einzeldosis-Maximum ({ref['max_dose']}{ref['unit']})",
                        severity=ValidationSeverity.WARNING,
                        field="dosage",
                        value=f"{dose}{ext['unit']}"
                    ))
                else:
                    issues.append(ValidationIssue(
                        code="DOSAGE_OVERDOSE",
                        message=f"{ext['medication']} {dose}{ext['unit']} überschreitet Tagesmaximum ({max_daily}{ref['unit']})",
                        severity=ValidationSeverity.ERROR,
                        field="dosage",
                        value=f"{dose}{ext['unit']}"
                    ))

            # Unterdosierung
            if ref.get("min_dose") and dose < ref["min_dose"]:
                issues.append(ValidationIssue(
                    code="DOSAGE_LOW",
                    message=f"{ext['medication']} {dose}{ext['unit']} unter Mindestdosis ({ref['min_dose']}{ref['unit']})",
                    severity=ValidationSeverity.WARNING,
                    field="dosage",
                    value=f"{dose}{ext['unit']}"
                ))

        return extractions, issues


class ICD10Validator:
    """Validiert ICD-10 Codes."""

    ICD10_PATTERN = re.compile(r"\b([A-Z]\d{2})(?:\.(\d{1,2}))?\b")

    def __init__(self):
        self.male_only = set(ICD10_GENDER["male_only"])
        self.female_only = set(ICD10_GENDER["female_only"])

    def extract_codes(self, text: str) -> List[str]:
        """Extrahiert ICD-10 Codes aus Text."""
        codes = []
        for match in self.ICD10_PATTERN.finditer(text):
            main = match.group(1)
            sub = match.group(2)
            codes.append(f"{main}.{sub}" if sub else main)
        return codes

    def validate(self, text: str, patient_gender: Optional[str] = None) -> Tuple[List[str], List[ValidationIssue]]:
        """Validiert alle ICD-10 Codes im Text."""
        codes = self.extract_codes(text)
        issues = []

        for code in codes:
            main = code.split(".")[0]

            # Syntax-Check
            if not self.ICD10_PATTERN.match(code):
                issues.append(ValidationIssue(
                    code="ICD10_INVALID_SYNTAX",
                    message=f"Ungültige ICD-10 Syntax: {code}",
                    severity=ValidationSeverity.ERROR,
                    field="icd10",
                    value=code
                ))
                continue

            # Geschlechts-Check
            if patient_gender:
                if patient_gender.lower() == "male" and main in self.female_only:
                    issues.append(ValidationIssue(
                        code="ICD10_GENDER_MISMATCH",
                        message=f"ICD-10 {code} ist nur für weibliche Patienten gültig",
                        severity=ValidationSeverity.ERROR,
                        field="icd10",
                        value=code
                    ))
                elif patient_gender.lower() == "female" and main in self.male_only:
                    issues.append(ValidationIssue(
                        code="ICD10_GENDER_MISMATCH",
                        message=f"ICD-10 {code} ist nur für männliche Patienten gültig",
                        severity=ValidationSeverity.ERROR,
                        field="icd10",
                        value=code
                    ))

        return codes, issues


class LabValueValidator:
    """Validiert Laborwerte."""

    LAB_PATTERNS = [
        r"(?P<name>[A-Za-zäöüÄÖÜß]+(?:[-\s][A-Za-zäöüÄÖÜß]+)?)\s*[:\s]\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Zµ/%²]+(?:/[a-zA-Zµ]+)?)",
        r"(?P<name>HbA1c|CRP|TSH|INR)\s*[:\s]?\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>%|mg/l|mU/l)?",
    ]

    def __init__(self, reference_data: Optional[Dict] = None):
        self.reference = reference_data or LAB_REFERENCE
        self.aliases = self._build_aliases()

    def _build_aliases(self) -> Dict[str, str]:
        aliases = {}
        for lab in self.reference.keys():
            aliases[lab.lower()] = lab
        return aliases

    def validate(self, text: str, patient_gender: Optional[str] = None) -> List[ValidationIssue]:
        """Validiert Laborwerte im Text."""
        issues = []

        for pattern in self.LAB_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    name = match.group("name").strip()
                    value = float(match.group("value").replace(",", "."))
                    unit = match.group("unit") or ""

                    ref_name = self.aliases.get(name.lower())
                    if not ref_name:
                        continue

                    ref = self.reference[ref_name]

                    # Kritische Werte
                    if ref.get("critical_low") and value < ref["critical_low"]:
                        issues.append(ValidationIssue(
                            code="LAB_CRITICAL_LOW",
                            message=f"KRITISCH: {name} = {value} unter kritischem Grenzwert ({ref['critical_low']})",
                            severity=ValidationSeverity.CRITICAL,
                            field="lab_value",
                            value=f"{value} {unit}"
                        ))
                    elif ref.get("critical_high") and value > ref["critical_high"]:
                        issues.append(ValidationIssue(
                            code="LAB_CRITICAL_HIGH",
                            message=f"KRITISCH: {name} = {value} über kritischem Grenzwert ({ref['critical_high']})",
                            severity=ValidationSeverity.CRITICAL,
                            field="lab_value",
                            value=f"{value} {unit}"
                        ))
                    # Pathologisch
                    elif ref.get("normal_min") and value < ref["normal_min"]:
                        issues.append(ValidationIssue(
                            code="LAB_BELOW_NORMAL",
                            message=f"{name} = {value} unter Normalbereich ({ref['normal_min']}-{ref.get('normal_max', '?')})",
                            severity=ValidationSeverity.INFO,
                            field="lab_value",
                            value=f"{value} {unit}"
                        ))
                    elif ref.get("normal_max") and value > ref["normal_max"]:
                        issues.append(ValidationIssue(
                            code="LAB_ABOVE_NORMAL",
                            message=f"{name} = {value} über Normalbereich ({ref.get('normal_min', '?')}-{ref['normal_max']})",
                            severity=ValidationSeverity.INFO,
                            field="lab_value",
                            value=f"{value} {unit}"
                        ))

                except (ValueError, IndexError):
                    continue

        return issues


class LogicalConsistencyChecker:
    """Prüft logische Konsistenz."""

    def __init__(self, contraindications: Optional[List[Dict]] = None):
        self.contraindications = contraindications or CONTRAINDICATIONS

    def check_contraindications(self, text: str) -> List[ValidationIssue]:
        """Prüft auf Kontraindikationen."""
        issues = []
        text_lower = text.lower()

        for rule in self.contraindications:
            med_found = any(med.lower() in text_lower for med in rule["medication"])
            contra_found = any(contra.lower() in text_lower for contra in rule["contraindicated_with"])

            if med_found and contra_found:
                severity_map = {
                    "critical": ValidationSeverity.CRITICAL,
                    "high": ValidationSeverity.ERROR,
                    "warning": ValidationSeverity.WARNING
                }
                severity = severity_map.get(rule["severity"], ValidationSeverity.WARNING)

                issues.append(ValidationIssue(
                    code="LOGIC_CONTRAINDICATION",
                    message=f"Kontraindikation: {rule['medication']} bei {rule['contraindicated_with']}",
                    severity=severity,
                    field="contraindication"
                ))

        return issues

    def check_gender_consistency(self, text: str, patient_gender: Optional[str]) -> List[ValidationIssue]:
        """Prüft Geschlechts-Konsistenz."""
        issues = []
        text_lower = text.lower()

        female_keywords = ["schwanger", "gravidität", "menstruation", "uterus", "ovar"]
        male_keywords = ["prostata", "hoden", "skrotum"]

        if patient_gender:
            if patient_gender.lower() == "male":
                for kw in female_keywords:
                    if kw in text_lower:
                        issues.append(ValidationIssue(
                            code="LOGIC_GENDER_INCONSISTENT",
                            message=f"Geschlechts-Inkonsistenz: '{kw}' bei männlichem Patient",
                            severity=ValidationSeverity.ERROR,
                            field="gender",
                            value=patient_gender
                        ))
            elif patient_gender.lower() == "female":
                for kw in male_keywords:
                    if kw in text_lower:
                        issues.append(ValidationIssue(
                            code="LOGIC_GENDER_INCONSISTENT",
                            message=f"Geschlechts-Inkonsistenz: '{kw}' bei weiblicher Patientin",
                            severity=ValidationSeverity.ERROR,
                            field="gender",
                            value=patient_gender
                        ))

        return issues


class MedicalValidationLayer:
    """
    Haupt-Validierungsschicht für medizinische Inhalte.

    Kombiniert:
    - DosageValidator
    - ICD10Validator
    - LabValueValidator
    - LogicalConsistencyChecker
    """

    def __init__(self):
        self.dosage_validator = DosageValidator()
        self.icd10_validator = ICD10Validator()
        self.lab_validator = LabValueValidator()
        self.logic_checker = LogicalConsistencyChecker()

        # Statistiken
        self.stats = {
            "total_validated": 0,
            "valid": 0,
            "invalid": 0,
            "quarantined": 0,
            "critical_issues": 0
        }

        logger.info("MedicalValidationLayer initialisiert")

    def validate(
        self,
        text: str,
        patient_gender: Optional[str] = None,
        patient_age: Optional[int] = None,
        source_file: Optional[str] = None
    ) -> ValidationResult:
        """
        Führt vollständige Validierung durch.

        Args:
            text: Zu validierender Text
            patient_gender: "male" oder "female"
            patient_age: Alter
            source_file: Quelldatei

        Returns:
            ValidationResult
        """
        self.stats["total_validated"] += 1

        all_issues: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        metadata = {
            "source_file": source_file,
            "patient_gender": patient_gender,
            "patient_age": patient_age,
            "text_length": len(text)
        }

        # 1. Dosierungsvalidierung
        dosages, dosage_issues = self.dosage_validator.validate(text)
        metadata["dosages_found"] = len(dosages)
        for issue in dosage_issues:
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                all_issues.append(issue)
            else:
                warnings.append(issue)

        # 2. ICD-10 Validierung
        codes, icd_issues = self.icd10_validator.validate(text, patient_gender)
        metadata["icd_codes_found"] = len(codes)
        for issue in icd_issues:
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                all_issues.append(issue)
            else:
                warnings.append(issue)

        # 3. Laborwert-Validierung
        lab_issues = self.lab_validator.validate(text, patient_gender)
        for issue in lab_issues:
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                all_issues.append(issue)
            else:
                warnings.append(issue)

        # 4. Logische Konsistenz
        contra_issues = self.logic_checker.check_contraindications(text)
        gender_issues = self.logic_checker.check_gender_consistency(text, patient_gender)
        for issue in contra_issues + gender_issues:
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                all_issues.append(issue)
            else:
                warnings.append(issue)

        # Confidence Score berechnen
        confidence = self._calculate_confidence(
            dosage_issues, icd_issues, lab_issues, contra_issues + gender_issues,
            has_dosages=len(dosages) > 0,
            has_icd_codes=len(codes) > 0
        )

        # Validität bestimmen
        has_critical = any(i.severity == ValidationSeverity.CRITICAL for i in all_issues)
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in all_issues)
        is_valid = not has_critical and not has_errors

        # Statistiken aktualisieren
        if has_critical:
            self.stats["critical_issues"] += 1
            self.stats["quarantined"] += 1
        elif is_valid:
            self.stats["valid"] += 1
        else:
            self.stats["invalid"] += 1

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            issues=all_issues,
            warnings=warnings,
            metadata=metadata
        )

    def _calculate_confidence(
        self,
        dosage_issues: List[ValidationIssue],
        icd_issues: List[ValidationIssue],
        lab_issues: List[ValidationIssue],
        logic_issues: List[ValidationIssue],
        has_dosages: bool,
        has_icd_codes: bool
    ) -> float:
        """Berechnet Confidence Score."""
        score = 0.2  # Basis

        def count_errors(issues):
            return sum(1 for i in issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL))

        # Dosierung (0.3)
        dosage_errors = count_errors(dosage_issues)
        if has_dosages:
            score += 0.3 if dosage_errors == 0 else (0.15 if dosage_errors == 1 else 0)
        else:
            score += 0.15

        # ICD-10 (0.2)
        icd_errors = count_errors(icd_issues)
        if has_icd_codes:
            score += 0.2 if icd_errors == 0 else (0.1 if icd_errors == 1 else 0)
        else:
            score += 0.1

        # Logik (0.3)
        logic_errors = count_errors(logic_issues)
        score += 0.3 if logic_errors == 0 else (0.15 if logic_errors == 1 else 0)

        return round(min(1.0, max(0.0, score)), 2)

    def validate_qa_pair(
        self,
        question: str,
        answer: str,
        patient_gender: Optional[str] = None,
        patient_age: Optional[int] = None,
        source_file: Optional[str] = None
    ) -> ValidationResult:
        """Validiert ein Q&A-Paar."""
        combined = f"{question}\n\n{answer}"
        return self.validate(combined, patient_gender, patient_age, source_file)

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        total = self.stats["total_validated"]
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "valid_rate": round(self.stats["valid"] / total * 100, 1),
            "invalid_rate": round(self.stats["invalid"] / total * 100, 1),
            "quarantine_rate": round(self.stats["quarantined"] / total * 100, 1)
        }


class HallucinationDetector:
    """
    Erkennt mögliche Halluzinationen in LLM-generierten Antworten.

    Strategien:
    1. RAG-Quellenabdeckung: Prüft ob Aussagen durch RAG-Kontext belegt sind
    2. Fakten-Plausibilität: Erkennt unplausible medizinische Fakten
    3. Zahlen-Konsistenz: Prüft ob Zahlen in plausiblen Bereichen liegen
    4. Placeholder-Erkennung: Findet nicht-ersetzte Platzhalter
    """

    # Typische Halluzinations-Marker
    HALLUCINATION_PATTERNS = [
        # Platzhalter die nicht ersetzt wurden
        r'\[(?:PLACEHOLDER|EINFÜGEN|TODO|XXX|TBD)\]',
        r'\{(?:medication|dosage|value|name|date)\}',
        r'<(?:MEDICATION|DOSIERUNG|WERT)>',
        # Vage/unsichere Formulierungen als Halluzinationsmarker
        r'(?:möglicherweise|vielleicht|eventuell|könnte sein)\s+(?:dass|wenn)',
        # Erfundene Referenzen
        r'(?:laut|nach|gemäß)\s+(?:Dr\.\s+)?[A-Z][a-z]+(?:\s+et\s+al\.?)?\s*\(\d{4}\)',
    ]

    # Unplausible medizinische Fakten
    IMPLAUSIBLE_FACTS = [
        # Lebenszeichen außerhalb menschlicher Grenzen
        {"pattern": r"Herzfrequenz[:\s]+(\d+)", "min": 20, "max": 300, "name": "Herzfrequenz"},
        {"pattern": r"Blutdruck[:\s]+(\d+)/(\d+)", "systolic_min": 40, "systolic_max": 300, "name": "Blutdruck"},
        {"pattern": r"Temperatur[:\s]+(\d+(?:[.,]\d+)?)\s*°?C", "min": 25, "max": 45, "name": "Temperatur"},
        {"pattern": r"Atemfrequenz[:\s]+(\d+)", "min": 4, "max": 60, "name": "Atemfrequenz"},
        {"pattern": r"SpO2[:\s]+(\d+)\s*%", "min": 50, "max": 100, "name": "SpO2"},
        # Altersgrenzen
        {"pattern": r"(?:Alter|Jahre alt)[:\s]+(\d+)", "min": 0, "max": 130, "name": "Alter"},
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.HALLUCINATION_PATTERNS]

    def detect_placeholders(self, text: str) -> List[ValidationIssue]:
        """Erkennt nicht-ersetzte Platzhalter."""
        issues = []
        for pattern in self.compiled_patterns[:3]:  # Nur Platzhalter-Patterns
            for match in pattern.finditer(text):
                issues.append(ValidationIssue(
                    code="HALLUC_PLACEHOLDER",
                    message=f"Nicht-ersetzter Platzhalter gefunden: {match.group(0)}",
                    severity=ValidationSeverity.ERROR,
                    field="placeholder",
                    value=match.group(0)
                ))
        return issues

    def detect_implausible_values(self, text: str) -> List[ValidationIssue]:
        """Erkennt unplausible medizinische Werte."""
        issues = []
        for fact in self.IMPLAUSIBLE_FACTS:
            for match in re.finditer(fact["pattern"], text, re.IGNORECASE):
                try:
                    value = float(match.group(1).replace(",", "."))

                    # Spezialfall Blutdruck
                    if fact["name"] == "Blutdruck":
                        systolic = value
                        if systolic < fact["systolic_min"] or systolic > fact["systolic_max"]:
                            issues.append(ValidationIssue(
                                code="HALLUC_IMPLAUSIBLE",
                                message=f"Unplausibler {fact['name']}: {match.group(0)}",
                                severity=ValidationSeverity.WARNING,
                                field="vital_sign",
                                value=str(value)
                            ))
                    else:
                        if value < fact["min"] or value > fact["max"]:
                            issues.append(ValidationIssue(
                                code="HALLUC_IMPLAUSIBLE",
                                message=f"Unplausibler Wert für {fact['name']}: {value} (erwartet: {fact['min']}-{fact['max']})",
                                severity=ValidationSeverity.WARNING,
                                field="vital_sign",
                                value=str(value)
                            ))
                except (ValueError, IndexError):
                    continue
        return issues

    def check_rag_coverage(
        self,
        answer: str,
        rag_context: Optional[str] = None,
        rag_sources: Optional[List[str]] = None
    ) -> Tuple[float, List[ValidationIssue]]:
        """
        Prüft wie gut die Antwort durch RAG-Kontext abgedeckt ist.

        Returns:
            (coverage_score, issues) - Score 0-1, höher = besser abgedeckt
        """
        issues = []

        if not rag_context and not rag_sources:
            issues.append(ValidationIssue(
                code="HALLUC_NO_RAG",
                message="Keine RAG-Quellen verfügbar - erhöhtes Halluzinationsrisiko",
                severity=ValidationSeverity.WARNING,
                field="rag_sources"
            ))
            return 0.3, issues  # Niedrige Basis-Confidence ohne RAG

        # Extrahiere Schlüsselbegriffe aus der Antwort
        answer_lower = answer.lower()
        context_lower = (rag_context or "").lower()

        # Medizinische Schlüsselwörter
        medical_keywords = []
        keyword_patterns = [
            r'\b(?:diagnos\w+|therap\w+|behandl\w+|medikament\w+|symptom\w+)\b',
            r'\b(?:mg|µg|ml|IE)\b',
            r'\b[A-Z][a-z]+(?:in|ol|id|at|on)\b',  # Medikamentennamen
        ]

        for pattern in keyword_patterns:
            medical_keywords.extend(re.findall(pattern, answer_lower, re.IGNORECASE))

        if not medical_keywords:
            return 0.7, issues  # Keine spezifischen Terme zu prüfen

        # Prüfe wie viele Keywords im RAG-Kontext vorkommen
        covered = sum(1 for kw in medical_keywords if kw.lower() in context_lower)
        coverage = covered / len(medical_keywords) if medical_keywords else 0.5

        if coverage < 0.3:
            issues.append(ValidationIssue(
                code="HALLUC_LOW_COVERAGE",
                message=f"Nur {coverage*100:.0f}% der medizinischen Begriffe durch RAG belegt",
                severity=ValidationSeverity.WARNING,
                field="rag_coverage",
                value=f"{coverage:.2f}"
            ))

        return max(0.3, coverage), issues

    def validate(
        self,
        text: str,
        rag_context: Optional[str] = None,
        rag_sources: Optional[List[str]] = None
    ) -> Tuple[float, List[ValidationIssue]]:
        """
        Vollständige Halluzinations-Prüfung.

        Returns:
            (hallucination_risk, issues) - Risk 0-1, höher = mehr Risiko
        """
        all_issues = []

        # 1. Platzhalter
        all_issues.extend(self.detect_placeholders(text))

        # 2. Implausible Werte
        all_issues.extend(self.detect_implausible_values(text))

        # 3. RAG-Abdeckung
        coverage, coverage_issues = self.check_rag_coverage(text, rag_context, rag_sources)
        all_issues.extend(coverage_issues)

        # Berechne Risiko-Score
        error_count = sum(1 for i in all_issues if i.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL))
        warning_count = sum(1 for i in all_issues if i.severity == ValidationSeverity.WARNING)

        risk = 0.0
        risk += error_count * 0.3
        risk += warning_count * 0.1
        risk += (1 - coverage) * 0.3

        return min(1.0, risk), all_issues


class AnswerQualityChecker:
    """
    Prüft die fachliche Qualität generierter Antworten.

    Kriterien:
    1. Strukturierung (5-Punkte-Schema)
    2. Quellenangaben
    3. Evidenzgrad
    4. Vollständigkeit
    """

    # Erwartete Struktur für medizinische Antworten
    EXPECTED_SECTIONS = [
        (r"(?:1\.|Definition|Zusammenfassung)", "Definition/Zusammenfassung"),
        (r"(?:2\.|Ätiologie|Pathophysiologie|Ursachen)", "Ätiologie"),
        (r"(?:3\.|Diagnostik|Untersuchung)", "Diagnostik"),
        (r"(?:4\.|Therapie|Behandlung|Management)", "Therapie"),
        (r"(?:5\.|Prognose|Komplikationen|Rechtlich)", "Prognose/Rechtlich"),
    ]

    # Evidenzgrad-Marker
    EVIDENZ_PATTERNS = [
        r"(?:Evidenzgrad|LoE)[:\s]*([A-D]|[IV]+|[1-4])",
        r"(?:Empfehlungsgrad)[:\s]*([A-D]|stark|schwach)",
        r"(?:Leitlinie)[:\s]*([^\n]+)",
    ]

    # Mindestanforderungen
    MIN_LENGTH = 200  # Zeichen
    MIN_SECTIONS = 2  # Mindestens 2 Abschnitte

    def check_structure(self, text: str) -> Tuple[float, List[ValidationIssue]]:
        """Prüft ob die Antwort strukturiert ist."""
        issues = []
        found_sections = []

        for pattern, name in self.EXPECTED_SECTIONS:
            if re.search(pattern, text, re.IGNORECASE):
                found_sections.append(name)

        section_score = len(found_sections) / len(self.EXPECTED_SECTIONS)

        if len(found_sections) < self.MIN_SECTIONS:
            issues.append(ValidationIssue(
                code="QUALITY_LOW_STRUCTURE",
                message=f"Wenig Struktur: nur {len(found_sections)} von {len(self.EXPECTED_SECTIONS)} Abschnitten",
                severity=ValidationSeverity.WARNING,
                field="structure",
                value=", ".join(found_sections) if found_sections else "keine"
            ))

        return section_score, issues

    def check_evidenz(self, text: str) -> Tuple[bool, List[ValidationIssue]]:
        """Prüft ob Evidenzangaben vorhanden sind."""
        issues = []
        has_evidenz = False

        for pattern in self.EVIDENZ_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                has_evidenz = True
                break

        if not has_evidenz:
            # Nur Info, keine harte Anforderung
            issues.append(ValidationIssue(
                code="QUALITY_NO_EVIDENZ",
                message="Keine Evidenzgrad-Angabe gefunden",
                severity=ValidationSeverity.INFO,
                field="evidenz"
            ))

        return has_evidenz, issues

    def check_completeness(self, text: str, question: str) -> Tuple[float, List[ValidationIssue]]:
        """Prüft Vollständigkeit der Antwort."""
        issues = []

        # Längenprüfung
        if len(text) < self.MIN_LENGTH:
            issues.append(ValidationIssue(
                code="QUALITY_TOO_SHORT",
                message=f"Antwort zu kurz: {len(text)} Zeichen (min: {self.MIN_LENGTH})",
                severity=ValidationSeverity.WARNING,
                field="length",
                value=str(len(text))
            ))
            return 0.3, issues

        # Prüfe ob Frage-Schlüsselwörter in Antwort vorkommen
        question_words = set(re.findall(r'\b[A-Za-zäöüÄÖÜß]{4,}\b', question.lower()))
        answer_words = set(re.findall(r'\b[A-Za-zäöüÄÖÜß]{4,}\b', text.lower()))

        overlap = len(question_words & answer_words) / len(question_words) if question_words else 0.5

        if overlap < 0.2:
            issues.append(ValidationIssue(
                code="QUALITY_OFF_TOPIC",
                message="Antwort scheint nicht zur Frage zu passen",
                severity=ValidationSeverity.WARNING,
                field="relevance",
                value=f"{overlap:.2f}"
            ))

        return min(1.0, len(text) / 500 * 0.5 + overlap * 0.5), issues

    def validate(self, answer: str, question: str = "") -> Tuple[float, List[ValidationIssue]]:
        """
        Vollständige Qualitätsprüfung.

        Returns:
            (quality_score, issues) - Score 0-1, höher = bessere Qualität
        """
        all_issues = []

        # 1. Struktur
        structure_score, structure_issues = self.check_structure(answer)
        all_issues.extend(structure_issues)

        # 2. Evidenz
        has_evidenz, evidenz_issues = self.check_evidenz(answer)
        all_issues.extend(evidenz_issues)

        # 3. Vollständigkeit
        completeness_score, completeness_issues = self.check_completeness(answer, question)
        all_issues.extend(completeness_issues)

        # Gesamtscore
        quality_score = (
            structure_score * 0.3 +
            (0.2 if has_evidenz else 0.1) +
            completeness_score * 0.5
        )

        return quality_score, all_issues


def validate_medical_content(
    text: str,
    patient_gender: Optional[str] = None,
    patient_age: Optional[int] = None
) -> ValidationResult:
    """
    Schnelle Validierung medizinischer Inhalte.

    Args:
        text: Zu validierender Text
        patient_gender: Optional Geschlecht
        patient_age: Optional Alter

    Returns:
        ValidationResult
    """
    validator = MedicalValidationLayer()
    return validator.validate(text, patient_gender, patient_age)


def validate_generated_answer(
    question: str,
    answer: str,
    rag_context: Optional[str] = None,
    rag_sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Vollständige Validierung einer generierten Antwort.

    Prüft:
    1. Medizinische Korrektheit (Dosierungen, Laborwerte, etc.)
    2. Halluzinationsrisiko
    3. Antwortqualität

    Args:
        question: Die gestellte Frage
        answer: Die generierte Antwort
        rag_context: Optional RAG-Kontext für Halluzinations-Check
        rag_sources: Optional Liste der RAG-Quellen

    Returns:
        Dict mit validation_passed, scores, und issues
    """
    # 1. Medizinische Validierung
    med_validator = MedicalValidationLayer()
    med_result = med_validator.validate(answer)

    # 2. Halluzinations-Check
    halluc_detector = HallucinationDetector()
    halluc_risk, halluc_issues = halluc_detector.validate(answer, rag_context, rag_sources)

    # 3. Qualitäts-Check
    quality_checker = AnswerQualityChecker()
    quality_score, quality_issues = quality_checker.validate(answer, question)

    # Kombinierte Bewertung
    all_issues = med_result.issues + halluc_issues + quality_issues
    all_warnings = med_result.warnings

    # Gesamtscore
    overall_score = (
        med_result.confidence_score * 0.4 +
        (1 - halluc_risk) * 0.3 +
        quality_score * 0.3
    )

    # Validierung bestanden wenn:
    # - Keine kritischen/error Issues
    # - Halluzinationsrisiko < 0.5
    # - Qualitätsscore > 0.4
    validation_passed = (
        not med_result.has_critical_issues and
        not med_result.has_errors and
        halluc_risk < 0.5 and
        quality_score > 0.4
    )

    return {
        "validation_passed": validation_passed,
        "overall_score": round(overall_score, 2),
        "scores": {
            "medical_confidence": med_result.confidence_score,
            "hallucination_risk": round(halluc_risk, 2),
            "quality_score": round(quality_score, 2)
        },
        "issues": [i.to_dict() for i in all_issues],
        "warnings": [w.to_dict() for w in all_warnings],
        "recommendation": (
            "ACCEPT" if validation_passed else
            "REVIEW" if overall_score > 0.5 else
            "REJECT"
        )
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_text = """
    Patient: männlich, 45 Jahre
    Diagnose: Diabetes mellitus Typ 2 (E11.9), Hypertonie (I10)

    Therapie:
    - Metformin 500 mg 2x täglich
    - Ramipril 5 mg 1x täglich
    - Methylphenidat 500 mg (FEHLER: viel zu hoch!)

    Labor:
    - Kreatinin: 1.8 mg/dl (erhöht)
    - HbA1c: 8.5%
    - Kalium: 6.8 mmol/l (kritisch!)

    Schwangerschaft ausgeschlossen (FEHLER: männlicher Patient!)
    """

    validator = MedicalValidationLayer()
    result = validator.validate(test_text, patient_gender="male", patient_age=45)

    print("\n" + "=" * 60)
    print("VALIDIERUNGSERGEBNIS")
    print("=" * 60)
    print(f"Valide: {result.is_valid}")
    print(f"Confidence: {result.confidence_score}")
    print(f"Kritische Issues: {result.has_critical_issues}")
    print(f"Fehler: {result.has_errors}")

    print("\nIssues:")
    for issue in result.issues:
        print(f"  [{issue.severity.value.upper()}] {issue.message}")

    print("\nWarnungen:")
    for warning in result.warnings:
        print(f"  [{warning.severity.value.upper()}] {warning.message}")

    print("\nStatistiken:")
    print(json.dumps(validator.get_statistics(), indent=2))
