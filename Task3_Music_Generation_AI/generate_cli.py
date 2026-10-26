"""
Command-Line Music Generation Script for Task 3
Run: python generate_cli.py --length 64 --temperature 0.8
"""

import argparse
from pathlib import Path
from src.generator import MusicGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate new music sequences using trained LSTM neural network.")
    parser.add_argument("--length", type=int, default=48, help="Number of notes to generate (default: 48)")
    parser.add_argument("--temperature", type=float, default=0.8, help="Creativity temperature 0.2 - 1.5 (default: 0.8)")
    parser.add_argument("--tempo", type=int, default=110, help="Playback tempo in BPM (default: 110)")
    parser.add_argument("--output", type=str, default=None, help="Custom output MIDI filename")

    args = parser.parse_args()

    print("=" * 65)
    print("        AI MUSIC GENERATOR (LSTM) - COMMAND LINE INTERFACE      ")
    print("=" * 65)
    print(f"Notes Length:     {args.length}")
    print(f"Temperature:      {args.temperature}")
    print(f"Tempo (BPM):      {args.tempo}")
    print("-" * 65)

    generator = MusicGenerator()
    result = generator.generate(
        length=args.length,
        temperature=args.temperature,
        tempo_bpm=args.tempo,
        output_filename=args.output
    )

    print("\nGeneration Complete!")
    print(f"  * Total Notes:     {result['total_notes']}")
    print(f"  * MIDI File:       {result['midi_file']}")
    print(f"  * First 12 Notes:  {', '.join(result['notes'][:12])}")
    print("\nYou can open the generated .mid file in any media player (Windows Media Player, VLC, GarageBand, etc.) or run the web studio via `python app.py`.")
    print("=" * 65)


if __name__ == "__main__":
    main()
