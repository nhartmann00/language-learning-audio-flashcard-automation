# test_trim_silence.py
"""
Batch test of silence trimming across all 100 lessons.
Converts MP3 → trimmed WAV → Whisper transcript, saved to transcripts_trimmed/.
"""
import os
import whisper
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from src.audio_converter import mp3_to_wav
from src.transcript_cleaner import clean_transcript

MP3_DIR        = "data/raw_audio"
WAV_DIR        = "data/processed_audio"
TRANSCRIPT_DIR = "data/transcripts_trimmed"
MODEL_SIZE     = "small"
LANGUAGE       = "fr"

os.makedirs(WAV_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# ── 1. Find all lesson MP3s ───────────────────────────────────────────────────
mp3_files = sorted([f for f in os.listdir(MP3_DIR) if f.endswith(".mp3")])
print(f"Found {len(mp3_files)} MP3 files\n")

# ── 2. Load Whisper once ──────────────────────────────────────────────────────
print(f"Loading Whisper model '{MODEL_SIZE}'...")
model = whisper.load_model(MODEL_SIZE)
print()

# ── 3. Process each lesson ────────────────────────────────────────────────────
successes, failures = [], []

for i, mp3_file in enumerate(mp3_files, 1):
    lesson_name = mp3_file.replace(".mp3", "")
    mp3_path    = os.path.join(MP3_DIR, mp3_file)
    wav_path    = os.path.join(WAV_DIR, f"{lesson_name}.wav")
    txt_path    = os.path.join(TRANSCRIPT_DIR, f"{lesson_name}.txt")

    print(f"[{i:>3}/{len(mp3_files)}] {lesson_name}")

    try:
        # Convert + trim silence
        mp3_to_wav(mp3_path, wav_path, trim=True, silence_threshold_db=-40)

        # Transcribe
        result = model.transcribe(wav_path, language=LANGUAGE, verbose=False,
                                  condition_on_previous_text=False)

        # Clean and save
        cleaned = clean_transcript(result["text"])
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        print(f"  ✓ Transcript saved → {txt_path}\n")
        successes.append(lesson_name)

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        failures.append((lesson_name, str(e)))

# ── 4. Summary ────────────────────────────────────────────────────────────────
print("=" * 70)
print("BATCH COMPLETE")
print("=" * 70)
print(f"✓ Succeeded: {len(successes)}/{len(mp3_files)}")

if failures:
    print(f"✗ Failed: {len(failures)}")
    for lesson, err in failures:
        print(f"  {lesson}: {err}")

print(f"\nTrimmed WAVs:   {WAV_DIR}")
print(f"Transcripts:    {TRANSCRIPT_DIR}")