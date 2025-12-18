#!/usr/bin/env python3
"""
Script to analyze answer files from GPT-5.1 run to identify empty answers,
server errors, and malformed responses.
"""

import argparse
import json
import os


def analyze_answer_files(input_path=None):
    """
    Analyze answer files.
    If input_path is provided, analyze that specific file.
    Otherwise, analyze all answer files in medexam_batch/answers/ directory.
    """
    report = {
        "summary": {
            "total_files": 0,
            "total_entries": 0,
            "problematic_entries": 0,
            "empty_answers": 0,
            "server_errors": 0,
            "short_answers": 0,
        },
        "files": [],
        "problematic_entries": [],
    }

    files_to_process = []

    if input_path:
        if os.path.isfile(input_path):
            files_to_process.append((os.path.basename(input_path), input_path))
        else:
            print(f"Error: Input file {input_path} not found.")
            return report
    else:
        answers_dir = "medexam_batch/answers"
        # Get all answer files
        if os.path.exists(answers_dir):
            answer_files = [
                f for f in os.listdir(answers_dir) if f.endswith("_answers.json")
            ]
            answer_files.sort()
            for filename in answer_files:
                files_to_process.append((filename, os.path.join(answers_dir, filename)))
        else:
            print(f"Warning: Directory {answers_dir} not found.")

    for filename, file_path in files_to_process:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Ensure data is a list
            if not isinstance(data, list):
                print(
                    f"Error: {filename} - expected list, " f"got {type(data).__name__}"
                )
                continue

            file_report = {
                "filename": filename,
                "entries": len(data),
                "problematic_entries": 0,
                "empty_answers": 0,
                "server_errors": 0,
                "short_answers": 0,
            }

            # Update summary
            report["summary"]["total_files"] += 1
            report["summary"]["total_entries"] += len(data)

            # Analyze each entry
            for entry in data:
                # Skip if entry is not a dictionary
                if not isinstance(entry, dict):
                    print(f"Warning: {filename} - entry not dict, skipping")
                    continue

                is_problematic = False
                reason = []

                # Check for empty answer (None, empty string, whitespace only)
                if "antwort" not in entry or entry["antwort"] is None:
                    is_problematic = True
                    reason.append("empty_answer")
                    report["summary"]["empty_answers"] += 1
                    file_report["empty_answers"] += 1
                elif isinstance(entry["antwort"], str):
                    answer_clean = entry["antwort"].strip()
                    if not answer_clean:  # Whitespace-only answer
                        is_problematic = True
                        reason.append("empty_answer")
                        report["summary"]["empty_answers"] += 1
                        file_report["empty_answers"] += 1
                # Check for malformed JSON responses or other non-string
                # server errors
                elif not isinstance(entry["antwort"], str):
                    # If answer is not a string, it might be malformed
                    is_problematic = True
                    reason.append("server_error")
                    report["summary"]["server_errors"] += 1
                    file_report["server_errors"] += 1

                # Check for server error indicators (more specific to avoid
                # false positives with medical terms)
                if isinstance(entry["antwort"], str):
                    answer_lower = entry["antwort"].lower()
                    # More specific server error indicators
                    # with medical terms
                    server_error_indicators = [
                        "server error",
                        "internal server error",
                        "http 500",
                        "500 error",
                        "unable to process",
                        "cannot process request",
                        "technical issue",
                        "service unavailable",
                        "connection error",
                        "timeout error",
                        "api error",
                        "backend error",
                    ]
                    # Medical term exclusion list to avoid false positives
                    medical_term_exclusions = [
                        "error in",
                        "fehler in",
                        "thrombozytopenie",
                        "vitamin k",
                        "medication error",
                        "diagnostic error",
                        "human error",
                    ]

                    # Check for server error indicators that are not part of
                    # medical terms
                    for indicator in server_error_indicators:
                        if indicator in answer_lower and not any(
                            exclusion in answer_lower
                            for exclusion in medical_term_exclusions
                        ):
                            is_problematic = True
                            reason.append("server_error")
                            report["summary"]["server_errors"] += 1
                            file_report["server_errors"] += 1
                            break

                # Check for very short answers (potential empty/placeholder)
                # - separate check
                if isinstance(entry["antwort"], str):
                    answer_clean = entry["antwort"].strip()
                    # Adjust threshold to 30 characters to account for short
                    # but substantive answers
                    if len(answer_clean) < 30:
                        placeholder_indicators = [
                            "",
                            "Keine Antwort",
                            "N/A",
                            "Keine Frage vorhanden",
                            "Keine Frage angegeben",
                            "keine frage",
                            "keine antwort",
                            "kein inhalt",
                            "keine",
                            "unbekannt",
                            "nicht bekannt",
                            "k.a.",
                            "k. a.",
                            "entfällt",
                            "n/a",
                        ]
                        # Check if the short answer is actually a placeholder
                        if answer_clean in placeholder_indicators or any(
                            indicator in answer_clean.lower()
                            for indicator in placeholder_indicators
                        ):
                            is_problematic = True
                            reason.append("short_answer")
                            report["summary"]["short_answers"] += 1
                            file_report["short_answers"] += 1
                        # Also check for very short non-placeholder answers
                        # that might be legitimate
                        elif len(answer_clean) < 10 and answer_clean not in [
                            "Ja",
                            "Nein",
                            "ja",
                            "nein",
                        ]:
                            # Very short answers that are not simple yes/no
                            # could be problematic
                            is_problematic = True
                            reason.append("short_answer")
                            report["summary"]["short_answers"] += 1
                            file_report["short_answers"] += 1

                if is_problematic:
                    report["summary"]["problematic_entries"] += 1
                    file_report["problematic_entries"] += 1

                    # Extract question text
                    question_text = entry.get("frage", "Keine Frage angegeben")
                    if not question_text or question_text.strip() == "":
                        question_text = "Keine Frage angegeben"

                    problematic_entry = {
                        "file": filename,
                        "index": entry.get("index", "N/A"),
                        "question_id": entry.get("index", "N/A"),
                        "question_text": question_text,
                        "answer_text": str(entry.get("antwort", "")),
                        "reasons": reason,
                        "evidenzgrad": entry.get("evidenzgrad", "N/A"),
                        "leitlinie": entry.get("leitlinie", "N/A"),
                    }
                    report["problematic_entries"].append(problematic_entry)

            report["files"].append(file_report)

        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            continue

    return report


def save_report(report, output_path):
    """Save the report to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze answer files for quality issues."
    )
    parser.add_argument("--input", help="Path to a specific input file to analyze.")
    args = parser.parse_args()

    print("Analyzing answer files...")
    report = analyze_answer_files(input_path=args.input)

    if args.input:
        output_path = "medexam_batch/quality_report_single.json"
    else:
        output_path = "medexam_batch/missing_answers_report.json"

    save_report(report, output_path)
    print(f"Analysis complete. Report saved to {output_path}")

    # Print summary
    summary = report["summary"]
    print("\nSummary:")
    print(f"Total files analyzed: {summary['total_files']}")
    print(f"Total entries analyzed: {summary['total_entries']}")
    print(f"Problematic entries found: {summary['problematic_entries']}")
    print(f"  - Empty answers: {summary['empty_answers']}")
    print(f"  - Server errors: {summary['server_errors']}")
    print(f"  - Short/placeholder answers: {summary['short_answers']}")
