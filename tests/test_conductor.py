import numpy as np
import pytest

from mechanical_orchestra.core import Composition, Conductor, PerformanceDirection, Track


class ConstantPerformer:
    def __init__(self, samples):
        self.samples = np.asarray(samples, dtype=float)

    def perform(self, direction, sample_rate):
        return self.samples


def test_overlapping_tracks_are_summed():
    direction = PerformanceDirection(0.0, 0.1, "test")
    composition = Composition([
        Track("a", ConstantPerformer([0.2, 0.2]), [direction]),
        Track("b", ConstantPerformer([0.3, 0.3]), [direction]),
    ])
    np.testing.assert_allclose(Conductor(10).perform(composition)[:, 0], [0.5, 0.5])


def test_offset_and_audio_tail():
    composition = Composition([
        Track("gong", ConstantPerformer([0.4, 0.2, 0.1]),
              [PerformanceDirection(0.2, 0.1, "strike")]),
    ])
    np.testing.assert_allclose(
        Conductor(10).perform(composition)[:, 0], [0, 0, 0.4, 0.2, 0.1]
    )


def test_mute():
    composition = Composition([
        Track("muted", ConstantPerformer([1.0]),
              [PerformanceDirection(0, 1, "test")], mute=True),
    ])
    assert Conductor(10).perform(composition).shape == (0, 1)


def test_negative_start_rejected():
    with pytest.raises(ValueError):
        PerformanceDirection(-1, 1, "invalid")
