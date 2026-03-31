# 🔍 Resumen de cambios (marzo 2026)

## Sesión 2026-03-15 (noche) — Exportación Profesional (MD & PDF)

Se implementa un sistema de exportación de conocimiento de alta fidelidad para transformar transcripciones y respuestas de IA en documentos estructurados.

### 1. Motor de Exportación (`ExportManager` en `viewer.html`)
- **Markdown (.md)**: Generación de archivos con **YAML Frontmatter** (metadatos de vídeo: título, canal, fecha, URL, video_id). Ideal para Obsidian y Notion.
- **PDF (.pdf)**: Generación mediante `html2pdf.js` con diseño editorial:
  - **Tipografía**: Títulos en *Outfit* (sans) y cuerpo en *Lora* (serif).
  - **Legibilidad**: Interlineado 2.0 y márgenes de párrafo 2.2em para evitar "muros de texto".
  - **Branding**: Encabezado con logo VerbaSant, rejilla de metadatos y pie de página institucional.

### 2. Segmentación Heurística de Texto
- Mejora de la función `groupCues()`:
  - Umbral de silencio reducido a **2.5s**.
  - Límite forzado de **8 líneas por párrafo** para asegurar que el texto "respire" incluso en discursos sin pausas.

### 3. Integración en UI
- **Toolbar del Visualizador**: Botones MD/PDF para exportar la transcripción activa.
- **Panel IA**: Botones MD/PDF dinámicos que aparecen tras recibir una respuesta de la IA.

### 4. Dependencias nuevas
- `cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js` (inyectado vía CDN).

---

## Sesión 2026-03-15 (tarde) — Fix yt-dlp + limpieza entorno Python

### 1. Fix descarga (`server.py`)
`yt-dlp` en el PATH apuntaba al wrapper de Python314 (`C:\Users\Edu\AppData\Local\Programs\Python\Python314\Scripts\yt-dlp.exe`) cuyo intérprete no existía en esa ruta — salía con código 1 sin output.

Solución: cambiar el comando en `run_download_and_index()`:
```python
# Antes
cmd = ["yt-dlp", ...]
# Ahora
cmd = ["py", "-3.12", "-m", "yt_dlp", ...]
```

### 2. Limpieza PATH de usuario
- Eliminadas `C:\Python314` y `C:\Python314\Scripts` del PATH de usuario.
- `PY_PYTHON=3.12` fijado → `py` sin versión siempre resuelve a Python 3.12.
- Python 3.14 accesible con `py -3.14` si se necesita explícitamente.

### 3. Aclaración arquitectura
- **PyTorch + CUDA + ChromaDB** → exclusivo de AstroExtracto (embeddings semánticos locales con e5-large en RTX 4070).
- **VerbaSant** → sin inferencia local. Búsqueda por keywords en Python puro + APIs externas (Gemini, Anthropic, OpenAI).

### Estado paquetes clave en Python 3.12
| Paquete | Versión |
|---|---|
| google-generativeai | 0.8.6 |
| yt-dlp | 2026.03.13 |

---

## Sesión 2026-03-15 — Fixes Gemini + RAG básico por keywords

### 1. Fixes críticos Gemini (`server.py`)

**API obsoleta corregida:**
`genai.generate_text()` no existe en `google-generativeai` v0.8.6. Sustituido por:
```python
genai.configure(api_key=effective_key)
gemini_model = genai.GenerativeModel(model)
response = gemini_model.generate_content(prompt_text)
```

**Key de UI ahora funciona:**
`_request_gemini` ignoraba el parámetro `api_key` y usaba solo el global `GEMINI_API_KEY`.
Corregido con `effective_key = api_key or GEMINI_API_KEY`.

**Modelos Gemini actualizados:**
`gemini-1.5-pro` y `gemini-1.5` retirados por Google. Nuevos modelos en dropdown:
- `gemini-2.5-flash` → default (free tier, 20 RPD)
- `gemini-1.5-flash` → alternativa free tier
- `gemini-2.0-flash` → requiere billing (quota 0 en free tier)

### 2. RAG básico: contexto completo + búsqueda por keywords (`server.py`)

**`_build_context_text(context, query="")` rediseñada:**

- **Con vídeo seleccionado:** envía `full_text` completo (~14K chars) en lugar del recorte de 500 chars anterior.
- **Sin vídeo seleccionado y con query:** busca keywords (palabras >3 chars) en los 999 vídeos del índice; envía top-5 por score de relevancia (sum de ocurrencias) con transcripción completa.

Corpus: 999 vídeos · ~18.9M chars · ~4.7M tokens totales · ~14K chars/vídeo media.
Top-5 vídeos × 14K chars ≈ 70K chars / ~17K tokens → dentro del límite de Gemini 2.5 Flash (1M tokens).

**`_query_with_provider()` actualizado:** pasa `query` a `_build_context_text()`.

### 3. Modelos dropdown (`viewer.html`)
Actualizado `LLM_PROVIDER_MAP.gemini.models` con los modelos actuales.

---

## Sesión 2026-03-14 — Multi-proveedor LLM

Se amplía la integración LLM para soportar **Anthropic Claude, OpenAI Chat y Google Gemini**
desde la UI, sin variables de entorno.

### Backend (`server.py`)
- `LLM_PROVIDERS` map con label y modelo por defecto.
- `_query_with_provider()` despachador unificado.
- Helpers: `_request_anthropic`, `_request_openai`, `_request_gemini`.
- `_handle_http_error()` y `_extract_response()` para normalización.
- `configure_gemini()` solicita key interactivamente al arrancar.
- `POST /api/llm-query` acepta `provider`, `model`, `api_key`.

### Frontend (`viewer.html`)
- `LLM_PROVIDER_MAP` con proveedores y modelos.
- Selects de proveedor/modelo + campo password para API key.
- `setupLLMSelectors()` / `updateLLMModelOptions()`.
- `sendLLMQuery()` actualizado para multi-proveedor.

### Documentación
- `README.md`, `LLM_QUERIES.md`, `RESUMEN_CAMBIOS.md`: actualizados.

## Próximos pasos sugeridos
1. Mejorar scoring RAG: TF-IDF o embeddings (ChromaDB) en lugar de conteo simple.
2. Mostrar en UI qué vídeos se han usado como contexto.
3. Sesión de API key en `sessionStorage` para no reintroducirla cada recarga.
4. Limitar tokens de contexto dinámicamente según el modelo seleccionado.
