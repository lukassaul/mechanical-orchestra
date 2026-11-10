"""Download the official GeneralUser GS SoundFont without committing binaries.

Run: python scripts/install_soundfonts.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

SOURCE = "https://raw.githubusercontent.com/mrbumpy409/GeneralUser-GS/main/GeneralUser-GS.sf2"
DESTINATION = Path(__file__).resolve().parents[1] / "assets" / "soundfonts" / "GeneralUser-GS.sf2"
MAX_BYTES = 80 * 1024 * 1024


def install(destination: Path = DESTINATION, force: bool = False) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"Already installed: {destination} (use --force to replace)")
        return destination

    request = Request(SOURCE, headers={"User-Agent": "mechanical-orchestra-soundfont-installer"})
    temporary: Path | None = None
    try:
        with urlopen(request, timeout=60) as response:
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as output:
                temporary = Path(output.name)
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError("SoundFont download exceeded expected maximum size")
                    output.write(chunk)
        with temporary.open("rb") as downloaded:
            header = downloaded.read(12)
        if header[:4] != b"RIFF" or header[8:12] != b"sfbk":
            raise ValueError("Downloaded file is not a valid SF2 RIFF SoundFont")
        if total < 1024 * 1024:
            raise ValueError("Downloaded SoundFont is unexpectedly small")
        os.replace(temporary, destination)
        temporary = None
        print(f"Installed {destination} ({total / 1024 / 1024:.1f} MiB)")
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install GeneralUser GS from the author's GitHub repository")
    parser.add_argument("--force", action="store_true", help="replace an existing SoundFont")
    args = parser.parse_args()
    install(force=args.force)


if __name__ == "__main__":
    main()
