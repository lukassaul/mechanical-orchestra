"""Small, audio-first contracts and a deterministic multitrack conductor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class AudioClip:
    """Audio samples with a position in seconds on the shared timeline."""

    samples: np.ndarray
    start_seconds: float
    sample_rate: int

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError("start_seconds must be nonnegative")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.samples.ndim not in (1, 2):
            raise ValueError("samples must be mono or multichannel")


@dataclass(frozen=True)
class PerformanceDirection:
    """A minimal instruction; future versions may carry MusicXML, MIDI, or other material."""

    start_seconds: float
    duration_seconds: float
    instruction: str

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.duration_seconds < 0:
            raise ValueError("direction times must be nonnegative")


class Instrument(Protocol):
    def render(self, direction: PerformanceDirection, sample_rate: int) -> np.ndarray:
        """Return mono or multichannel audio; a tail may exceed direction duration."""
        ...


class Instrumentalist(Protocol):
    def perform(self, direction: PerformanceDirection, sample_rate: int) -> np.ndarray:
        """Interpret a direction, operate an instrument, and return audio."""
        ...


class InstrumentFactory(Protocol):
    def create(self, name: str) -> Instrument: ...


class InstrumentalistFactory(Protocol):
    def create(self, name: str, instrument: Instrument) -> Instrumentalist: ...


@dataclass
class Track:
    name: str
    instrumentalist: Instrumentalist
    directions: list[PerformanceDirection] = field(default_factory=list)
    gain: float = 1.0
    mute: bool = False


@dataclass
class Composition:
    """A Composer can construct this using resources from its factories."""

    tracks: list[Track] = field(default_factory=list)


class Conductor:
    """Sequentially generate tracks, then assemble audio on one timeline."""

    def __init__(self, sample_rate: int = 44100) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        self.sample_rate = sample_rate

    def perform(self, composition: Composition) -> np.ndarray:
        positioned: list[tuple[np.ndarray, int]] = []
        total_samples = 0
        channels = 1

        for track in composition.tracks:
            if track.mute:
                continue
            for direction in track.directions:
                audio = np.asarray(
                    track.instrumentalist.perform(direction, self.sample_rate),
                    dtype=np.float64,
                )
                if audio.ndim not in (1, 2):
                    raise ValueError("performer audio must be mono or multichannel")
                if not np.all(np.isfinite(audio)):
                    raise ValueError("performer audio must contain finite samples")
                if audio.ndim == 2 and audio.shape[1] not in (1, 2):
                    raise ValueError("only mono and stereo audio are supported")
                channels = max(channels, 1 if audio.ndim == 1 else audio.shape[1])
                offset = round(direction.start_seconds * self.sample_rate)
                positioned.append((audio * track.gain, offset))
                total_samples = max(total_samples, offset + len(audio))

        mix = np.zeros((total_samples, channels), dtype=np.float64)
        for audio, offset in positioned:
            if audio.ndim == 1:
                audio = audio[:, None]
            if audio.shape[1] == 1 and channels == 2:
                audio = np.repeat(audio, 2, axis=1)
            mix[offset : offset + len(audio)] += audio
        return mix

    def write_wav(self, composition: Composition, path: str | Path) -> Path:
        audio = self.perform(composition)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 1.0:
            audio = audio / peak
        output = Path(path)
        sf.write(output, audio, self.sample_rate)
        return output
