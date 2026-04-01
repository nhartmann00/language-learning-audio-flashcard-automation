"""
Transcript cleaning utilities for MFA alignment.
Prepares Whisper transcripts by converting numbers to words and normalizing text.
"""

import re
import os
from num2words import num2words


# French number words that can precede unit abbreviations like "m"
# (generated from num2words for 0–1,000,000)
FRENCH_NUMBER_WORDS = {
    'cent', 'cents', 'cinq', 'cinquante', 'deux', 'dix', 'douze', 'et',
    'huit', 'mille', 'million', 'neuf', 'onze', 'quarante', 'quatorze',
    'quatre', 'quinze', 'seize', 'sept', 'six', 'soixante', 'treize',
    'trente', 'trois', 'un', 'vingt', 'vingts', 'zéro',
}

# Single letters NOT in the MFA French dictionary — must be stripped
# (letters in the dict: a, c, d, e, g, i, j, l, m, n, o, p, q, s, t, u, v, w, x, y)
MFA_MISSING_LETTERS = {'b', 'f', 'h', 'k', 'r', 'z'}


def clean_transcript(text):
    """
    Clean a Whisper transcript for MFA alignment.
    Converts numbers, ordinals, and times to French words.
    Expands abbreviations and strips words not in the MFA dictionary.
    """
    # Lowercase
    text = text.lower()

    # Convert ordinals (e.g., "2e" → "deuxième")
    def replace_ordinal(match):
        num = int(match.group(1))
        return num2words(num, lang='fr', to='ordinal')

    text = re.sub(r'(\d+)(?:ème|eme|ère|er|re|e)', replace_ordinal, text)

    # Convert time notation (e.g., "8h" → "huit heures", "8h30" → "huit heures trente")
    def replace_time(match):
        hour = int(match.group(1))
        minutes = match.group(2)

        hour_word = num2words(hour, lang='fr')
        result = f"{hour_word} heure{'s' if hour > 1 else ''}"

        if minutes:
            minute_num = int(minutes)
            if minute_num > 0:
                minute_word = num2words(minute_num, lang='fr')
                result += f" {minute_word}"

        return result

    text = re.sub(r'(\d+)h(\d+)?', replace_time, text)

    # Convert any remaining standalone numbers (e.g., "2" → "deux")
    def replace_number(match):
        num = int(match.group(0))
        return num2words(num, lang='fr')

    text = re.sub(r'\b\d+\b', replace_number, text)

    # Remove hyphens (splits compound numbers like "quarante-sept" → "quarante sept")
    text = text.replace('-', ' ')

    # Remove punctuation except apostrophes
    text = re.sub(r"[^\w\s']", "", text)

    # ── New cleaning steps ────────────────────────────────────────────────

    # Expand unconditional abbreviations
    text = re.sub(r'\bkm\b', 'kilomètres', text)
    text = re.sub(r'\bmme\b', 'madame', text)
    text = re.sub(r'\bmlle\b', 'mademoiselle', text)
    text = re.sub(r'\bmr\b', 'monsieur', text)
    text = re.sub(r'\barobase\b', 'aarau base', text)

    # Expand "m" to "mètres" only when preceded by a French number word
    number_pattern = '|'.join(re.escape(w) for w in FRENCH_NUMBER_WORDS)
    text = re.sub(
        rf'\b({number_pattern})\s+m\b',
        r'\1 mètres',
        text
    )

    # Strip standalone single letters and short tokens not in the MFA dictionary
    letters_pattern = '|'.join(MFA_MISSING_LETTERS)
    text = re.sub(rf'\b({letters_pattern})\b', '', text)
    text = re.sub(r'\bfr\b', '', text)  # "fr" as in URL "point fr"

    # ── End new cleaning steps ────────────────────────────────────────────

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def prepare_mfa_corpus(wav_dir, transcript_dir, corpus_dir):
    """
    Prepare MFA corpus by pairing WAV files with cleaned transcripts.
    """
    os.makedirs(corpus_dir, exist_ok=True)

    # Find all WAV files
    wav_files = [f for f in os.listdir(wav_dir) if f.endswith('.wav')]

    print(f"Found {len(wav_files)} WAV files")

    prepared = 0
    skipped = 0

    for wav_file in wav_files:
        base_name = wav_file.replace('.wav', '')

        # Find matching transcript
        transcript_file = f"{base_name}.txt"
        transcript_path = os.path.join(transcript_dir, transcript_file)

        if not os.path.exists(transcript_path):
            print(f"⚠ No transcript for {wav_file}")
            skipped += 1
            continue

        # Read and clean transcript
        with open(transcript_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        cleaned_text = clean_transcript(raw_text)

        # Copy WAV to corpus
        wav_src = os.path.join(wav_dir, wav_file)
        wav_dst = os.path.join(corpus_dir, wav_file)

        import shutil
        shutil.copy2(wav_src, wav_dst)

        # Save cleaned transcript to corpus
        txt_dst = os.path.join(corpus_dir, f"{base_name}.txt")
        with open(txt_dst, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)

        print(f"✓ Prepared {base_name}")
        prepared += 1

    print(f"\n✓ Corpus ready: {prepared} files prepared, {skipped} skipped")
    print(f"  Corpus location: {corpus_dir}")


if __name__ == "__main__":
    # Test the cleaner
    test_cases = [
        ("2e leçon à 8h30. J'ai 47 ans.", "ordinals, time, numbers"),
        ("Exercice 1er.", "1er ordinal"),
        ("La 1re fois.", "1re ordinal"),
        ("Il habite à 5 km de Paris.", "km expansion"),
        ("La tour fait 300 m de haut.", "m after number → mètres"),
        ("Le mot m est une lettre.", "m without number → unchanged"),
        ("Mme Dupont est là.", "mme → madame"),
        ("Envoyez un mail à arobase gmail.", "arobase → aarau base"),
        ("Le site est assimil point fr.", "fr stripped"),
    ]

    for text, desc in test_cases:
        print(f"[{desc}]")
        print(f"  Original: {text}")
        print(f"  Cleaned:  {clean_transcript(text)}")
        print()