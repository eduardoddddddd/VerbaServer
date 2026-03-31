# CHANGELOG

## [1.4.0] - 2026-03-15

### 🐛 Fix descarga yt-dlp + limpieza PATH Python

#### Backend (`server.py`)
- Comando `yt-dlp` sustituido por `py -3.12 -m yt_dlp` en `run_download_and_index()`.
  El wrapper `yt-dlp.exe` del PATH apuntaba a Python314 inexistente y salía con código 1 silenciosamente.

#### Entorno Windows (PATH usuario)
- Eliminadas `C:\Python314` y `C:\Python314\Scripts` del PATH de usuario.
- `PY_PYTHON=3.12` fijado como variable de entorno de usuario → `py` sin versión explícita va siempre a 3.12.
- Python 3.14 sigue instalado en `C:\Python314` y accesible con `py -3.14` si hace falta.

#### Aclaración arquitectura (sin cambios en código)
- PyTorch + CUDA + ChromaDB son exclusivos de **AstroExtracto** (embeddings locales).
- **VerbaSant** no usa inferencia local: búsqueda por keywords en Python puro + llamadas a APIs externas.

---

## [1.3.0] - 2026-03-15

### ✨ RAG básico: búsqueda por keywords + transcripción completa

#### Backend (`server.py`)
- `_build_context_text()` rediseñada con firma `(context, query="")`:
  - **Con vídeo seleccionado:** manda `full_text` completo (~14K chars/vídeo) en lugar del recorte arbitrario de 500 chars anterior.
  - **Sin vídeo seleccionado:** búsqueda por keywords de la query en los 999 vídeos del índice; manda los top-5 más relevantes con transcripción completa. Score = sum de ocurrencias de cada palabra clave (>3 chars) en el texto.
- `_query_with_provider()` actualizado para pasar `query` a `_build_context_text()`.

#### Modelos Gemini actualizados
- Default cambiado de `gemini-1.5-pro` (retirado) a `gemini-2.5-flash`.
- Dropdown viewer: `gemini-2.5-flash` (free tier), `gemini-1.5-flash`, `gemini-2.0-flash` (requiere billing).

### 🐛 Fixes críticos Gemini

- **API obsoleta:** `genai.generate_text()` sustituido por `genai.GenerativeModel(model).generate_content(prompt)` (API correcta para `google-generativeai` v0.8.6).
- **Key de UI ignorada:** `_request_gemini` usaba solo el global `GEMINI_API_KEY` (introducido por consola al arrancar). Ahora usa `effective_key = api_key or GEMINI_API_KEY`, priorizando la key introducida en la UI.
- **Python incorrecto:** el server arrancaba con Python 3.14 donde `google-generativeai` no estaba instalado. Fijado usando `py server.py` (launcher → Python 3.12 donde el paquete sí está instalado).

### 📊 Estadísticas del corpus

- 999 vídeos indexados
- ~18.9M chars totales (~4.7M tokens)
- ~14K chars/vídeo de media

---

## [1.2.0] - 2026-03-14

### ✨ Multi-proveedor LLM: Anthropic, OpenAI y Google Gemini

#### Backend (`server.py`)
- `LLM_PROVIDERS` map con label y modelo por defecto para cada proveedor.
- `_query_with_provider(provider, api_key, model, query, context)` despachador unificado.
- Helpers dedicados: `_request_anthropic()`, `_request_openai()`, `_request_gemini()`.
- `_handle_http_error()` unifica extracción de mensajes de error HTTP.
- `_extract_response()` normaliza respuesta para la UI independientemente del proveedor.
- `configure_gemini()` solicita API Key de Gemini interactivamente al arrancar.
- `POST /api/llm-query` acepta campos `provider`, `model`, `api_key` además de `query` y `videos`.
- Eliminada dependencia de variable de entorno `ANTHROPIC_API_KEY`.

#### Frontend (`viewer.html`)
- `LLM_PROVIDER_MAP` con proveedores y modelos disponibles.
- `setupLLMSelectors()` / `updateLLMModelOptions()` rellenan selects en tiempo de carga.
- Campo `password` para API key con hint informativo.
- `sendLLMQuery()` recoge proveedor, modelo y key de la UI antes de enviar.

#### Documentación
- `README.md`: eliminadas instrucciones de variable de entorno; nueva sección multi-proveedor.
- `LLM_QUERIES.md`: reescrito para configuración multi-proveedor.
- `RESUMEN_CAMBIOS.md`: añadido.

---

## [1.1.0] - 2026-03-14

### ✨ Características nuevas

#### Integración Anthropic Claude
- **Nueva pestaña "🤖 Preguntas IA"** en la barra de navegación
- Consultas LLM sobre contenido de subtítulos
- Soporte para preguntas complejas y análisis de patrones
- Panel dedicado con interfaz limpia e intuitiva

