import numpy as np
import pytest

from mechanical_orchestra.audio_effects import echo, leslie
from mechanical_orchestra.midi_ensemble import MidiInstrumentFactory


def test_effects_preserve_shape_and_finite_samples():
    audio = np.zeros((44100, 2), dtype=np.float32)
    audio[1000:1100] = 0.4
    for effect in (leslie(audio, 44100), echo(audio, 44100)):
        assert effect.shape == audio.shape
        assert np.isfinite(effect).all()
        assert np.max(np.abs(effect)) > 0


def test_echo_has_a_delayed_repeat():
    audio = np.zeros((1000, 2), dtype=np.float32)
    audio[0] = 1
    output = echo(audio, 1000, delay_seconds=0.1)
    assert output[100, 0] == pytest.approx(0.28)
    assert output[200, 0] == pytest.approx(0.28 * 0.35)


def test_factory_effect_routing():
    factory = MidiInstrumentFactory("unused.sf2")
    assert factory.create("organ").effect == "leslie"
    assert factory.create("melody").effect == "echo"
    assert factory.create("drums").effect is None
