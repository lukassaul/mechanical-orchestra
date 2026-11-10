"""Whole-piece MIDI performers backed by a single offline FluidSynth render per take."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .audio_effects import echo, leslie


@dataclass(frozen=True)
class Note:
    pitch: int
    start_beat: float
    duration_beats: float
    velocity: int = 90


@dataclass(frozen=True)
class ChordChange:
    start_bar: int  # 1-based
    pitches: tuple[int, ...]
    start_beat: float | None = None  # absolute, zero-based; overrides start_bar


@dataclass(frozen=True)
class Piece:
    bars: int = 8
    bpm: float = 120
    beats_per_bar: int = 4

    def __post_init__(self):
        if self.bars < 1 or self.bpm <= 0 or self.beats_per_bar < 1:
            raise ValueError("Invalid piece duration or meter")

    @property
    def total_beats(self) -> int:
        return self.bars * self.beats_per_bar


@dataclass(frozen=True)
class MidiEvent:
    beat: float
    pitch: int
    velocity: int
    on: bool


class FluidSynthInstrument:
    """Instrument owns MIDI rendering; performers own musical decisions."""

    def __init__(self, soundfont: str | Path, program: int = 19, drums: bool = False, effect: str | None = None):
        self.soundfont = Path(soundfont)
        self.program = program
        self.drums = drums
        self.effect = effect

    def render(self, events: Sequence[MidiEvent], piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        try:
            import fluidsynth
        except ImportError as exc:
            raise RuntimeError("Install pyfluidsynth and the native FluidSynth library") from exc
        if not self.soundfont.is_file():
            raise FileNotFoundError(f"SoundFont missing: {self.soundfont}. Run python scripts/install_soundfonts.py")
        synth = fluidsynth.Synth(samplerate=sample_rate)
        try:
            sfid = synth.sfload(str(self.soundfont))
            if sfid < 0:
                raise RuntimeError(f"Cannot load SoundFont: {self.soundfont}")
            channel = 9 if self.drums else 0
            # General MIDI percussion kits live in bank 128. Selecting the
            # SoundFont alone does not reliably configure channel 10.
            bank = 128 if self.drums else 0
            status = synth.program_select(channel, sfid, bank, self.program)
            if status != 0:
                raise RuntimeError(
                    f"Could not select SoundFont preset: bank={bank}, program={self.program}"
                )
            total_samples = round(piece.total_beats * 60 / piece.bpm * sample_rate)
            result = np.zeros((total_samples, 2), dtype=np.float32)
            cursor = 0
            # Note-offs before note-ons at identical timestamps.
            ordered = sorted(events, key=lambda e: (e.beat, e.on))
            for event in ordered:
                if not (0 <= event.beat <= piece.total_beats):
                    raise ValueError("MIDI event outside piece")
                if not (0 <= event.pitch <= 127 and 0 <= event.velocity <= 127):
                    raise ValueError("Invalid MIDI pitch or velocity")
                target = round(event.beat * 60 / piece.bpm * sample_rate)
                if target > cursor:
                    chunk = np.asarray(synth.get_samples(target - cursor), dtype=np.float32)
                    result[cursor:target] = chunk.reshape(-1, 2) / 32768.0
                    cursor = target
                if event.on:
                    synth.noteon(channel, event.pitch, event.velocity)
                else:
                    synth.noteoff(channel, event.pitch)
            if cursor < total_samples:
                chunk = np.asarray(synth.get_samples(total_samples - cursor), dtype=np.float32)
                result[cursor:] = chunk.reshape(-1, 2) / 32768.0
            if self.effect == 'leslie':
                result = leslie(result, sample_rate)
            elif self.effect == 'echo':
                result = echo(result, sample_rate)
            elif self.effect is not None:
                raise ValueError(f'Unknown instrument effect: {self.effect}')
            return result
        finally:
            synth.delete()


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


class MidiInstrumentFactory:
    def __init__(self, soundfont: str | Path):
        self.soundfont = Path(soundfont)

    def create(self, kind: str) -> FluidSynthInstrument:
        presets = {"organ": (19, False, "leslie"), "melody": (66, False, "echo"), "drums": (0, True, None)}
        if kind not in presets:
            raise ValueError(f"Unknown MIDI instrument: {kind}")
        program, drums, effect = presets[kind]
        return FluidSynthInstrument(self.soundfont, program, drums, effect)


def record_ensemble(performers: Sequence, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
    """Conductor-facing whole-take interface: each performer returns a full recording."""
    recordings = [np.asarray(p.perform(piece, sample_rate), dtype=np.float64) for p in performers]
    if not recordings:
        raise ValueError("Need at least one performer")
    expected = round(piece.total_beats * 60 / piece.bpm * sample_rate)
    for audio in recordings:
        if audio.shape != (expected, 2) or not np.isfinite(audio).all():
            raise ValueError("Performer must return finite, full-length stereo audio")
    mix = np.sum(recordings, axis=0) / len(recordings)
    return mix.astype(np.float32)
