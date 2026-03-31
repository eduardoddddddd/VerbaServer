# VerbaServer Deploy

## Estructura recomendada

```bash
/opt/verbaserver/
  app/
  venv/
  data/
    subtitles/
```

## Variables de entorno

```bash
VERBATUBE_HOST=127.0.0.1
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

## Endpoints locales

```bash
http://127.0.0.1:8090/viewer.html
http://127.0.0.1:8090/health
```

## Endpoint publico provisional

Si abres el puerto 8090 en firewall o lo publicas por nginx/subdominio:

```bash
http://34.175.40.49:8090/viewer.html
```
