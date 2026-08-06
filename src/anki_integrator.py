"""
Anki integration via AnkiConnect.
Creates/updates Anki cards with audio from MFA-aligned transcripts.
"""

import re
import requests
import json
import csv
import os
from src.textgrid_parser import parse_textgrid, find_phrase_timestamps
from src.audio_extractor import extract_phrase


class AnkiConnector:
    """Interface to AnkiConnect API."""
    
    def __init__(self, url="http://localhost:8765"):
        self.url = url
    
    def invoke(self, action, **params):
        """Call AnkiConnect API."""
        payload = {
            'action': action,
            'version': 6,
            'params': params
        }
        
        response = requests.post(self.url, json=payload)
        result = response.json()
        
        if result.get('error'):
            raise Exception(f"AnkiConnect error: {result['error']}")
        
        return result.get('result')
    
    def deck_exists(self, deck_name):
        """Check if a deck exists."""
        decks = self.invoke('deckNames')
        return deck_name in decks
    
    def create_deck(self, deck_name):
        """Create a new deck."""
        return self.invoke('createDeck', deck=deck_name)
    
    def add_note(self, deck_name, front, back, audio_filename=None):
        """Add a new note (card) to Anki."""
        note = {
            'deckName': deck_name,
            'modelName': 'Basic',
            'fields': {
                'Front': front,
                'Back': back
            },
            'tags': ['assimil', 'auto-generated']
        }
        
        # Add audio if provided
        if audio_filename:
            # Convert to absolute path
            audio_filename = os.path.abspath(audio_filename)
            note['audio'] = [{
                'path': audio_filename,
                'filename': os.path.basename(audio_filename),
                'fields': ['Front']
            }]
        
        return self.invoke('addNote', note=note)
    
    def update_note_audio(self, note_id, audio_filename):
        """Add audio to an existing note without modifying field text.
        
        Uses AnkiConnect's storeMediaFile to save the audio, then updates
        the note using the same audio attachment mechanism as add_note —
        keeping the Front field text intact.
        """
        audio_filename = os.path.abspath(audio_filename)
        media_name = os.path.basename(audio_filename)
        
        # Store the media file in Anki's collection
        self.invoke('storeMediaFile', 
            filename=media_name,
            path=audio_filename
        )
        
        # Get current note to check if audio is already attached
        note_info = self.invoke('notesInfo', notes=[note_id])[0]
        front_value = note_info['fields']['Front']['value']
        
        audio_tag = f'[sound:{media_name}]'
        
        # Only update if this audio isn't already on the card
        if audio_tag not in front_value:
            # Append sound tag after the existing text (not prepended)
            # This keeps the visible text clean and the audio plays on card display
            self.invoke('updateNoteFields', note={
                'id': note_id,
                'fields': {
                    'Front': front_value + audio_tag
                }
            })
        
        return note_id


def find_and_extract_audio(french, textgrids, audio_source_dir, audio_clips_dir):
    """
    Search all TextGrids for a phrase and extract its audio clip.

    Args:
        french (str): The French phrase to search for
        textgrids (dict): Loaded TextGrid word lists keyed by lesson name
        audio_source_dir (str): Directory containing source WAV files
        audio_clips_dir (str): Directory where extracted clips are saved

    Returns:
        str or None: Path to extracted audio clip, or None if not found
    """
    phrase = french.lower().replace('!', '').replace('?', '').replace(',', '')

    for lesson_name, words in textgrids.items():
        match = find_phrase_timestamps(words, phrase)

        if match:
            audio_source = os.path.join(audio_source_dir, f"{lesson_name}.wav")
            if os.path.exists(audio_source):
                result = extract_phrase(
                    audio_source,
                    words,
                    phrase,
                    audio_clips_dir,
                    padding_ms=100
                )
                if result['found']:
                    print(f"  ✓ Audio found in {lesson_name}")
                    return result['audio_path']

    return None


