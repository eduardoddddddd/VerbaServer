# VerbaServer

Servicio web para extraer subtítulos de YouTube, indexarlos y consultarlos desde navegador o API.

`VerbaServer` nace como variante orientada a servidor Linux a partir de `VerbaSant / VerbaTube`. Está pensado para correr 24/7 en una máquina propia, servir como base de conocimiento personal y actuar más adelante como backend para automatizaciones de Telegram.

## Qué hace

- descarga subtítulos de YouTube con `yt-dlp`
- guarda `.vtt` y `.info.json`
- construye un índice `verbatube.json`
- sirve una UI web (`viewer.html`)
- expone endpoints para descarga, logs, reindexado y consultas LLM
- incluye wrappers Linux para despliegue con `systemd`

## Estado actual

Desplegado en `astromalik-server`:

- UI: `http://34.175.40.49:8090/viewer.html`
- healthcheck: `http://34.175.40.49:8090/health`

Servicio activo:

```bash
sudo systemctl status verbaserver
```

## Estructura del repo

```text
VerbaServer/
├── server.py
├── downloader.py
├── indexer.py
├── server_linux.py
├── downloader_linux.py
├── indexer_linux.py
├── viewer.html
├── .env.example
├── requirements-linux.txt
├── deploy/
│   ├── verbaserver.service
│   └── nginx.verbaserver.conf
└── DEPLOY.md
```

## Variables de entorno

```env
VERBATUBE_HOST=0.0.0.0
VERBATUBE_PORT=8090
VERBATUBE_DATA_DIR=/opt/verbaserver/data
VERBATUBE_OPEN_BROWSER=false
GEMINI_API_KEY=
```

## Arranque en Linux

```bash
python3 -m venv /opt/verbaserver/venv
/opt/verbaserver/venv/bin/pip install -r requirements-linux.txt
cp .env.example .env
/opt/verbaserver/venv/bin/python server_linux.py
```

Endpoints locales:

```bash
http://127.0.0.1:8090/viewer.html
http://127.0.0.1:8090/health
```

## API disponible

- `GET /api/download?url=...&lang=...`
- `GET /api/log?offset=0`
- `GET /api/reindex`
- `POST /api/llm-query`
- `GET /health`

## Notas operativas

- Para vídeos sueltos funciona muy bien.
- Para canales grandes, YouTube puede bloquear parte de la descarga con protección antibot.
- Sin cookies persistentes de YouTube, la cobertura de canales grandes puede ser parcial.
- El texto ocupa poco; lo que más pesa son los `.info.json`.

## Hoja de ruta

- soporte de cookies de YouTube
- reverse proxy limpio con `nginx`
- integración con Telegram para procesar vídeos individuales
- modo ligero con menos metadatos persistidos

## Referencias

- despliegue: [DEPLOY.md](./DEPLOY.md)
- servicio de systemd: [deploy/verbaserver.service](./deploy/verbaserver.service)
