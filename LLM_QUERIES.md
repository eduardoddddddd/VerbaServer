# 🤖 Consultas LLM en Verbatube
El servidor ya no depende de una sola API: la pestaña **"Preguntas IA"** permite elegir entre Anthropic Claude, OpenAI Chat y Google Gemini, seleccionar el modelo exacto para cada proveedor y pegar la clave API directamente en el panel. El backend recibe estos datos en cada consulta (`provider`, `model`, `api_key`) y dispara la llamada correspondiente sin guardar las claves en el servidor.

## Cambios realizados

### 1. Backend (`server.py`)
- Se añadió un mapa `LLM_PROVIDER_MAP` con los proveedores soportados y sus modelos predeterminados.
- Nuevo despachador `_query_with_provider()` que acepta `provider`, `model`, `api_key`, arma el mismo contexto enriquecido y llama a `fetch` sobre Anthropic, OpenAI o Gemini según sea necesario.
- Cada proveedor tiene su helper (`_request_anthropic`, `_request_openai`, `_request_gemini`), con manejo común de errores HTTP y traducción de la respuesta al formato `{ok, response, error}`.
- El endpoint `POST /api/llm-query` ahora valida `provider`, `model` y `api_key`, construye un resumen (`videos_summary`) y pasa la carga al despachador. Devuelve la respuesta lista para el cliente, incluyendo mensajes de error manejables.

### 2. Frontend (`viewer.html`)
- Nuevo bloque de campos encima del textarea: selector de proveedor, selector de modelo y campo de clave API (tipo `password`) acompañados por un mensaje que aclara que la clave no se persiste.
- La función `setupLLMSelectors()` carga los proveedores definidos en el script, reactualiza los modelos disponibles y mantiene el primer modelo como valor por defecto.
- `sendLLMQuery()` incorpora el proveedor elegido, el modelo y la clave al cuerpo JSON y valida que el usuario haya escrito la clave antes de enviar la consulta. También sigue mostrando el spinner y el área de respuesta en el mismo panel.
- Se agregaron estilos específicos para `input/select` junto a una pista (`.llm-hint`) que explica qué hace la clave API.

## Configuración requerida

1. Instala `yt-dlp` para descargar subtítulos (`pip install yt-dlp`) y la librería oficial de Gemini (`pip install google-generativeai`).
2. Obtén las claves para los proveedores que quieras usar:
   - **Anthropic:** crea una cuenta en [https://console.anthropic.com](https://console.anthropic.com) y copia la clave tipo `sk_ant_...`.
   - **OpenAI:** genera una clave en [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys) (por ejemplo `sk-...`).
   - **Gemini:** copia tu API Key directa desde Google AI Studio.
3. Arranca el servidor con `python server.py`. Durante el inicio se te pedirá la clave de Gemini en la consola; esa API Key se queda en memoria y se usa sin OAuth ni tokens de servicio. Si la dejas vacía, Gemini no estará disponible en esta sesión.
4. Abre `http://localhost:8080/viewer.html`.
5. En la pestaña **"Preguntas IA"**:
   - Elige el proveedor y el modelo deseado.
   - Introduce la clave API en el campo correspondiente (tipo `password`) para Anthropic u OpenAI.
   - Escribe tu pregunta y pulsa "Enviar pregunta".

## Proveedores soportados

- **Anthropic Claude** (`claude-3-5-sonnet-20241022`, `claude-3-opus-20250219`, etc.). Usa `x-api-key` y el endpoint `https://api.anthropic.com/v1/messages`.
- **OpenAI Chat** (`gpt-4o-mini`, `gpt-4o`, `gpt-4o-mini-2024-12-17`). Llama a `https://api.openai.com/v1/chat/completions` con cabecera `Authorization: Bearer <api_key>`.
- **Google Gemini** (`gemini-1.5-pro`, `gemini-1.5`). Se invoca con la librería oficial `google-generativeai`, y el servidor pide la API Key durante el arranque para configurar `genai.configure(api_key=...)` y generar texto con `genai.generate_text`.

Para cada proveedor el servidor repite el mismo contexto enriquecido con títulos, canales y fragmentos de texto de hasta 10 vídeos, y limita la solicitud a 2048 tokens o 512 tokens según el proveedor.

## Uso

1. Abre la pestaña **"Preguntas IA"** desde la barra de navegación.
2. Elige el proveedor (Anthropic, OpenAI o Gemini) y el modelo preferido.
3. Pega la clave API (El campo es confidencial y se limpia al cerrar la página).
4. Redacta tu pregunta sobre los subtítulos disponibles y haz clic en **"Enviar pregunta"**.
5. La respuesta aparece en el panel, o se muestra un error si la clave/modelo no funcionan (ver sección de troubleshooting).

### Ejemplos de preguntas
```
¿Cuáles son los temas principales sobre astrología?
¿Hay alguna conexión entre los vídeos de diferentes canales?
Resumir los puntos clave del vídeo sobre "Las casas astrológicas"
¿Qué diferencias hay entre los conceptos mencionados en los vídeos sobre Reiki?
Analizar patrones comunes en los temas de espiritualidad
```

## Estructura de datos

### Contexto enviado al modelo
Cada consulta incluye:
- `videos_summary`: el número total de vídeos indexados.
- `selected_videos`: el vídeo activo (si hay alguno) con `video_id`, `title`, `channel`, `duration_fmt`, `languages_available` y `full_text`.

### Payload
```json
{
  "query": "Tu pregunta aquí",
  "videos": [ ... ],
  "provider": "anthropic | openai | gemini",
  "model": "claude-3-5-sonnet-20241022",
  "api_key": "tu_clave_secreta"
}
```

El API key se usa solo en la petición y **no se almacena en el servidor**.

## Limitaciones

1. Cada proveedor tiene sus propios límites de tokens y costos; ajusta el modelo/temperatura según lo necesites.
2. Las respuestas pueden tardar entre 5 y 30 segundos en función del contexto y la latencia del proveedor.
3. Si cambias de modelo o proveedor, recuerda pegar la clave correspondiente en el panel.
4. El servidor no gestiona renovación automática de claves; si una expira, actualiza el campo y vuelve a enviar la pregunta.

## Troubleshooting

- **"Clave API no proporcionada"**: asegúrate de haber escrito la clave antes de enviar la consulta.
- **"Error API (401)"**: revisa que la clave sigue activa en la consola del proveedor y no contiene espacios.
- **"No hay vídeos indexados"**: descarga subtítulos primero usando la pestaña **"+ Descargar"** y espera a que termine la indexación.
- **"Timeout/latencia alta"**: reduce el número de vídeos en contexto o elige un modelo más económico (por ejemplo `gpt-4o-mini`).

## Notas técnicas

- `server.py` expone únicamente `/api/llm-query` para enviar las consultas.
- El servidor detecta `provider`, `model` y `api_key` en cada petición y nunca guarda la clave en disco.
- `viewer.html` mantiene el `LLM_PROVIDER_MAP` en el frontend, y `setupLLMSelectors()` rellena los selects en caliente.
- Si necesitas añadir un nuevo proveedor, extiende el mapa tanto en el servidor como en `viewer.html` para mantener la coherencia.
