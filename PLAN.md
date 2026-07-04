# Plan de trabajo: Editor de censura de audio (PBP)

## Objetivo
Aplicación local (Docker) con interfaz web que:
1. Recibe un archivo de audio ya editado/listo.
2. Lo transcribe completo con Whisper, generando timestamps por palabra.
3. Muestra el **caption completo** en pantalla, con las **palabras prohibidas resaltadas dentro del texto** (para poder ver el contexto alrededor, no solo una lista suelta).
4. Permite al usuario tildar/destildar qué palabras censurar.
5. Genera el audio final con esas palabras censuradas (beep o silencio).
6. Permite descargar la transcripción (texto plano y/o JSON con timestamps).

Debe correr 100% en local (sin mandar audio a APIs externas) y funcionar vía Docker en:
- Mac Apple Silicon (M1, M2... M5) → arquitectura `arm64`
- Windows 10 → Docker Desktop con backend WSL2, arquitectura `amd64`

---

## Arquitectura

```
┌─────────────────────┐      ┌──────────────────────┐
│   Frontend (web)     │ HTTP │   Backend (API)       │
│  React/Vite o simple │◄────►│  FastAPI (Python)     │
│  HTML+JS             │      │  - faster-whisper     │
└─────────────────────┘      │  - ffmpeg (censura)   │
                              │  - lista palabras      │
                              └──────────────────────┘
        docker-compose (2 servicios: web + api)
```

- **Backend**: Python + FastAPI
  - `faster-whisper` (basado en CTranslate2, corre bien en CPU tanto ARM como x86, más rápido que whisper original)
  - Endpoint `POST /transcribe`: recibe audio, devuelve JSON con palabras + timestamps + flags de "prohibida"
  - Endpoint `POST /censor`: recibe audio + lista de rangos (timestamps) a censurar, devuelve audio procesado con `ffmpeg` (silencio o beep)
  - Endpoint `GET /transcript/export`: devuelve la transcripción en `.txt` (plano) y `.json` (con timestamps) para descarga
  - Diccionario de palabras prohibidas configurable (archivo `words.json`), con normalización (minúsculas, sin tildes, variantes leet-speak básicas)

- **Frontend**: página simple (HTML/CSS/JS vanilla o React ligero)
  - Subida de archivo (drag & drop)
  - Vista de transcripción completa como texto corrido, con `<mark>` o resaltado en las palabras detectadas
  - Al pasar el mouse o click sobre la palabra resaltada: checkbox para incluir/excluir de la censura + mostrar timestamp
  - Reproductor de audio con marcador de posición (opcional: waveform con wavesurfer.js)
  - Botón "Generar audio censurado" → descarga el resultado
  - Botón "Descargar transcripción" → descarga el texto (y opcionalmente el JSON con timestamps)

- **Docker**:
  - Imagen backend basada en `python:3.11-slim`, con `ffmpeg` instalado vía `apt`
  - Build multi-arquitectura con `docker buildx` (`linux/amd64,linux/arm64`) para que la misma imagen funcione en Mac Apple Silicon y Windows/WSL2
  - `docker-compose.yml` con 2 servicios (`api`, `web`) y un volumen para modelos de Whisper (para no re-descargarlos en cada arranque)

---

## Fases de trabajo

### Fase 1 — Setup del proyecto
- [ ] Estructura de carpetas: `backend/`, `frontend/`, `docker-compose.yml`
- [ ] `Dockerfile` backend (Python + ffmpeg + faster-whisper)
- [ ] `Dockerfile` frontend (nginx sirviendo estático, o Node si se usa build step)
- [ ] `docker-compose.yml` uniendo ambos servicios + volumen para cache de modelos Whisper

### Fase 2 — Backend: transcripción
- [ ] Endpoint `/transcribe`: recibe audio, corre `faster-whisper` con `word_timestamps=True`
- [ ] Normalización de texto (minúsculas, sin tildes) para matching
- [ ] Diccionario de palabras prohibidas (`words.json`), fácil de editar/ampliar
- [ ] Devolver JSON: lista de segmentos con texto completo + array de palabras con `{word, start, end, flagged: bool}`

### Fase 3 — Backend: censura
- [ ] Endpoint `/censor`: recibe audio original + lista de rangos `[{start, end}]` a censurar
- [ ] Usar `ffmpeg`/`pydub` para aplicar silencio o tono "beep" en esos rangos
- [ ] Devolver el audio procesado (descarga)

### Fase 4 — Frontend
- [ ] Página de subida de audio
- [ ] Vista de transcripción completa con resaltado inline de palabras detectadas (mostrando contexto)
- [ ] Checkboxes por palabra detectada para decidir censura
- [ ] Reproductor de audio sincronizado (click en palabra → salta a ese timestamp)
- [ ] Botón para generar y descargar el audio final censurado
- [ ] Botón para descargar la transcripción (`.txt` y/o `.json`)

### Fase 5 — Empaquetado multiplataforma
- [ ] Verificar build con `docker buildx build --platform linux/amd64,linux/arm64`
- [ ] Probar en Mac Apple Silicon (nativo arm64)
- [ ] Probar en Windows 10 con Docker Desktop + WSL2 (amd64)
- [ ] Documentar en `README.md` cómo levantar todo con `docker compose up`

### Fase 6 — Ajustes finales
- [ ] Elegir tamaño de modelo Whisper por defecto (ej. `small` o `medium` para balance velocidad/precisión en CPU)
- [ ] Permitir editar la lista de palabras prohibidas desde la interfaz (opcional)
- [ ] Manejo de archivos grandes (barra de progreso, límite de tamaño)

---

## Consideraciones técnicas clave
- **Multiplataforma real**: usar `faster-whisper` (CTranslate2) en vez de `openai-whisper` puro, porque tiene mejor soporte y rendimiento en CPU en ambas arquitecturas (ARM y x86), evitando dependencias pesadas de CUDA que no aplican en Mac.
- **Sin GPU requerida**: todo corre en CPU dentro del contenedor (en Mac Apple Silicon el acceso a GPU/Neural Engine desde Docker no está disponible, así que CPU es el camino más simple y portable).
- **Modelos Whisper**: se descargan la primera vez que se ejecuta; guardarlos en un volumen Docker para no re-descargar en cada `docker compose up`.
- **Todo local**: no se llama a la API de OpenAI ni ningún servicio externo, todo el procesamiento (Whisper + censura) ocurre dentro de los contenedores.

---

## Próximo paso
Confirmar con el usuario:
1. ¿Frontend simple (HTML/JS vanilla) o con React/Vite?
2. ¿Tamaño de modelo Whisper por defecto (`tiny`, `base`, `small`, `medium`)? Modelos más grandes = más precisión pero más lentos en CPU.
3. ¿Censura por defecto: silencio o beep?
