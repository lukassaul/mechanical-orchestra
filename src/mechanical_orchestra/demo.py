"""A runnable audio-only proof of concept (no MIDI dependency yet)."""

import numpy as np

from .core import Composition, Conductor, PerformanceDirection, Track


class ToneInstrument:
    def __init__(self, frequency: float, decay: float = 0.0) -> None:
        self.frequency = frequency
        self.decay = decay

    def render(self, direction: PerformanceDirection, sample_rate: int) -> np.ndarray:
        duration = direction.duration_seconds + (2.0 if self.decay else 0.0)
        t = np.arange(round(duration * sample_rate)) / sample_rate
        envelope = np.exp(-self.decay * t) if self.decay else np.ones_like(t)
        return 0.22 * np.sin(2 * np.pi * self.frequency * t) * envelope


class LiteralInstrumentalist:
    def __init__(self, instrument: ToneInstrument) -> None:
        self.instrument = instrument

    def perform(self, direction: PerformanceDirection, sample_rate: int) -> np.ndarray:
        return self.instrument.render(direction, sample_rate)


def main() -> None:
    composition = Composition(
        tracks=[
            Track(
                "bass",
                LiteralInstrumentalist(ToneInstrument(110)),
                [PerformanceDirection(i * 0.5, 0.4, "bass pulse") for i in range(8)],
                gain=0.65,
            ),
            Track(
                "melody",
                LiteralInstrumentalist(ToneInstrument(440)),
                [PerformanceDirection(0.0, 2.0, "sustained melody")],
                gain=0.35,
            ),
            Track(
                "gong",
                LiteralInstrumentalist(ToneInstrument(165, decay=1.8)),
                [PerformanceDirection(2.0, 0.2, "strike gong")],
                gain=0.8,
            ),
        ]
    )
    path = Conductor().write_wav(composition, "mechanical_orchestra_demo.wav")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
