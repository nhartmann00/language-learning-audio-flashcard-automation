"""
Language Learning Audio Flashcard Automation Pipeline

End-to-end pipeline that processes audio files, aligns them with transcripts,
extracts audio clips for specific phrases, and integrates them into Anki flashcards.

Usage:
    1. Set up config.json with your paths and settings
    2. Run: python main.py
    
Inputs:
    - Audio files (MP3 or WAV) containing dialogue/lesson audio
    - Anki CSV with target language phrases (and optional Source column)
    - Optional: manual transcripts for better alignment accuracy

Outputs:
    - Audio clips for each phrase in the CSV
    - Anki cards with audio attached (via AnkiConnect)
"""

import os
import sys
import json
import csv
import subprocess

from src.audio_converter import mp3_to_wav, trim_silence
from src.transcriber import transcribe_audio, save_transcript
from src.transcript_cleaner import clean_transcript
from src.textgrid_parser import parse_textgrid, find_phrase_timestamps
from src.audio_extractor import extract_audio_segment
from src.anki_integrator import AnkiConnector

from pydub import AudioSegment


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    "audio_dir": "data/raw_audio",
    "transcript_dir": "",
    "csv_path": "",
    "deck_name": "",
    "front_column": "Front",
    "back_column": "Back",
    "source_column": "Source",

    "processed_audio_dir": "data/processed_audio",
    "mfa_corpus_dir": "data/mfa_corpus",
    "mfa_output_dir": "data/mfa_output",
    "audio_clips_dir": "data/audio_clips",

    "mfa_dictionary": "french_mfa",
    "mfa_acoustic_model": "french_mfa",

    "whisper_model": "small",
    "language": "fr",
    "silence_threshold_db": -40,
    "tail_padding_ms": 150,
    "clip_padding_ms": 100,

    "anki_connect_url": "http://localhost:8765",
}


def load_config(config_path="config.json"):
    """Load config from JSON file, filling in defaults for missing keys."""
    if not os.path.exists(config_path):
        print(f"✗ Config file not found: {config_path}")
        print(f"  Creating template config.json — please fill in your settings and re-run.")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        user_config = json.load(f)

    # Merge with defaults
    config = {**DEFAULT_CONFIG, **user_config}
    return config


# ─────────────────────────────────────────────
# STEP 1: VALIDATE INPUTS
# ─────────────────────────────────────────────

