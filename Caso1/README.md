# Caso 1 - Descargador de Videos (YouTube, Instagram, TikTok, Facebook, LinkedIn)

Aplicacion web simple en Python (Flask + `yt-dlp`) que recibe la URL de un video y lo descarga en MP4.

## Estructura

```
Caso1/
├── app.py                   # Aplicacion Flask
├── requirements.txt         # Dependencias Python
├── templates/index.html     # Formulario web
├── Dockerfile               # Version basica (una sola etapa)
├── Dockerfile.optimizado    # Una sola etapa, con buenas practicas
├── Dockerfile.multistage    # Dos etapas: build y runtime
└── .dockerignore
```

## Ejecutar en local (sin Docker)

```bash
pip install -r requirements.txt
python app.py
```

Abrir `http://localhost:5000`.

## Construir y etiquetar cada imagen

```bash
# Version basica
docker build -t descargador-videos:basico -f Dockerfile .

# Version optimizada
docker build -t descargador-videos:optimizado -f Dockerfile.optimizado .

# Version multistage
docker build -t descargador-videos:multistage -f Dockerfile.multistage .
```

Ver las imagenes creadas y su tamaño:

```bash
docker images descargador-videos
```

## Ejecutar un contenedor

Para una prueba rápida y descartable:

```bash
docker run --rm -p 5000:5000 descargador-videos:multistage
```

Para dejarlo corriendo de forma persistente (se reinicia solo si se cae o si reinicias Docker/el PC, pero no si tú lo detienes a mano):

```bash
docker run -d --name descargador-app -p 5000:5000 --restart unless-stopped descargador-videos:multistage
```

> `--restart` y `--rm` son incompatibles (uno reinicia el contenedor, el otro lo borra al salir), por eso no se usan juntos.

Luego abrir `http://localhost:5000` en el navegador.

Comandos útiles para administrarlo:

```bash
docker ps --filter "name=descargador-app"     # ver si esta corriendo
docker logs -f descargador-app                # ver logs en vivo
docker stop descargador-app                   # detenerlo (no se reinicia solo tras esto)
docker rm descargador-app                     # eliminarlo definitivamente
```

## Diferencias entre los 3 Dockerfiles

| Aspecto | Dockerfile (basico) | Dockerfile.optimizado | Dockerfile.multistage |
|---|---|---|---|
| Imagen base | `python:3.12` (completa) | `python:3.12-slim` | `python:3.12-slim` (build y runtime) |
| Capas | `COPY . .` + varios `RUN` sin combinar | `RUN` combinados, cache de apt/pip limpiada | Igual que optimizado, ademas separa build/runtime |
| Orden de capas | Copia todo antes de instalar dependencias (invalida cache seguido) | Copia `requirements.txt` antes del codigo (aprovecha cache) | Igual que optimizado |
| Herramientas de compilacion | No aplica | No incluidas | `gcc` solo existe en la etapa `builder`, no en la imagen final |
| Usuario | root | usuario no root (`appuser`) | usuario no root (`appuser`) |
| Tamaño final | Mayor (imagen completa + cache sin limpiar) | Menor | El mas pequeño (sin herramientas de build) |

## Notas

- `ffmpeg` es necesario para unir video y audio cuando `yt-dlp` los descarga por separado.
- Usa la aplicacion solo con videos propios o con autorizacion del titular de los derechos; respeta los terminos de servicio de cada plataforma.
- Algunas plataformas (Instagram, Facebook, LinkedIn) pueden bloquear la descarga de contenido privado o requerir sesion iniciada; funciona de forma mas confiable con contenido publico.
- `yt-dlp` cambia seguido para seguir el ritmo de YouTube: mantener la version actualizada (`requirements.txt` usa `yt-dlp>=2024.12.6`, sin fijarla a un build exacto).

### Limitacion conocida: "Sign in to confirm you're not a bot" (YouTube)

YouTube aplica verificacion anti-bot mas agresiva a solicitudes que vienen de IPs de datacenter (como las de Docker/servidores en la nube), independientemente de la version de `yt-dlp`. Cuando aparece este error, la unica solucion documentada por el propio proyecto es autenticarse con cookies de una sesion real:

1. Exporta tus cookies de YouTube desde el navegador (por ejemplo con la extension "Get cookies.txt") a un archivo `cookies.txt`.
2. Móntalo en el contenedor y apunta la variable `COOKIES_FILE` hacia esa ruta:

```bash
docker run --rm -p 5000:5000 \
  -v /ruta/local/cookies.txt:/app/cookies.txt \
  -e COOKIES_FILE=/app/cookies.txt \
  descargador-videos:multistage
```

Sin esto, la descarga de YouTube puede fallar en entornos de servidor aunque funcione perfecto en tu máquina local con conexión residencial. TikTok, Instagram y Facebook con contenido público suelen no tener esta restricción.
