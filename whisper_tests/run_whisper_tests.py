"""
Whisper Configuration Test Suite
Tests all 8 combinations of trim config (no_trim, 0ms, 150ms, 500ms) x Whisper model (small, medium).

Run from the project root:
    python whisper_tests/run_whisper_tests.py

Directory structure created under whisper_tests/:
  whisper_tests/
  ├── run_whisper_tests.py         ← this file
  ├── audio_no_trim/               # Control: original audio, full silence preserved
  ├── audio_trim_0ms/
  ├── audio_trim_150ms/
  ├── audio_trim_500ms/
  ├── transcripts_small_no_trim/
  ├── transcripts_small_0ms/
  ├── transcripts_small_150ms/
  ├── transcripts_small_500ms/
  ├── transcripts_medium_no_trim/
  ├── transcripts_medium_0ms/
  ├── transcripts_medium_150ms/
  └── transcripts_medium_500ms/
"""

import os
import sys
import time
import whisper

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Ensure project root is on the path so src imports work
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.audio_converter import mp3_to_wav
from src.transcriber import save_transcript

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

AUDIO_DIR  = os.path.join(PROJECT_ROOT, "data", "raw_audio")
TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))   # whisper_tests/

# None = control (no trimming at all); integers = tail_padding_ms after trim
PADDING_CONFIGS = [None, 0, 150, 500]
MODELS          = ["small", "medium"]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def config_label(padding_ms) -> str:
    """Return a filesystem-safe label for a padding config."""
    return "no_trim" if padding_ms is None else f"{padding_ms}ms"


# ─────────────────────────────────────────────
# PHASE 1: AUDIO PREPARATION
# ─────────────────────────────────────────────

def prepare_audio_directory(padding_ms) -> tuple[str, int, int]:
    """
    Convert all MP3s to WAVs using mp3_to_wav() from src.audio_converter.
    Each config gets its own subdirectory. Skips files already converted.

    padding_ms=None → control: no trimming, original silence fully preserved
    padding_ms=int  → trim trailing silence, keeping padding_ms ms of natural tail

    Returns:
        (output_dir, files_processed, files_skipped)
    """
    output_dir = os.path.join(TESTS_ROOT, f"audio_{config_label(padding_ms)}")
    os.makedirs(output_dir, exist_ok=True)

    mp3_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(".mp3")])

    if not mp3_files:
        print(f"  ⚠  No MP3 files found in {AUDIO_DIR}")
        return output_dir, 0, 0

    processed = 0
    skipped   = 0

    for mp3_file in mp3_files:
        wav_name = mp3_file.replace(".mp3", ".wav")
        wav_path = os.path.join(output_dir, wav_name)

        if os.path.exists(wav_path):
            skipped += 1
            continue

        mp3_path = os.path.join(AUDIO_DIR, mp3_file)

        try:
            if padding_ms is None:
                # Control condition: straight MP3 → WAV, no trimming whatsoever
                mp3_to_wav(mp3_path, wav_path, trim=False)
            else:
                mp3_to_wav(
                    mp3_path,
                    wav_path,
                    trim=True,
                    silence_threshold_db=-40,
                    tail_padding_ms=padding_ms
                )
            processed += 1

        except Exception as e:
            print(f"    ✗ Error processing {mp3_file}: {e}")

    return output_dir, processed, skipped


# ─────────────────────────────────────────────
# PHASE 2: TRANSCRIPTION
# ─────────────────────────────────────────────

