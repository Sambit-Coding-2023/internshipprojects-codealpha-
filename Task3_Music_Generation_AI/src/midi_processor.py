"""
MIDI Processing & Preprocessing Module using music21
Extracts musical note and chord sequences from MIDI files, prepares training datasets,
and reconstructs MIDI files from generated sequences.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import music21 as m21


class MidiProcessor:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data" / "sample_midi"
        else:
            self.data_dir = Path(data_dir)

        self.vocab_file = Path(__file__).parent.parent / "data" / "notes_vocab.json"
        self.note_to_int: Dict[str, int] = {}
        self.int_to_note: Dict[int, str] = {}
        self.vocab_size: int = 0

    def parse_midi_file(self, file_path: Path) -> List[str]:
        """
        Parses a single MIDI file into a sequential list of note/chord string tokens.
        """
        notes: List[str] = []
        try:
            midi_stream = m21.converter.parse(str(file_path))
            parts = m21.instrument.partitionByInstrument(midi_stream)
            elements_to_parse = parts.parts[0].recurse() if parts else midi_stream.flat.notes

            for element in elements_to_parse:
                if isinstance(element, m21.note.Note):
                    notes.append(str(element.pitch))
                elif isinstance(element, m21.chord.Chord):
                    # Sort chord pitches by frequency/MIDI pitch
                    sorted_pitches = sorted(element.pitches, key=lambda p: p.midi)
                    chord_str = ".".join(str(p) for p in sorted_pitches)
                    notes.append(chord_str)
                elif isinstance(element, m21.note.Rest):
                    # Represent rests
                    notes.append("REST")
        except Exception as e:
            print(f"Warning: Failed to parse {file_path.name}: {e}")

        return notes

    def parse_all_midi(self, use_cache: bool = True) -> List[str]:
        """Parses all MIDI files in the data directory into a unified note stream with caching."""
        cache_file = self.vocab_file.parent / "parsed_notes_cache.json"
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached:
                        return cached
            except Exception:
                pass

        all_notes: List[str] = []
        midi_files = list(self.data_dir.glob("*.mid")) + list(self.data_dir.glob("*.midi"))

        if not midi_files:
            raise FileNotFoundError(f"No MIDI files found in {self.data_dir}")

        for mf in sorted(midi_files):
            notes = self.parse_midi_file(mf)
            all_notes.extend(notes)

        # Save cache
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(all_notes, f)
        except Exception:
            pass

        return all_notes

    def build_vocabulary(self, notes: List[str]) -> Tuple[Dict[str, int], Dict[int, str]]:
        """Constructs note-to-integer and integer-to-note mapping dictionaries."""
        unique_notes = sorted(list(set(notes)))
        self.note_to_int = {note: idx for idx, note in enumerate(unique_notes)}
        self.int_to_note = {idx: note for idx, note in enumerate(unique_notes)}
        self.vocab_size = len(unique_notes)

        # Save vocabulary to disk
        self.vocab_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vocab_file, "w", encoding="utf-8") as f:
            json.dump({
                "note_to_int": self.note_to_int,
                "int_to_note": {str(k): v for k, v in self.int_to_note.items()},
                "vocab_size": self.vocab_size
            }, f, indent=2)

        return self.note_to_int, self.int_to_note

    def load_vocabulary(self) -> Tuple[Dict[str, int], Dict[int, str]]:
        """Loads precomputed vocabulary from disk."""
        if not self.vocab_file.exists():
            raise FileNotFoundError(f"Vocabulary file not found at {self.vocab_file}. Run training or build_vocabulary first.")

        with open(self.vocab_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.note_to_int = data["note_to_int"]
            self.int_to_note = {int(k): v for k, v in data["int_to_note"].items()}
            self.vocab_size = data["vocab_size"]

        return self.note_to_int, self.int_to_note

    def prepare_sequences(self, notes: List[str], seq_length: int = 16) -> Tuple[List[List[int]], List[int]]:
        """
        Creates sliding window input-target sequences for LSTM training.
        """
        if not self.note_to_int:
            self.build_vocabulary(notes)

        network_input = []
        network_output = []

        for i in range(len(notes) - seq_length):
            seq_in = notes[i:i + seq_length]
            seq_out = notes[i + seq_length]

            network_input.append([self.note_to_int[char] for char in seq_in])
            network_output.append(self.note_to_int[seq_out])

        return network_input, network_output

    def sequence_to_midi(
        self,
        predicted_tokens: List[str],
        output_filepath: Path,
        tempo_bpm: int = 110,
        default_duration: float = 0.5
    ) -> Path:
        """
        Converts a list of note/chord string tokens into a playable MIDI file.
        """
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
        midi_stream = m21.stream.Stream()
        midi_stream.append(m21.tempo.MetronomeMark(number=tempo_bpm))
        midi_stream.append(m21.meter.TimeSignature('4/4'))

        offset = 0.0
        for token in predicted_tokens:
            if token == "REST":
                r = m21.note.Rest()
                r.quarterLength = default_duration
                r.offset = offset
                midi_stream.append(r)
                offset += default_duration
            elif "." in token:
                # Chord
                chord_pitches = token.split(".")
                new_chord = m21.chord.Chord(chord_pitches)
                new_chord.quarterLength = default_duration
                new_chord.offset = offset
                midi_stream.append(new_chord)
                offset += default_duration
            else:
                # Single note
                try:
                    new_note = m21.note.Note(token)
                    new_note.quarterLength = default_duration
                    new_note.offset = offset
                    midi_stream.append(new_note)
                    offset += default_duration
                except Exception:
                    # Skip malformed token
                    continue

        midi_stream.write("midi", fp=str(output_filepath))
        return output_filepath

    def get_notes_metadata(self, note_tokens: List[str], default_duration: float = 0.5) -> List[Dict]:
        """
        Converts note tokens to JSON metadata format (pitch name, frequency/midi pitch, duration)
        for Web Audio / Tone.js interactive piano roll synthesizer.
        """
        events = []
        current_time = 0.0

        for token in note_tokens:
            if token == "REST":
                current_time += default_duration
                continue

            if "." in token:
                # Chord pitches
                pitches = token.split(".")
                for p in pitches:
                    try:
                        m_note = m21.note.Note(p)
                        events.append({
                            "note": p,
                            "midi": m_note.pitch.midi,
                            "time": round(current_time, 2),
                            "duration": default_duration
                        })
                    except Exception:
                        pass
            else:
                try:
                    m_note = m21.note.Note(token)
                    events.append({
                        "note": token,
                        "midi": m_note.pitch.midi,
                        "time": round(current_time, 2),
                        "duration": default_duration
                    })
                except Exception:
                    pass

            current_time += default_duration

        return events


if __name__ == "__main__":
    processor = MidiProcessor()
    notes = processor.parse_all_midi()
    vocab, _ = processor.build_vocabulary(notes)
    print(f"Parsed {len(notes)} notes across MIDI dataset.")
    print(f"Unique vocabulary size: {len(vocab)} unique notes/chords.")
    X, y = processor.prepare_sequences(notes, seq_length=16)
    print(f"Prepared {len(X)} training sequence pairs.")
