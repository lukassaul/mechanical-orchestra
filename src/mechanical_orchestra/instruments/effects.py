"""Lightweight stereo effects applied to full-length instrument recordings."""

import numpy as np


def leslie(audio: np.ndarray, sample_rate: int, rate_hz: float = 5.2) -> np.ndarray:
    """Approximate a rotating speaker with stereo tremolo and moving short delays."""
    n = len(audio)
    t = np.arange(n, dtype=np.float64) / sample_rate
    mono = np.mean(audio, axis=1)
    result = np.empty_like(audio, dtype=np.float32)
    positions = np.arange(n, dtype=np.float64)
    for channel, phase in enumerate((0.0, np.pi)):
        angle = 2 * np.pi * rate_hz * t + phase
        # Small periodic delay gives a Doppler-like motion; modulation in
        # amplitude and opposite stereo phase produces a rotary impression.
        delay = (0.004 + 0.0018 * np.sin(angle)) * sample_rate
        shifted = np.interp(positions - delay, positions, mono, left=0.0)
        gain = 0.72 + 0.28 * np.sin(angle)
        result[:, channel] = (0.40 * audio[:, channel] + 0.60 * shifted * gain)
    return result


def echo(audio: np.ndarray, sample_rate: int, delay_seconds: float = 0.23,
         feedback: float = 0.35, wet: float = 0.28) -> np.ndarray:
    """Add a few decaying repeats without changing the recording length."""
    if delay_seconds <= 0 or not 0 <= feedback < 1 or not 0 <= wet <= 1:
        raise ValueError("Invalid echo settings")
    delay = max(1, round(delay_seconds * sample_rate))
    output = np.array(audio, dtype=np.float32, copy=True)
    for repeat in range(1, 5):
        shift = delay * repeat
        if shift >= len(output):
            break
        output[shift:] += audio[:-shift] * (wet * feedback ** (repeat - 1))
    return output
