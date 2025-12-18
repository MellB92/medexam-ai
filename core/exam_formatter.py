"""
exam_formatter.py
Robust formatting utilities for medical examination questions and clinical cases.
Supports structured Q&A format, case studies, and experience reports.

Features:
- Multi-format question parsing (Fragestellung, Fallbeispiel, etc.)
- Structured answer extraction and normalization
- Medical terminology preservation
- Batch processing support
- Quality validation
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Types of medical exam questions"""
    STANDARD = "standard"  # Standard Q&A
    CASE_STUDY = "case_study"  # Clinical case with patient data
    EXPERIENCE_REPORT = "experience_report"  # Exam experience report
    MULTIPLE_CHOICE = "multiple_choice"  # MC questions
    UNKNOWN = "unknown"


@dataclass
class FormattedQuestion:
    """Structured representation of a formatted question"""
    question_text: str
    answers: List[str]
    question_type: QuestionType
    metadata: Dict[str, str]
    original_text: str
    validation_score: float  # 0.0-1.0


def _clean_text(text: str) -> str:
    """Clean and normalize text while preserving medical terminology"""
    if not text:
        return ""
    
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', text)
    
    # Preserve medical abbreviations
    t = re.sub(r'(\d+)\s*([mg|ml|µg|mcg|IU|mmol|μmol|kPa|mmHg])\b', r'\1 \2', t)
    
    return t.strip()


def _extract_question_markers(text: str) -> List[Tuple[str, int]]:
    """Extract all potential question markers with their positions"""
    patterns = [
        (r'(?mi)^(?:fragestellung|frage)[:\s-]*', 'question'),
        (r'(?mi)^(?:fallbeispiel|fall|klinischer fall)[:\s-]*', 'case'),
        (r'(?mi)^(?:patient|patientin|anamnese)[:\s-]*', 'patient'),
        (r'(?mi)^(?:aufgabe|aufgabenstellung)[:\s-]*', 'task'),
    ]
    
    markers = []
    for pattern, marker_type in patterns:
        for match in re.finditer(pattern, text):
            markers.append((marker_type, match.start()))
    
    return sorted(markers, key=lambda x: x[1])


def _extract_answer_markers(text: str) -> List[Tuple[str, int]]:
    """Extract all potential answer markers with their positions"""
    patterns = [
        (r'(?mi)^(?:erwartete antwort|erwartete antworten|antwort|antworten)[:\s-]*', 'answer'),
        (r'(?mi)^(?:therapie|behandlung|management)[:\s-]*', 'therapy'),
        (r'(?mi)^(?:lösung|loesung)[:\s-]*', 'solution'),
        (r'(?mi)^(?:diagnose|differentialdiagnose)[:\s-]*', 'diagnosis'),
    ]
    
    markers = []
    for pattern, marker_type in patterns:
        for match in re.finditer(pattern, text):
            markers.append((marker_type, match.start()))
    
    return sorted(markers, key=lambda x: x[1])


