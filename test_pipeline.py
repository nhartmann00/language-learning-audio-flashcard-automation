"""
Test script to verify the full pipeline works on a new lesson.
Tests: audio conversion, transcription, cleaning, MFA prep, and parsing.
"""

import os
from src.audio_converter import mp3_to_wav
from src.transcriber import transcribe_audio, save_transcript
from src.transcript_cleaner import clean_transcript, prepare_mfa_corpus
from src.textgrid_parser import parse_textgrid, find_all_phrases

# Configuration
LESSON_NUMBER = "002"
LESSON_FILE = f"L{LESSON_NUMBER}-LESSON"

# Paths
MP3_PATH = f"data/raw_audio/{LESSON_FILE}.mp3"
WAV_PATH = f"data/processed_audio/{LESSON_FILE}.wav"
RAW_TRANSCRIPT_PATH = f"data/transcripts/{LESSON_FILE}.txt"
MFA_CORPUS_DIR = "data/mfa_corpus"
MFA_OUTPUT_DIR = "data/mfa_output"
TEXTGRID_PATH = f"{MFA_OUTPUT_DIR}/{LESSON_FILE}.TextGrid"

# Test phrases (update these based on what's actually in lesson 2)
TEST_PHRASES = [
    "deux",
    "s'il vous plaît",
    "préfère",
    "petit déjeuner",
    "monsieur madame vous désirez",
    "oui c'est ça",
    "le déjeuner",
    "deuxième"
]

def main():
    print("="*70)
    print(f"TESTING PIPELINE ON {LESSON_FILE}")
    print("="*70)
    
    # Step 1: Convert MP3 to WAV
    print("\n[STEP 1] Converting MP3 to WAV...")
    if not os.path.exists(MP3_PATH):
        print(f"✗ ERROR: MP3 file not found at {MP3_PATH}")
        print("  Please add the file and try again.")
        return
    
    mp3_to_wav(MP3_PATH, WAV_PATH)
    print(f"✓ WAV created at {WAV_PATH}")
    
    # Step 2: Transcribe with Whisper
    print("\n[STEP 2] Transcribing audio with Whisper...")
    result = transcribe_audio(WAV_PATH, model_size="small", language="fr")
    
    print(f"\nTranscript preview (first 200 chars):")
    print(result['text'][:200] + "...")
    
    save_transcript(result, RAW_TRANSCRIPT_PATH)
    print(f"✓ Transcript saved to {RAW_TRANSCRIPT_PATH}")
    
    # Step 3: Clean transcript and prepare MFA corpus
    print("\n[STEP 3] Cleaning transcript for MFA...")
    with open(RAW_TRANSCRIPT_PATH, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    cleaned_text = clean_transcript(raw_text)
    print(f"\nCleaned transcript preview (first 200 chars):")
    print(cleaned_text[:200] + "...")
    
    # Prepare MFA corpus
    prepare_mfa_corpus(
        wav_dir="data/processed_audio",
        transcript_dir="data/transcripts",
        corpus_dir=MFA_CORPUS_DIR
    )
    print(f"✓ MFA corpus ready at {MFA_CORPUS_DIR}")
    
    # Step 4: Instructions for MFA alignment
    print("\n[STEP 4] MFA Alignment")
    print("⚠ Manual step required!")
    print("Run this command in your terminal:")
    print(f"\n  mfa align {MFA_CORPUS_DIR} french_mfa french_mfa {MFA_OUTPUT_DIR}\n")
    
    input("Press Enter after running MFA alignment to continue...")
    
    # Step 5: Parse TextGrid and test phrase lookup
    print("\n[STEP 5] Parsing TextGrid output...")
    
    if not os.path.exists(TEXTGRID_PATH):
        print(f"✗ ERROR: TextGrid not found at {TEXTGRID_PATH}")
        print("  Make sure MFA alignment completed successfully.")
        return
    
    words = parse_textgrid(TEXTGRID_PATH)
    print(f"✓ Found {len(words)} words")
    
    # Show first 10 words
    print("\nFirst 10 words with timestamps:")
    for w in words[:10]:
        print(f"  {w['start']:.3f}s - {w['end']:.3f}s : {w['word']}")
    
    # Test phrase lookup
    print(f"\n[STEP 6] Testing phrase lookup...")
    print(f"Looking for {len(TEST_PHRASES)} test phrases:")
    
    results = find_all_phrases(words, TEST_PHRASES)
    
    # Summary
    print("\n" + "="*70)
    print("PIPELINE TEST SUMMARY")
    print("="*70)
    
    found_count = sum(1 for r in results if r['found'])
    print(f"✓ Audio conversion: SUCCESS")
    print(f"✓ Transcription: SUCCESS")
    print(f"✓ Transcript cleaning: SUCCESS")
    print(f"✓ TextGrid parsing: SUCCESS")
    print(f"✓ Phrase lookup: {found_count}/{len(TEST_PHRASES)} phrases found")
    
    if found_count < len(TEST_PHRASES):
        print(f"\n⚠ {len(TEST_PHRASES) - found_count} phrase(s) not found - may need manual review")
    
    print("\n✓ PIPELINE TEST COMPLETE!")


if __name__ == "__main__":
    main()