# Language Learning Audio Flashcard Automation

Automated pipeline to extract specific words and phrases from textbook dialogue audio files and integrate them into Anki flashcards for language learning.

## Motivation

As a current temporary resident of Canada, learning French has become a vital tool in order to get closer to the Permanent Residence point threshold. Many immigrants such as myself are finding themselves in a tight spot trying to get to the cutoff.

As such, I have been looking into language learning and what effective methods are out there. The motivation for this project came from a language learning workflow approach highlighted by youtuber **languagejones** in the following [video](https://www.youtube.com/watch?v=QVpu66njzdE).

The workflow is simple:
- Get a hold of a textbook for your language at the appropriate level, and start reading it. Go through the dialogues, exercises and everything that it offers.
- As you go through the textbook, write down any words or (small) phrases that you aren't yet familiar with and intend to memorize.
- This collection of words and phrases will be used to create your Anki deck. To do it more efficiently, create an Excel spreadsheet to export this as a CSV into Anki with the word and its translation.
- Keep going through the textbook and use Anki to learn and memorize all the content of the book.
- languagejones recommends adding audio and/or images to the cards to learn quicker.

## The Problem

Here is where the tool comes in. As most language learning textbooks, the French book I'm using (Assimil French for Beginners) comes with MP3 files for all the dialogue in the book, to listen alongside reading. These audio files contain natural and authentic and context-appropriate native level pronunciation and intonation; much better quality than any Text-to-Speech tools. I want to add this audio files to my Anki deck, but chopping files manuallt is a long and tedious process given the large amount of cards there are. It will make the actual language learning very inefficient.

## The Solution

This tool automates the process of:
- Locating the specific phrases within full dialogue audio files using a CSV (from Excel or Anki).
- Extracting clean audio clips for individual words/phrases.
- Adding these clips to Anki cards for pronunciation practice.

## Features (Planned)

- [ ] Convert MP3 audio files to WAV for processing
- [ ] Perform forced alignment on transcripts and audio
- [ ] Extract audio segments based on text input
- [ ] Programmatically create/update Anki decks with audio clips
- [ ] Batch processing for ~100 dialogue files

## Tech Stack

- **Python** - Main programming language. Ecosystem for audio processing and ML tools.
- **Montreal Forced Aligner** - Audio-text alignment. Industry standard with support for French and many other languages.
- **pydub** - Audio processing and segmentation. Pythonic audio manipulation (built on ffmpeg).
- **genanki** - Anki deck generation.

## Project Status

🚧 **In Development** - Currently setting up the project structure and testing audio conversion

## Setup

(Instructions will be added as the project develops)

## Usage

(Usage examples will be added once core functionality is implemented)

## Future Enhancements

- Support for other languages
- GUI for easier phrase selection
- Audio quality normalization
- Statistics on learning progress

## License

MIT License - See LICENSE file for details
