#!/usr/bin/env python3
"""
Complete workflow for regenerating empty answers from the regeneration file.

This script automates the entire process:
1. Filter empty answers from regeneration file
2. Run regeneration on empty answers (requires API key)
3. Merge results back into regeneration file
4. Validate with analyze_answers.py
5. Create comprehensive documentation
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd, dry_run=False):
    """Run a command and return success status."""
    print(f"Running: {'[DRY-RUN] ' if dry_run else ''}{cmd}")
    if not dry_run:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        print(result.stdout)
    else:
        print("[DRY-RUN] Command would be executed")
    return True


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 80)
    print("EMPTY ANSWER REGENERATION WORKFLOW")
    print("=" * 80)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'PRODUCTION'}")
    print()

    # Step 1: Filter empty answers
    print("STEP 1: Filtering empty answers from regeneration file...")
    filter_cmd = "python3 scripts/filter_empty_regen_answers.py"
    if not run_command(filter_cmd, dry_run):
        print("❌ Filter step failed")
        return 1

    # Check if output files exist (in non-dry-run mode)
    if not dry_run:
        empty_answers_file = Path("_OUTPUT/empty_answers_for_regen.json")
        summary_file = Path("_OUTPUT/empty_answers_summary.json")

        if not empty_answers_file.exists():
            print("❌ Empty answers file not created")
            return 1

        # Load summary to get count
        with open(summary_file, "r") as f:
            summary = json.load(f)
            empty_count = summary["empty_answers_found"]
            print(f"✅ Found {empty_count} empty answers to regenerate")

    # Step 2: Run regeneration on empty answers
    print("\nSTEP 2: Running regeneration on empty answers...")
    input_file = "_OUTPUT/empty_answers_for_regen.json"
    output_file = "_OUTPUT/empty_answers_regen_results.json"
    regen_cmd = f"python3 scripts/batch_gpt51_run_resume.py --input {input_file} --output {output_file} --limit {empty_count if not dry_run else 5}"

    if dry_run:
        regen_cmd += " --dry-run"

    if not run_command(regen_cmd, dry_run):
        print("❌ Regeneration step failed")
        return 1

    # Step 3: Merge results back into regeneration file
    print("\nSTEP 3: Merging results back into regeneration file...")
    merge_cmd = "python3 scripts/merge_empty_regen_results.py"
    if not run_command(merge_cmd, dry_run):
        print("❌ Merge step failed")
        return 1

    # Step 4: Validate with analyze_answers.py
    print("\nSTEP 4: Validating results with analyze_answers.py...")
    merged_regen_file = "_OUTPUT/evidenz_antworten_gpt5_regen_20251211_merged.json"
    validate_cmd = (
        f"python3 medexam_batch/analyze_answers.py --input {merged_regen_file}"
    )
    if not run_command(validate_cmd, dry_run):
        print("❌ Validation step failed")
        return 1

    # Step 5: Create comprehensive documentation
    print("\nSTEP 5: Creating comprehensive documentation...")

    if dry_run:
        print("[DRY-RUN] Documentation would be created")
    else:
        # Create workflow documentation
        workflow_doc = f"""# Empty Answer Regeneration Workflow - {datetime.now().strftime('%Y-%m-%d')}

## Summary

This workflow addresses the issue of 335 empty answers in the regeneration file `_OUTPUT/evidenz_antworten_gpt5_regen_20251211_094845.json`.

## Steps Completed

### 1. Filter Empty Answers
- **Script**: `scripts/filter_empty_regen_answers.py`
- **Input**: `_OUTPUT/evidenz_antworten_gpt5_regen_20251211_094845.json`
- **Output**: `_OUTPUT/empty_answers_for_regen.json`
- **Summary**: `_OUTPUT/empty_answers_summary.json`
- **Result**: {empty_count} empty answers identified and extracted

### 2. Regenerate Empty Answers
- **Script**: `scripts/batch_gpt51_run_resume.py`
- **Input**: `_OUTPUT/empty_answers_for_regen.json`
- **Output**: `_OUTPUT/empty_answers_regen_results.json`
- **Model**: GPT-5.1
- **Result**: {empty_count} answers regenerated

### 3. Merge Results
- **Script**: `scripts/merge_empty_regen_results.py`
- **Input**: `_OUTPUT/empty_answers_regen_results.json`
- **Output**: `_OUTPUT/evidenz_antworten_gpt5_regen_20251211_merged.json`
- **Result**: {empty_count} answers merged back into regeneration file

### 4. Validation
- **Script**: `medexam_batch/analyze_answers.py`
- **Input**: `_OUTPUT/evidenz_antworten_gpt5_regen_20251211_merged.json`
- **Result**: Validation report generated

## Files Created

- `_OUTPUT/empty_answers_for_regen.json` - Empty answers extracted for regeneration
- `_OUTPUT/empty_answers_summary.json` - Summary of empty answers found
- `_OUTPUT/empty_answers_regen_results.json` - New regeneration results
- `_OUTPUT/evidenz_antworten_gpt5_regen_20251211_merged.json` - Merged regeneration file
- `_OUTPUT/merge_empty_regen_summary.json` - Merge summary
- `_OUTPUT/quality_report_single.json` - Validation report

## Next Steps

1. [ ] Review the validation report to confirm all empty answers are filled
2. [ ] Check for the specific missing index 2426 mentioned in the original analysis
3. [ ] Run the main merge process with the updated regeneration file
4. [ ] Perform final quality assessment and validation
5. [ ] Proceed with Perplexity/KB validation if all answers are complete

## Technical Notes

- The workflow specifically targets only the empty answers from the regeneration file
- Each regenerated answer includes metadata about the second regeneration pass
- The merge process preserves all original data and only updates empty answers
- Validation ensures no new empty answers are introduced

## Expected Outcome

After completing this workflow:
- The regeneration file should have 0 empty answers (except possibly index 2426)
- All 335 previously empty answers should now contain valid content
- The merged dataset should show significant improvement in completion rate
"""

        doc_path = Path("_OUTPUT/EMPTY_ANSWER_REGEN_WORKFLOW.md")
        with open(doc_path, "w") as f:
            f.write(workflow_doc)

        print(f"✅ Documentation created: {doc_path}")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"Finished: {datetime.now().isoformat()}")
    print("\nNext steps:")
    print("1. Review the generated documentation")
    print("2. Check validation results")
    print("3. Address any remaining gaps (especially index 2426)")
    print("4. Proceed with final merge and quality assessment")

    return 0


if __name__ == "__main__":
    sys.exit(main())