#### Backend (`server.py`)
- `load_index()` - Carga automática del índice al iniciar
- `query_anthropic(query, context)` - Conexión con API de Anthropic
- Endpoint `POST /api/llm-query` - Procesamiento de consultas LLM
- Variables de configuración para API key y modelo
- Validación de API key con feedback en consola

#### Frontend (`viewer.html`)
- Nueva pestaña de navegación: "🤖 Preguntas IA"
- Panel LLM con:
  - Campo textarea para preguntas
  - Botón enviar
  - Área de respuesta con scroll automático
  - Indicador de carga
  - Manejo de errores con estilos diferenciados
- Nuevos estilos CSS (~90 líneas)
- Función `sendLLMQuery()` para envío de consultas
- Actualización de `setAppTab()` para nueva pestaña

### 📚 Documentación

- `LLM_QUERIES.md` - Guía completa de:
  - Instalación y configuración
  - Ejemplos de uso
  - Troubleshooting
  - Notas técnicas
  - Roadmap futuro
- Actualización de `README.md` con:
  - Instrucciones de configuración API key
  - Nueva sección de uso de IA
  - Detalles técnicos de la integración
  - Guía para desarrolladores

### 🔧 Cambios técnicos

**Dependencias nuevas:**
- `urllib.request`, `urllib.error` (stdlib Python)

**Configuración nueva:**
```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
```

**Protocolo API:**
```
POST /api/llm-query
{
  "query": "string",
  "videos": [
    {"video_id": "...", "title": "...", "full_text": "..."}
  ]
}

Response:
{
  "ok": boolean,
  "response": "string",
  "error": "string (si no ok)"
}
```

### 🎯 Características del modelo

- **Modelo:** Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- **Max tokens:** 2048
- **Context:** Hasta 10 vídeos
- **Latencia:** 5-30 segundos típicamente
- **Seguridad:** API key solo servidor, HTTPS

### 🚀 Mejoras de rendimiento

- Carga incremental del índice
- Limitación de vídeos en contexto (máx 10) para evitar overflow de tokens
- Request timeouts de 30 segundos
- Error handling graceful

### 🔒 Seguridad

- API key: Solo en variables de entorno (no en código)
- HTTPS: Comunicación segura con Anthropic
- Validación: Verificación de API key al iniciar
- Sin persistencia: Las consultas no se guardan
- Sanitización: Manejo de caracteres especiales en JSON

### 📝 Cambios en archivos existentes

#### `server.py`
- Línea 13-15: Imports nuevos (urllib)
- Línea 18-22: Configuración Anthropic
- Línea 25-42: Función load_index()
- Línea 62-148: Función query_anthropic()
- Línea 310-341: Método do_POST() en VerbaTubeHandler
- Línea 355-365: Actualización de __main__ con load_index()

#### `viewer.html`
- Línea 145-232: Estilos CSS para LLM panel
- Línea 856: Nueva pestaña "🤖 Preguntas IA"
- Línea 915-931: Panel HTML LLM
- Línea 1458-1471: Actualización setAppTab()
- Línea 1533-1584: Función sendLLMQuery() y sección LLM TAB

### ✅ Testing

- Validación de sintaxis Python: ✓
- Sintaxis HTML/CSS: ✓
- Funciones JavaScript: ✓
- Manejo de errores API: ✓

### 📋 Archivos nuevos

- `LLM_QUERIES.md` (208 líneas)
- `CHANGELOG.md` (este archivo)

### 🔄 Compatibilidad

- ✓ Windows (CMD, PowerShell)
- ✓ Mac (Bash, Zsh)
- ✓ Linux (Bash, etc.)
- ✓ Python 3.8+
- ✓ Todos los navegadores modernos

### 💡 Qué es fácilmente modificable

- Cambiar modelo LLM: Edita `ANTHROPIC_MODEL` en `server.py:19`
- Cambiar max_tokens: Edita en `query_anthropic():121`
- Agregar más contexto: Expande `context_text` en `query_anthropic():87`
- Cambiar estilos: CSS en `viewer.html:145-232`
- Agregar historial: Captura respuestas en localStorage

### 🐛 Problemas conocidos

Ninguno identificado. Sistema completamente funcional.

### 📚 Documentación relacionada

- `README.md` - Guía general del proyecto
- `LLM_QUERIES.md` - Guía específica de consultas IA
- `CHANGELOG.md` - Este archivo (historial de cambios)

---

## [1.0.0] - 2024-XX-XX (Versión inicial)

Base de datos local de subtítulos YouTube con:
- Búsqueda full-text
- Filtros por canal e idioma
- Visualización con/sin timestamps
- Descarga automática de subtítulos
- Indexación incremental
