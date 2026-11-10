"""Small MusicXML lead-sheet reader for our single-part, concert-pitch demos.

Supports .musicxml/.xml and compressed .mxl, pitched notes/rests,
chord symbols, per-measure harmony offsets, and a fixed 4/4 tempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .midi_ensemble import ChordChange, Note, Piece

_STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_INTERVALS = {
    "major": (0, 4, 7), "minor": (0, 3, 7),
    "dominant": (0, 4, 7, 10),
    "major-seventh": (0, 4, 7, 11),
    "minor-seventh": (0, 3, 7, 10),
    "diminished": (0, 3, 6),
}


@dataclass(frozen=True)
class LeadSheet:
    piece: Piece
    melody: tuple[Note, ...]
    chords: tuple[ChordChange, ...]


def _score_root(path: Path) -> ET.Element:
    if path.suffix.lower() != ".mxl":
        return ET.parse(path).getroot()
    with ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None:
            raise ValueError("MXL missing rootfile")
        return ET.fromstring(archive.read(rootfile.attrib["full-path"]))


def _pitch(element: ET.Element) -> int:
    step = element.findtext("step")
    if step not in _STEPS:
        raise ValueError(f"Unsupported pitch step: {step}")
    return 12 * (int(element.findtext("octave")) + 1) + _STEPS[step] + int(element.findtext("alter", "0"))


def _chord_pitches(harmony: ET.Element) -> tuple[int, ...]:
    root = harmony.find("root")
    if root is None:
        raise ValueError("Chord symbol has no root")
    step = root.findtext("root-step")
    if step not in _STEPS:
        raise ValueError(f"Unsupported chord root: {step}")
    root_midi = 48 + _STEPS[step] + int(root.findtext("root-alter", "0"))
    kind = harmony.findtext("kind", "major")
    if kind not in _INTERVALS:
        raise ValueError(f"Unsupported chord kind: {kind}")
    return tuple(root_midi + interval for interval in _INTERVALS[kind])


def load_lead_sheet(path: str | Path, bpm: float | None = None) -> LeadSheet:
    """Read a monophonic lead sheet in concert pitch; fail on unsupported notation."""
    root = _score_root(Path(path))
    if root.tag.split("}")[-1] != "score-partwise":
        raise ValueError("Expected partwise MusicXML")
    # Remove namespaces to keep the parsing logic readable.
    for element in root.iter():
        element.tag = element.tag.split("}")[-1]

    parts = root.findall("part")
    if len(parts) != 1:
        raise ValueError("This first-pass importer expects one melody part")
    measures = parts[0].findall("measure")
    if not measures:
        raise ValueError("Score has no measures")

    divisions = None
    beats_per_bar = None
    beat_type = None
    tempo = bpm
    notes: list[Note] = []
    chords: list[ChordChange] = []
    absolute_beat = 0.0
    for measure_index, measure in enumerate(measures):
        attributes = measure.find("attributes")
        if attributes is not None:
            if attributes.find("divisions") is not None:
                divisions = int(attributes.findtext("divisions"))
            time = attributes.find("time")
            if time is not None:
                beats_per_bar = int(time.findtext("beats"))
                beat_type = int(time.findtext("beat-type"))
            if attributes.find("transpose") is not None:
                raise ValueError("Transposing parts are not supported; use concert pitch")
        if not divisions or beats_per_bar != 4 or beat_type != 4:
            raise ValueError("First-pass importer requires 4/4 with divisions specified")
        for sound in measure.findall(".//sound"):
            if tempo is None and sound.get("tempo"):
                tempo = float(sound.get("tempo"))

        cursor = 0.0
        for child in measure:
            if child.tag == "harmony":
                offset = float(child.findtext("offset", "0")) / divisions
                at = absolute_beat + cursor + offset
                chords.append(ChordChange(measure_index + 1, _chord_pitches(child), at))
            elif child.tag == "note":
                if child.find("chord") is not None:
                    raise ValueError("Polyphonic melody not supported yet")
                duration = float(child.findtext("duration", "0")) / divisions
                if duration <= 0:
                    raise ValueError("Invalid note duration")
                if child.find("rest") is None:
                    pitch_el = child.find("pitch")
                    if pitch_el is None:
                        raise ValueError("Unpitched notes not supported")
                    notes.append(Note(_pitch(pitch_el), absolute_beat + cursor, duration))
                cursor += duration
            elif child.tag in ("backup", "forward"):
                raise ValueError("Multiple voices not supported yet")
        if abs(cursor - beats_per_bar) > 1e-6:
            raise ValueError(f"Measure {measure_index + 1} has {cursor} beats, expected 4")
        absolute_beat += beats_per_bar
    if not chords or chords[0].start_beat != 0:
        raise ValueError("Score must provide a chord at the beginning")
    return LeadSheet(Piece(bars=len(measures), bpm=tempo or 120, beats_per_bar=4),
                     tuple(notes), tuple(chords))
