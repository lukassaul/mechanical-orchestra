# Mechanical Orchestra

A programmable orchestra of composers, conductors, instrumentalists, and instruments.

## Architecture

- **Composer** selects resources from instrument and instrumentalist factories and creates a Composition.
- **Conductor** executes the Composition, directing performers and assembling their audio on a multitrack timeline.
- **Instrumentalist** interprets musical instructions and operates an Instrument.
- **Instrument** generates audio, whether by MIDI synthesis, samples, algorithms, or a nested orchestra.
- **Factories** are libraries of available implementations, not intelligent performance coordinators.

Audio is the common output. MIDI is an optional internal representation of an instrument or performance.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
python -m mechanical_orchestra.demo
pytest
```

The demo writes `mechanical_orchestra_demo.wav` using synthetic tones and a gong-like sound. It requires no SoundFont or external synthesizer.

## Install the GeneralUser GS SoundFont

```bash
python scripts/install_soundfonts.py
```

This downloads the official `GeneralUser-GS.sf2` to `assets/soundfonts/`. SoundFont binaries are ignored by Git. Use `--force` to redownload. See [SoundFont notes](assets/soundfonts/README.md) for provenance and licensing. The MIDI/FluidSynth adapter is a future milestone; downloading the SoundFont does not yet enable MIDI playback.

## Next milestones

1. Expand the timeline to support tempo maps, bars, beats, and meter.
2. Add discoverable controls and capability descriptions.
3. Implement a MIDI/FluidSynth instrument adapter.
4. Add a performance repository and dependency-aware generation.
5. Experiment with musically capable, improvising instrumentalists.

The first milestone is intentionally deterministic and single-threaded. The musical intelligence will evolve independently of the audio engine.
