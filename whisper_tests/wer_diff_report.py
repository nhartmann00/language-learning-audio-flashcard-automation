"""
WER Word-Level Diff Report
Shows exact word differences between ground truth and all 8 Whisper configs.

Run from the project root:
    python whisper_tests/wer_diff_report.py

Output:
    whisper_tests/wer_results/diffs/          — one .txt per config with side-by-side diffs
    whisper_tests/wer_results/all_errors.csv  — every S/I/D with the actual words involved
    Console summary of most common error patterns
"""

import os
import sys
import csv
from collections import Counter

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from jiwer import process_words

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
GROUND_TRUTH_DIR = os.path.join(TESTS_ROOT, "transcripts_manual")
RESULTS_DIR = os.path.join(TESTS_ROOT, "wer_results")
DIFFS_DIR = os.path.join(RESULTS_DIR, "diffs")

CONFIGS = [
    "small_no_trim",
    "small_0ms",
    "small_150ms",
    "small_500ms",
    "medium_no_trim",
    "medium_0ms",
    "medium_150ms",
    "medium_500ms",
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def load_transcript(filepath):
    """Load transcript text, or None if missing."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


def extract_word_ops(reference, hypothesis):
    """
    Use jiwer's alignment to extract every operation with the actual words.

    Returns list of dicts:
        {'type': 'S'|'I'|'D'|'ok', 'ref': str|None, 'hyp': str|None}
    """
    output = process_words(reference, hypothesis)

    ref_words = reference.split()
    hyp_words = hypothesis.split()

    ops = []

    for chunk in output.alignments[0]:
        if chunk.type == "equal":
            for i in range(chunk.ref_end_idx - chunk.ref_start_idx):
                ops.append({
                    "type": "ok",
                    "ref": ref_words[chunk.ref_start_idx + i],
                    "hyp": hyp_words[chunk.hyp_start_idx + i],
                })
        elif chunk.type == "substitute":
            for i in range(chunk.ref_end_idx - chunk.ref_start_idx):
                ops.append({
                    "type": "S",
                    "ref": ref_words[chunk.ref_start_idx + i],
                    "hyp": hyp_words[chunk.hyp_start_idx + i],
                })
        elif chunk.type == "delete":
            for i in range(chunk.ref_end_idx - chunk.ref_start_idx):
                ops.append({
                    "type": "D",
                    "ref": ref_words[chunk.ref_start_idx + i],
                    "hyp": None,
                })
        elif chunk.type == "insert":
            for i in range(chunk.hyp_end_idx - chunk.hyp_start_idx):
                ops.append({
                    "type": "I",
                    "ref": None,
                    "hyp": hyp_words[chunk.hyp_start_idx + i],
                })

    return ops


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    os.makedirs(DIFFS_DIR, exist_ok=True)

    lesson_files = sorted([f for f in os.listdir(GROUND_TRUTH_DIR) if f.endswith(".txt")])
    print(f"Found {len(lesson_files)} ground truth transcripts")
    print(f"Generating diffs for {len(CONFIGS)} configs\n")

    # Collect all errors for the CSV
    all_errors = []

    for config in CONFIGS:
        print(f"── {config} ──")

        diff_path = os.path.join(DIFFS_DIR, f"{config}_diffs.txt")
        config_errors = 0

        with open(diff_path, "w", encoding="utf-8") as diff_file:
            diff_file.write(f"WORD-LEVEL DIFFS: {config}\n")
            diff_file.write(f"Ground truth: {GROUND_TRUTH_DIR}\n")
            diff_file.write(f"Hypothesis:   transcripts_{config}/\n")
            diff_file.write("=" * 80 + "\n\n")

            for lesson_file in lesson_files:
                lesson_name = lesson_file.replace(".txt", "")
                gt_text = load_transcript(os.path.join(GROUND_TRUTH_DIR, lesson_file))
                hyp_text = load_transcript(
                    os.path.join(TESTS_ROOT, f"transcripts_{config}", lesson_file)
                )

                if not gt_text or hyp_text is None:
                    continue

                if not hyp_text:
                    diff_file.write(f"\n{'─' * 80}\n")
                    diff_file.write(f"{lesson_name}  —  EMPTY HYPOTHESIS (all words deleted)\n")
                    diff_file.write(f"{'─' * 80}\n")
                    continue

                ops = extract_word_ops(gt_text, hyp_text)

                # Count errors for this lesson
                lesson_errors = [op for op in ops if op["type"] != "ok"]

                if not lesson_errors:
                    continue  # Perfect match, skip

                config_errors += len(lesson_errors)

                # Write lesson header
                n_sub = sum(1 for op in lesson_errors if op["type"] == "S")
                n_ins = sum(1 for op in lesson_errors if op["type"] == "I")
                n_del = sum(1 for op in lesson_errors if op["type"] == "D")

                diff_file.write(f"\n{'─' * 80}\n")
                diff_file.write(
                    f"{lesson_name}  —  S={n_sub} I={n_ins} D={n_del}  "
                    f"({len(ops)} words total)\n"
                )
                diff_file.write(f"{'─' * 80}\n")

                # Write each error with surrounding context
                for i, op in enumerate(ops):
                    if op["type"] == "ok":
                        continue

                    # Get context: 3 words before and after
                    ctx_before = []
                    for j in range(max(0, i - 3), i):
                        if ops[j]["type"] == "ok":
                            ctx_before.append(ops[j]["ref"])
                        elif ops[j]["type"] == "S":
                            ctx_before.append(f"[{ops[j]['ref']}]")

                    ctx_after = []
                    for j in range(i + 1, min(len(ops), i + 4)):
                        if ops[j]["type"] == "ok":
                            ctx_after.append(ops[j]["ref"])
                        elif ops[j]["type"] == "S":
                            ctx_after.append(f"[{ops[j]['ref']}]")

                    context_str = " ".join(ctx_before) + " ___ " + " ".join(ctx_after)

                    if op["type"] == "S":
                        diff_file.write(
                            f"  SUB: '{op['ref']}' → '{op['hyp']}'  "
                            f"  context: ...{context_str}...\n"
                        )
                    elif op["type"] == "I":
                        diff_file.write(
                            f"  INS: +'{op['hyp']}'  "
                            f"  context: ...{context_str}...\n"
                        )
                    elif op["type"] == "D":
                        diff_file.write(
                            f"  DEL: -'{op['ref']}'  "
                            f"  context: ...{context_str}...\n"
                        )

                    # Add to master error list
                    all_errors.append({
                        "config": config,
                        "lesson": lesson_name,
                        "type": op["type"],
                        "ref_word": op["ref"] or "",
                        "hyp_word": op["hyp"] or "",
                    })

        print(f"  ✓ {config_errors} errors → {diff_path}")

    # ── Save all errors CSV ───────────────────────────────────────────────
    errors_path = os.path.join(RESULTS_DIR, "all_errors.csv")
    with open(errors_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["config", "lesson", "type", "ref_word", "hyp_word"])
        writer.writeheader()
        writer.writerows(all_errors)

    print(f"\n✓ All errors saved to {errors_path} ({len(all_errors)} total)")

    # ── Most common error patterns ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("MOST COMMON SUBSTITUTION PATTERNS (across all configs)")
    print("=" * 80)

    sub_pairs = Counter()
    for err in all_errors:
        if err["type"] == "S":
            sub_pairs[(err["ref_word"], err["hyp_word"])] += 1

    print(f"\n{'Count':>6}  {'Ground Truth':<25} {'Whisper Output':<25}")
    print("-" * 60)
    for (ref, hyp), count in sub_pairs.most_common(30):
        print(f"  {count:>4}   {ref:<25} {hyp:<25}")

    # ── Most common insertions ────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("MOST COMMON INSERTIONS (across all configs)")
    print("=" * 80)

    ins_words = Counter()
    for err in all_errors:
        if err["type"] == "I":
            ins_words[err["hyp_word"]] += 1

    print(f"\n{'Count':>6}  {'Inserted Word':<30}")
    print("-" * 40)
    for word, count in ins_words.most_common(20):
        print(f"  {count:>4}   {word}")

    # ── Most common deletions ─────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("MOST COMMON DELETIONS (across all configs)")
    print("=" * 80)

    del_words = Counter()
    for err in all_errors:
        if err["type"] == "D":
            del_words[err["ref_word"]] += 1

    print(f"\n{'Count':>6}  {'Deleted Word':<30}")
    print("-" * 40)
    for word, count in del_words.most_common(20):
        print(f"  {count:>4}   {word}")

    print(f"\n✓ Diff report complete!")
    print(f"  Per-config diffs:  {DIFFS_DIR}/")
    print(f"  All errors CSV:    {errors_path}")


if __name__ == "__main__":
    main()
