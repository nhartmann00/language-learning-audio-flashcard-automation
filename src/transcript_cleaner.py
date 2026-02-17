"""
Transcript cleaning utilities for Montreal Forced Aligner (MFA) preparation.
Cleans Whisper transcripts to meet MFA input requirements.
"""

import re
import os


def clean_transcript(text):
    """
    Clean a Whisper transcript for MFA alignment.
    
    MFA requirements:
    - No punctuation (except apostrophes for French contractions)
    - No numbers (convert to words or remove)
    - Lowercase
    - No extra whitespace
    
    Args:
        text (str): Raw Whisper transcript text
    
    Returns:
        str: Cleaned transcript ready for MFA
    """
    # Lowercase
    text = text.lower()
    
    # Replace hyphens with spaces (allez-vous → allez vous)
    text = text.replace('-', ' ')

    # Remove punctuation except apostrophes (needed for French: j'ai, c'est, etc.)
    text = re.sub(r"[^\w\s']", "", text)
    
    # Remove numbers
    text = re.sub(r"\d+", "", text)
    
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


def prepare_mfa_corpus(wav_dir, transcript_dir, corpus_dir):
    """
    Prepare MFA corpus folder by pairing WAV files with cleaned transcripts.
    
    MFA expects:
    corpus/
    ├── L001-LESSON.wav
    ├── L001-LESSON.txt
    ├── L002-LESSON.wav
    └── L002-LESSON.txt
    
    Args:
        wav_dir (str): Directory containing WAV files
        transcript_dir (str): Directory containing Whisper transcript .txt files
        corpus_dir (str): Output directory for MFA corpus
    """
    os.makedirs(corpus_dir, exist_ok=True)
    
    # Find all WAV files
    wav_files = [f for f in os.listdir(wav_dir) if f.endswith('.wav')]
    
    if not wav_files:
        print(f"No WAV files found in {wav_dir}")
        return
    
    print(f"Found {len(wav_files)} WAV files")
    
    prepared = 0
    skipped = 0
    
    for wav_file in wav_files:
        base_name = os.path.splitext(wav_file)[0]
        transcript_file = f"{base_name}.txt"
        
        wav_path = os.path.join(wav_dir, wav_file)
        transcript_path = os.path.join(transcript_dir, transcript_file)
        
        # Check transcript exists
        if not os.path.exists(transcript_path):
            print(f"⚠ No transcript found for {wav_file} - skipping")
            skipped += 1
            continue
        
        # Read and clean transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        cleaned_text = clean_transcript(raw_text)
        
        # Copy WAV to corpus
        import shutil
        shutil.copy2(wav_path, os.path.join(corpus_dir, wav_file))
        
        # Save cleaned transcript to corpus
        cleaned_path = os.path.join(corpus_dir, transcript_file)
        with open(cleaned_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        print(f"✓ Prepared {base_name}")
        prepared += 1
    
    print(f"\n✓ Corpus ready: {prepared} files prepared, {skipped} skipped")
    print(f"  Corpus location: {corpus_dir}")


if __name__ == "__main__":
    # Test cleaning on a single transcript
    test_text = "première leçon comment allez-vous? bonjour Jean, comment allez-vous? bien et vous? ça va très bien, merci!"
    
    print("Original:")
    print(test_text)
    
    print("\nCleaned:")
    cleaned = clean_transcript(test_text)
    print(cleaned)
    
    # Prepare MFA corpus
    prepare_mfa_corpus(
        wav_dir="data/processed_audio",
        transcript_dir="data/transcripts",
        corpus_dir="data/mfa_corpus"
    )
