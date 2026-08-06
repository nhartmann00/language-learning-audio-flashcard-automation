# Language Learning Audio Flashcard Automation

Automated pipeline to extract specific words and phrases from textbook dialogue audio files and integrate them into Anki flashcards for language learning.

## Background

Language learning textbooks typically come with companion MP3 dialogue files containing native-speaker pronunciation — far higher quality than any TTS alternative. Adding precise audio clips to Anki flashcards significantly improves retention, but manually chopping audio files for hundreds of vocabulary cards is impractical. This tool automates the entire process, from raw audio to ready-to-study Anki cards with word-level precision.

## Pipeline

The end-to-end pipeline is orchestrated by `main.py` and driven by `config.json`:

1. **MP3 → WAV Conversion** — Converts raw audio files to WAV format for processing.
2. **Silence Trimming** — Trims trailing silence, retaining a 150ms tail. End-only; head trimming causes transcription drift in the opening words.
3. **Whisper Transcription** — Generates French transcripts using OpenAI's Whisper (`small` model).
4. **Transcript Cleaning** — Normalizes text for MFA compatibility (numbers → French words, abbreviation expansion, punctuation stripping).
5. **MFA Forced Alignment** — Aligns transcripts to audio at the word level using Montreal Forced Aligner, producing TextGrid files.
6. **TextGrid Parsing** — Extracts word-level timestamps from MFA output.
7. **Audio Extraction** — Cuts precise audio clips for each target word/phrase based on timestamps.
8. **Anki Integration** — Creates or updates Anki flashcards with extracted audio clips via AnkiConnect.

The `small` model and 150ms tail were selected by measuring word error rate for eight model/trim combinations across all 100 lessons against hand-verified ground truth. Methodology, results and reasoning are in [`whisper_tests/README.md`](whisper_tests/README.md).

## Features

- [x] Convert MP3 audio files to WAV for processing
- [x] Trim trailing silence to prevent ASR hallucinations
- [x] Transcribe audio with Whisper (small model, French)
- [x] Clean transcripts for MFA compatibility (numbers, abbreviations, punctuation)
- [x] Perform forced alignment on transcripts and audio via MFA
- [x] Parse TextGrid output for word-level timestamps
- [x] Extract audio segments based on text input
- [x] Programmatically create/update Anki decks with audio clips via AnkiConnect
- [x] Batch processing for 100 dialogue files
- [x] Config-driven pipeline (`config.json`)
- [x] WER evaluation harness for ASR configuration selection

## Tech Stack

- **Python** — Main programming language. Ecosystem for audio processing and ML tools.
- **Whisper** — Automatic speech recognition from OpenAI. Provides transcripts for each audio file automatically.
- **Montreal Forced Aligner** — Audio-text alignment. Industry standard with support for French and many other languages.
- **pydub** — Audio processing and segmentation. Pythonic audio manipulation (built on ffmpeg).
- **AnkiConnect** — Anki integration API. Creates and updates flashcards programmatically.
- **jiwer** — Word error rate computation for the ASR configuration comparison.

## Project Structure

```
language-learning-audio-flashcard-automation/
├── main.py                       # End-to-end pipeline orchestrator
├── src/
│   ├── __init__.py
│   ├── audio_converter.py        # MP3→WAV conversion + silence trimming
│   ├── transcriber.py            # Whisper transcription
│   ├── transcript_cleaner.py     # Text normalization for MFA
│   ├── textgrid_parser.py        # MFA TextGrid parsing + phrase lookup
│   ├── audio_extractor.py        # Audio clip extraction by timestamp
│   └── anki_integrator.py        # AnkiConnect API integration
├── whisper_tests/
│   ├── README.md                 # ASR config testing methodology and results
│   ├── batch_clean_all.py        # Normalize transcript sets before scoring
│   ├── wer_analysis.py           # Per-lesson and per-config WER against ground truth
│   ├── wer_diff_report.py        # Error-type breakdowns by config
│   └── wer_results/
│       ├── aggregate.csv         # One row per config
│       ├── summary.csv           # One row per lesson, all eight configs
│       └── worst_lessons.txt     # Top 10 worst lessons per config
├── data/                         # Audio files, transcripts, TextGrids (gitignored)
├── requirements.txt
├── LICENSE
└── README.md
```

`config.json` is not tracked — it holds local paths and your deck name. Running `python main.py` with no config present writes a template and exits so you can fill it in.

## Project Status

✅ **Pipeline Complete** — The Assimil French pipeline is fully functional end-to-end. All 100 lessons process through the pipeline from raw MP3 to Anki flashcards with native audio clips.

## Setup

1. **Install ffmpeg** — required by pydub for audio decoding, and by Whisper. It must be on your `PATH`.

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Montreal Forced Aligner** (separate install, conda only):
   ```bash
   conda install -c conda-forge montreal-forced-aligner
   mfa model download acoustic french_mfa
   mfa model download dictionary french_mfa
   ```

4. **Set up AnkiConnect:**
   - Install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on in Anki.
   - Ensure Anki is running when executing the pipeline.

5. **Configure `config.json`** with your paths, deck name, and CSV location. Run the pipeline once to generate the template.

6. **Run the pipeline:**
   ```bash
   python main.py
   ```

Each stage skips work that has already been done — existing WAVs, transcripts, TextGrids, clips and cards with audio attached are all detected and passed over, so reruns are cheap and targeted re-processing is a matter of deleting the specific outputs you want rebuilt.

## Future Enhancements

- Podcast integration via RSS feeds (Podcast Index API for discovery)
- YouTube integration via `yt-dlp` (auto-generated subtitles bypass Whisper)
- Support for other languages
- GUI for easier phrase selection
- Audio quality normalization

## License

MIT License - See LICENSE file for details