"""
Audio transcription using OpenAI Whisper.
Generates transcripts from audio files for forced alignment.
"""

import whisper
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


def transcribe_audio(audio_path, model_size="small", language="fr"):
    """
    Transcribe audio file using Whisper.
    
    Args:
        audio_path (str): Path to audio file (MP3, WAV, etc.)
        model_size (str): Whisper model size - "tiny", "base", "small", "medium", "large"
                         (larger = more accurate but slower)
        language (str): Language code (e.g., "fr" for French, "en" for English)
    
    Returns:
        dict: Transcription result with 'text' and 'segments' (word-level timestamps)
    """
    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    
    print(f"Transcribing {audio_path}...")
    result = model.transcribe(
        audio_path,
        language=language,
        verbose=True,  # Set to True to see progress
        word_timestamps=True
    )
    
    print(f"✓ Transcription complete")
    return result


def save_transcript(result, output_path):
    """
    Save transcript to a text file.
    
    Args:
        result (dict): Whisper transcription result
        output_path (str): Path where transcript will be saved
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result['text'])
    
    print(f"✓ Transcript saved to {output_path}")


def batch_transcribe(audio_dir, output_dir, model_size="small", language="fr"):
    """
    Transcribe all audio files in a directory.
    
    Args:
        audio_dir (str): Directory containing audio files
        output_dir (str): Directory where transcripts will be saved
        model_size (str): Whisper model size
        language (str): Language code
    
    Returns:
        list: Paths to all created transcript files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all audio files
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac']
    audio_files = [f for f in os.listdir(audio_dir) 
                   if any(f.lower().endswith(ext) for ext in audio_extensions)]
    
    if not audio_files:
        print(f"No audio files found in {audio_dir}")
        return []
    
    print(f"Found {len(audio_files)} audio files to transcribe")
    
    # Load model once (reuse for all files)
    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    
    transcript_files = []
    for i, audio_file in enumerate(audio_files, 1):
        audio_path = os.path.join(audio_dir, audio_file)
        
        # Create transcript filename (same name, .txt extension)
        base_name = os.path.splitext(audio_file)[0]
        transcript_path = os.path.join(output_dir, f"{base_name}.txt")
        
        try:
            print(f"\n[{i}/{len(audio_files)}] Transcribing {audio_file}...")
            result = model.transcribe(audio_path, language=language, verbose=False)
            
            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            
            transcript_files.append(transcript_path)
            print(f"✓ Saved to {transcript_path}")
            
        except Exception as e:
            print(f"✗ Error transcribing {audio_file}: {e}")
    
    print(f"\n✓ Successfully transcribed {len(transcript_files)}/{len(audio_files)} files")
    return transcript_files


if __name__ == "__main__":
    import os
    os.makedirs("data/transcripts", exist_ok=True)
    
    # Transcribe lesson 1
    result = transcribe_audio(
        "data/raw_audio/L001-LESSON.mp3",
        model_size="small",
        language="fr"
    )
    
    # Print transcript
    print("\nTranscript:")
    print(result['text'])
    
    # Print word-level timestamps
    print("\nWord-level timestamps:")
    for segment in result['segments']:
        for word in segment['words']:
            print(f"{word['start']:.3f}s - {word['end']:.3f}s : {word['word'].strip()}")

    # Save to file
    save_transcript(result, "data/transcripts/L001-LESSON.txt")
    print("\n✓ Done!")