def transcribe_directory(model, audio_dir: str, output_dir: str) -> tuple[int, int, list]:
    """
    Transcribe all WAVs in audio_dir using the provided Whisper model.
    Saves one .txt per file via save_transcript(). Skips already-transcribed files.

    Returns:
        (successes, skipped, failures)
    """
    os.makedirs(output_dir, exist_ok=True)

    wav_files = sorted([f for f in os.listdir(audio_dir) if f.lower().endswith(".wav")])

    successes = 0
    skipped   = 0
    failures  = []

    for wav_file in wav_files:
        txt_path = os.path.join(output_dir, wav_file.replace(".wav", ".txt"))

        if os.path.exists(txt_path):
            skipped += 1
            continue

        wav_path = os.path.join(audio_dir, wav_file)

        try:
            result = model.transcribe(
                wav_path,
                language="fr",
                verbose=False,
                word_timestamps=True,
                condition_on_previous_text=False
            )

            save_transcript(result, txt_path)
            successes += 1

        except Exception as e:
            failures.append((wav_file, str(e)))

    return successes, skipped, failures


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 70)
    print("WHISPER CONFIGURATION TEST SUITE")
    print(f"Padding configs : {PADDING_CONFIGS} (None = control, no trim)")
    print(f"Whisper models  : {MODELS}")
    print(f"Audio source    : {AUDIO_DIR}")
    print(f"Output root     : {TESTS_ROOT}")
    print("=" * 70)

    # ── PHASE 1: Audio preparation ────────────────────────────────────────
    print("\n── PHASE 1: Audio preparation ──────────────────────────────────────")

    audio_dirs = {}  # padding_ms → path to WAV directory

    for padding_ms in PADDING_CONFIGS:
        label = config_label(padding_ms)
        print(f"\n  Config = {label}")
        audio_dir, processed, skipped = prepare_audio_directory(padding_ms)
        audio_dirs[padding_ms] = audio_dir

        if processed == 0 and skipped > 0:
            print(f"    ✓ All {skipped} files already processed — skipping")
        else:
            print(f"    ✓ Processed: {processed}  |  Skipped (existing): {skipped}")
            print(f"    → {audio_dir}")

    # ── PHASE 2: Transcription ────────────────────────────────────────────
    print("\n── PHASE 2: Transcription ───────────────────────────────────────────")

    total_start = time.time()
    run_summary = []

    for model_size in MODELS:
        print(f"\n  Loading Whisper model '{model_size}'...")
        model = whisper.load_model(model_size)
        print(f"  ✓ Model loaded")

        for padding_ms in PADDING_CONFIGS:
            label          = config_label(padding_ms)
            run_label      = f"{model_size}_{label}"
            transcript_dir = os.path.join(TESTS_ROOT, f"transcripts_{run_label}")

            print(f"\n  [{run_label}] Transcribing...")

            t_start = time.time()
            successes, skipped, failures = transcribe_directory(
                model,
                audio_dirs[padding_ms],
                transcript_dir
            )
            elapsed = time.time() - t_start

            status = "✓" if not failures else "⚠"
            print(f"  {status} Done in {elapsed:.1f}s  |  New: {successes}  Skipped: {skipped}  Failed: {len(failures)}")

            if failures:
                for fname, err in failures:
                    print(f"      ✗ {fname}: {err}")

            run_summary.append({
                "config" : run_label,
                "new"    : successes,
                "skipped": skipped,
                "failed" : len(failures),
                "time_s" : round(elapsed, 1),
            })

        del model  # Free memory before loading next model

    # ── SUMMARY TABLE ─────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Config':<32} {'New':>5} {'Skip':>5} {'Fail':>5} {'Time':>8}")
    print("-" * 70)

    for r in run_summary:
        flag = " ⚠" if r["failed"] else ""
        print(
            f"  {r['config']:<30} {r['new']:>5} {r['skipped']:>5} {r['failed']:>5} "
            f"{r['time_s']:>7.1f}s{flag}"
        )

    print("-" * 70)
    print(f"Total wall time: {total_elapsed / 60:.1f} min")
    print()
    print("Next steps:")
    print("  1. Compare transcripts across configs for hallucination frequency")
    print("  2. Check for Chinese characters / fabricated sentences in no_trim + 500ms configs")
    print("  3. Check for end-of-sentence clipping in 0ms config")
    print("  4. Ideal config = lowest hallucination rate + no clipping")
    print("=" * 70)


if __name__ == "__main__":
    main()