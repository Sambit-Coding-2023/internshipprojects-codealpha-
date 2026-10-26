"""
Comprehensive Test Suite for Task 3: AI Music Generation with LSTM
Tests MIDI parsing, vocabulary creation, sequence batching, PyTorch model forward pass,
music generation with temperature sampling, MIDI file export, and Flask endpoints.
"""

import sys
import os
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src.") or mod == "app":
        del sys.modules[mod]
while str(project_root) in sys.path:
    sys.path.remove(str(project_root))
sys.path.insert(0, str(project_root))

import pytest
import torch

from src.midi_processor import MidiProcessor
from src.model import MusicLSTM
from src.generator import MusicGenerator
from app import app


@pytest.fixture(scope="module")
def base_dir():
    return Path(__file__).parent.parent


@pytest.fixture(scope="module")
def midi_processor(base_dir):
    return MidiProcessor(str(base_dir / "data" / "sample_midi"))


@pytest.fixture(scope="module")
def trained_generator(base_dir):
    return MusicGenerator(
        model_path=str(base_dir / "models" / "music_lstm.pth"),
        vocab_path=str(base_dir / "data" / "notes_vocab.json")
    )


class TestMusicGenerationTask:
    def test_midi_dataset_exists(self, midi_processor):
        """Verifies MIDI files are present in the dataset directory."""
        midi_files = list(midi_processor.data_dir.glob("*.mid"))
        assert len(midi_files) > 0, "No MIDI files found in sample_midi dataset!"
        assert len(midi_files) >= 4, f"Expected multiple MIDI files, found {len(midi_files)}"

    def test_midi_parsing_and_vocabulary(self, midi_processor):
        """Verifies MIDI files are parsed into note/chord tokens and vocab is generated."""
        notes = midi_processor.parse_all_midi(use_cache=True)
        assert len(notes) > 50, f"Parsed notes sequence too short: {len(notes)}"
        
        note_to_int, int_to_note = midi_processor.build_vocabulary(notes)
        assert len(note_to_int) > 10, "Vocabulary size unexpectedly small"
        assert len(note_to_int) == len(int_to_note), "Vocab mapping mismatch"
        
        # Test serialization / loading
        loaded_n2i, loaded_i2n = midi_processor.load_vocabulary()
        assert len(loaded_n2i) == len(note_to_int)

    def test_sequence_preparation(self, midi_processor):
        """Verifies preparation of sliding window sequences (X, y) for LSTM."""
        notes = midi_processor.parse_all_midi(use_cache=True)
        seq_len = 16
        X, y = midi_processor.prepare_sequences(notes, seq_length=seq_len)
        
        assert len(X) == len(y)
        assert len(X) == len(notes) - seq_len
        assert len(X[0]) == seq_len

    def test_model_architecture_and_forward_pass(self):
        """Tests PyTorch MusicLSTM initialization and output tensor dimensionality."""
        vocab_sz = 60
        embed_dim = 32
        hidden_dim = 128
        batch_size = 4
        seq_len = 16
        
        model = MusicLSTM(vocab_size=vocab_sz, embedding_dim=embed_dim, hidden_dim=hidden_dim, num_layers=2)
        model.eval()
        
        x = torch.randint(0, vocab_sz, (batch_size, seq_len))
        with torch.no_grad():
            logits, hidden = model(x)
            
        assert logits.shape == (batch_size, vocab_sz), f"Expected shape ({batch_size}, {vocab_sz}), got {logits.shape}"
        assert hidden[0].shape == (2, batch_size, hidden_dim)

    def test_generator_autoregressive_generation(self, trained_generator, tmp_path):
        """Tests music generation with temperature control and output verification."""
        gen_len = 24
        temp = 0.8
        output_file = tmp_path / "test_composition.mid"
        
        result = trained_generator.generate(
            length=gen_len,
            temperature=temp,
            tempo_bpm=120,
            output_filename=output_file.name
        )
        
        assert result["success"] is True
        assert len(result["notes"]) >= gen_len
        assert result["temperature"] == temp
        assert result["tempo_bpm"] == 120
        assert len(result["audio_events"]) > 0
        
        # Verify MIDI file creation
        midi_path = Path(result["midi_file"])
        assert midi_path.exists(), f"MIDI output file {midi_path} was not created!"
        assert midi_path.stat().st_size > 50, "Generated MIDI file is empty or corrupted"

    def test_audio_events_metadata(self, midi_processor):
        """Verifies note token conversion to Web Audio API event timings."""
        sample_tokens = ["C4", "E4", "G4", "C4.E4.G4", "REST", "D5"]
        events = midi_processor.get_notes_metadata(sample_tokens, default_duration=0.5)
        
        assert len(events) >= 5
        # Ensure pitch, midi number, and time are present
        for event in events:
            assert "note" in event
            assert "midi" in event
            assert "time" in event
            assert "duration" in event

    def test_flask_web_endpoints(self):
        """Tests Flask web studio routes."""
        client = app.test_client()
        
        # 1. Main UI
        res = client.get("/")
        assert res.status_code == 200
        assert b"AI Music Generation Studio" in res.data or b"AI Music Studio" in res.data or b"Music" in res.data
        
        # 2. Vocab endpoint
        res = client.get("/api/vocab")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["vocab_size"] > 0
        
        # 3. Generate endpoint
        res = client.post("/api/generate", json={"length": 20, "temperature": 0.7, "tempo": 115})
        assert res.status_code == 200
        gen_data = res.get_json()
        assert gen_data["success"] is True
        assert "filename" in gen_data
        assert "download_url" in gen_data
        assert len(gen_data["audio_events"]) > 0
        
        # 4. Download endpoint
        filename = gen_data["filename"]
        dl_res = client.get(f"/api/download/{filename}")
        assert dl_res.status_code == 200
        assert len(dl_res.data) > 50
