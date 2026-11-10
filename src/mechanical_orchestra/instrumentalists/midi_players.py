"""Melody, organ and drum performers; each records a complete take."""
from typing import Sequence
import numpy as np
from ..musical_material import Note, ChordChange, Piece, MidiEvent
from ..instruments.fluidsynth import FluidSynthInstrument

class MelodyPlayer:
    def __init__(self, instrument: FluidSynthInstrument, notes: Sequence[Note]):
        self.instrument, self.notes = instrument, list(notes)

    def events(self, piece: Piece) -> list[MidiEvent]:
        events = []
        for note in self.notes:
            if note.start_beat < 0 or note.duration_beats <= 0:
                raise ValueError("Invalid note timing")
            events.extend([MidiEvent(note.start_beat, note.pitch, note.velocity, True),
                           MidiEvent(note.start_beat + note.duration_beats, note.pitch, 0, False)])
        return events

    def perform(self, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        return self.instrument.render(self.events(piece), piece, sample_rate)


class Organist:
    def __init__(self, instrument: FluidSynthInstrument, changes: Sequence[ChordChange]):
        self.instrument, self.changes = instrument, sorted(changes, key=self._beat)

    @staticmethod
    def _beat(chord: ChordChange) -> float:
        return chord.start_beat if chord.start_beat is not None else (chord.start_bar - 1) * 4

    def events(self, piece: Piece) -> list[MidiEvent]:
        def position(chord: ChordChange) -> float:
            return (chord.start_beat if chord.start_beat is not None
                    else (chord.start_bar - 1) * piece.beats_per_bar)

        changes = sorted(self.changes, key=position)
        if not changes or position(changes[0]) != 0:
            raise ValueError("Organist needs an initial chord at beat 0")
        events = []
        for i, chord in enumerate(changes):
            start = position(chord)
            if not 0 <= start < piece.total_beats:
                raise ValueError("Chord change outside piece")
            end = position(changes[i + 1]) if i + 1 < len(changes) else piece.total_beats
            if end <= start:
                raise ValueError("Chord changes must be at distinct increasing beats")
            for pitch in chord.pitches:
                events.extend([MidiEvent(start, pitch, 85, True),
                               MidiEvent(end, pitch, 0, False)])
        return events

    def perform(self, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        return self.instrument.render(self.events(piece), piece, sample_rate)


class Drummer:
    """A punchy, repeating 4/4 groove with a small fill every four bars."""

    def __init__(self, instrument: FluidSynthInstrument, gain: float = 1.8):
        self.instrument = instrument
        self.gain = gain

    def events(self, piece: Piece) -> list[MidiEvent]:
        events: list[MidiEvent] = []

        def hit(beat: float, pitch: int, velocity: int, length: float = 0.10) -> None:
            events.append(MidiEvent(beat, pitch, velocity, True))
            events.append(MidiEvent(min(beat + length, piece.total_beats), pitch, 0, False))

        for bar in range(piece.bars):
            start = bar * piece.beats_per_bar
            # Eight hi-hats per 4/4 bar, alternating accents.
            for step in range(piece.beats_per_bar * 2):
                hit(start + step * 0.5, 42, 90 if step % 2 == 0 else 70)

            # Kick on 1 and 3, plus a pickup on the 'and' of 3.
            for offset in (0, 2, 2.5):
                if offset < piece.beats_per_bar:
                    hit(start + offset, 36, 118 if offset == 0 else 105)

            # Snare on beats 2 and 4.
            for offset in (1, 3):
                if offset < piece.beats_per_bar:
                    hit(start + offset, 38, 120)

            # A simple snare fill at the end of every fourth bar.
            if (bar + 1) % 4 == 0 and piece.beats_per_bar == 4:
                for offset in (3.25, 3.5, 3.75):
                    hit(start + offset, 38, 78 + int(offset * 8), 0.07)

        return events

    def perform(self, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        return self.instrument.render(self.events(piece), piece, sample_rate) * self.gain


