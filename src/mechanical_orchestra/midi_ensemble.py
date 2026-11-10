"""Whole-piece MIDI performers backed by a single offline FluidSynth render per take."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np


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

    def __init__(self, soundfont: str | Path, program: int = 19, drums: bool = False):
        self.soundfont = Path(soundfont)
        self.program = program
        self.drums = drums

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
            if not self.drums:
                synth.program_select(channel, sfid, 0, self.program)
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
        self.instrument, self.changes = instrument, sorted(changes, key=lambda c: c.start_bar)

    def events(self, piece: Piece) -> list[MidiEvent]:
        if not self.changes or self.changes[0].start_bar != 1:
            raise ValueError("Organist needs an initial chord at bar 1")
        events = []
        for i, chord in enumerate(self.changes):
            if not 1 <= chord.start_bar <= piece.bars:
                raise ValueError("Chord change outside piece")
            if i and chord.start_bar <= self.changes[i - 1].start_bar:
                raise ValueError("Chord changes must occur in distinct bars")
            start = (chord.start_bar - 1) * piece.beats_per_bar
            end = ((self.changes[i + 1].start_bar - 1) * piece.beats_per_bar
                   if i + 1 < len(self.changes) else piece.total_beats)
            for pitch in chord.pitches:
                events.extend([MidiEvent(start, pitch, 85, True),
                               MidiEvent(end, pitch, 0, False)])
        return events

    def perform(self, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        return self.instrument.render(self.events(piece), piece, sample_rate)


class Drummer:
    def __init__(self, instrument: FluidSynthInstrument):
        self.instrument = instrument

    def events(self, piece: Piece) -> list[MidiEvent]:
        events = []
        for beat in range(piece.total_beats):
            hits = [42]  # closed hi-hat on every beat
            if beat % piece.beats_per_bar == 0:
                hits.append(36)  # kick
            if beat % piece.beats_per_bar in (1, 3):
                hits.append(38)  # snare
            for pitch in hits:
                events.extend([MidiEvent(float(beat), pitch, 95, True),
                               MidiEvent(min(beat + 0.12, piece.total_beats), pitch, 0, False)])
        return events

    def perform(self, piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        return self.instrument.render(self.events(piece), piece, sample_rate)


class MidiInstrumentFactory:
    def __init__(self, soundfont: str | Path):
        self.soundfont = Path(soundfont)

    def create(self, kind: str) -> FluidSynthInstrument:
        presets = {"organ": (19, False), "melody": (65, False), "drums": (0, True)}
        if kind not in presets:
            raise ValueError(f"Unknown MIDI instrument: {kind}")
        program, drums = presets[kind]
        return FluidSynthInstrument(self.soundfont, program, drums)


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
