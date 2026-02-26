"""
Batch transcript cleaner.
Runs clean_transcript() on all lesson transcripts and saves cleaned versions.
"""

import os
import sys

# Add project root to path so src imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.transcript_cleaner import clean_transcript

# Configuration
INPUT_DIR = "data/whisper_transcripts" # Raw Whisper transcripts
OUTPUT_DIR = "data/transcripts_clean"  # Cleaned output


def batch_clean_transcripts(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Find all transcript files
    txt_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])

    if not txt_files:
        print(f"No .txt files found in {input_dir}")
        return

    print(f"Found {len(txt_files)} transcript(s) to clean")
    print(f"Output directory: {output_dir}\n")
    print("=" * 60)

    success = 0
    errors = 0

    for i, filename in enumerate(txt_files, 1):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            cleaned_text = clean_transcript(raw_text)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)

            print(f"[{i:>3}/{len(txt_files)}] ✓ {filename}")
            success += 1

        except Exception as e:
            print(f"[{i:>3}/{len(txt_files)}] ✗ {filename} — ERROR: {e}")
            errors += 1

    # Summary
    print("=" * 60)
    print(f"\n✓ Done! {success} cleaned, {errors} failed")
    print(f"Cleaned transcripts saved to: {output_dir}")


def preview_diff(input_dir, output_dir, filename):
    """
    Print a before/after preview for a single file. Useful for spot-checking.
    """
    input_path = os.path.join(input_dir, filename)
    output_path = os.path.join(output_dir, filename)

    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()
    with open(output_path, "r", encoding="utf-8") as f:
        cleaned = f.read()

    print(f"\n--- BEFORE ({filename}) ---")
    print(raw[:300])
    print(f"\n--- AFTER ({filename}) ---")
    print(cleaned[:300])


if __name__ == "__main__":
    batch_clean_transcripts(INPUT_DIR, OUTPUT_DIR)

    # Optional: spot-check the first file to verify output looks right
    txt_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")])
    if txt_files:
        print()
        preview_diff(INPUT_DIR, OUTPUT_DIR, txt_files[0])