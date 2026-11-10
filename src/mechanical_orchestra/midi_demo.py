"""Run: python -m mechanical_orchestra.midi_demo"""

from pathlib import Path

import soundfile as sf

from .midi_ensemble import (
    ChordChange, Drummer, MelodyPlayer, MidiInstrumentFactory,
    Note, Organist, Piece, record_ensemble,
)


def main() -> None:
    piece = Piece(bars=8, bpm=120)
    factory = MidiInstrumentFactory("assets/soundfonts/GeneralUser-GS.sf2")
    melody = [Note(pitch, i * 2, 1.7) for i, pitch in enumerate(
        [60, 62, 64, 67, 69, 67, 64, 60, 62, 64, 65, 69, 67, 65, 62, 60]
    )]
    players = [
        MelodyPlayer(factory.create("melody"), melody),
        Drummer(factory.create("drums")),
        Organist(factory.create("organ"), [
            ChordChange(1, (60, 64, 67, 71)),
            ChordChange(3, (57, 60, 64, 67)),
            ChordChange(5, (62, 65, 69, 72)),
            ChordChange(7, (55, 59, 62, 65)),
        ]),
    ]
    output = Path("mechanical_orchestra_midi_demo.wav")
    sf.write(output, record_ensemble(players, piece), 44100)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
