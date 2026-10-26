"""
Synthetic & Classical MIDI Generator with Transposition Augmentation
Generates foundational compositions and automatically transposes them across keys
to build an augmented training dataset for deep learning.
"""

from pathlib import Path
import music21 as m21


def create_classical_motif_1(output_path: Path):
    """Mozart-style Sonata Allegro motif in C Major"""
    s = m21.stream.Stream()
    s.append(m21.tempo.MetronomeMark(number=120))
    s.append(m21.meter.TimeSignature('4/4'))
    s.append(m21.key.Key('C'))

    notes_and_durations = [
        ("C4", 1.0), ("E4", 0.5), ("G4", 0.5), ("C5", 1.0), ("B4", 0.5), ("A4", 0.5),
        ("G4", 1.0), ("E4", 0.5), ("F4", 0.5), ("G4", 1.0), ("E4", 1.0),
        ("F4", 1.0), ("A4", 0.5), ("C5", 0.5), ("D5", 1.0), ("B4", 1.0),
        ("C5", 2.0), ("G4", 1.0), ("E4", 1.0),
        ("C4.E4.G4", 2.0), ("F4.A4.C5", 2.0),
        ("G4.B4.D5", 2.0), ("C4.E4.G4.C5", 2.0),
        ("E4", 0.5), ("G4", 0.5), ("C5", 0.5), ("E5", 0.5),
        ("D5", 0.5), ("B4", 0.5), ("G4", 0.5), ("F4", 0.5),
        ("E4", 1.0), ("D4", 1.0), ("C4", 2.0)
    ]

    for item, dur in notes_and_durations:
        if "." in item:
            c = m21.chord.Chord(item.split("."))
            c.quarterLength = dur
            s.append(c)
        else:
            n = m21.note.Note(item)
            n.quarterLength = dur
            s.append(n)

    s.write("midi", fp=str(output_path))


def create_bach_motif_2(output_path: Path):
    """J.S. Bach Two-Part Invention style motif in D Minor"""
    s = m21.stream.Stream()
    s.append(m21.tempo.MetronomeMark(number=108))
    s.append(m21.meter.TimeSignature('4/4'))
    s.append(m21.key.Key('d'))

    notes_and_durations = [
        ("D4", 0.5), ("E4", 0.5), ("F4", 0.5), ("G4", 0.5), ("A4", 1.0), ("F4", 0.5), ("D4", 0.5),
        ("B-4", 1.0), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5), ("E4", 0.5), ("D4", 1.0),
        ("C#4", 1.0), ("D4", 0.5), ("E4", 0.5), ("A3", 1.0), ("C#4", 1.0),
        ("D4.F4.A4", 2.0), ("G3.B-3.D4", 2.0),
        ("A3.C#4.E4", 2.0), ("D4.F4.A4", 2.0),
        ("F4", 0.5), ("A4", 0.5), ("D5", 0.5), ("C5", 0.5),
        ("B-4", 0.5), ("A4", 0.5), ("G4", 0.5), ("F4", 0.5),
        ("E4", 1.0), ("C#4", 1.0), ("D4", 2.0)
    ]

    for item, dur in notes_and_durations:
        if "." in item:
            c = m21.chord.Chord(item.split("."))
            c.quarterLength = dur
            s.append(c)
        else:
            n = m21.note.Note(item)
            n.quarterLength = dur
            s.append(n)

    s.write("midi", fp=str(output_path))


def create_chopin_motif_3(output_path: Path):
    """Chopin Nocturne style lyrical melody in E-flat Major"""
    s = m21.stream.Stream()
    s.append(m21.tempo.MetronomeMark(number=90))
    s.append(m21.meter.TimeSignature('3/4'))
    s.append(m21.key.Key('E-'))

    notes_and_durations = [
        ("G4", 1.5), ("B-4", 0.5), ("E-5", 1.0),
        ("D5", 1.5), ("C5", 0.5), ("B-4", 1.0),
        ("A-4", 1.0), ("C5", 1.0), ("E-5", 1.0),
        ("G4.B-4.E-5", 3.0),
        ("A-4.C5.E-5", 1.5), ("B-4.D5.F5", 1.5),
        ("E-4.G4.B-4", 3.0),
        ("F4", 1.0), ("A-4", 1.0), ("D5", 1.0),
        ("E-5", 2.0), ("B-4", 1.0),
        ("G4", 2.0), ("E-4", 1.0)
    ]

    for item, dur in notes_and_durations:
        if "." in item:
            c = m21.chord.Chord(item.split("."))
            c.quarterLength = dur
            s.append(c)
        else:
            n = m21.note.Note(item)
            n.quarterLength = dur
            s.append(n)

    s.write("midi", fp=str(output_path))


def create_jazz_motif_4(output_path: Path):
    """Jazz Blues progression in F"""
    s = m21.stream.Stream()
    s.append(m21.tempo.MetronomeMark(number=130))
    s.append(m21.meter.TimeSignature('4/4'))

    notes_and_durations = [
        ("F4.A4.C5.E-5", 1.5), ("F4", 0.5), ("A-4", 0.5), ("A4", 0.5), ("C5", 1.0),
        ("B-4.D5.F5.A-5", 1.5), ("D5", 0.5), ("F5", 0.5), ("D5", 0.5), ("B-4", 1.0),
        ("G4.B4.D5.F5", 1.0), ("C4.E4.G4.B-4", 1.0), ("F4.A4.C5", 2.0),
        ("A4", 0.5), ("C5", 0.5), ("E-5", 0.5), ("F5", 0.5),
        ("E5", 0.5), ("E-5", 0.5), ("C5", 1.0),
        ("F4.A4.C5.E-5", 2.0)
    ]

    for item, dur in notes_and_durations:
        if "." in item:
            c = m21.chord.Chord(item.split("."))
            c.quarterLength = dur
            s.append(c)
        else:
            n = m21.note.Note(item)
            n.quarterLength = dur
            s.append(n)

    s.write("midi", fp=str(output_path))


def create_augmented_dataset(target_dir: Path):
    """Generates base motifs and applies standard musical pitch transposition augmentation."""
    target_dir.mkdir(parents=True, exist_ok=True)
    base_files = [
        ("sonata_c_major", create_classical_motif_1),
        ("invention_d_minor", create_bach_motif_2),
        ("nocturne_eb_major", create_chopin_motif_3),
        ("jazz_blues_f", create_jazz_motif_4)
    ]

    count = 0
    for name, creator in base_files:
        base_path = target_dir / f"{name}.mid"
        creator(base_path)
        count += 1

        # Pitch transposition data augmentation (-5 to +6 semitones)
        try:
            base_stream = m21.converter.parse(str(base_path))
            for interval_steps in [-4, -2, 2, 4, 5]:
                transposed = base_stream.transpose(interval_steps)
                out_name = f"{name}_transp_{interval_steps}.mid"
                transposed.write("midi", fp=str(target_dir / out_name))
                count += 1
        except Exception as e:
            print(f"Warning: transposition skipped for {name}: {e}")

    print(f"Successfully generated {count} augmented MIDI files in {target_dir}")


if __name__ == "__main__":
    out_dir = Path(__file__).parent.parent / "data" / "sample_midi"
    create_augmented_dataset(out_dir)
