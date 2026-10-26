"""
AI Music Generation Package
"""
from .midi_processor import MidiProcessor
from .model import MusicLSTM
from .generator import MusicGenerator

__all__ = ["MidiProcessor", "MusicLSTM", "MusicGenerator"]
