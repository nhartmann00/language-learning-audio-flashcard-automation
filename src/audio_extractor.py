"""
Audio extraction utilities.
Extracts specific audio segments based on timestamps from MFA alignment.
"""

import os
from pydub import AudioSegment


def extract_audio_segment(audio_path, start_time, end_time, output_path, padding_ms=100):
    """
    Extract a specific segment from an audio file.
    
    Args:
        audio_path (str): Path to input audio file (WAV or MP3)
        start_time (float): Start time in seconds
        end_time (float): End time in seconds
        output_path (str): Path where extracted segment will be saved
        padding_ms (int): Milliseconds of padding to add before/after (default 100ms)
    
    Returns:
        str: Path to extracted audio file
    """
    # Load audio
    print(f"Loading {audio_path}...")
    audio = AudioSegment.from_file(audio_path)
    
    # Convert seconds to milliseconds
    start_ms = int(start_time * 1000) - padding_ms
    end_ms = int(end_time * 1000) + padding_ms
    
    # Ensure we don't go out of bounds
    start_ms = max(0, start_ms)
    end_ms = min(len(audio), end_ms)
    
    # Extract segment
    segment = audio[start_ms:end_ms]
    
    # Export
    print(f"Extracting {start_time:.3f}s - {end_time:.3f}s...")
    segment.export(output_path, format="mp3")
    
    print(f"✓ Saved to {output_path}")
    return output_path


def extract_phrase(audio_path, words, phrase, output_dir, padding_ms=100):
    """
    Find a phrase in the word list and extract its audio.
    
    Args:
        audio_path (str): Path to source audio file
        words (list): List of word dicts from parse_textgrid()
        phrase (str): Phrase to extract (e.g., "comment allez vous")
        output_dir (str): Directory where clips will be saved
        padding_ms (int): Milliseconds of padding
    
    Returns:
        dict: Result with 'phrase', 'audio_path', 'found' keys
    """
    from src.textgrid_parser import find_phrase_timestamps
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Find timestamps
    match = find_phrase_timestamps(words, phrase)
    
    if not match:
        print(f"⚠ Phrase not found: '{phrase}'")
        return {
            'phrase': phrase,
            'audio_path': None,
            'found': False
        }
    
    # Create filename from phrase (sanitize for filesystem)
    filename = phrase.replace(' ', '_').replace("'", "")
    filename = "".join(c for c in filename if c.isalnum() or c == '_')
    output_path = os.path.join(output_dir, f"{filename}.mp3")
    
    # Extract audio
    extract_audio_segment(
        audio_path,
        match['start'],
        match['end'],
        output_path,
        padding_ms
    )
    
    return {
        'phrase': phrase,
        'audio_path': output_path,
        'start': match['start'],
        'end': match['end'],
        'found': True
    }


def batch_extract_phrases(audio_path, words, phrases, output_dir, padding_ms=100):
    """
    Extract multiple phrases from an audio file.
    
    Args:
        audio_path (str): Path to source audio file
        words (list): List of word dicts from parse_textgrid()
        phrases (list): List of phrases to extract
        output_dir (str): Directory where clips will be saved
        padding_ms (int): Milliseconds of padding
    
    Returns:
        list: Results for all phrases
    """
    print(f"Extracting {len(phrases)} phrases from {audio_path}...")
    print(f"Output directory: {output_dir}\n")
    
    results = []
    for i, phrase in enumerate(phrases, 1):
        print(f"[{i}/{len(phrases)}] '{phrase}'")
        result = extract_phrase(audio_path, words, phrase, output_dir, padding_ms)
        results.append(result)
        print()
    
    # Summary
    found_count = sum(1 for r in results if r['found'])
    print(f"✓ Extraction complete: {found_count}/{len(phrases)} phrases extracted")
    
    if found_count < len(phrases):
        print(f"⚠ {len(phrases) - found_count} phrase(s) not found")
        print("\nNot found:")
        for r in results:
            if not r['found']:
                print(f"  - {r['phrase']}")
    
    return results


if __name__ == "__main__":
    from src.textgrid_parser import parse_textgrid
    
    # Test extraction on L001
    print("Testing audio extraction on L002-LESSON\n")
    
    # Parse TextGrid
    textgrid_path = "data/mfa_output/L002-LESSON.TextGrid"
    words = parse_textgrid(textgrid_path)
    
    # Test phrases
    test_phrases = [
        "deux",
        "s'il vous plaît",
        "préfère",
        "petit déjeuner",
        "monsieur madame vous désirez",
        "oui c'est ça",
        "le déjeuner",
        "deuxième"
    ]
    
    # Extract audio clips
    audio_path = "data/processed_audio/L002-LESSON.wav"
    output_dir = "data/audio_clips"
    
    results = batch_extract_phrases(
        audio_path,
        words,
        test_phrases,
        output_dir,
        padding_ms=100  # 100ms padding on each side
    )
    
    print("\n" + "="*70)
    print("EXTRACTED AUDIO CLIPS:")
    print("="*70)
    for r in results:
        if r['found']:
            print(f"✓ {r['phrase']}")
            print(f"  File: {r['audio_path']}")
            print(f"  Time: {r['start']:.3f}s - {r['end']:.3f}s")
        else:
            print(f"✗ {r['phrase']} - NOT FOUND")