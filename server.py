#!/usr/bin/env python3
"""
Verbatube - Server
Servidor local que reemplaza 'python -m http.server' y añade endpoints
para lanzar descarga e indexación desde el propio viewer.html.
Reutiliza la lógica yt-dlp ya probada en AstroExtracto.

Uso:
    python server.py
    → http://localhost:8080/viewer.html
"""

import http.server, subprocess, json, threading, os, sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import urllib.request
import urllib.error
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ModuleNotFoundError:
    genai = None
    GENAI_AVAILABLE = False

BASE_DIR   = Path(__file__).parent
CORPUS_DIR = Path(r"C:\Users\Edu\VTTs")   # Carpeta común para todos los proyectos
PORT       = 8080

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_API_KEY = ""
LLM_SYSTEM_PROMPT = """Eres un asistente experto en análisis de contenido de subtítulos de videos.

Contexto disponible:
- Tienes acceso a una base de datos de subtítulos de YouTube
- Se te proporcionará información sobre los videos disponibles y su contenido
- Debes hacer preguntas específicas sobre el contenido, patrones, temas y conexiones entre videos
- Siempre cita los videos o timestamps específicos cuando sea relevante
- Si una pregunta requiere información que no está presente en el contexto, lo indicarás claramente"""


def configure_gemini():
    """Solicita la clave de Gemini al arrancar y configura google-generativeai."""
    global GEMINI_API_KEY
    if not GENAI_AVAILABLE:
        print("google-generativeai no está instalado. Gemini quedará deshabilitado.")
        return
    try:
        key = input("API Key Gemini (deja en blanco si no la tienes): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nNo se capturó clave. Gemini desactivado.")
        key = ""
    GEMINI_API_KEY = key
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("Gemini API Key configurada para este arranque.")
    else:
        print("Gemini no estará disponible sin clave.")

# Log en memoria para streaming
_log_lock   = threading.Lock()
_log_lines  = []
_running    = False
_index      = None  # Índice de vídeos cargado desde verbatube.json


def load_index():
    """Carga el índice de vídeos desde verbatube.json"""
    global _index
    index_path = BASE_DIR / "verbatube.json"
    if index_path.exists():
        try:
            with open(index_path, encoding="utf-8") as f:
                _index = json.load(f)
        except Exception as e:
            print(f"[WARN] No se pudo cargar el índice: {e}")

def log(msg):
    with _log_lock:
        _log_lines.append(msg)
    print(msg)

def reset_log():
    global _running
    with _log_lock:
        _log_lines.clear()
    _running = True

def get_log_since(offset):
    with _log_lock:
        return _log_lines[offset:], len(_log_lines), _running


def _build_context_text(context: dict, query: str = "") -> str:
    """Uniformiza el texto de contexto que se envía a los diferentes proveedores.
    - Si hay vídeo seleccionado: manda transcripción completa.
    - Si no: busca por keywords en el índice y manda los top-5 más relevantes.
    """
    parts = ["Información de vídeos:"]
    if context.get("selected_videos"):
        for video in context["selected_videos"][:10]:
            full = video.get('full_text', '')
            parts.append(f"- [{video.get('title', 'N/A')}]")
            parts.append(f"  Canal: {video.get('channel', 'N/A')}")
            parts.append(f"  Duración: {video.get('duration_fmt', 'N/A')}")
            parts.append(f"  Transcripción completa ({len(full)} chars):\n{full}")
    elif query and _index:
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        scored = []
        for video in _index.get("videos", []):
            text = video.get("full_text", "").lower()
            score = sum(text.count(kw) for kw in keywords)
            if score > 0:
                scored.append((score, video))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]
        if top:
            parts.append(f"Top {len(top)} vídeos más relevantes para '{query}' (de {len(scored)} con coincidencias sobre {len(_index.get('videos',[]))} totales):\n")
            for score, video in top:
                full = video.get('full_text', '')
                parts.append(f"--- [{video.get('title','N/A')}] | Canal: {video.get('channel','N/A')} | Relevancia: {score} menciones ---")
                parts.append(full)
        else:
            parts.append(f"No se encontraron vídeos con los términos: {', '.join(keywords)}")
    elif context.get("videos_summary"):
        parts.append(context["videos_summary"])
    else:
        parts.append("No hay contexto específico de videos disponible.")
    return "\n".join(parts)


def _extract_response(result: dict, provider: str) -> dict:
    """Normaliza la respuesta para la UI."""
    if provider == "openai":
        choices = result.get("choices", [])
        if not choices:
            return {"ok": False, "error": "Respuesta vacía de OpenAI"}
        text = choices[0].get("message", {}).get("content", "")
        return {"ok": True, "response": text}

    if provider == "gemini":
        candidates = result.get("candidates", [])
        if not candidates:
            return {"ok": False, "error": "Respuesta vacía de Gemini"}
        return {"ok": True, "response": candidates[0].get("output", "")}

    # Anthropic por defecto
    content = result.get("content", [])
    if content:
        return {"ok": True, "response": content[0].get("text", "")}
    return {"ok": False, "error": "Respuesta vacía de Anthropic"}


