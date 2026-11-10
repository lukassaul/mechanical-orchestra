"""Perform the Giant Steps MusicXML draft with our existing trio.

Run from the repository root:
    python -m mechanical_orchestra.giant_steps_demo
"""

from pathlib import Path
import argparse

import soundfile as sf

from .midi_ensemble import Drummer, MelodyPlayer, MidiInstrumentFactory, Organist, record_ensemble
from .musicxml import load_lead_sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, default=Path("scores/giant_steps_draft.musicxml"))
    parser.add_argument("--bpm", type=float, default=160, help="Playback tempo (score marking: 286)")
    args = parser.parse_args()

    score = load_lead_sheet(args.score, bpm=args.bpm)
    factory = MidiInstrumentFactory("assets/soundfonts/GeneralUser-GS.sf2")
    performers = [
        MelodyPlayer(factory.create("melody"), score.melody),
        Organist(factory.create("organ"), score.chords),
        Drummer(factory.create("drums")),
    ]
    output = Path("mechanical_orchestra_giant_steps.wav")
    audio = record_ensemble(performers, score.piece)
    sf.write(output, audio, 44100)
    print(f"Read {score.piece.bars} bars, {len(score.melody)} notes, {len(score.chords)} chords")
    print(f"Wrote {output} at {score.piece.bpm:g} BPM")


if __name__ == "__main__":
    main()
