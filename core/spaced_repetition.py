#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spaced Repetition System (SM-2 Algorithmus)
============================================

Implementiert den SuperMemo-2 (SM-2) Algorithmus für optimales Lernen.

Der SM-2 Algorithmus berechnet:
- Easiness Factor (EF): Wie einfach ist die Karte?
- Interval: Wann soll die Karte wieder gezeigt werden?
- Repetition: Wie oft wurde die Karte schon wiederholt?

Bewertungsskala (0-5):
- 0: "Völlig falsch" - Keine Erinnerung
- 1: "Falsch" - Falsche Antwort, aber nach Sehen erkannt
- 2: "Falsch, aber nah" - Fast richtig, aber signifikante Fehler
- 3: "Richtig mit Mühe" - Richtig, aber mit großer Schwierigkeit
- 4: "Richtig" - Richtig nach einigem Nachdenken
- 5: "Perfekt" - Sofort und fehlerfrei

Autor: O3 Agent
Basiert auf: Piotr Wozniak's SuperMemo-2 Algorithm
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Card:
    """Eine Lernkarte mit SM-2 Metadaten."""
    id: str
    question: str
    answer: str
    
    # SM-2 Daten
    easiness_factor: float = 2.5  # EF - startet bei 2.5
    interval: int = 0  # Tage bis zur nächsten Review
    repetitions: int = 0  # Anzahl erfolgreicher Wiederholungen
    
    # Terminplanung
    next_review: Optional[str] = None  # ISO Format
    last_review: Optional[str] = None
    
    # Metadaten
    question_type: str = ""
    specialty: str = ""
    difficulty: str = "medium"
    tags: List[str] = field(default_factory=list)
    
    # Statistik
    total_reviews: int = 0
    correct_reviews: int = 0
    average_quality: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        return cls(**data)
    
    def is_due(self, current_date: Optional[datetime] = None) -> bool:
        """Prüft ob die Karte zur Wiederholung fällig ist."""
        if current_date is None:
            current_date = datetime.now()
        
        if self.next_review is None:
            return True  # Neue Karte
        
        next_review_date = datetime.fromisoformat(self.next_review)
        return current_date >= next_review_date


class SM2Algorithm:
    """
    SuperMemo-2 Algorithmus für Spaced Repetition.
    
    Der Algorithmus passt den Easiness Factor (EF) und das Wiederholungsintervall
    basierend auf der Qualität der Antwort an.
    """
    
    MIN_EF = 1.3  # Minimaler Easiness Factor
    
    @staticmethod
    def calculate_next_review(card: Card, quality: int) -> Card:
        """
        Berechnet das nächste Review-Datum basierend auf SM-2.
        
        Args:
            card: Die zu aktualisierende Karte
            quality: Bewertung 0-5
        
        Returns:
            Aktualisierte Karte
        """
        # Validiere Quality
        quality = max(0, min(5, quality))
        
        # Update Statistiken
        card.total_reviews += 1
        if quality >= 3:
            card.correct_reviews += 1
        card.average_quality = (
            (card.average_quality * (card.total_reviews - 1) + quality) 
            / card.total_reviews
        )
        
        # SM-2 Kernalgorithmus
        if quality < 3:
            # Nicht bestanden - zurück auf Anfang
            card.repetitions = 0
            card.interval = 1
        else:
            # Bestanden - berechne neues Intervall
            if card.repetitions == 0:
                card.interval = 1
            elif card.repetitions == 1:
                card.interval = 6
            else:
                card.interval = round(card.interval * card.easiness_factor)
            
            card.repetitions += 1
        
        # Update Easiness Factor
        card.easiness_factor = max(
            SM2Algorithm.MIN_EF,
            card.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        )
        
        # Setze Review-Termine
        card.last_review = datetime.now().isoformat()
        card.next_review = (datetime.now() + timedelta(days=card.interval)).isoformat()
        
        return card


