"""
Anki integration via AnkiConnect.
Creates/updates Anki cards with audio from MFA-aligned transcripts.
"""

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
    
    def find_cards_by_front(self, deck_name, front_text):
        """Find cards in a deck by front text (French phrase)."""
        # Search for cards with this exact front text in this deck
        query = f'deck:"{deck_name}" front:"{front_text}"'
        card_ids = self.invoke('findCards', query=query)
        return card_ids
    
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
        """Add audio to an existing note."""
        # Convert to absolute path
        audio_filename = os.path.abspath(audio_filename)
        
        # Get current note
        note_info = self.invoke('notesInfo', notes=[note_id])[0]
        
        # Add audio field
        self.invoke('storeMediaFile', 
            filename=os.path.basename(audio_filename),
            path=audio_filename
        )
        
        # Update note with audio reference
        front_field = note_info['fields']['Front']['value']
        audio_tag = f'[sound:{os.path.basename(audio_filename)}]'
        
        # Only add if not already there
        if audio_tag not in front_field:
            updated_front = audio_tag + '<br>' + front_field
            self.invoke('updateNoteFields', note={
                'id': note_id,
                'fields': {
                    'Front': updated_front
                }
            })
        
        return note_id


def process_csv_to_anki(config_path='config.json'):
    """
    Main function to process CSV and update Anki.
    
    Workflow:
    1. Read CSV with French/English pairs
    2. For each card:
       - Check if exists in Anki
       - If not, create it
       - Find matching audio from TextGrid
       - Extract audio clip
       - Attach audio to card
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
        
        # Check if card exists
        existing_cards = anki.find_cards_by_front(deck_name, french)
        
        # Try to find audio in any lesson
        audio_path = None
        for lesson_name, words in textgrids.items():
            match = find_phrase_timestamps(words, french.lower().replace('!', '').replace('?', '').replace(',', ''))
            
            if match:
                # Extract audio
                audio_source = os.path.join(audio_source_dir, f"{lesson_name}.wav")
                if os.path.exists(audio_source):
                    result = extract_phrase(
                        audio_source,
                        words,
                        french.lower().replace('!', '').replace('?', '').replace(',', ''),
                        audio_clips_dir,
                        padding_ms=100
                    )
                    
                    if result['found']:
                        audio_path = result['audio_path']
                        stats['audio_added'] += 1
                        print(f"  ✓ Audio found in {lesson_name}")
                        break
        
        if not audio_path:
            stats['audio_not_found'] += 1
            print(f"  ⚠ Audio not found")
        
        # Create or update card
        if not existing_cards:
            # Create new card
            try:
                anki.add_note(deck_name, french, english, audio_path)
                stats['created'] += 1
                print(f"  ✓ Card created")
            except Exception as e:
                print(f"  ✗ Error creating card: {e}")
                stats['skipped'] += 1
        else:
            # Card exists - update with audio if we found it
            if audio_path:
                try:
                    # Get note ID from card ID
                    card_info = anki.invoke('cardsInfo', cards=existing_cards)[0]
                    note_id = card_info['note']
                    anki.update_note_audio(note_id, audio_path)
                    stats['updated'] += 1
                    print(f"  ✓ Audio added to existing card")
                except Exception as e:
                    print(f"  ✗ Error updating card: {e}")
                    stats['skipped'] += 1
            else:
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