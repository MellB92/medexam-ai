# Codex Tasks - Open List Cleaning and Batch Generation

## Overview
Clean the open list (~147 meaningful gaps from questions_missing_strict.json), generate answers in small batches using gpt-4o-mini with guidelines KB and web search, perform QC/merge, create MD samples, and ensure backup/checkpoint procedures.

## Specific Tasks

### 1. Open List Cleaning and Preparation
**Objective:** Prepare and clean the questions_missing_strict.json file for processing

**Tasks:**
- [ ] Locate or create questions_missing_strict.json file
- [ ] Validate file format and structure
- [ ] Clean and normalize question data
- [ ] Remove duplicates and invalid entries
- [ ] Categorize questions by topic and difficulty
- [ ] Prioritize questions based on exam relevance
- [ ] Create backup of original file before cleaning

**Expected file structure:**
```json
{
  "total_questions": 147,
  "last_updated": "2025-12-09",
  "questions": [
    {
      "id": "unique_id",
      "question_text": "Question text here",
      "category": "medical_topic",
      "difficulty": "high/medium/low",
      "source": "original_source",
      "priority": 1-5,
      "status": "pending/processing/completed"
    }
  ]
}
```

### 2. Batch Generation Setup
**Objective:** Set up the generation pipeline for processing questions in batches

**Tasks:**
- [ ] Configure gpt-4o-mini model parameters
- [ ] Set up guidelines KB integration
- [ ] Configure web search parameters and filters
- [ ] Define batch size (recommended: 10-20 questions per batch)
- [ ] Implement quality control criteria
- [ ] Set up generation monitoring and logging
- [ ] Configure backup/checkpoint triggers

**Batch configuration:**
- Model: gpt-4o-mini
- Temperature: 0.3-0.5
- Max tokens: 1024-2048
- Top-p: 0.9
- Frequency penalty: 0.1
- Presence penalty: 0.1

### 3. Answer Generation Process
**Objective:** Generate high-quality answers for the cleaned questions

**Tasks:**
- [ ] Implement batch processing loop
- [ ] Integrate RAG system with guidelines KB
- [ ] Add web search augmentation (DocCheck, Fachgesellschaften)
- [ ] Implement prompt engineering for medical accuracy
- [ ] Generate structured answers (5-point schema)
- [ ] Add source citations and references
- [ ] Include evidence grading (A/B/C)
- [ ] Implement quality scoring system

**Answer structure:**
```json
{
  "question_id": "unique_id",
  "generated_answer": {
    "definition_klassifikation": "Definition text",
    "aetiologie_pathophysiologie": "Etiology text",
    "diagnostik": "Diagnostics text",
    "therapie": "Therapy text",
    "rechtliche_aspekte": "Legal aspects text",
    "leitlinie": "AWMF S3-Leitlinie [Name] ([Jahr])",
    "evidenzgrad": "A/B/C",
    "sources": [
      {
        "type": "guideline/web/kb",
        "reference": "Source reference",
        "url": "source_url"
      }
    ]
  },
  "generation_metadata": {
    "model": "gpt-4o-mini",
    "timestamp": "ISO_timestamp",
    "batch_number": "X",
    "quality_score": 0-100,
    "confidence": 0-1
  }
}
```

### 4. Quality Control and Merge
**Objective:** Ensure answer quality and integrate with existing knowledge base

**Tasks:**
- [ ] Implement automated quality control checks
- [ ] Add manual review process for critical questions
- [ ] Implement hallucination detection
- [ ] Add medical accuracy validation
- [ ] Implement consistency checking
- [ ] Set up review and approval workflow
- [ ] Implement merge strategy with existing KB
- [ ] Handle conflicts and duplicates

**Quality control criteria:**
- Medical accuracy (primary)
- Completeness of answer
- Proper citations and references
- Evidence-based content
- No hallucinations or contradictions
- Proper legal aspects coverage
- Appropriate evidence grading

### 5. MD Sample Creation
**Objective:** Create Markdown samples for validation and documentation

**Tasks:**
- [ ] Implement MD export template
- [ ] Create sample generation script
- [ ] Implement random sampling for QC
- [ ] Generate MD files with proper formatting
- [ ] Add metadata and source information
- [ ] Create validation samples for review
- [ ] Implement sample tracking system

**MD template:**
```markdown
# [Question Topic]

**Frage:** [Question text]

**Antwort:**

### 1. Definition/Klassifikation
[Definition text]

### 2. Ätiologie/Pathophysiologie
[Etiology text]

### 3. Diagnostik
[Diagnostics text]

### 4. Therapie
[Therapy text]

### 5. Rechtliche Aspekte
[Legal aspects text]

**Leitlinie:** [AWMF S3-Leitlinie [Name] ([Jahr])]
**Evidenzgrad:** [A/B/C]

**Quellen:**
- [Source 1](url1)
- [Source 2](url2)

**Generiert:** [Timestamp] | **Batch:** [X] | **Modell:** gpt-4o-mini
```

### 6. Backup and Checkpoint Management
**Objective:** Ensure data safety and recovery capability

**Tasks:**
- [ ] Implement automated backup system
- [ ] Create checkpoint after each batch
- [ ] Implement version control for generated answers
- [ ] Set up backup verification process
- [ ] Implement recovery procedures
- [ ] Document backup/restore processes
- [ ] Monitor backup success/failure

**Backup strategy:**
- Backup before starting each batch
- Checkpoint after each successful batch
- Full backup after completing all batches
- Retain last 5 checkpoints
- Backup location: `checkpoints/` directory
- Backup format: JSON with timestamp

### 7. Monitoring and Reporting
**Objective:** Track progress and report results

**Tasks:**
- [ ] Implement progress tracking dashboard
- [ ] Set up batch completion monitoring
- [ ] Implement quality metrics tracking
- [ ] Create generation statistics reporting
- [ ] Set up error and exception logging
- [ ] Implement performance monitoring
- [ ] Create final completion report

**Monitoring metrics:**
- Total questions processed
- Batches completed/success/failure
- Average generation time per question
- Quality scores distribution
- Error rates and types
- KB integration success rate
- Web search success rate

## Implementation Approach

### Priority Order:
1. Open list cleaning and preparation (foundation)
2. Batch generation setup (infrastructure)
3. Quality control implementation (safety)
4. Answer generation process (core)
5. MD sample creation (validation)
6. Backup/checkpoint management (reliability)
7. Monitoring and reporting (transparency)

### Technical Requirements:
- Python 3.9+
- Required libraries: json, datetime, logging, pathlib
- RAG system integration
- Web search API access
- gpt-4o-mini API access
- Guidelines KB access

### Success Criteria:
- All 147 questions processed successfully
- Minimum 90% quality score average
- No data loss (verified backups)
- Complete documentation and samples
- All checkpoints created successfully
- Final report with statistics generated

## Deliverables:
- Cleaned `questions_missing_strict.json` file
- Generated answers in structured JSON format
- MD samples for validation
- Complete backup/checkpoint history
- Quality control reports
- Final generation statistics
- Process documentation