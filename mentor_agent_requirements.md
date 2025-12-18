# Mentor-Agenten Anforderungen

## 1. Spezifische Inhalte und Themenbereiche

### 1.1 Prüfungsablauf und Struktur
- Drei Teile der Prüfung:
  1. Anamnese & körperliche Untersuchung
  2. Dokumentation
  3. Mündliche Prüfung

### 1.2 Medizinische Themenbereiche

#### Innere Medizin
- Anämie: Alle Anämie-Typen (Ursachen, Diagnostik, Therapie), Makrozytäre hyperchrome Anämie, B12-Mangelanämie, Folsäuremangel
- Herz-Kreislauf-Erkrankungen: KHK, EKG-Interpretation, Herzinsuffizienz, Echokardiografie, Perikarderguss, WPW-Syndrom
- Endokrinologie: Hypothyreose, Hyperthyreose, Cushing-Syndrom, Conn-Syndrom, Addison-Krise
- Nieren- und ableitende Harnwege: Pyelonephritis, akutes Nierenversagen, chronisches Nierenversagen, Nephrotisches Syndrom
- Gastroenterologie: GERD, Gastritis, Ulkuskrankheit, Colitis ulcerosa, Morbus Crohn, Divertikulitis, Ileus
- Pneumologie: Pneumonie, COPD, Lungenembolie, Tuberkulose
- Hämatologie: Thrombozytopenie, DIC, ITP, HIT, Leukämie
- Metabolisches Syndrom: Definition, Kriterien
- Diabetes mellitus: Typ 1 & 2 (Pathophysiologie, Diagnostik, Therapie, Komplikationen)

#### Chirurgie
- Unfallchirurgie: Frakturen, Luxationen, Weichteilverletzungen, Kompartmentsyndrom, Polytrauma
- Viszeralchirurgie: Appendizitis, Cholezystektomie, Hernien, Ileus, Kolonkarzinom, Rektumkarzinom
- Gefäßchirurgie: pAVK, akuter arterieller Verschluss, TVT, Aortenaneurysma
- Bariatrische Chirurgie: BMI, Adipositas-Klassifikation, operative Verfahren

#### Allgemeinmedizin/Pharmakologie/Radiologie/Rechtsmedizin/Strahlenschutz
- Pharmakologie: Wirkmechanismen, Indikationen, Kontraindikationen, Nebenwirkungen, Dosierungen
- Notfallmedizin: ABCDE-Schema, Reanimation, Anaphylaktischer Schock, Schock (Typen, Therapie)
- Radiologie: Röntgen, CT, MRT, Sono, Strahlenschutz
- Rechtsmedizin: Todeszeichen, Patientenverfügung, Schweigepflicht, Meldepflicht

### 1.3 Klassifikationssysteme
- Fontaine-Klassifikation (pAVK)
- Garden-Klassifikation (Femurhalsfraktur)
- Pauwels-Klassifikation (Femurhalsfraktur)
- GOLD-Stadien (COPD)

### 1.4 Referenzbereiche und Grenzwerte
- TSH, fT₃, fT₄, NT-proBNP, CRP, Leukozyten, Hb, INR, aPTT

### 1.5 Medikamentendosierungen
- Salbutamol, Ibuprofen, Adrenalin, Cyanocobalamin, Folsäure, Enoxaparin, Ticagrelor + ASS

### 1.6 Scores und Skalen
- CRB-65, Epworth Sleepiness Scale, CHA₂DS₂-VASc

### 1.7 Häufig gestellte Fragen und Themen
- Anaphylaxie, Trauma/Polytrauma, Herzinsuffizienz, Anämie, Divertikulitis, Frakturen, Schilddrüsenerkrankungen

## 2. Technische Anforderungen

### 2.1 Webanwendung oder Chatbot

