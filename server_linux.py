#!/usr/bin/env python3
"""
Entrada Linux/servidor para VerbaTube.
Reutiliza server.py pero lo adapta para despliegue en astromalik-server.
"""

import http.server
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import server as legacy

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv("VERBATUBE_DATA_DIR", BASE_DIR / "data")).expanduser()
SUBTITLES_DIR = DATA_DIR / "subtitles"
HOST = os.getenv("VERBATUBE_HOST", "127.0.0.1")
PORT = int(os.getenv("VERBATUBE_PORT", "8090"))
AUTO_OPEN_BROWSER = os.getenv("VERBATUBE_OPEN_BROWSER", "").lower() in {"1", "true", "yes"}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

DATA_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

legacy.BASE_DIR = BASE_DIR
legacy.DATA_DIR = DATA_DIR
legacy.CORPUS_DIR = SUBTITLES_DIR
legacy.PORT = PORT
legacy.GEMINI_API_KEY = GEMINI_API_KEY


def configure_gemini():
    if not legacy.GENAI_AVAILABLE:
        print("google-generativeai no esta instalado. Gemini quedara deshabilitado.")
        return
    if legacy.GEMINI_API_KEY:
        legacy.genai.configure(api_key=legacy.GEMINI_API_KEY)
        print("Gemini API Key configurada desde entorno.")
    else:
        print("Gemini no estara disponible sin GEMINI_API_KEY.")


def run_download_and_index(url: str, lang: str):
    global legacy
    try:
        legacy.log(f"Iniciando descarga: {url}")
        legacy.log(f"   Idiomas: {lang}")
        legacy.log("-" * 50)

        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs",
            lang,
            "--sub-format",
            "vtt",
            "--write-info-json",
            "--no-overwrites",
            "--ignore-errors",
            "--download-archive",
            str(BASE_DIR / "download_archive.txt"),
            "--output",
            str(SUBTITLES_DIR / "%(channel)s" / "%(upload_date)s_%(id)s_%(title)s.%(ext)s"),
            url,
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE_DIR),
            env=env,
        )

        for line in proc.stdout:
            line = line.rstrip()
            if any(k in line for k in ["Downloading", "Writing", "already", "ERROR", "warning", "Finished"]):
                legacy.log(f"  {line}")

        proc.wait()
        legacy.log(f"\nDescarga completada (codigo: {proc.returncode})")
        legacy.log("-" * 50)
        legacy.log("Indexando...")

        idx = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "indexer_linux.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(BASE_DIR),
            env=env,
        )
        for line in idx.stdout:
            legacy.log(line.rstrip())
        idx.wait()

        legacy.load_index()
        legacy.log("\nTodo listo. Recarga el viewer para ver los nuevos videos.")
    except Exception as exc:
        legacy.log(f"Error: {exc}")
    finally:
        legacy._running = False


legacy.configure_gemini = configure_gemini
legacy.run_download_and_index = run_download_and_index


class VerbaServerHandler(legacy.VerbaTubeHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        decoded_path = unquote(parsed.path, encoding="utf-8")
        if decoded_path in {"/health", "/api/health"}:
            self._json(
                {
                    "ok": True,
                    "service": "verbaserver",
                    "host": HOST,
                    "port": PORT,
                    "data_dir": str(DATA_DIR),
                    "subtitles_dir": str(SUBTITLES_DIR),
                    "indexed_videos": len(legacy._index.get("videos", [])) if legacy._index else 0,
                    "running": legacy._running,
                }
            )
            return
        return super().do_GET()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    configure_gemini()
    legacy.load_index()
    print(f"VerbaServer en http://{HOST}:{PORT}/viewer.html")
    print(f"Directorio: {BASE_DIR}")
    print(f"Datos: {DATA_DIR}")
    print("Ctrl+C para detener\n")
    if AUTO_OPEN_BROWSER:
        import webbrowser

        threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}/viewer.html")).start()
    with http.server.ThreadingHTTPServer((HOST, PORT), VerbaServerHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
