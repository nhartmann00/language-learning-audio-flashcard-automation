# Whisper Configuration Testing

Methodology and analysis tooling used to select the production Whisper
configuration for the pipeline.

## The experiment

Eight configurations were run across all 100 Assimil lessons — every
combination of two Whisper model sizes and four trailing-silence trim
settings:

| Model  | Trim setting | Output directory              |
|--------|--------------|-------------------------------|
| small  | none         | `transcripts_small_no_trim/`  |
| small  | 0 ms tail    | `transcripts_small_0ms/`      |
| small  | 150 ms tail  | `transcripts_small_150ms/`    |
| small  | 500 ms tail  | `transcripts_small_500ms/`    |
| medium | none         | `transcripts_medium_no_trim/` |
| medium | 0 ms tail    | `transcripts_medium_0ms/`     |
| medium | 150 ms tail  | `transcripts_medium_150ms/`   |
| medium | 500 ms tail  | `transcripts_medium_500ms/`   |

"Trim setting" is the `tail_padding_ms` value passed to `trim_silence()` —
the amount of original trailing silence retained after trimming. Trimming
is end-only; head trimming was found to cause transcription drift in the
opening words.

Trimmed audio for each setting lives in `audio_no_trim/`, `audio_0ms/`,
`audio_150ms/` and `audio_500ms/` (gitignored).

## Reproducing the transcript sets

Generation is manual. For each of the eight configurations:

1. Set `tail_padding_ms` in `config.json` to the trim value. For the
   `no_trim` variant, pass `trim=False` to `mp3_to_wav()` /
   `trim_silence()` — `main.py` hardcodes `trim=True` in `convert_audio()`,
   so this variant is not reachable from `config.json` alone.
2. Delete `data/processed_audio/` so audio is re-trimmed at the new setting.
3. Set `whisper_model` in `config.json` to `small` or `medium`.
4. Run `python main.py` and stop after Step 3 (Transcription).
5. Rename `data/whisper_transcripts/` to
   `whisper_tests/transcripts_{model}_{trim}/`.

Whisper is non-deterministic: re-running the same configuration on the same
audio produces slightly different output. This is why configurations are
scored against fixed ground truth rather than compared pairwise against
each other — and it sets a floor on how small a difference between configs
can be treated as meaningful.

## Ground truth

WER is measured against hand-verified transcripts for all 100 lessons in
`data/transcripts_manual/`. These are verbatim transcriptions of
copyrighted Assimil course material and are **not committed**. Reproducing
the WER numbers requires supplying your own ground truth in the same
normalised format: lowercase, no punctuation except apostrophes, hyphens
replaced by spaces, digits spelled out as French words.

## Scripts

Run from the repository root — `batch_clean_all.py` imports from `src/`.

- `batch_clean_all.py` — normalises every `transcripts_*/` set through
  `clean_transcript()` so WER is measured on MFA-ready text rather than raw
  Whisper output.
- `wer_analysis.py` — computes WER for every configuration against ground
  truth using `jiwer`. Writes `wer_results/summary.csv` (per lesson, all
  eight configs) and `wer_results/aggregate.csv` (one row per config).
- `wer_diff_report.py` — error-type breakdowns. Writes
  `wer_results/worst_lessons.txt` (top 10 worst lessons per config) and
  `wer_results/all_errors.csv` (every individual substitution, insertion
  and deletion as a `ref_word,hyp_word` pair).

`all_errors.csv` is gitignored — it is ~8,000 rows of raw diff output,
useful only as an input to further analysis.

## Results

Averaged across all 100 lessons (28,720 reference words):

| Config         | Avg WER | Median | Max     | Sub | Ins | Del |
|----------------|---------|--------|---------|-----|-----|-----|
| small_no_trim  | 3.90%   | 3.72%  | 12.20%  | 879 |  82 | 205 |
| small_0ms      | 4.02%   | 3.95%  | 12.20%  | 877 | 114 | 214 |
| small_150ms    | 3.92%   | 3.73%  | 12.20%  | 876 |  85 | 214 |
| small_500ms    | 3.93%   | 3.73%  | 12.20%  | 879 |  87 | 214 |
| medium_no_trim | 2.95%   | 2.05%  | 28.69%  | 495 |  41 | 288 |
| medium_0ms     | 2.80%   | 2.05%  | 28.69%  | 494 |  34 | 263 |
| medium_150ms   | 3.07%   | 2.05%  | 28.69%  | 520 |  50 | 273 |
| medium_500ms   | 2.86%   | 2.07%  | 28.69%  | 497 |  48 | 264 |

**Model size was the decision that mattered.** Medium averages roughly a
percentage point lower and halves substitutions (~495 vs ~878), but its
worst case is 28.69% against small's 12.20%, and it accumulates more
deletions overall despite being more accurate on the typical lesson. That
asymmetry is the whole story: L033 under medium shows 70 deletions against
2 substitutions, which is not noise but mid-dialogue truncation dropping
entire turns. L008, L006 and L017 show the same pattern at smaller scale.

For this pipeline, deletions and substitutions are not comparable failures.
A substitution — mostly homophones like `ses`/`ces`, `a`/`à`, or a botched
verb ending — still aligns phonetically in MFA and yields a usable clip. A
deletion removes the phrase from the alignment entirely, so the card
silently gets no audio and the failure is invisible until you study the
deck. Small was chosen for its ceiling, not its average.

**Trim value was not decided by aggregate WER, and could not have been.**
The four small configs span 0.12 percentage points, share an identical
maximum, and sit within Whisper's own run-to-run variance; only 17% of
lessons show any WER difference across them (8% for medium).
`small_no_trim` posts the lowest average of the four.

The tail-padding value was chosen on error *type* rather than error rate.
Scanning `all_errors.csv` for non-Latin script injection — the clearest
hallucination signature — `small_0ms` produced two artifacts and
`small_500ms` one, while `no_trim` and `150ms` produced none. Trimming hard
to the speech boundary appears to create a discontinuity the decoder
generates garbage against; retaining ~150 ms of natural room tone avoids
that.

Trimming is retained rather than dropped for robustness reasons the Assimil
corpus cannot test. These files carry only a second or two of trailing
silence. The pipeline is content-agnostic and intended to take podcast and
long-form audio, where silent tails run to minutes and Whisper's silence
failure mode is well documented. 150 ms trims defensively without cutting
into the decay.

The production configuration is `small_150ms`.