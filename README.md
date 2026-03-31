# Verbatube

Base de datos local de subtítulos de YouTube con visualizador web.
Sin servidores externos, sin APIs de pago. Todo local y offline.

**🆕 Con soporte para consultas LLM via API Anthropic (Claude)**

## Requisitos

```bash
pip install yt-dlp
```

**Para usar consultas IA (opcional):**
- Cuenta en [Anthropic Console](https://console.anthropic.com)
- API key configurada como variable de entorno

## Instalación en un PC/Mac nuevo

### 1. Clona el repositorio

```bash
git clone https://github.com/eduardoddddddd/verbatube.git
cd verbatube
```

### 2. Configura la ruta de tus VTTs

Abre los tres archivos siguientes y cambia `CORPUS_DIR` a la ruta donde quieres guardar los subtítulos:

**`server.py`** (línea ~18):
```python
CORPUS_DIR = Path(r"C:\Users\Edu\VTTs")   # ← cambia esto
```

**`indexer.py`** (línea ~21):
```python
CORPUS_DIR = Path(r"C:\Users\Edu\VTTs")   # ← cambia esto
```

**`downloader.py`** (línea ~17):
```python
CORPUS_DIR = Path(r"C:\Users\Edu\VTTs")   # ← cambia esto
```

**Ejemplos por sistema:**
- Windows: `Path(r"C:\Users\TuUsuario\VTTs")`
- Mac/Linux: `Path("/Users/tuusuario/VTTs")` o `Path.home() / "VTTs"`

> Esta es la **única configuración necesaria**. El resto funciona igual en cualquier sistema.

### 3. (Opcional) Configura tu API key de Anthropic

Para usar la pestaña "Preguntas IA":

**Windows (CMD):**
```bash
set ANTHROPIC_API_KEY=sk_ant_... (tu clave)
python server.py
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk_ant_..."
python server.py
```

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY="sk_ant_..."
python server.py
```

Para obtener tu clave:
1. Ve a https://console.anthropic.com
2. Crea una cuenta o inicia sesión
3. Genera una nueva clave en la sección de configuración
4. Úsala en el comando anterior

### 4. Arranca el servidor

```bash
python server.py
```

Se abre automáticamente en: **http://localhost:8080/viewer.html**

Si configuraste la API key de Anthropic, verás:
```
✅ VerbaTube server en http://localhost:8080/viewer.html
   Directorio: ...
   ✓ API key Anthropic detectada
   Ctrl+C para detener
```

## Uso diario

### Descargar un canal o vídeo

**Opción A — desde el propio viewer** (recomendado):
Pestaña **"+ Descargar"** → URL → Iniciar descarga → log en tiempo real → recarga automática.

**Opción B — línea de comandos:**
```bash
python downloader.py --channel "https://www.youtube.com/@canal"
python downloader.py --playlist "https://www.youtube.com/playlist?list=PLxxx"
python downloader.py --video "https://www.youtube.com/watch?v=xxxxx"
python downloader.py --channel "URL" --lang es        # solo español
python downloader.py --channel "URL" --lang es,en     # español + inglés
```

Tras la descarga, el indexer se lanza automáticamente desde el viewer.
Si se usa la línea de comandos, ejecutar también:
```bash
python indexer.py             # incremental (solo nuevos)
python indexer.py --rebuild   # reconstruir todo desde cero
```

### Consultar con IA 🤖

**Pestaña nueva: "🤖 Preguntas IA"**

1. Haz clic en la pestaña "Preguntas IA" en la barra superior
2. Escribe tu pregunta (puede ser compleja, sobre múltiples vídeos, etc.)
3. Haz clic en "▶ Enviar pregunta"
4. Claude analizará todos tus subtítulos y te dará una respuesta

### Selección de proveedor y modelo
El panel **"Preguntas IA"** ahora incluye tres campos adicionales: un desplegable para elegir el proveedor (Anthropic Claude, OpenAI Chat o Google Gemini), otro para seleccionar el modelo disponible de ese proveedor y un campo de clave API (tipo `password`). Introduce la clave allí; no es necesario exportarla como variable de entorno, ya que se usa en cada consulta y no se guarda en el servidor.

Si cambias de proveedor o modelo, pega la clave correspondiente antes de enviar una nueva pregunta. Cada opción del desplegable se carga desde `viewer.html` para mantener sincronizados los modelos soportados.

**Gemini y la clave desde la consola:**
Al arrancar `python server.py` se te pedirá de forma interactiva la API Key de Google Gemini. Copia la clave que obtienes en Google AI Studio y pégala cuando aparezca el prompt; el servidor la configura en memoria y la usa para todas las consultas gemini. Si lo dejas vacío, Gemini queda deshabilitado hasta el siguiente reinicio. Esta clave se maneja con la librería oficial `google-generativeai`, así que antes de empezar instala `pip install google-generativeai`.

**Ejemplos de preguntas:**
```
¿Cuáles son los temas principales sobre astrología?

¿Hay alguna conexión entre los vídeos de diferentes canales?

Resumir los puntos clave del vídeo sobre "Las casas astrológicas"

¿Qué diferencias hay entre los conceptos mencionados en los vídeos sobre Reiki?

Analizar patrones comunes en los temas de espiritualidad
```

## Estructura del proyecto

```
verbatube/
├── server.py           # Servidor local (arrancar siempre con esto)
├── downloader.py       # Descarga subtítulos de YouTube vía yt-dlp
├── indexer.py          # Construye el índice JSON de búsqueda
├── viewer.html         # Interfaz web (SPA completa)
├── verbatube.json      # Índice generado — NO subir a git
├── README.md           # Este archivo
└── LLM_QUERIES.md      # 🆕 Documentación detallada de consultas IA
```

Los VTTs se guardan en `CORPUS_DIR` (configurable), organizados por canal:
```
VTTs/
├── Canal A/
│   ├── 20240101_VIDEOID_Título.es.vtt
│   └── 20240101_VIDEOID_Título.info.json
└── Canal B/
    └── ...
```

## Funcionalidades del visualizador

- Búsqueda full-text en tiempo real sobre el texto de todos los subtítulos
- Filtro por canal e idioma
- Vista limpia (párrafos agrupados, sin timestamps)
- Vista con timestamps (cada fragmento enlaza al minuto exacto en YouTube)
- Búsqueda dentro del vídeo activo con navegación entre coincidencias
- Deduplicación del ASR de YouTube (elimina las repeticiones típicas)
- Pestaña Descargar con log en tiempo real
- **🆕 Pestaña Preguntas IA** — Consultas LLM sobre todos tus subtítulos

## Cambios recientes (v1.1)

### ✅ Integración Anthropic Claude

#### Backend (`server.py`)
- Nueva función `load_index()` — Carga automáticamente `verbatube.json` al iniciar
- Nueva función `query_anthropic(query, context)` — Conecta con API de Anthropic
- Nuevo endpoint `POST /api/llm-query` — Procesa consultas LLM
- Nuevas variables globales:
  ```python
  ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
  ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
  ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
  ```
- Validación de API key con mensaje al iniciar servidor

#### Frontend (`viewer.html`)
- **Nueva pestaña navegación**: "🤖 Preguntas IA"
- **Nuevo panel LLM** con:
  - Campo textarea para preguntas
  - Botón para enviar
  - Área de respuesta con scroll
  - Indicador de carga
- **Nuevos estilos CSS**:
  ```css
  #llm-panel { /* Panel principal */ }
  .llm-title, .llm-subtitle { /* Títulos */ }
  .llm-field { /* Campos de entrada */ }
  .llm-btn { /* Botones */ }
  #llm-response { /* Área de respuestas */ }
  #llm-response.error { /* Estilos de error */ }
  .llm-loading { /* Indicador carga */ }
  ```
- **Nuevas funciones JavaScript**:
  - `sendLLMQuery()` — Envía consulta y muestra respuesta
  - `setAppTab(tab)` — Actualizada para soportar pestaña LLM

#### Archivos nuevos
- `LLM_QUERIES.md` — Documentación completa sobre consultas IA

### Detalles técnicos

**Endpoint API:**
```
POST /api/llm-query
Content-Type: application/json

{
  "query": "Tu pregunta aquí",
  "videos": [
    { "video_id": "...", "title": "...", "full_text": "..." }
  ]
}

Response:
{
  "ok": true,
  "response": "Respuesta del modelo Claude..."
}
```

**Modelo utilizado:**
- `claude-3-5-sonnet-20241022` (última versión)
- Max tokens: 2048
- Context window: Hasta 10 vídeos

**Seguridad:**
- API key solo se usa en servidor (no se envía al cliente)
- Comunicación HTTPS con Anthropic
- Sin persistencia de consultas

## Notas importantes

- **Arrancar siempre con `python server.py`**, no con `python -m http.server`.
  Si se modifica cualquier `.py`, reiniciar el servidor.
- `verbatube.json` puede pesar bastante (≈50 KB por vídeo). Está en `.gitignore`.
- Algunos vídeos de YouTube no tienen subtítulos automáticos — en ese caso
  solo se descarga el `.info.json` sin `.vtt` y no aparecen en el viewer.
- La indexación es incremental: solo procesa VTTs nuevos o modificados.
- **Consultas IA**: Cada consulta consume tokens y tiene costo en Anthropic

## Troubleshooting

### Consultas IA no funcionan
```
❌ "ANTHROPIC_API_KEY no configurada"
```
- Verifica que configuraste la variable de entorno antes de iniciar `server.py`
- En Windows, usa la misma ventana CMD/PowerShell donde iniciaste el servidor

### API key inválida
```
❌ "Error 401: API key inválida"
```
- Copia la clave completa sin espacios desde https://console.anthropic.com
- Verifica que la clave sigue siendo válida (algunas se revocan)

### Timeout en consultas
- Las consultas con mucho contexto pueden ser lentas (5-30 segundos)
- Intenta con preguntas más específicas
- Verifica tu conexión a Internet

### "No hay vídeos indexados"
- Descarga subtítulos primero: Pestaña "+ Descargar"
- Espera a que se complete la indexación

## Para desarrolladores

### Cambiar el modelo LLM
En `server.py`, línea ~19:
```python
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"  # ← cambia esto
```

Modelos disponibles en Anthropic:
- `claude-3-5-sonnet-20241022` (recomendado - mejor balance precio/rendimiento)
- `claude-3-opus-20250219` (más potente pero más caro)
- `claude-3-haiku-20250307` (más rápido pero menos capaz)

### Aumentar contexto
En `query_anthropic()`, modifica:
```python
"max_tokens": 2048,  # ← aumenta o reduce según necesites
```

### Agregar persistencia de consultas
Modifica `sendLLMQuery()` en `viewer.html` para guardar respuestas en localStorage o IndexedDB

### Exportar respuestas
Agrega botón de descarga en el panel LLM para generar PDF/Markdown

---

## Autoría

**Eduardo Abdul Malik Arias**
Ingeniero en Informática · Consultor SAP Basis · Órgiva, Granada
Concepción, diseño y dirección del proyecto.

**Claude Sonnet 3.5 & 4.6** — *Anthropic*
Modelos de lenguaje de propósito general.
Desarrollo de código, arquitectura, documentación e integración LLM.

> *Este proyecto nació de una conversación. La idea es humana; la implementación, colaborativa.*

---

**Última actualización:** 14 de marzo de 2026  
**Versión:** 1.1 (con soporte LLM Anthropic)
