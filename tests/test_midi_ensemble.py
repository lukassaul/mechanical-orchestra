import numpy as np
import pytest

from mechanical_orchestra.midi_ensemble import (
    ChordChange, Drummer, MelodyPlayer, MidiEvent, Note, Organist,
    Piece, record_ensemble,
)


class FakeInstrument:
    def __init__(self):
        self.received = None

    def render(self, events, piece, sample_rate):
        self.received = list(events)
        return np.zeros((round(piece.total_beats * 60 / piece.bpm * sample_rate), 2))


def test_organ_chords_are_sustained_until_next_change():
    instrument = FakeInstrument()
    player = Organist(instrument, [ChordChange(1, (60, 64)), ChordChange(3, (62, 65))])
    player.perform(Piece(bars=4), 100)
    assert MidiEvent(8, 60, 0, False) in instrument.received
    assert MidiEvent(8, 62, 85, True) in instrument.received
    assert MidiEvent(16, 62, 0, False) in instrument.received


def test_drums_repeat_and_finish_within_piece():
    instrument = FakeInstrument()
    Drummer(instrument).perform(Piece(bars=2), 100)
    kicks = [e for e in instrument.received if e.on and e.pitch == 36]
    assert [e.beat for e in kicks] == [0, 4]


def test_melody_uses_supplied_notes():
    instrument = FakeInstrument()
    MelodyPlayer(instrument, [Note(60, 0, 2)]).perform(Piece(bars=1), 100)
    assert instrument.received == [MidiEvent(0, 60, 90, True), MidiEvent(2, 60, 0, False)]


def test_record_ensemble_mixes_whole_takes():
    class Player:
        def perform(self, piece, sample_rate):
            return np.full((round(piece.total_beats * 60 / piece.bpm * sample_rate), 2), .5)
    mix = record_ensemble([Player(), Player()], Piece(bars=1), 100)
    assert mix.shape == (200, 2)
    assert np.allclose(mix, .5)


def test_missing_initial_chord_rejected():
    with pytest.raises(ValueError):
        Organist(FakeInstrument(), [ChordChange(2, (60,))]).events(Piece())
