"""Render an isolated drum performance for troubleshooting and listening.

Run from the repository root:
    python -m mechanical_orchestra.drum_demo
"""

from pathlib import Path

import numpy as np
import soundfile as sf

from .midi_ensemble import Drummer, MidiInstrumentFactory, Piece


def main() -> None:
    piece = Piece(bars=8, bpm=120)
    factory = MidiInstrumentFactory("assets/soundfonts/GeneralUser-GS.sf2")
    drummer = Drummer(factory.create("drums"))
    audio = drummer.perform(piece)
    output = Path("mechanical_orchestra_drums_only.wav")
    sf.write(output, audio, 44100)
    peak = float(np.max(np.abs(audio)))
    print(f"Wrote {output}")
    print(f"Drum peak amplitude: {peak:.6f}")
    if peak < 0.001:
        print("WARNING: Drums are nearly silent. Check FluidSynth percussion setup.")


if __name__ == "__main__":
    main()
