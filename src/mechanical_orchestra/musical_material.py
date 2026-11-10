"""Small shared musical types for the current MIDI ensemble."""
from dataclasses import dataclass

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


