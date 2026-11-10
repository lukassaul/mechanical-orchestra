"""Compatibility imports for existing demos and tests.

New code should import from musical_material, instruments, instrumentalists,
and ensemble_recording directly.
"""
from .musical_material import Note, ChordChange, Piece, MidiEvent
from .instruments import FluidSynthInstrument, MidiInstrumentFactory
from .instrumentalists import MelodyPlayer, Organist, Drummer
from .ensemble_recording import record_ensemble

__all__ = ["Note", "ChordChange", "Piece", "MidiEvent", "FluidSynthInstrument", "MidiInstrumentFactory", "MelodyPlayer", "Organist", "Drummer", "record_ensemble"]
