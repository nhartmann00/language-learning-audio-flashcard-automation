import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from src.transcriber import transcribe_audio, save_transcript
import os

# Create transcripts folder if it doesn't exist
os.makedirs("data/transcripts", exist_ok=True)

# Test with one dialogue file - replace with your actual filename
result = transcribe_audio(
    "data/raw_audio/dialogue_01.mp3",
    model_size="base",
    language="fr"
)

# Print transcript to screen
print("\nTranscript:")
print(result['text'])

# Save it to file
save_transcript(result, "data/transcripts/dialogue_01.txt")
