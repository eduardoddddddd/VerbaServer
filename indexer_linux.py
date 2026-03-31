#!/usr/bin/env python3
"""
Wrapper Linux para reutilizar indexer.py sin tocar el original.
"""

import argparse
import json
import re
from pathlib import Path
import os

import indexer as legacy

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("VERBATUBE_DATA_DIR", BASE_DIR / "data")).expanduser()
SUBTITLES_DIR = DATA_DIR / "subtitles"
INDEX_FILE = BASE_DIR / "verbatube.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

legacy.BASE_DIR = BASE_DIR
legacy.DATA_DIR = DATA_DIR
legacy.CORPUS_DIR = SUBTITLES_DIR
legacy.SUBTITLES_DIR = SUBTITLES_DIR
legacy.INDEX_FILE = INDEX_FILE


def normalize_languages():
    if not INDEX_FILE.exists():
        return

    data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    changed = False

    for video in data.get("videos", []):
        subtitle_file = video.get("subtitle_file", "")
        match = re.search(r"\.([a-z]{2}(?:-[a-z]+)?)\.vtt$", subtitle_file, re.IGNORECASE)
        if not match:
            continue
        language = match.group(1).lower()
        if video.get("language") != language:
            video["language"] = language
            changed = True
        langs = video.get("languages_available") or []
        if langs != [language]:
            video["languages_available"] = [language]
            changed = True

    if changed:
        INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Wrapper Linux de indexer.py")
    parser.add_argument("--rebuild", action="store_true", help="Reconstruir índice desde cero")
    args = parser.parse_args()
    legacy.build_index(rebuild=args.rebuild)
    normalize_languages()


if __name__ == "__main__":
    main()
