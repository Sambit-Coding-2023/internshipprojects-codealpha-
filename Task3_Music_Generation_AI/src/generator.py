"""
Music Sequence Generator Module
Loads trained Stacked LSTM weights and generates novel musical note sequences with temperature control.
Exports to MIDI and WebAudio event metadata.
"""

from datetime import datetime
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional
import torch

try:
    from .midi_processor import MidiProcessor
    from .model import MusicLSTM
except ImportError:
    from midi_processor import MidiProcessor
    from model import MusicLSTM


class MusicGenerator:
    def __init__(
        self,
        model_path: Optional[str] = None,
        vocab_path: Optional[str] = None
    ):
        base_dir = Path(__file__).parent.parent
        if model_path is None:
            model_path = str(base_dir / "models" / "music_lstm.pth")
        if vocab_path is None:
            vocab_path = str(base_dir / "data" / "notes_vocab.json")

        self.model_path = Path(model_path)
        self.vocab_path = Path(vocab_path)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.processor = MidiProcessor()
        self.note_to_int, self.int_to_note = self.processor.load_vocabulary()
        self.vocab_size = len(self.note_to_int)

        self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {self.model_path}. Run train.py first.")

        checkpoint = torch.load(self.model_path, map_location=self.device)
        self.seq_length = checkpoint.get("seq_length", 16)
        hidden_dim = checkpoint.get("hidden_dim", 256)
        embedding_dim = checkpoint.get("embedding_dim", 64)

        self.model = MusicLSTM(
            vocab_size=self.vocab_size,
            embedding_dim=embedding_dim,
            hidden_dim=hidden_dim,
            num_layers=2,
            dropout=0.0
        ).to(self.device)

        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()

    def generate(
        self,
        length: int = 48,
        temperature: float = 0.8,
        seed_genre: Optional[str] = None,
        tempo_bpm: int = 110,
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a sequence of musical notes using temperature-controlled sampling.
        Returns:
            Dictionary containing generated notes, MIDI file path, and Web Audio events.
        """
        all_notes = self.processor.parse_all_midi()

        # Determine seed
        if len(all_notes) > self.seq_length:
            max_start = len(all_notes) - self.seq_length
            start_idx = random.randint(0, max_start)
            seed_notes = all_notes[start_idx:start_idx + self.seq_length]
        else:
            seed_notes = list(self.note_to_int.keys())[:self.seq_length]

        current_sequence = [self.note_to_int[n] for n in seed_notes]
        generated_tokens: List[str] = list(seed_notes)

        # Autoregressive generation loop
        with torch.no_grad():
            for _ in range(length):
                input_tensor = torch.tensor([current_sequence[-self.seq_length:]], dtype=torch.long).to(self.device)
                logits, _ = self.model(input_tensor)

                # Apply temperature scaling
                # T < 1.0 makes distribution sharper (conservative/coherent)
                # T > 1.0 makes distribution flatter (creative/surprising)
                temp = max(0.1, min(temperature, 2.0))
                scaled_logits = logits[0] / temp
                probs = torch.softmax(scaled_logits, dim=-1)

                # Sample from probability distribution
                pred_idx = torch.multinomial(probs, num_samples=1).item()
                pred_note = self.int_to_note[pred_idx]

                generated_tokens.append(pred_note)
                current_sequence.append(pred_idx)

        # Export to MIDI
        outputs_dir = Path(__file__).parent.parent / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"composition_{timestamp}.mid"

        midi_path = outputs_dir / output_filename
        self.processor.sequence_to_midi(
            predicted_tokens=generated_tokens,
            output_filepath=midi_path,
            tempo_bpm=tempo_bpm,
            default_duration=0.5
        )

        # Note metadata for Tone.js interactive piano roll
        audio_events = self.processor.get_notes_metadata(generated_tokens, default_duration=0.5)

        return {
            "success": True,
            "notes": generated_tokens,
            "total_notes": len(generated_tokens),
            "midi_file": str(midi_path),
            "filename": output_filename,
            "temperature": temperature,
            "tempo_bpm": tempo_bpm,
            "audio_events": audio_events
        }


if __name__ == "__main__":
    generator = MusicGenerator()
    print("Generating AI music composition...")
    res = generator.generate(length=32, temperature=0.85)
    print(f"Generated {res['total_notes']} notes!")
    print(f"MIDI saved to: {res['midi_file']}")
    print(f"Sample notes: {res['notes'][:10]}")
