# Editor PBP - Censura de audio

Aplicacion local (Docker) que transcribe un audio con Whisper, resalta palabras
prohibidas dentro del texto completo, y permite generar un audio censurado
(beep) sobre las palabras seleccionadas. Todo corre en local, sin llamadas a
APIs externas.

## Requisitos
- Docker y Docker Compose (Docker Desktop en Mac/Windows)

## Uso

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend (API): http://localhost:8080/api (proxied por nginx)

El primer arranque descarga el modelo Whisper `medium` (configurable con la
variable de entorno `WHISPER_MODEL_SIZE` en `docker-compose.yml`), y lo guarda
en el volumen `whisper_models` para no volver a descargarlo en cada inicio.

## Palabras prohibidas

Editar `backend/words.json` (lista simple de palabras, sin necesidad de
tildes ni mayusculas: la normalizacion es automatica).

## Build multiplataforma (arm64 + amd64)

Para publicar imagenes que corran tanto en Mac Apple Silicon (arm64) como en
Windows/WSL2 (amd64):

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t editor-pbp-backend ./backend
docker buildx build --platform linux/amd64,linux/arm64 -t editor-pbp-frontend ./frontend
```

(Requiere un builder con soporte multiplataforma: `docker buildx create --use`.)

## Estructura

```
backend/    FastAPI + faster-whisper + ffmpeg (transcripcion y censura)
frontend/   React + Vite, servido con nginx (proxy /api -> backend)
```