def _detect_question_type(text: str) -> QuestionType:
    """Detect the type of medical question"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['fallbeispiel', 'patient', 'anamnese', 'befund']):
        return QuestionType.CASE_STUDY
    elif any(word in text_lower for word in ['erfahrungsbericht', 'protokoll', 'prüfung']):
        return QuestionType.EXPERIENCE_REPORT
    elif re.search(r'\b[a-e]\)', text_lower) or 'multiple choice' in text_lower:
        return QuestionType.MULTIPLE_CHOICE
    elif any(word in text_lower for word in ['frage', 'aufgabe']):
        return QuestionType.STANDARD
    else:
        return QuestionType.UNKNOWN


def _extract_question_text(text: str) -> str:
    """Extract the main question text"""
    # Split by answer markers FIRST (before cleaning), then clean the question part
    answer_split = re.split(
        r'(?mi)\n\s*(?:erwartete antwort|antwort|therapie|lösung|diagnose)\s*[:\s-]+',
        text,
        maxsplit=1
    )
    
    if len(answer_split) > 1:
        # We found an answer section, return the question part
        question_part = answer_split[0].strip()
        return _clean_text(question_part)
    
    # No answer section found, try to extract question by markers
    m = re.search(
        r'(?mi)^(?:fragestellung|frage|aufgabe)[:\s-]*(.+?)$',
        text,
        re.DOTALL
    )
    if m:
        return _clean_text(m.group(1))
    
    # Fallback: use first paragraph
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if paragraphs:
        return _clean_text(paragraphs[0])
    
    return _clean_text(text[:500])  # First 500 chars as fallback


def _extract_answers(text: str) -> List[str]:
    """
    Extract answer items from text with robust handling of various formats.
    
    Supports:
    - Numbered lists: 1), 1., a), I., etc.
    - Bullet points: -, •, *, ►
    - Multi-line answers with proper whitespace handling
    - Medical terminology with semicolons
    """
    # Try explicit answer section - match until end of text
    m = re.search(
        r'(?mi)\n\s*(?:erwartete antwort|antwort|therapie|lösung|diagnose)\s*[:\s-]+(.+)',
        text,
        re.DOTALL
    )
    
    answer_text = m.group(1).strip() if m else ""
    
    # If no explicit answer section, try second paragraph
    if not answer_text:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) > 1:
            answer_text = paragraphs[1]
    
    if not answer_text:
        return []
    
    # Normalize excessive whitespace while preserving structure
    answer_text = re.sub(r'\n{3,}', '\n\n', answer_text)
    
    # Try to extract structured items
    items: List[str] = []
    
    # Try numbered/lettered lists with improved pattern
    # Supports: 1), 1., a), a., I), I., etc.
    numbered_pattern = r'(?m)^\s*([0-9]+|[a-z]|[IVX]+)[\)\.:]\s*(.+?)(?=^\s*(?:[0-9]+|[a-z]|[IVX]+)[\)\.:]\s*|$)'
    numbered_matches = re.findall(numbered_pattern, answer_text, re.MULTILINE | re.DOTALL)
    if numbered_matches and len(numbered_matches) >= 2:
        items = [_clean_text(match[1]) for match in numbered_matches if match[1].strip()]
    
    # Try bullet points with extended character support
    if not items:
        bullet_pattern = r'(?m)^\s*[-•*►▪]\s+(.+?)(?=^\s*[-•*►▪]\s+|$)'
        bullet_matches = re.findall(bullet_pattern, answer_text, re.MULTILINE | re.DOTALL)
        if bullet_matches and len(bullet_matches) >= 2:
            items = [_clean_text(item) for item in bullet_matches if item.strip()]
    
    # Try semicolon separation (but be cautious with medical terms)
    if not items:
        # Only split on semicolons followed by whitespace to avoid medical abbreviations
        semicolon_split = re.split(r';\s+', answer_text)
        if len(semicolon_split) >= 2:
            items = [_clean_text(item) for item in semicolon_split if item.strip()]
        elif len(semicolon_split) == 1 and answer_text.strip():
            # Single answer without semicolons - take the whole text as one answer
            items = [_clean_text(answer_text)]
    
    # Filter out very short, empty items, or items that are just numbers
    items = [item for item in items if len(item) > 3 and not item.isdigit()]
    
    # Remove duplicate items (case-insensitive)
    seen = set()
    unique_items = []
    for item in items:
        item_lower = item.lower()
        if item_lower not in seen:
            seen.add(item_lower)
            unique_items.append(item)
    
    return unique_items[:10]  # Max 10 answer items


def _extract_metadata(text: str) -> Dict[str, str]:
    """Extract metadata from question text"""
    metadata = {}
    
    # Extract year if present
    year_match = re.search(r'\b(20\d{2})\b', text)
    if year_match:
        metadata['year'] = year_match.group(1)
    
    # Extract location/institution
    location_match = re.search(r'(?i)(münster|düsseldorf|berlin|hamburg|köln|frankfurt|münchen)', text)
    if location_match:
        metadata['location'] = location_match.group(1).title()
    
    # Extract medical specialty
    specialties = [
        'kardiologie', 'neurologie', 'innere medizin', 'chirurgie',
        'gynäkologie', 'pädiatrie', 'psychiatrie', 'dermatologie',
        'urologie', 'orthopädie', 'hno', 'anästhesie'
    ]
    for specialty in specialties:
        if specialty in text.lower():
            metadata['specialty'] = specialty.title()
            break
    
    return metadata


def _calculate_validation_score(question: FormattedQuestion) -> float:
    """Calculate quality/completeness score for formatted question"""
    score = 0.0
    max_score = 5.0
    
    # Has question text
    if question.question_text and len(question.question_text) > 10:
        score += 1.0
    
    # Has answers
    if question.answers:
        score += 1.0
        
        # Multiple structured answers
        if len(question.answers) >= 3:
            score += 0.5
        
        # Answers are substantive
        avg_length = sum(len(a) for a in question.answers) / len(question.answers)
        if avg_length > 20:
            score += 0.5
    
    # Has metadata
    if question.metadata:
        score += 0.5
    
    # Type detected
    if question.question_type != QuestionType.UNKNOWN:
        score += 0.5
    
    # Question length appropriate
    if 50 < len(question.question_text) < 1000:
        score += 1.0
    
    return min(score / max_score, 1.0)


def format_to_exam_standard(
    text: str,
    max_answers: int = 5,
    min_answer_length: int = 5,
    include_separator: bool = True
) -> str:
    """
    Format text into standardized exam Q&A format.
    
    Args:
        text: Raw text to format
        max_answers: Maximum number of answer lines to generate
        min_answer_length: Minimum character length for valid answers
        include_separator: Include visual separator between questions
        
    Returns:
        Formatted string in exam standard format
    """
    if not text or not isinstance(text, str):
        raise ValueError("Invalid input text")
    
    question_text = _extract_question_text(text)
    answers = _extract_answers(text)
    
    # Filter answers by minimum length
    answers = [a for a in answers if len(a) >= min_answer_length]
    
    # Build output
    lines: List[str] = []
    
    if include_separator:
        lines.append('=' * 60)
    
    lines.append('FRAGE:')
    lines.append(question_text if question_text else '(Keine Frage erkannt)')
    lines.append('')
    lines.append('ERWARTETE ANTWORT:')
    
    # Always output exactly max_answers numbered lines
    for i in range(1, max_answers + 1):
        if i <= len(answers):
            lines.append(f'{i}) {answers[i-1]}')
        else:
            lines.append(f'{i}) ')
    
    if include_separator:
        lines.append('=' * 60)
    
    return '\n'.join(lines)


def parse_to_structured_format(text: str) -> FormattedQuestion:
    """
    Parse text into a structured FormattedQuestion object.
    
    Args:
        text: Raw text to parse
        
    Returns:
        FormattedQuestion object with extracted data
    """
    question_text = _extract_question_text(text)
    answers = _extract_answers(text)
    question_type = _detect_question_type(text)
    metadata = _extract_metadata(text)
    
    formatted = FormattedQuestion(
        question_text=question_text,
        answers=answers,
        question_type=question_type,
        metadata=metadata,
        original_text=text,
        validation_score=0.0  # Will be calculated
    )
    
    # Calculate validation score
    formatted.validation_score = _calculate_validation_score(formatted)
    
    return formatted


def batch_format_questions(
    texts: List[str],
    output_format: str = "standard",
    continue_on_error: bool = True,
    min_validation_score: float = 0.0
) -> Dict[str, any]:
    """
    Format multiple questions in batch with comprehensive error handling.
    
    Args:
        texts: List of raw question texts
        output_format: Output format ('standard', 'structured')
        continue_on_error: If True, continue processing on errors; if False, raise
        min_validation_score: Minimum validation score to include (0.0-1.0)
        
    Returns:
        Dictionary with:
            - 'formatted': List of successfully formatted questions
            - 'errors': List of dicts with 'index', 'text', 'error' keys
            - 'stats': Processing statistics
    """
    formatted_questions: List[FormattedQuestion] = []
    errors: List[Dict[str, any]] = []
    
    for i, text in enumerate(texts):
        try:
            # Validate input
            if not text or not isinstance(text, str):
                raise ValueError("Empty or invalid text input")
            
            if len(text.strip()) < 10:
                raise ValueError("Text too short (< 10 characters)")
            
            formatted = parse_to_structured_format(text)
            
            # Check minimum validation score
            if formatted.validation_score >= min_validation_score:
                formatted_questions.append(formatted)
                logger.debug(
                    f"Processed question {i+1}/{len(texts)}: "
                    f"score={formatted.validation_score:.2f}, "
                    f"type={formatted.question_type.value}"
                )
            else:
                logger.warning(
                    f"Question {i+1} below validation threshold: "
                    f"score={formatted.validation_score:.2f} < {min_validation_score}"
                )
                errors.append({
                    'index': i,
                    'text': text[:100],
                    'error': f'Validation score too low: {formatted.validation_score:.2f}'
                })
                
        except Exception as e:
            error_msg = f"Failed to format question {i+1}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            errors.append({
                'index': i,
                'text': text[:100] if text else "(empty)",
                'error': str(e)
            })
            
            if not continue_on_error:
                raise RuntimeError(f"Batch processing stopped at question {i+1}: {e}") from e
    
    # Calculate statistics
    stats = {
        'total': len(texts),
        'successful': len(formatted_questions),
        'failed': len(errors),
        'success_rate': len(formatted_questions) / len(texts) if texts else 0.0,
        'avg_validation_score': (
            sum(q.validation_score for q in formatted_questions) / len(formatted_questions)
            if formatted_questions else 0.0
        )
    }
    
    logger.info(
        f"Batch processing complete: {stats['successful']}/{stats['total']} successful "
        f"({stats['success_rate']:.1%}), avg_score={stats['avg_validation_score']:.2f}"
    )
    
    return {
        'formatted': formatted_questions,
        'errors': errors,
        'stats': stats
    }


def export_to_markdown(questions: List[FormattedQuestion], output_path: str) -> None:
    """
    Export formatted questions to Markdown file.
    
    Args:
        questions: List of formatted questions
        output_path: Output file path
    """
    lines: List[str] = []
    lines.append('# Medizinische Prüfungsfragen\n')
    lines.append(f'*Generiert: {len(questions)} Fragen*\n')
    
    for i, q in enumerate(questions, 1):
        lines.append(f'\n## Frage {i}\n')
        lines.append(f'**Typ:** {q.question_type.value}\n')
        
        if q.metadata:
            lines.append(f'**Metadaten:** {", ".join(f"{k}={v}" for k, v in q.metadata.items())}\n')
        
        lines.append(f'\n### Fragestellung\n')
        lines.append(f'{q.question_text}\n')
        
        if q.answers:
            lines.append(f'\n### Erwartete Antwort\n')
            for j, answer in enumerate(q.answers, 1):
                lines.append(f'{j}. {answer}\n')
        
        lines.append(f'\n*Qualitätsscore: {q.validation_score:.2%}*\n')
        lines.append('\n---\n')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    logger.info(f'Exported {len(questions)} questions to {output_path}')


def export_to_anki_csv(questions: List[FormattedQuestion], output_path: str) -> None:
    """
    Export formatted questions to Anki-compatible CSV.
    
    Args:
        questions: List of formatted questions
        output_path: Output CSV file path
    """
    import csv
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Front', 'Back', 'Tags'])
        
        for q in questions:
            front = q.question_text
            back = '<br>'.join(f'{i+1}. {ans}' for i, ans in enumerate(q.answers))
            tags = f"{q.question_type.value} {' '.join(q.metadata.values())}"
            
            writer.writerow([front, back, tags])
    
    logger.info(f'Exported {len(questions)} questions to Anki CSV: {output_path}')