@dataclass
class StudySession:
    """Eine Lernsession."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    cards_reviewed: int = 0
    cards_correct: int = 0
    cards_incorrect: int = 0
    average_quality: float = 0.0
    time_spent_seconds: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SpacedRepetitionSystem:
    """
    Haupt-System für Spaced Repetition Learning.
    
    Features:
    - SM-2 Algorithmus für optimale Wiederholungsintervalle
    - Fachgebiet-Filter
    - Fortschrittsverfolgung
    - Statistiken und Prognosen
    """
    
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.cards_file = data_path / "srs_cards.json"
        self.progress_file = data_path / "srs_progress.json"
        self.sessions_file = data_path / "srs_sessions.json"
        
        self.cards: Dict[str, Card] = {}
        self.sessions: List[StudySession] = []
        self.current_session: Optional[StudySession] = None
        
        self._load_data()
    
    def _load_data(self):
        """Lädt gespeicherte SRS-Daten."""
        # Lade Karten
        if self.cards_file.exists():
            try:
                with open(self.cards_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for card_data in data.get("cards", []):
                    card = Card.from_dict(card_data)
                    self.cards[card.id] = card
                logger.info(f"📂 Loaded {len(self.cards)} cards")
            except Exception as e:
                logger.error(f"Error loading cards: {e}")
        
        # Lade Sessions
        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sessions = [StudySession(**s) for s in data.get("sessions", [])]
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
    
    def _save_data(self):
        """Speichert SRS-Daten."""
        # Speichere Karten
        with open(self.cards_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_cards": len(self.cards),
                "cards": [card.to_dict() for card in self.cards.values()]
            }, f, ensure_ascii=False, indent=2)
        
        # Speichere Sessions
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "sessions": [s.to_dict() for s in self.sessions]
            }, f, ensure_ascii=False, indent=2)
    
    def import_qa_pairs(self, qa_file: Path) -> int:
        """
        Importiert Q&A-Paare als Lernkarten.
        
        Args:
            qa_file: Pfad zur JSON-Datei mit Q&A-Paaren
        
        Returns:
            Anzahl importierter Karten
        """
        if not qa_file.exists():
            logger.error(f"File not found: {qa_file}")
            return 0
        
        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            qa_pairs = data.get("qa_pairs", data if isinstance(data, list) else [])
            imported = 0
            
            for i, qa in enumerate(qa_pairs):
                card_id = f"card_{i:06d}"
                
                if card_id not in self.cards:
                    card = Card(
                        id=card_id,
                        question=qa.get("question", ""),
                        answer=qa.get("answer", ""),
                        question_type=qa.get("question_type", ""),
                        specialty=qa.get("specialty", "Allgemein"),
                        difficulty=qa.get("difficulty", "medium"),
                        tags=qa.get("tags", [])
                    )
                    self.cards[card_id] = card
                    imported += 1
            
            self._save_data()
            logger.info(f"✅ Imported {imported} new cards (total: {len(self.cards)})")
            return imported
            
        except Exception as e:
            logger.error(f"Error importing Q&A: {e}")
            return 0
    
    def get_due_cards(
        self, 
        limit: Optional[int] = None,
        specialty: Optional[str] = None,
        question_type: Optional[str] = None
    ) -> List[Card]:
        """
        Gibt alle fälligen Karten zurück.
        
        Args:
            limit: Maximale Anzahl Karten
            specialty: Optional - nur dieses Fachgebiet
            question_type: Optional - nur dieser Fragetyp
        
        Returns:
            Liste fälliger Karten
        """
        due_cards = []
        
        for card in self.cards.values():
            if not card.is_due():
                continue
            
            if specialty and card.specialty != specialty:
                continue
            
            if question_type and card.question_type != question_type:
                continue
            
            due_cards.append(card)
        
        # Sortiere nach Priorität (niedrigerer EF = schwieriger = höhere Priorität)
        due_cards.sort(key=lambda c: (c.easiness_factor, c.repetitions))
        
        if limit:
            due_cards = due_cards[:limit]
        
        return due_cards
    
    def get_new_cards(self, limit: int = 20) -> List[Card]:
        """Gibt neue (noch nie gelernte) Karten zurück."""
        new_cards = [c for c in self.cards.values() if c.repetitions == 0]
        random.shuffle(new_cards)
        return new_cards[:limit]
    
    def start_session(self) -> StudySession:
        """Startet eine neue Lernsession."""
        session = StudySession(
            session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            started_at=datetime.now().isoformat()
        )
        self.current_session = session
        logger.info(f"🎓 Started session {session.session_id}")
        return session
    
    def review_card(self, card_id: str, quality: int) -> Optional[Card]:
        """
        Bewertet eine Karte und aktualisiert SM-2 Daten.
        
        Args:
            card_id: ID der Karte
            quality: Bewertung 0-5
        
        Returns:
            Aktualisierte Karte oder None
        """
        if card_id not in self.cards:
            logger.error(f"Card not found: {card_id}")
            return None
        
        card = self.cards[card_id]
        updated_card = SM2Algorithm.calculate_next_review(card, quality)
        self.cards[card_id] = updated_card
        
        # Update Session-Statistik
        if self.current_session:
            self.current_session.cards_reviewed += 1
            if quality >= 3:
                self.current_session.cards_correct += 1
            else:
                self.current_session.cards_incorrect += 1
            self.current_session.average_quality = (
                (self.current_session.average_quality * (self.current_session.cards_reviewed - 1) + quality)
                / self.current_session.cards_reviewed
            )
        
        self._save_data()
        return updated_card
    
    def end_session(self) -> Optional[StudySession]:
        """Beendet die aktuelle Session."""
        if not self.current_session:
            return None
        
        self.current_session.ended_at = datetime.now().isoformat()
        
        start = datetime.fromisoformat(self.current_session.started_at)
        end = datetime.fromisoformat(self.current_session.ended_at)
        self.current_session.time_spent_seconds = int((end - start).total_seconds())
        
        self.sessions.append(self.current_session)
        session = self.current_session
        self.current_session = None
        
        self._save_data()
        logger.info(f"✅ Ended session: {session.cards_reviewed} cards reviewed")
        return session
    
    def get_statistics(self) -> Dict[str, Any]:
        """Berechnet Lernstatistiken."""
        total_cards = len(self.cards)
        mastered = sum(1 for c in self.cards.values() if c.repetitions >= 5 and c.easiness_factor > 2.0)
        learning = sum(1 for c in self.cards.values() if 0 < c.repetitions < 5)
        new = sum(1 for c in self.cards.values() if c.repetitions == 0)
        due_today = len(self.get_due_cards())
        
        total_reviews = sum(c.total_reviews for c in self.cards.values())
        correct_reviews = sum(c.correct_reviews for c in self.cards.values())
        
        return {
            "total_cards": total_cards,
            "mastered": mastered,
            "learning": learning,
            "new": new,
            "due_today": due_today,
            "total_reviews": total_reviews,
            "correct_reviews": correct_reviews,
            "accuracy": (correct_reviews / total_reviews * 100) if total_reviews > 0 else 0,
            "average_ef": sum(c.easiness_factor for c in self.cards.values()) / total_cards if total_cards > 0 else 2.5,
            "total_sessions": len(self.sessions),
            "total_study_time_hours": sum(s.time_spent_seconds for s in self.sessions) / 3600,
        }
    
    def get_forecast(self, days: int = 30) -> Dict[str, int]:
        """
        Prognostiziert die Anzahl fälliger Karten für die nächsten Tage.
        
        Args:
            days: Anzahl Tage für die Prognose
        
        Returns:
            Dict mit Datum -> Anzahl fälliger Karten
        """
        forecast = {}
        today = datetime.now()
        
        for day_offset in range(days):
            check_date = today + timedelta(days=day_offset)
            date_str = check_date.strftime("%Y-%m-%d")
            
            due_count = sum(
                1 for c in self.cards.values()
                if c.next_review and datetime.fromisoformat(c.next_review).date() == check_date.date()
            )
            
            forecast[date_str] = due_count
        
        return forecast
    
    def print_dashboard(self):
        """Gibt ein Übersichts-Dashboard aus."""
        stats = self.get_statistics()
        
        print("\n" + "=" * 60)
        print("📊 SPACED REPETITION DASHBOARD")
        print("=" * 60)
        print(f"\n📚 Kartenübersicht:")
        print(f"   Gesamt:        {stats['total_cards']:,}")
        print(f"   Gemeistert:    {stats['mastered']:,} 🏆")
        print(f"   Im Lernen:     {stats['learning']:,} 📖")
        print(f"   Neu:           {stats['new']:,} ✨")
        print(f"   Heute fällig:  {stats['due_today']:,} 📅")
        
        print(f"\n📈 Lernstatistik:")
        print(f"   Wiederholungen:  {stats['total_reviews']:,}")
        print(f"   Genauigkeit:     {stats['accuracy']:.1f}%")
        print(f"   Ø Difficulty:    {stats['average_ef']:.2f}")
        print(f"   Sessions:        {stats['total_sessions']}")
        print(f"   Lernzeit:        {stats['total_study_time_hours']:.1f}h")
        
        print("\n" + "=" * 60)


def interactive_session(srs: SpacedRepetitionSystem, cards_limit: int = 20):
    """Führt eine interaktive Lernsession durch."""
    print("\n" + "=" * 60)
    print("🎓 INTERAKTIVE LERNSESSION")
    print("=" * 60)
    
    # Hole fällige Karten
    due_cards = srs.get_due_cards(limit=cards_limit)
    
    if not due_cards:
        # Wenn keine fälligen, zeige neue Karten
        new_cards = srs.get_new_cards(limit=cards_limit)
        if not new_cards:
            print("\n✅ Keine Karten zum Lernen! Gut gemacht!")
            return
        due_cards = new_cards
        print(f"\n📚 {len(due_cards)} neue Karten zum Lernen")
    else:
        print(f"\n📚 {len(due_cards)} Karten zur Wiederholung")
    
    print("\nBewertungsskala:")
    print("  0 = Völlig falsch - Keine Erinnerung")
    print("  1 = Falsch")
    print("  2 = Falsch, aber nah dran")
    print("  3 = Richtig mit Mühe")
    print("  4 = Richtig")
    print("  5 = Perfekt")
    print("\nDrücke 'q' zum Beenden\n")
    print("-" * 60)
    
    srs.start_session()
    
    for i, card in enumerate(due_cards, 1):
        print(f"\n[{i}/{len(due_cards)}] {card.specialty} | {card.question_type}")
        print("-" * 40)
        print(f"\n❓ FRAGE:\n{card.question}\n")
        
        input("Drücke Enter um die Antwort zu sehen...")
        
        print(f"\n✅ ANTWORT:\n{card.answer}\n")
        
        while True:
            response = input("Bewertung (0-5, oder 'q' zum Beenden): ").strip().lower()
            
            if response == 'q':
                print("\n👋 Session beendet!")
                session = srs.end_session()
                if session:
                    print(f"   Karten gelernt: {session.cards_reviewed}")
                    print(f"   Richtig: {session.cards_correct}")
                    print(f"   Falsch: {session.cards_incorrect}")
                return
            
            try:
                quality = int(response)
                if 0 <= quality <= 5:
                    srs.review_card(card.id, quality)
                    
                    if quality >= 3:
                        print("✅ Richtig! Nächste Wiederholung in", srs.cards[card.id].interval, "Tagen")
                    else:
                        print("❌ Nochmal lernen! Karte kommt bald wieder.")
                    break
                else:
                    print("Bitte 0-5 eingeben")
            except ValueError:
                print("Bitte eine Zahl eingeben")
        
        print("-" * 60)
    
    print("\n🎉 Session abgeschlossen!")
    session = srs.end_session()
    if session:
        print(f"   Karten gelernt: {session.cards_reviewed}")
        print(f"   Richtig: {session.cards_correct} ({session.cards_correct/session.cards_reviewed*100:.0f}%)")
        print(f"   Zeit: {session.time_spent_seconds//60} Minuten")


def main():
    """Hauptfunktion."""
    project_dir = Path(__file__).parent.parent
    srs = SpacedRepetitionSystem(project_dir)
    
    # Importiere Q&A falls noch nicht geschehen
    qa_file = project_dir / "generated_qa_from_cases.json"
    if qa_file.exists() and len(srs.cards) == 0:
        srs.import_qa_pairs(qa_file)
    
    # Zeige Dashboard
    srs.print_dashboard()
    
    print("\n\nOptionen:")
    print("  1. Interaktive Lernsession starten")
    print("  2. Nur Statistiken anzeigen")
    print("  3. Prognose für 30 Tage")
    print("  4. Beenden")
    
    choice = input("\nWahl: ").strip()
    
    if choice == "1":
        limit = input("Anzahl Karten (default: 20): ").strip()
        limit = int(limit) if limit.isdigit() else 20
        interactive_session(srs, limit)
    elif choice == "3":
        forecast = srs.get_forecast(30)
        print("\n📅 30-Tage-Prognose:")
        for date, count in list(forecast.items())[:7]:
            bar = "█" * min(count // 5, 20)
            print(f"  {date}: {count:4d} {bar}")


if __name__ == "__main__":
    main()

