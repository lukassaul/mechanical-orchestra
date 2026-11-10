"""FluidSynth sound generation and preset factory."""
from pathlib import Path
from typing import Sequence
import numpy as np
from ..musical_material import MidiEvent, Piece
from .effects import echo, leslie

class FluidSynthInstrument:
    """Instrument owns MIDI rendering; performers own musical decisions."""

    def __init__(self, soundfont: str | Path, program: int = 19, drums: bool = False, effect: str | None = None):
        self.soundfont = Path(soundfont)
        self.program = program
        self.drums = drums
        self.effect = effect

    def render(self, events: Sequence[MidiEvent], piece: Piece, sample_rate: int = 44100) -> np.ndarray:
        try:
            import fluidsynth
        except ImportError as exc:
            raise RuntimeError("Install pyfluidsynth and the native FluidSynth library") from exc
        if not self.soundfont.is_file():
            raise FileNotFoundError(f"SoundFont missing: {self.soundfont}. Run python scripts/install_soundfonts.py")
        synth = fluidsynth.Synth(samplerate=sample_rate)
        try:
            sfid = synth.sfload(str(self.soundfont))
            if sfid < 0:
                raise RuntimeError(f"Cannot load SoundFont: {self.soundfont}")
            channel = 9 if self.drums else 0
            # General MIDI percussion kits live in bank 128. Selecting the
            # SoundFont alone does not reliably configure channel 10.
            bank = 128 if self.drums else 0
            status = synth.program_select(channel, sfid, bank, self.program)
            if status != 0:
                raise RuntimeError(
                    f"Could not select SoundFont preset: bank={bank}, program={self.program}"
                )
            total_samples = round(piece.total_beats * 60 / piece.bpm * sample_rate)
            result = np.zeros((total_samples, 2), dtype=np.float32)
            cursor = 0
            # Note-offs before note-ons at identical timestamps.
            ordered = sorted(events, key=lambda e: (e.beat, e.on))
            for event in ordered:
                if not (0 <= event.beat <= piece.total_beats):
                    raise ValueError("MIDI event outside piece")
                if not (0 <= event.pitch <= 127 and 0 <= event.velocity <= 127):
                    raise ValueError("Invalid MIDI pitch or velocity")
                target = round(event.beat * 60 / piece.bpm * sample_rate)
                if target > cursor:
                    chunk = np.asarray(synth.get_samples(target - cursor), dtype=np.float32)
                    result[cursor:target] = chunk.reshape(-1, 2) / 32768.0
                    cursor = target
                if event.on:
                    synth.noteon(channel, event.pitch, event.velocity)
                else:
                    synth.noteoff(channel, event.pitch)
            if cursor < total_samples:
                chunk = np.asarray(synth.get_samples(total_samples - cursor), dtype=np.float32)
                result[cursor:] = chunk.reshape(-1, 2) / 32768.0
            if self.effect == 'leslie':
                result = leslie(result, sample_rate)
            elif self.effect == 'echo':
                result = echo(result, sample_rate)
            elif self.effect is not None:
                raise ValueError(f'Unknown instrument effect: {self.effect}')
            return result
        finally:
            synth.delete()



class MidiInstrumentFactory:
    def __init__(self, soundfont: str | Path):
        self.soundfont = Path(soundfont)

    def create(self, kind: str) -> FluidSynthInstrument:
        presets = {"organ": (19, False, "leslie"), "melody": (66, False, "echo"), "drums": (0, True, None)}
        if kind not in presets:
            raise ValueError(f"Unknown MIDI instrument: {kind}")
        program, drums, effect = presets[kind]
        return FluidSynthInstrument(self.soundfont, program, drums, effect)