def _handle_http_error(e: urllib.error.HTTPError, provider: str) -> dict:
    body = e.read().decode('utf-8', errors='ignore')
    try:
        error_json = json.loads(body)
        if provider == "openai":
            error_msg = error_json.get("error", {}).get("message", body)
        else:
            error_msg = error_json.get("error", {}).get("message", body) or error_json.get("error_description", body)
    except Exception:
        error_msg = body or str(e)
    return {"ok": False, "error": f"Error API ({e.code}): {error_msg}"}


def _request_anthropic(api_key: str, model: str, payload: dict) -> dict:
    if not api_key:
        return {"ok": False, "error": "Anthropic requiere una API key válida."}
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def _request_openai(api_key: str, payload: dict) -> dict:
    if not api_key:
        return {"ok": False, "error": "OpenAI requiere una API key válida."}
    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))


def _request_gemini(api_key: str, model: str, payload: dict) -> dict:
    if not GENAI_AVAILABLE:
        return {"ok": False, "error": "google-generativeai no esta instalado. Gemini no esta disponible."}
    # Prioridad: key enviada desde la UI; fallback a la introducida al arrancar
    effective_key = api_key or GEMINI_API_KEY
    if not effective_key:
        return {"ok": False, "error": "Gemini requiere una API Key. Introduzca la clave en el campo Clave API de la UI o al arrancar server.py."}
    prompt_text = payload["prompt"]["text"]
    try:
        genai.configure(api_key=effective_key)
        gemini_model = genai.GenerativeModel(model)
        response = gemini_model.generate_content(prompt_text)
        return {"candidates": [{"output": response.text}]}
    except Exception as e:
        return {"ok": False, "error": f"Gemini error: {str(e)}"}


def _query_with_provider(provider: str, api_key: str, model: str, query: str, context: dict) -> dict:
    context_text = _build_context_text(context, query)
    system = LLM_SYSTEM_PROMPT
    user_message = f"{context_text}\n\nPregunta del usuario: {query}"
    payload = {}

    try:
        if provider == "openai":
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 2048,
                "temperature": 0.2
            }
            result = _request_openai(api_key, payload)
        elif provider == "gemini":
            payload = {
                "prompt": {"text": f"{system}\n\n{user_message}"},
                "temperature": 0.2,
                "maxOutputTokens": 512
            }
            result = _request_gemini(api_key, model, payload)
        else:
            payload = {
                "model": model,
                "max_tokens": 2048,
                "system": system,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            result = _request_anthropic(api_key, model, payload)
        if isinstance(result, dict) and result.get("ok") is False:
            return result
        return _extract_response(result, provider)
    except urllib.error.HTTPError as e:
        return _handle_http_error(e, provider)
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Error de conexión: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": f"Error inesperado: {str(e)}"}


LLM_PROVIDERS = {
    "anthropic": {
        "label": "Anthropic Claude",
        "default_model": "claude-3-5-sonnet-20241022"
    },
    "openai": {
        "label": "OpenAI Chat (gpt-4o-mini)",
        "default_model": "gpt-4o-mini"
    },
    "gemini": {
        "label": "Google Gemini",
        "default_model": "gemini-2.5-flash"
    }
}

DEFAULT_LLM_PROVIDER = "anthropic"


def run_download_and_index(url, lang):
    """Ejecuta descarga e indexación en hilo aparte. Misma lógica que AstroExtracto."""
    global _running
    try:
        log(f"🚀 Iniciando descarga: {url}")
        log(f"   Idiomas: {lang}")
        log("─" * 50)

        # Comando yt-dlp via py -3.12 para evitar el wrapper roto de Python314
        cmd = [
            "py", "-3.12", "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", lang,
            "--sub-format", "vtt",
            "--write-info-json",
            "--no-overwrites",
            "--ignore-errors",
            "--download-archive", str(BASE_DIR / "download_archive.txt"),
            "--output", str(CORPUS_DIR / "%(channel)s" / "%(upload_date)s_%(id)s_%(title)s.%(ext)s"),
            url
        ]

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", env=env
        )

        for line in proc.stdout:
            line = line.rstrip()
            if any(k in line for k in ["Downloading", "Writing", "already", "ERROR", "warning", "Finished"]):
                log(f"  {line}")

        proc.wait()
        log(f"\n✅ Descarga completada (código: {proc.returncode})")
        log("─" * 50)
        log("🗄️  Indexando...")

        # Lanzar indexer.py reutilizando el mismo proceso Python
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        idx = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "indexer.py")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(BASE_DIR), env=env
        )
        for line in idx.stdout:
            log(line.rstrip())
        idx.wait()

        log("\n🎉 ¡Todo listo! Recarga el viewer para ver los nuevos vídeos.")

    except Exception as e:
        log(f"❌ Error: {e}")
    finally:
        _running = False


class VerbaTubeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # Silenciar logs de peticiones estáticas

    def do_GET(self):
        parsed = urlparse(self.path)
        # Decodificar URL para manejar caracteres especiales (tildes, ñ, etc.)
        decoded_path = unquote(parsed.path, encoding='utf-8')
        params = parse_qs(parsed.query)

        # ── API: iniciar descarga ─────────────────────────────────────────────
        if decoded_path == "/api/download":
            if _running:
                self._json({"ok": False, "msg": "Ya hay una descarga en curso"})
                return
            url  = params.get("url", [""])[0].strip()
            lang = params.get("lang", ["es,en"])[0].strip()
            if not url:
                self._json({"ok": False, "msg": "URL vacía"})
                return
            reset_log()
            threading.Thread(target=run_download_and_index, args=(url, lang), daemon=True).start()
            self._json({"ok": True, "msg": "Descarga iniciada"})

        # ── API: leer log (polling) ───────────────────────────────────────────
        elif decoded_path == "/api/log":
            offset = int(params.get("offset", ["0"])[0])
            lines, total, running = get_log_since(offset)
            self._json({"lines": lines, "total": total, "running": running})

        # ── API: sólo reindexar ───────────────────────────────────────────────
        elif decoded_path == "/api/reindex":
            if _running:
                self._json({"ok": False, "msg": "Proceso en curso"})
                return
            reset_log()
            def do_index():
                global _running
                try:
                    idx = subprocess.Popen(
                        [sys.executable, str(BASE_DIR / "indexer.py")],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", cwd=str(BASE_DIR)
                    )
                    for line in idx.stdout:
                        log(line.rstrip())
                    idx.wait()
                    log("🎉 Reindexación completada. Recarga el viewer.")
                finally:
                    _running = False
            threading.Thread(target=do_index, daemon=True).start()
            self._json({"ok": True, "msg": "Indexación iniciada"})

        # ── Archivos estáticos (viewer.html, subtitles/, etc.) ────────────────
        else:
            # Mapear subtitles/ → CORPUS_DIR directamente (sin depender de junction)
            if decoded_path.startswith('/subtitles/'):
                rel = decoded_path[len('/subtitles/'):]
                file_path = CORPUS_DIR / rel
            else:
                file_path = BASE_DIR / decoded_path.lstrip('/')

            if file_path.is_file():
                self._serve_file(file_path)
            else:
                super().do_GET()

    def do_POST(self):
        """Maneja solicitudes POST para consultas LLM."""
        parsed = urlparse(self.path)
        decoded_path = unquote(parsed.path, encoding='utf-8')
        
        # ── API: consultar LLM (Anthropic) ────────────────────────────────────
        if decoded_path == "/api/llm-query":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                payload = json.loads(body)

                query = payload.get("query", "").strip()
                if not query:
                    self._json({"ok": False, "error": "Pregunta vacía"})
                    return

                provider = payload.get("provider", DEFAULT_LLM_PROVIDER)
                if provider not in LLM_PROVIDERS:
                    provider = DEFAULT_LLM_PROVIDER

                model = payload.get("model", "") or LLM_PROVIDERS[provider]["default_model"]
                api_key = payload.get("api_key", "").strip()

                context = {
                    "videos_summary": f"Total de {len(_index.get('videos', []))} vídeos indexados" if _index else "No hay vídeos indexados",
                    "selected_videos": payload.get("videos", [])
                }

                result = _query_with_provider(provider, api_key, model, query, context)
                self._json(result)

            except Exception as e:
                self._json({"ok": False, "error": f"Error procesando solicitud: {str(e)}"})
        else:
            self.send_error(404, "Endpoint no encontrado")

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, file_path: Path):
        """Sirve un archivo estático con detección de tipo MIME."""
        ext = file_path.suffix.lower()
        mime_types = {
            '.html': 'text/html; charset=utf-8',
            '.js':   'application/javascript; charset=utf-8',
            '.css':  'text/css; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.vtt':  'text/vtt; charset=utf-8',
            '.srt':  'text/plain; charset=utf-8',
            '.png':  'image/png',
            '.jpg':  'image/jpeg',
            '.ico':  'image/x-icon',
        }
        content_type = mime_types.get(ext, 'application/octet-stream')
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, str(e))


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    configure_gemini()
    load_index()  # Cargar índice al iniciar
    print(f"✔ VerbaTube server en http://localhost:{PORT}/viewer.html")
    print(f"   Directorio: {BASE_DIR}")
    print("   ✔ Soporta Anthropic, OpenAI y Gemini desde la pestaña 'Preguntas IA' (configura proveedor y clave allí).")
    print("   Ctrl+C para detener\n")
    import webbrowser
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}/viewer.html")).start()
    with http.server.ThreadingHTTPServer(("", PORT), VerbaTubeHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