def validate_inputs(config):
    """Check that all required inputs exist and dependencies are available."""
    print("=" * 70)
    print("STEP 1: Validating inputs")
    print("=" * 70)

    errors = []

    # Audio directory
    if not os.path.isdir(config["audio_dir"]):
        errors.append(f"Audio directory not found: {config['audio_dir']}")
    else:
        audio_files = [f for f in os.listdir(config["audio_dir"])
                       if f.lower().endswith((".mp3", ".wav"))]
        if not audio_files:
            errors.append(f"No MP3/WAV files found in {config['audio_dir']}")
        else:
            print(f"  ✓ Audio directory: {len(audio_files)} files found")

    # CSV
    if not config["csv_path"]:
        errors.append("csv_path is not set in config.json")
    elif not os.path.exists(config["csv_path"]):
        errors.append(f"CSV not found: {config['csv_path']}")
    else:
        print(f"  ✓ CSV: {config['csv_path']}")

    # Deck name
    if not config["deck_name"]:
        errors.append("deck_name is not set in config.json")
    else:
        print(f"  ✓ Deck name: {config['deck_name']}")

    # Transcript directory (optional)
    if config["transcript_dir"]:
        if os.path.isdir(config["transcript_dir"]):
            transcripts = [f for f in os.listdir(config["transcript_dir"])
                           if f.endswith(".txt")]
            print(f"  ✓ Manual transcripts: {len(transcripts)} files found")
        else:
            print(f"  ⚠ Transcript directory not found: {config['transcript_dir']}")
            print(f"    Will use Whisper for all files")
            config["transcript_dir"] = ""
    else:
        print(f"  ⚠ No transcript directory specified — will use Whisper for all files")

    # MFA
    try:
        result = subprocess.run(["mfa", "version"], capture_output=True, text=True)
        print(f"  ✓ MFA installed: {result.stdout.strip()}")
    except FileNotFoundError:
        errors.append("MFA is not installed or not in PATH. Install: https://montreal-forced-aligner.readthedocs.io/")

    # AnkiConnect
    try:
        import requests
        response = requests.post(config["anki_connect_url"],
                                 json={"action": "version", "version": 6})
        print(f"  ✓ AnkiConnect: connected (v{response.json().get('result', '?')})")
    except Exception:
        errors.append(f"Cannot connect to AnkiConnect at {config['anki_connect_url']}. "
                      f"Make sure Anki is open with AnkiConnect installed.")

    if errors:
        print(f"\n✗ {len(errors)} error(s) found:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print(f"\n✓ All inputs validated\n")
    return config


# ─────────────────────────────────────────────
# STEP 2: AUDIO CONVERSION
# ─────────────────────────────────────────────

def convert_audio(config):
    """Convert MP3 files to WAV with silence trimming. WAV files are trimmed in place."""
    print("=" * 70)
    print("STEP 2: Audio conversion")
    print("=" * 70)

    audio_dir = config["audio_dir"]
    output_dir = config["processed_audio_dir"]
    os.makedirs(output_dir, exist_ok=True)

    audio_files = sorted([f for f in os.listdir(audio_dir)
                          if f.lower().endswith((".mp3", ".wav"))])

    converted = 0
    skipped = 0

    for i, audio_file in enumerate(audio_files, 1):
        base_name = os.path.splitext(audio_file)[0]
        wav_output = os.path.join(output_dir, f"{base_name}.wav")

        # Skip if already processed
        if os.path.exists(wav_output):
            skipped += 1
            continue

        input_path = os.path.join(audio_dir, audio_file)
        print(f"  [{i}/{len(audio_files)}] {audio_file}")

        if audio_file.lower().endswith(".mp3"):
            mp3_to_wav(
                input_path, wav_output,
                trim=True,
                silence_threshold_db=config["silence_threshold_db"],
                tail_padding_ms=config["tail_padding_ms"]
            )
        else:
            # WAV input — load, trim silence, save to output dir
            audio = AudioSegment.from_wav(input_path)
            audio = trim_silence(
                audio,
                silence_threshold_db=config["silence_threshold_db"],
                tail_padding_ms=config["tail_padding_ms"]
            )
            audio.export(wav_output, format="wav")
            print(f"  ✓ Trimmed and saved: {wav_output}")

        converted += 1

    print(f"\n✓ Audio conversion complete: {converted} converted, {skipped} skipped\n")


# ─────────────────────────────────────────────
# STEP 3: TRANSCRIPTION
# ─────────────────────────────────────────────

def transcribe_files(config):
    """Transcribe audio files using Whisper, skipping those with manual transcripts."""
    print("=" * 70)
    print("STEP 3: Transcription")
    print("=" * 70)

    wav_dir = config["processed_audio_dir"]
    transcript_dir = config["transcript_dir"]

    # Collect manual transcripts if available
    manual_transcripts = set()
    if transcript_dir and os.path.isdir(transcript_dir):
        manual_transcripts = {os.path.splitext(f)[0] for f in os.listdir(transcript_dir)
                              if f.endswith(".txt")}
        print(f"  Found {len(manual_transcripts)} manual transcript(s)")

    wav_files = sorted([f for f in os.listdir(wav_dir) if f.lower().endswith(".wav")])
    needs_whisper = [f for f in wav_files
                     if os.path.splitext(f)[0] not in manual_transcripts]

    if not needs_whisper:
        print(f"  ✓ All {len(wav_files)} files have manual transcripts — skipping Whisper\n")
        return

    print(f"  {len(needs_whisper)} file(s) need Whisper transcription\n")

    # Load model once
    import whisper
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    print(f"  Loading Whisper model '{config['whisper_model']}'...")
    model = whisper.load_model(config["whisper_model"])

    # Create a whisper transcript directory if no transcript dir was specified
    if not transcript_dir:
        transcript_dir = "data/whisper_transcripts"
        config["transcript_dir"] = transcript_dir
    os.makedirs(transcript_dir, exist_ok=True)

    successes = 0
    failures = []

    for i, wav_file in enumerate(needs_whisper, 1):
        base_name = os.path.splitext(wav_file)[0]
        wav_path = os.path.join(wav_dir, wav_file)
        transcript_path = os.path.join(transcript_dir, f"{base_name}.txt")

        # Skip if already transcribed
        if os.path.exists(transcript_path):
            continue

        print(f"  [{i}/{len(needs_whisper)}] Transcribing {wav_file}...")

        try:
            result = model.transcribe(
                wav_path,
                language=config["language"],
                verbose=False,
                condition_on_previous_text=False
            )
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(result["text"])

            successes += 1
            print(f"    ✓ Saved to {transcript_path}")

        except Exception as e:
            failures.append((wav_file, str(e)))
            print(f"    ✗ Error: {e}")

    del model

    print(f"\n✓ Transcription complete: {successes} transcribed, {len(failures)} failed\n")

    if failures:
        print("  Failed files:")
        for fname, err in failures:
            print(f"    - {fname}: {err}")
        print()


# ─────────────────────────────────────────────
# STEP 4: TRANSCRIPT CLEANING + MFA CORPUS PREP
# ─────────────────────────────────────────────

def prepare_corpus(config):
    """Clean transcripts and prepare MFA corpus directory."""
    print("=" * 70)
    print("STEP 4: Transcript cleaning & MFA corpus preparation")
    print("=" * 70)

    wav_dir = config["processed_audio_dir"]
    transcript_dir = config["transcript_dir"]
    corpus_dir = config["mfa_corpus_dir"]
    os.makedirs(corpus_dir, exist_ok=True)

    import shutil

    wav_files = sorted([f for f in os.listdir(wav_dir) if f.lower().endswith(".wav")])

    prepared = 0
    skipped = 0

    for wav_file in wav_files:
        base_name = os.path.splitext(wav_file)[0]
        transcript_path = os.path.join(transcript_dir, f"{base_name}.txt")

        if not os.path.exists(transcript_path):
            print(f"  ⚠ No transcript for {wav_file} — skipping")
            skipped += 1
            continue

        # Read and clean transcript
        with open(transcript_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        cleaned_text = clean_transcript(raw_text)

        # Copy WAV to corpus
        shutil.copy2(
            os.path.join(wav_dir, wav_file),
            os.path.join(corpus_dir, wav_file)
        )

        # Save cleaned transcript to corpus
        with open(os.path.join(corpus_dir, f"{base_name}.txt"), "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        prepared += 1

    print(f"\n✓ Corpus ready: {prepared} files prepared, {skipped} skipped")
    print(f"  Location: {corpus_dir}\n")


# ─────────────────────────────────────────────
# STEP 5: MFA ALIGNMENT
# ─────────────────────────────────────────────

def run_mfa_alignment(config):
    """Run Montreal Forced Aligner on the prepared corpus."""
    print("=" * 70)
    print("STEP 5: MFA alignment")
    print("=" * 70)

    corpus_dir = config["mfa_corpus_dir"]
    output_dir = config["mfa_output_dir"]
    dictionary = config["mfa_dictionary"]
    acoustic_model = config["mfa_acoustic_model"]

    # Check if TextGrids already exist
    existing = [f for f in os.listdir(output_dir) if f.endswith(".TextGrid")] \
        if os.path.exists(output_dir) else []
    corpus_wavs = [f for f in os.listdir(corpus_dir) if f.endswith(".wav")]

    if len(existing) >= len(corpus_wavs) and len(existing) > 0:
        print(f"  ✓ {len(existing)} TextGrid(s) already exist — skipping alignment")
        print(f"    Delete {output_dir} to force re-alignment\n")
        return

    cmd = ["mfa", "align", "--clean", corpus_dir, dictionary, acoustic_model, output_dir]
    print(f"  Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            textgrids = [f for f in os.listdir(output_dir) if f.endswith(".TextGrid")]
            print(f"\n✓ MFA alignment complete: {len(textgrids)} TextGrid(s) created")

            if len(textgrids) < len(corpus_wavs):
                missing = set(f.replace(".wav", ".TextGrid") for f in corpus_wavs) - set(textgrids)
                print(f"\n  ⚠ Warning: {len(corpus_wavs) - len(textgrids)} file(s) in corpus did not produce a TextGrid")
                for m in sorted(missing):
                    print(f"    - {m}")

            print()
        else:
            print(f"\n✗ MFA alignment failed (exit code {result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
            sys.exit(1)

    except FileNotFoundError:
        print("✗ MFA command not found. Is MFA installed and in PATH?")
        sys.exit(1)


# ─────────────────────────────────────────────
# STEP 6: LOAD TEXTGRIDS
# ─────────────────────────────────────────────

def load_textgrids(config):
    """Parse all TextGrid files and return a dict of {source_name: word_list}."""
    print("=" * 70)
    print("STEP 6: Loading TextGrids")
    print("=" * 70)

    output_dir = config["mfa_output_dir"]
    textgrids = {}

    for filename in sorted(os.listdir(output_dir)):
        if not filename.endswith(".TextGrid"):
            continue

        source_name = filename.replace(".TextGrid", "")
        filepath = os.path.join(output_dir, filename)
        words = parse_textgrid(filepath)
        textgrids[source_name] = words
        print(f"  ✓ {source_name}: {len(words)} words")

    print(f"\n✓ Loaded {len(textgrids)} TextGrid(s)\n")
    return textgrids


# ─────────────────────────────────────────────
# STEP 7: EXTRACT AUDIO CLIPS
# ─────────────────────────────────────────────

def extract_clips(config, textgrids):
    """Read CSV, find phrases in TextGrids, extract audio clips."""
    print("=" * 70)
    print("STEP 7: Extracting audio clips")
    print("=" * 70)

    csv_path = config["csv_path"]
    front_col = config["front_column"]
    back_col = config["back_column"]
    source_col = config["source_column"]
    clips_dir = config["audio_clips_dir"]
    wav_dir = config["processed_audio_dir"]
    padding_ms = config["clip_padding_ms"]

    os.makedirs(clips_dir, exist_ok=True)

    # Read CSV
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check if Source column exists
    has_source = source_col in reader.fieldnames if reader.fieldnames else False
    if has_source:
        print(f"  Source column '{source_col}' found — using targeted search")
    else:
        print(f"  No '{source_col}' column — will search all TextGrids for each phrase")

    print(f"  Processing {len(rows)} cards\n")

    results = []
    found = 0
    not_found = 0

    for i, row in enumerate(rows, 1):
        front = row.get(front_col, "").strip()
        back = row.get(back_col, "").strip()
        source = row.get(source_col, "").strip() if has_source else ""

        # Skip empty rows
        if not front or not back:
            continue

        # Clean the phrase the same way we clean transcripts
        cleaned_phrase = clean_transcript(front)

        print(f"  [{i}/{len(rows)}] {front}")

        # Determine which TextGrids to search
        if source and source in textgrids:
            search_targets = {source: textgrids[source]}
        elif source:
            print(f"    ⚠ Source '{source}' not found in TextGrids — searching all")
            search_targets = textgrids
        else:
            search_targets = textgrids

        # Search for the phrase
        match_found = False
        for source_name, words in search_targets.items():
            match = find_phrase_timestamps(words, cleaned_phrase)

            if match:
                # Build output filename
                safe_name = cleaned_phrase.replace(" ", "_").replace("'", "")
                safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
                clip_path = os.path.join(clips_dir, f"{safe_name}.mp3")

                # Extract audio
                audio_path = os.path.join(wav_dir, f"{source_name}.wav")
                if os.path.exists(audio_path):
                    extract_audio_segment(
                        audio_path,
                        match["start"],
                        match["end"],
                        clip_path,
                        padding_ms=padding_ms
                    )

                    results.append({
                        "front": front,
                        "back": back,
                        "cleaned_phrase": cleaned_phrase,
                        "source": source_name,
                        "start": match["start"],
                        "end": match["end"],
                        "clip_path": clip_path,
                        "found": True,
                    })
                    found += 1
                    match_found = True
                    print(f"    ✓ Found in {source_name} ({match['start']:.3f}s - {match['end']:.3f}s)")
                    break
                else:
                    print(f"    ⚠ Audio file not found: {audio_path}")

        if not match_found:
            results.append({
                "front": front,
                "back": back,
                "cleaned_phrase": cleaned_phrase,
                "source": source if source else "",
                "clip_path": None,
                "found": False,
            })
            not_found += 1
            print(f"    ⚠ Phrase not found — flagged for manual review")

    print(f"\n✓ Extraction complete: {found} found, {not_found} not found\n")

    if not_found > 0:
        print("  Phrases not found:")
        for r in results:
            if not r["found"]:
                print(f"    - \"{r['front']}\" (cleaned: \"{r['cleaned_phrase']}\")")
        print()

    return results


# ─────────────────────────────────────────────
# STEP 8: ANKI INTEGRATION
# ─────────────────────────────────────────────

def update_anki(config, results):
    """Create/update Anki cards with extracted audio clips."""
    print("=" * 70)
    print("STEP 8: Anki integration")
    print("=" * 70)

    deck_name = config["deck_name"]
    anki = AnkiConnector(config["anki_connect_url"])

    # Ensure deck exists
    if not anki.deck_exists(deck_name):
        print(f"  Creating deck: {deck_name}")
        anki.create_deck(deck_name)

    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    for i, r in enumerate(results, 1):
        front = r["front"]
        back = r["back"]
        clip_path = r["clip_path"]

        print(f"  [{i}/{len(results)}] {front}")

        # Check if card already exists
        existing = anki.find_cards_by_front(deck_name, front)

        try:
            if not existing:
                # Create new card
                anki.add_note(deck_name, front, back, clip_path)
                stats["created"] += 1
                print(f"    ✓ Card created" + (" (with audio)" if clip_path else " (no audio)"))

            elif clip_path:
                # Card exists — update with audio
                card_info = anki.invoke("cardsInfo", cards=existing)[0]
                note_id = card_info["note"]
                anki.update_note_audio(note_id, clip_path)
                stats["updated"] += 1
                print(f"    ✓ Audio added to existing card")

            else:
                stats["skipped"] += 1
                print(f"    - Card exists, no audio to add")

        except Exception as e:
            stats["errors"] += 1
            print(f"    ✗ Error: {e}")

    print(f"\n✓ Anki integration complete:")
    print(f"    Created: {stats['created']}")
    print(f"    Updated: {stats['updated']}")
    print(f"    Skipped: {stats['skipped']}")
    print(f"    Errors:  {stats['errors']}\n")

    return stats


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n" + "=" * 70)
    print("  LANGUAGE LEARNING AUDIO FLASHCARD AUTOMATION")
    print("=" * 70 + "\n")

    # Load config
    config = load_config()

    # Step 1: Validate
    config = validate_inputs(config)

    # Step 2: Convert audio
    convert_audio(config)

    # Step 3: Transcribe (Whisper, skipping manual transcripts)
    transcribe_files(config)

    # Step 4: Clean transcripts + prepare MFA corpus
    prepare_corpus(config)

    # Step 5: MFA alignment
    run_mfa_alignment(config)

    # Step 6: Load TextGrids
    textgrids = load_textgrids(config)

    # Step 7: Extract audio clips
    results = extract_clips(config, textgrids)

    # Step 8: Update Anki
    anki_stats = update_anki(config, results)

    # Final summary
    print("=" * 70)
    print("  PIPELINE COMPLETE")
    print("=" * 70)

    found = sum(1 for r in results if r["found"])
    total = len(results)
    print(f"  Audio files processed: {len(os.listdir(config['processed_audio_dir']))}")
    print(f"  Phrases matched: {found}/{total}")
    print(f"  Cards created: {anki_stats['created']}")
    print(f"  Cards updated: {anki_stats['updated']}")

    if found < total:
        print(f"\n  ⚠ {total - found} phrase(s) could not be found in the audio.")
        print(f"    Check the output above for details.")

    print(f"\n✓ Done! Open Anki to see your updated deck: \"{config['deck_name']}\"\n")


if __name__ == "__main__":
    main()