#### Frontend
- Benutzerfreundliche Oberfläche für die Interaktion mit dem Mentor-Agenten
- Unterstützung für Text- und Bildbasierte Fragen und Antworten
- Responsive Design für verschiedene Geräte (Desktop, Tablet, Mobile)
- Integration von medizinischen Datenbanken und Leitlinien
- Möglichkeit zur Dokumentation und Speicherung von Prüfungsfällen

#### Backend
- RESTful API für die Kommunikation zwischen Frontend und Backend
- Datenbank für die Speicherung von medizinischen Daten, Prüfungsfällen und Benutzerinformationen
- Authentifizierung und Autorisierung für Benutzer
- Integration von externen APIs für medizinische Daten und Leitlinien

### 2.2 Funktionen

#### Suche und Abfrage
- Suche und Abfrage von medizinischen Fakten und Leitlinien
- Volltextsuche in medizinischen Dokumenten und Leitlinien
- Filterung und Sortierung von Suchergebnissen

#### Interaktive Lernmodule
- Interaktive Lernmodule und Quizfragen
- Simulation von Prüfungsszenarien
- Feedback und Bewertungssystem für Benutzerantworten

#### Dokumentation und Speicherung
- Möglichkeit zur Dokumentation und Speicherung von Prüfungsfällen
- Export von Dokumenten in verschiedenen Formaten (PDF, Word, etc.)
- Import von medizinischen Daten und Dokumenten

### 2.3 Technologien

#### Frontend
- HTML, CSS, JavaScript
- Framework: React, Angular oder Vue.js
- UI-Bibliothek: Material-UI, Bootstrap oder Tailwind CSS

#### Backend
- Programmiersprache: Python, Node.js oder Java
- Framework: Django, Flask, Express.js oder Spring Boot
- Datenbank: PostgreSQL, MySQL oder MongoDB

#### DevOps
- Containerisierung: Docker
- Orchestrierung: Kubernetes
- CI/CD: GitHub Actions, GitLab CI/CD oder Jenkins

## 3. Integration mit der Google Cloud Platform (GCP)

### 3.1 Spezifikation

#### GCP-Dienste
- **Cloud Storage:** Speicherung von medizinischen Daten, Dokumenten und Bildern
- **Cloud Functions:** Serverlose Ausführung von Funktionen für die Verarbeitung von medizinischen Daten
- **Cloud SQL:** Verwaltung von relationalen Datenbanken für medizinische Daten und Benutzerinformationen
- **Cloud AI und Machine Learning:** Integration von KI- und ML-Diensten für die Verarbeitung und Analyse von medizinischen Daten
- **Cloud Security und Compliance:** Nutzung von GCP Security- und Compliance-Diensten für den Schutz von sensiblen Daten

#### Kostenoptimierung
- Nutzung des $850 Guthabens für die Einrichtung und den Betrieb der Anwendung
- Optimierung der Kosten durch Nutzung von GCP-Kostenmanagement-Tools
- Überwachung und Verwaltung der Kosten durch Nutzung von GCP-Budget- und Alert-Tools

### 3.2 Implementierung

#### Einrichtung von GCP-Projekten und -Diensten
- Einrichtung eines GCP-Projekts für die Webanwendung oder den Chatbot
- Konfiguration von GCP-Diensten wie Cloud Storage, Cloud Functions, Cloud SQL
- Einrichtung von GCP-Authentifizierung und -Autorisierung für Benutzer

#### Integration von GCP-APIs
- Integration von GCP-APIs in die Webanwendung oder den Chatbot
- Nutzung von GCP-APIs für die Verarbeitung und Analyse von medizinischen Daten
- Integration von GCP-AI- und ML-APIs für die Verarbeitung von medizinischen Daten

#### Überwachung und Verwaltung
- Nutzung von GCP-Tools für die Überwachung und Verwaltung der Anwendung
- Einrichtung von GCP-Logging und -Monitoring für die Überwachung der Anwendung
- Nutzung von GCP-Tools für die Verwaltung von Benutzerdaten und -informationen
