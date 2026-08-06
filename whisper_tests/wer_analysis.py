"""
WER Analysis: Ground Truth vs Whisper Configurations
Compares all 8 Whisper configs against manual ground truth transcripts.

Run from the project root:
    python whisper_tests/wer_analysis.py

Requires: pip install jiwer

Output:
    whisper_tests/wer_results/summary.csv       — per-lesson WER for all configs
    whisper_tests/wer_results/aggregate.csv      — overall stats per config
    whisper_tests/wer_results/worst_lessons.txt   — lessons with highest WER per config
    Console output with full analysis
"""

import os
import sys
import csv

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from jiwer import process_words

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))  # whisper_tests/
GROUND_TRUTH_DIR = os.path.join(TESTS_ROOT, "transcripts_manual")
RESULTS_DIR = os.path.join(TESTS_ROOT, "wer_results")

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
    """Load and return transcript text, or None if file doesn't exist."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_lesson_files():
    """Get sorted list of ground truth lesson filenames."""
    files = sorted([f for f in os.listdir(GROUND_TRUTH_DIR) if f.endswith(".txt")])
    return files


def compute_metrics(reference, hypothesis):
    """
    Compute WER and its components for a single lesson.

    Returns dict with:
        wer       — Word Error Rate (S + I + D) / N
        sub       — substitution count
        ins       — insertion count (hallucinations)
        del_      — deletion count (truncations)
        ref_len   — number of words in reference
        hyp_len   — number of words in hypothesis
    """
    output = process_words(reference, hypothesis)

    return {
        "wer": output.wer,
        "sub": output.substitutions,
        "ins": output.insertions,
        "del": output.deletions,
        "ref_len": len(reference.split()),
        "hyp_len": len(hypothesis.split()),
    }


# ─────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    lesson_files = get_lesson_files()
    print(f"Found {len(lesson_files)} ground truth transcripts")
    print(f"Comparing against {len(CONFIGS)} Whisper configurations\n")

    # ── Per-lesson results ────────────────────────────────────────────────
    # Structure: all_results[config][lesson_name] = metrics dict
    all_results = {config: {} for config in CONFIGS}
    missing_files = {config: [] for config in CONFIGS}

    for lesson_file in lesson_files:
        lesson_name = lesson_file.replace(".txt", "")
        gt_path = os.path.join(GROUND_TRUTH_DIR, lesson_file)
        gt_text = load_transcript(gt_path)

        if not gt_text:
            print(f"  ⚠ Empty ground truth: {lesson_file}")
            continue

        for config in CONFIGS:
            hyp_path = os.path.join(TESTS_ROOT, f"transcripts_{config}", lesson_file)
            hyp_text = load_transcript(hyp_path)

            if hyp_text is None:
                missing_files[config].append(lesson_name)
                continue

            if not hyp_text:
                # Empty hypothesis = 100% deletion
                all_results[config][lesson_name] = {
                    "wer": 1.0,
                    "sub": 0,
                    "ins": 0,
                    "del": len(gt_text.split()),
                    "ref_len": len(gt_text.split()),
                    "hyp_len": 0,
                }
                continue

            metrics = compute_metrics(gt_text, hyp_text)
            all_results[config][lesson_name] = metrics

    # ── Save per-lesson CSV ───────────────────────────────────────────────
    summary_path = os.path.join(RESULTS_DIR, "summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        header = ["lesson"]
        for config in CONFIGS:
            header.extend([
                f"{config}_wer",
                f"{config}_sub",
                f"{config}_ins",
                f"{config}_del",
                f"{config}_ref_len",
                f"{config}_hyp_len",
            ])
        writer.writerow(header)

        # Data rows
        for lesson_file in lesson_files:
            lesson_name = lesson_file.replace(".txt", "")
            row = [lesson_name]

            for config in CONFIGS:
                m = all_results[config].get(lesson_name)
                if m:
                    row.extend([
                        f"{m['wer']:.4f}",
                        m["sub"],
                        m["ins"],
                        m["del"],
                        m["ref_len"],
                        m["hyp_len"],
                    ])
                else:
                    row.extend(["", "", "", "", "", ""])

            writer.writerow(row)

    print(f"✓ Per-lesson results saved to {summary_path}")

    # ── Aggregate stats per config ────────────────────────────────────────
    print("\n" + "=" * 90)
    print("AGGREGATE RESULTS")
    print("=" * 90)
    print(
        f"{'Config':<25} {'Avg WER':>8} {'Med WER':>8} {'Max WER':>8} "
        f"{'Tot Sub':>8} {'Tot Ins':>8} {'Tot Del':>8} {'Lessons':>8}"
    )
    print("-" * 90)

    aggregate_rows = []

    for config in CONFIGS:
        results = all_results[config]
        if not results:
            print(f"  {config:<25} — no results")
            continue

        wers = [m["wer"] for m in results.values()]
        total_sub = sum(m["sub"] for m in results.values())
        total_ins = sum(m["ins"] for m in results.values())
        total_del = sum(m["del"] for m in results.values())
        total_ref = sum(m["ref_len"] for m in results.values())

        avg_wer = sum(wers) / len(wers)
        sorted_wers = sorted(wers)
        med_wer = sorted_wers[len(sorted_wers) // 2]
        max_wer = max(wers)
        overall_wer = (total_sub + total_ins + total_del) / total_ref if total_ref > 0 else 0

        print(
            f"  {config:<23} {avg_wer:>7.2%} {med_wer:>7.2%} {max_wer:>7.2%} "
            f"{total_sub:>8} {total_ins:>8} {total_del:>8} {len(results):>8}"
        )

        aggregate_rows.append({
            "config": config,
            "avg_wer": avg_wer,
            "median_wer": med_wer,
            "max_wer": max_wer,
            "overall_wer": overall_wer,
            "total_sub": total_sub,
            "total_ins": total_ins,
            "total_del": total_del,
            "total_ref_words": total_ref,
            "lessons_compared": len(results),
        })

    # Save aggregate CSV
    agg_path = os.path.join(RESULTS_DIR, "aggregate.csv")
    with open(agg_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=aggregate_rows[0].keys())
        writer.writeheader()
        writer.writerows(aggregate_rows)

    print(f"\n✓ Aggregate results saved to {agg_path}")

    # ── Worst lessons per config ──────────────────────────────────────────
    worst_path = os.path.join(RESULTS_DIR, "worst_lessons.txt")
    with open(worst_path, "w", encoding="utf-8") as f:
        for config in CONFIGS:
            results = all_results[config]
            if not results:
                continue

            # Sort by WER descending
            ranked = sorted(results.items(), key=lambda x: x[1]["wer"], reverse=True)
            top_10 = ranked[:10]

            header = f"\n{'=' * 70}\n{config.upper()} — TOP 10 WORST LESSONS\n{'=' * 70}\n"
            print(header, end="")
            f.write(header)

            for lesson_name, m in top_10:
                line = (
                    f"  {lesson_name:<20} WER={m['wer']:>7.2%}  "
                    f"S={m['sub']:>3} I={m['ins']:>3} D={m['del']:>3}  "
                    f"(ref={m['ref_len']} hyp={m['hyp_len']})\n"
                )
                print(line, end="")
                f.write(line)

    print(f"\n✓ Worst lessons saved to {worst_path}")

    # ── Missing files report ──────────────────────────────────────────────
    any_missing = any(v for v in missing_files.values())
    if any_missing:
        print("\n⚠ MISSING TRANSCRIPT FILES:")
        for config, missing in missing_files.items():
            if missing:
                print(f"  {config}: {len(missing)} missing — {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")

    # ── Quick recommendation ──────────────────────────────────────────────
    if aggregate_rows:
        print("\n" + "=" * 90)
        print("QUICK COMPARISON")
        print("=" * 90)

        best_avg = min(aggregate_rows, key=lambda x: x["avg_wer"])
        best_med = min(aggregate_rows, key=lambda x: x["median_wer"])
        lowest_ins = min(aggregate_rows, key=lambda x: x["total_ins"])
        lowest_del = min(aggregate_rows, key=lambda x: x["total_del"])

        print(f"  Lowest avg WER:        {best_avg['config']:<25} ({best_avg['avg_wer']:.2%})")
        print(f"  Lowest median WER:     {best_med['config']:<25} ({best_med['median_wer']:.2%})")
        print(f"  Fewest insertions:     {lowest_ins['config']:<25} ({lowest_ins['total_ins']} total)")
        print(f"  Fewest deletions:      {lowest_del['config']:<25} ({lowest_del['total_del']} total)")

    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
