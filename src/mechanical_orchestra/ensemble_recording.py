"""Whole-take assembly, independent of instrument implementation."""
from typing import Sequence
import numpy as np
from .musical_material import Piece

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
