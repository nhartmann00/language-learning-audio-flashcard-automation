"""
Audio conversion utilities for language learning flashcard automation.
Converts MP3 files to WAV format for forced alignment processing.
"""

from pydub import AudioSegment
import os


def mp3_to_wav(mp3_path, wav_path=None):
    """
    Convert MP3 file to WAV format, preserving original quality.
    
    Args:
        mp3_path (str): Path to input MP3 file
        wav_path (str, optional): Path for output WAV file. 
                                   If None, uses same name with .wav extension
    
    Returns:
        str: Path to the created WAV file
    """
    # Generate output path if not provided
    if wav_path is None:
        wav_path = mp3_path.replace('.mp3', '.wav')
    
    # Load MP3 file
    print(f"Loading {mp3_path}...")
    audio = AudioSegment.from_mp3(mp3_path)
    
    # Export as WAV (preserving original quality)
    print(f"Exporting to {wav_path}...")
    audio.export(wav_path, format="wav")
    
    print(f"✓ Conversion complete: {wav_path}")
    return wav_path


def batch_convert_mp3_to_wav(input_dir, output_dir):
    """
    Convert all MP3 files in a directory to WAV format.
    
    Args:
        input_dir (str): Directory containing MP3 files
        output_dir (str): Directory where WAV files will be saved
    
    Returns:
        list: Paths to all created WAV files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all MP3 files
    mp3_files = [f for f in os.listdir(input_dir) if f.endswith('.mp3')]
    
    if not mp3_files:
        print(f"No MP3 files found in {input_dir}")
        return []
    
    print(f"Found {len(mp3_files)} MP3 files to convert")
    
    wav_files = []
    for mp3_file in mp3_files:
        mp3_path = os.path.join(input_dir, mp3_file)
        wav_path = os.path.join(output_dir, mp3_file.replace('.mp3', '.wav'))
        
        try:
            mp3_to_wav(mp3_path, wav_path)
            wav_files.append(wav_path)
        except Exception as e:
            print(f"✗ Error converting {mp3_file}: {e}")
    
    print(f"\n✓ Successfully converted {len(wav_files)}/{len(mp3_files)} files")
    return wav_files


if __name__ == "__main__":
    # Test with a single file conversion
    # Example usage:
    # mp3_to_wav("data/raw_audio/test.mp3")
    
    # Or batch convert all files:
    # batch_convert_mp3_to_wav("data/raw_audio", "data/processed_audio")
    
    print("Audio converter module loaded. Import and use functions as needed.")
