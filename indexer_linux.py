#!/usr/bin/env python3
"""
Wrapper Linux para reutilizar indexer.py sin tocar el original.
"""

import os
from pathlib import Path

import indexer as legacy

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("VERBATUBE_DATA_DIR", BASE_DIR / "data")).expanduser()
SUBTITLES_DIR = DATA_DIR / "subtitles"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

legacy.BASE_DIR = BASE_DIR
legacy.DATA_DIR = DATA_DIR
legacy.CORPUS_DIR = SUBTITLES_DIR
legacy.SUBTITLES_DIR = SUBTITLES_DIR
legacy.INDEX_FILE = BASE_DIR / "verbatube.json"


if __name__ == "__main__":
    legacy.main()
