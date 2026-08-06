import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.transcript_cleaner import clean_transcript

TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))

CONFIGS = [
    "small_no_trim", "small_0ms", "small_150ms", "small_500ms",
    "medium_no_trim", "medium_0ms", "medium_150ms", "medium_500ms",
]

for config in CONFIGS:
    input_dir = os.path.join(TESTS_ROOT, f"transcripts_{config}")
    txt_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])

    print(f"\n── {config} ({len(txt_files)} files) ──")
    for filename in txt_files:
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        cleaned = clean_transcript(raw)
        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print(f"  ✓ {filename}")

print("\n✓ All configs cleaned.")