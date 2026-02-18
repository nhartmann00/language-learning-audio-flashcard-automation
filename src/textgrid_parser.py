"""
TextGrid parser for Montreal Forced Aligner output.
Extracts word-level timestamps from MFA TextGrid files.
"""

import re
import os


def detect_encoding(filepath):
    """
    Detect the encoding of a TextGrid file.
    
    Args:
        filepath (str): Path to TextGrid file
    
    Returns:
        str: Encoding string
    """
    # Try encodings in order of likelihood for MFA output
    encodings = ['utf-16', 'utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
                
                # Check if file is readable and contains TextGrid structure
                # (all TextGrid files have these markers)
                if 'File type = "ooTextFile"' in content and 'name = "words"' in content:
                    print(f"✓ Detected encoding: {encoding}")
                    return encoding
                    
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Default fallback
    print("⚠ Could not detect encoding, defaulting to utf-8")
    return 'utf-8'


def parse_textgrid(filepath):
    """
    Parse MFA TextGrid file and extract word-level timestamps.
    
    Args:
        filepath (str): Path to .TextGrid file
    
    Returns:
        list: List of dicts with 'word', 'start', 'end' keys
        Example: [
            {'word': 'bonjour', 'start': 7.63, 'end': 8.23},
            {'word': 'jean', 'start': 8.23, 'end': 8.61},
            ...
        ]
    """
    # Detect and read with correct encoding
    encoding = detect_encoding(filepath)
    
    with open(filepath, 'r', encoding=encoding) as f:
        content = f.read()
    
    # Extract word tier only (between item [1] and item [2])
    word_tier_match = re.search(
        r'name = "words".*?(?=item \[2\])',
        content,
        re.DOTALL
    )
    
    if not word_tier_match:
        print("✗ Could not find word tier in TextGrid")
        return []
    
    word_tier = word_tier_match.group(0)
    
    # Extract all intervals
    interval_pattern = re.compile(
        r'xmin = ([\d.]+)\s+xmax = ([\d.]+)\s+text = "([^"]*)"'
    )
    
    intervals = interval_pattern.findall(word_tier)
    
    # Build word list, skipping empty intervals and 'spn' markers
    words = []
    for start, end, text in intervals:
        text = text.strip()
        
        # Skip empty intervals (silence) and spn markers
        if not text or text == 'spn':
            continue
        
        words.append({
            'word': text,
            'start': float(start),
            'end': float(end)
        })
    
    return words


def find_phrase_timestamps(words, phrase):
    """
    Find timestamps for a specific phrase in the word list.
    
    Args:
        words (list): List of word dicts from parse_textgrid()
        phrase (str): Phrase to find (e.g. "comment allez vous")
    
    Returns:
        dict: {'phrase': str, 'start': float, 'end': float} or None if not found
    """
    # Clean and split phrase into words
    phrase_words = phrase.lower().strip().split()
    n = len(phrase_words)
    
    # Slide through word list looking for match
    for i in range(len(words) - n + 1):
        window = [w['word'].lower() for w in words[i:i+n]]
        
        if window == phrase_words:
            return {
                'phrase': phrase,
                'start': words[i]['start'],
                'end': words[i+n-1]['end']
            }
    
    return None


def find_all_phrases(words, phrases):
    """
    Find timestamps for multiple phrases.
    
    Args:
        words (list): List of word dicts from parse_textgrid()
        phrases (list): List of phrases to find
    
    Returns:
        list: List of results with found/not found status
    """
    results = []
    
    for phrase in phrases:
        match = find_phrase_timestamps(words, phrase)
        
        if match:
            results.append({
                'phrase': phrase,
                'start': match['start'],
                'end': match['end'],
                'found': True
            })
            print(f"✓ Found '{phrase}': {match['start']:.3f}s - {match['end']:.3f}s")
        else:
            results.append({
                'phrase': phrase,
                'start': None,
                'end': None,
                'found': False
            })
            print(f"⚠ Not found: '{phrase}' - flagged for manual review")
    
    return results


if __name__ == "__main__":
    # Test parsing
    textgrid_path = "data/mfa_output/L001-LESSON.TextGrid"
    
    print("Parsing TextGrid file...")
    words = parse_textgrid(textgrid_path)
    
    print(f"\nFound {len(words)} words\n")
    print("Word-level timestamps:")
    for w in words:
        print(f"  {w['start']:.3f}s - {w['end']:.3f}s : {w['word']}")
    
    # Test phrase lookup
    print("\nTesting phrase lookup:")
    test_phrases = [
        "comment allez vous",
        "bonjour",
        "ça va très bien",
        "merci",
        "je vous présente ma fille"
    ]
    
    results = find_all_phrases(words, test_phrases)