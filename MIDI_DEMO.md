# MIDI ensemble demo

The first real ensemble uses three whole-piece Instrumentalists: a melody player,
a repeating drummer, and a chord-holding organist. Each renders its own full
take with FluidSynth; the mixer combines those takes without bar-by-bar splicing.

## Setup

Install the native FluidSynth library (e.g. `brew install fluid-synth` on
macOS or `sudo apt install libfluidsynth3` on Ubuntu), then:

```bash
pip install -e '.[midi,dev]'
python scripts/install_soundfonts.py
python -m mechanical_orchestra.midi_demo
pytest
```

The demo writes `mechanical_orchestra_midi_demo.wav` in the current directory.
It uses GeneralUser GS from `assets/soundfonts/GeneralUser-GS.sf2`.

The demo is intentionally fixed at 8 bars and 120 BPM; this is an architectural
test, not an improvisation engine. The legacy sine-wave demo is still available
via `python -m mechanical_orchestra.demo`.

The FluidSynth integration has not yet been exercised in a local environment.
