"""
Audio conversion utilities for language learning flashcard automation.
Converts MP3 files to WAV format for forced alignment processing.
"""

from pydub import AudioSegment
from pydub.silence import detect_leading_silence
import os


def trim_silence(audio, silence_threshold_db=-40, chunk_size_ms=10, tail_padding_ms=750):
    """
    Trim trailing silence from an AudioSegment, keeping a short padding tail.

    Only trims from the end — leaving the start untouched avoids nudging
    Whisper's initial context window, which can cause transcription drift
    in the first few words.

    After trimming, tail_padding_ms of silence is added back to ensure the
    last syllable isn't clipped. 500ms is enough to protect speech while
    staying well short of the silence length that triggers Whisper hallucinations.

    Args:
        audio (AudioSegment): Audio to trim
        silence_threshold_db (int): dBFS threshold below which audio is
                                    considered silent (default: -40 dBFS).
                                    -40 is conservative — increase toward
                                    -30 if trailing noise remains,
                                    decrease toward -50 if speech is clipped.
        chunk_size_ms (int): Granularity of silence detection in ms (default: 10).
                             Smaller = more precise but slower.
        tail_padding_ms (int): Milliseconds of silence to add back after trimming
                               (default: 500ms). Prevents last syllable from being
                               clipped. Increase if speech still sounds cut off.

    Returns:
        AudioSegment: Trimmed audio segment with padding restored
    """
    # Trim trailing silence only — reverse, detect leading silence, reverse back
    end_trim_ms = detect_leading_silence(audio.reverse(), silence_threshold=silence_threshold_db,
                                         chunk_size=chunk_size_ms)

    duration_ms = len(audio)
    trimmed = audio[:duration_ms - end_trim_ms]

    # Add padding back to avoid clipping the last syllable
    padding = AudioSegment.silent(duration=tail_padding_ms)
    trimmed = trimmed + padding

    trimmed_end = end_trim_ms / 1000
    trimmed_duration = len(trimmed) / 1000
    original_duration = duration_ms / 1000

    print(f"  Silence trimmed — end: {trimmed_end:.2f}s removed, {tail_padding_ms}ms padding restored "
          f"| {original_duration:.2f}s → {trimmed_duration:.2f}s")

    return trimmed


def mp3_to_wav(mp3_path, wav_path=None, trim=True, silence_threshold_db=-40, tail_padding_ms=500):
    """
    Convert MP3 file to WAV format, preserving original quality.

    Args:
        mp3_path (str): Path to input MP3 file
        wav_path (str, optional): Path for output WAV file.
                                   If None, uses same name with .wav extension.
        trim (bool): Whether to trim trailing silence (default: True).
        silence_threshold_db (int): dBFS threshold for silence trimming (default: -40).
                                    Only used when trim=True.
        tail_padding_ms (int): Milliseconds of silence to restore after trimming
                               (default: 500ms). Only used when trim=True.

    Returns:
        str: Path to the created WAV file
    """
    # Generate output path if not provided
    if wav_path is None:
        wav_path = mp3_path.replace('.mp3', '.wav')

    # Load MP3 file
    print(f"Loading {mp3_path}...")
    audio = AudioSegment.from_mp3(mp3_path)

    # Optionally trim silence
    if trim:
        audio = trim_silence(audio, silence_threshold_db=silence_threshold_db,
                             tail_padding_ms=tail_padding_ms)

    # Export as WAV (preserving original quality)
    print(f"Exporting to {wav_path}...")
    audio.export(wav_path, format="wav")

    print(f"✓ Conversion complete: {wav_path}")
    return wav_path


def batch_convert_mp3_to_wav(input_dir, output_dir, trim=True, silence_threshold_db=-40, tail_padding_ms=500):
    """
    Convert all MP3 files in a directory to WAV format.

    Args:
        input_dir (str): Directory containing MP3 files
        output_dir (str): Directory where WAV files will be saved
        trim (bool): Whether to trim trailing silence (default: True).
        silence_threshold_db (int): dBFS threshold for silence trimming (default: -40).
                                    Only used when trim=True.
        tail_padding_ms (int): Milliseconds of silence to restore after trimming
                               (default: 500ms). Only used when trim=True.

    Returns:
        list: Paths to all created WAV files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Find all MP3 files
    mp3_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.mp3')])

    if not mp3_files:
        print(f"No MP3 files found in {input_dir}")
        return []

    print(f"Found {len(mp3_files)} MP3 files to convert")
    if trim:
        print(f"Silence trimming enabled (threshold: {silence_threshold_db} dBFS, "
              f"tail padding: {tail_padding_ms}ms)\n")

    wav_files = []
    for i, mp3_file in enumerate(mp3_files, 1):
        mp3_path = os.path.join(input_dir, mp3_file)
        wav_path = os.path.join(output_dir, mp3_file.replace('.mp3', '.wav'))

        print(f"[{i}/{len(mp3_files)}] {mp3_file}")
        try:
            mp3_to_wav(mp3_path, wav_path, trim=trim,
                       silence_threshold_db=silence_threshold_db,
                       tail_padding_ms=tail_padding_ms)
            wav_files.append(wav_path)
        except Exception as e:
            print(f"✗ Error converting {mp3_file}: {e}")
        print()

    print(f"✓ Successfully converted {len(wav_files)}/{len(mp3_files)} files")
    return wav_files


if __name__ == "__main__":
    # Convert all lessons with silence trimming (default)
    batch_convert_mp3_to_wav("data/raw_audio", "data/processed_audio")

    # To disable trimming:
    # batch_convert_mp3_to_wav("data/raw_audio", "data/processed_audio", trim=False)

    # To use a less aggressive threshold (e.g. -30 dBFS strips more):
    # batch_convert_mp3_to_wav("data/raw_audio", "data/processed_audio", silence_threshold_db=-30)