# batch_transcribe_all.py
"""
Batch transcribe all Assimil lessons (L001-L100).
"""

import os
import whisper
from src.transcript_cleaner import clean_transcript

def transcribe_all_lessons(
    audio_dir="data/raw_audio",
    output_dir="data/whisper_transcripts",
    model_size="small"
):
    """
    Transcribe all L001-L100 audio files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Load model once
    print(f"Loading Whisper model '{model_size}'...")
    model = whisper.load_model(model_size)
    
    # Find all lesson files
    lesson_files = []
    for i in range(1, 101):
        filename = f"L{i:03d}-LESSON.mp3"
        filepath = os.path.join(audio_dir, filename)
        if os.path.exists(filepath):
            lesson_files.append((i, filepath))
    
    print(f"\nFound {len(lesson_files)} lesson files")
    print("Starting transcription...\n")
    
    successes = 0
    failures = []
    
    for lesson_num, audio_path in lesson_files:
        lesson_name = f"L{lesson_num:03d}-LESSON"
        output_path = os.path.join(output_dir, f"{lesson_name}.txt")
        
        # Skip if already transcribed
        if os.path.exists(output_path):
            print(f"[{lesson_num}/100] {lesson_name} - Already transcribed, skipping")
            continue
        
        try:
            print(f"[{lesson_num}/100] Transcribing {lesson_name}...")
            
            result = model.transcribe(
                audio_path,
                language="fr",
                verbose=False,
                condition_on_previous_text=False
            )
            
            # Save raw transcript
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            
            print(f"  ✓ Saved to {output_path}")
            successes += 1
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failures.append((lesson_num, str(e)))
    
    # Summary
    print("\n" + "="*70)
    print("TRANSCRIPTION COMPLETE")
    print("="*70)
    print(f"Successfully transcribed: {successes}/{len(lesson_files)}")
    
    if failures:
        print(f"\nFailed transcriptions ({len(failures)}):")
        for lesson_num, error in failures:
            print(f"  L{lesson_num:03d}: {error}")
    
    print(f"\nTranscripts saved to: {output_dir}")


if __name__ == "__main__":
    transcribe_all_lessons()