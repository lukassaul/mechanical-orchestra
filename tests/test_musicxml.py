from pathlib import Path

import pytest

from mechanical_orchestra.midi_ensemble import ChordChange, MidiEvent, Organist, Piece
from mechanical_orchestra.musicxml import load_lead_sheet


SCORE = Path(__file__).resolve().parents[1] / "scores" / "giant_steps_draft.musicxml"


def test_giant_steps_score_loads():
    score = load_lead_sheet(SCORE, bpm=160)
    assert score.piece == Piece(bars=16, bpm=160)
    assert score.melody
    assert score.chords[0].start_beat == 0
    assert score.chords[1].start_beat == 2
    assert score.chords[2].start_beat == 4
    assert score.chords[-1].start_beat == 62


def test_organ_changes_at_half_bar():
    score = load_lead_sheet(SCORE)
    player = Organist(None, score.chords)
    events = player.events(score.piece)
    assert MidiEvent(2, score.chords[0].pitches[0], 0, False) in events
    assert MidiEvent(2, score.chords[1].pitches[0], 85, True) in events
    assert all(0 <= e.beat <= score.piece.total_beats for e in events)


def test_score_tempo_default():
    score = load_lead_sheet(SCORE)
    assert score.piece.bpm == 286