def process_csv_to_anki(config_path='config.json'):
    """
    Main function to process CSV and update Anki.

    Workflow:
    1. Read CSV with French/English pairs
    2. For each card:
       - Check if it exists in Anki
       - If it exists and already has audio, skip immediately (no audio search)
       - If it exists but has no audio, search for audio and attach if found
       - If it doesn't exist, search for audio and create the card
    """
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    deck_name = config['deck_name']
    csv_path = config['csv_path']
    audio_clips_dir = config['audio_clips_dir']
    textgrid_dir = config['textgrid_dir']
    audio_source_dir = config['audio_source_dir']
    
    # Connect to Anki
    anki = AnkiConnector(config.get('anki_connect_url', 'http://localhost:8765'))
    
    # Ensure deck exists
    if not anki.deck_exists(deck_name):
        print(f"Creating deck: {deck_name}")
        anki.create_deck(deck_name)
    
    # Load all available TextGrids
    textgrids = {}
    for filename in os.listdir(textgrid_dir):
        if filename.endswith('.TextGrid'):
            lesson_name = filename.replace('.TextGrid', '')
            textgrid_path = os.path.join(textgrid_dir, filename)
            textgrids[lesson_name] = parse_textgrid(textgrid_path)
            print(f"Loaded TextGrid: {lesson_name} ({len(textgrids[lesson_name])} words)")
    
    # Process CSV
    print(f"\nReading CSV: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Found {len(rows)} cards in CSV\n")

    # Load all existing notes from the deck once — avoids per-card API calls
    print("Loading existing Anki notes...")
    all_card_ids = anki.invoke('findNotes', query=f'deck:"{deck_name}"')
    existing_notes = {}
    if all_card_ids:
        notes_info = anki.invoke('notesInfo', notes=all_card_ids)
        for note in notes_info:
            clean_front = re.sub(r'\[sound:[^\]]+\]', '', note['fields']['Front']['value']).strip()
            existing_notes[clean_front] = note
    print(f"Found {len(existing_notes)} existing notes in deck\n")

    stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'audio_added': 0,
        'audio_not_found': 0
    }
    
    for i, row in enumerate(rows, 1):
        french = row['Front'].strip()
        english = row['Back'].strip()
        
        # Skip empty rows
        if not french or not english:
            print(f"[{i}/{len(rows)}] (empty row - skipped)\n")
            stats['skipped'] += 1
            continue
        
        print(f"[{i}/{len(rows)}] {french}")
        
        # Check if card exists via pre-loaded dict (O(1) lookup, no API call)
        existing_note = existing_notes.get(french)

        if not existing_note:
            # New card — search for audio then create
            audio_path = find_and_extract_audio(french, textgrids, audio_source_dir, audio_clips_dir)

            if audio_path:
                stats['audio_added'] += 1
            else:
                stats['audio_not_found'] += 1
                print(f"  ⚠ Audio not found")

            try:
                anki.add_note(deck_name, french, english, audio_path)
                stats['created'] += 1
                print(f"  ✓ Card created")
            except Exception as e:
                print(f"  ✗ Error creating card: {e}")
                stats['skipped'] += 1

        else:
            # Card exists — check for audio before doing any work
            note_id = existing_note['noteId']
            front_value = existing_note['fields']['Front']['value']

            if '[sound:' in front_value:
                # Already has audio — skip immediately, no TextGrid search
                stats['skipped'] += 1
                print(f"  - Already has audio, skipping")
                print()
                continue

            # No audio yet — search for it now
            audio_path = find_and_extract_audio(french, textgrids, audio_source_dir, audio_clips_dir)

            if audio_path:
                try:
                    anki.update_note_audio(note_id, audio_path)
                    stats['audio_added'] += 1
                    stats['updated'] += 1
                    print(f"  ✓ Audio added to existing card")
                except Exception as e:
                    print(f"  ✗ Error updating card: {e}")
                    stats['skipped'] += 1
            else:
                stats['audio_not_found'] += 1
                print(f"  - Card exists, no audio to add")
                stats['skipped'] += 1

        print()
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Cards created: {stats['created']}")
    print(f"Cards updated with audio: {stats['updated']}")
    print(f"Cards skipped: {stats['skipped']}")
    print(f"Audio clips found: {stats['audio_added']}")
    print(f"Audio not found: {stats['audio_not_found']}")
    print("\n✓ Done! Check Anki to see your updated deck.")


if __name__ == "__main__":
    process_csv_to_anki()
