# Caso 2 - Registro de Miembros de Mesa (ONPE)

Aplicación web simple en Python (Flask + `openpyxl`) para registrar en un Excel los datos de
miembros de mesa: DNI, nombre completo, si es miembro de mesa (Sí/No), ubicación
(región/provincia/distrito) y dirección del local de votación.

## Paso 1: verificar si eres miembro de mesa (manual, fuera de la app)

Este paso lo haces tú directamente en el portal oficial, porque implica ingresar tu DNI real y
resolver un captcha:

1. Ingresa a [https://consultaelectoral.onpe.gob.pe/inicio](https://consultaelectoral.onpe.gob.pe/inicio).
2. Ingresa tu DNI y resuelve el captcha para ver el resultado (DNI, nombre, si eres miembro de
   mesa, ubicación y local de votación).

### ¿Por qué no se automatiza esta consulta?

El endpoint que usa ese portal (`/v1/api/...`) está protegido con **AWS WAF CAPTCHA**: la respuesta
de configuración inicial del sitio expone `CAPTCHA.SCRIPT_URL` y `CAPTCHA.API_KEY`, que cargan el
SDK de `captcha-sdk.awswaf.com`. Eso significa que cada consulta necesita un token que solo se
genera resolviendo ese challenge en un navegador real. Automatizar esa consulta implicaría evadir
una protección anti-bot, así que esta app no lo hace: la consulta la resuelves tú, como humano.

### Autocompletar el formulario con el resultado (sin tocar el captcha)

Una vez que ya resolviste el captcha y tienes el resultado en pantalla, no hace falta tipear cada
campo a mano. Hay dos formas, de la más rápida a la más técnica:

**Forma rápida** (recomendada): en la página de resultado de ONPE, presiona `Ctrl+A` (seleccionar
todo) y `Ctrl+C` (copiar). En esta app, abre "¿Ya hiciste la consulta en ONPE?", pega ese texto
(`Ctrl+V`) y presiona **Extraer datos**.

**Forma alternativa** (si prefieres el dato crudo): DevTools (F12) → pestaña **Network** → la
petición de la consulta → **Response** → copiar el JSON, y pegarlo igual en el mismo cuadro.

En ambos casos la app detecta el formato automáticamente (texto visible de la página, JSON estricto,
o el volcado de un objeto de consola) y autocompleta DNI, nombre, Sí/No, región/provincia/distrito
y dirección del local. Revisa los campos y presiona **Registrar**.

> El Excel no se sube al repositorio (ver `.dockerignore`) porque contiene DNIs, que son datos personales.

## Estructura

```
Caso2/
├── app.py                   # Aplicacion Flask
├── requirements.txt         # Dependencias Python
├── templates/index.html     # Formulario + tabla de registros
├── data/                    # Excel generado en tiempo de ejecucion (miembros_mesa.xlsx)
├── Dockerfile                # Version basica (una sola etapa)
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
docker build -t registro-mesa:basico -f Dockerfile .

# Version optimizada
docker build -t registro-mesa:optimizado -f Dockerfile.optimizado .

# Version multistage
docker build -t registro-mesa:multistage -f Dockerfile.multistage .
```

Ver las imágenes creadas y su tamaño:

```bash
docker images registro-mesa
```

## Ejecutar un contenedor

Para que el Excel persista fuera del contenedor, monta la carpeta `data/` como volumen:

```bash
docker run --rm -p 5000:5000 -v "$(pwd)/data:/app/data" registro-mesa:multistage
```

En PowerShell:

```powershell
docker run --rm -p 5000:5000 -v "${PWD}/data:/app/data" registro-mesa:multistage
```

Luego abrir `http://localhost:5000` en el navegador, completar el formulario y descargar el Excel
desde el botón "Descargar Excel".

## Diferencias entre los 3 Dockerfiles

| Aspecto | Dockerfile (basico) | Dockerfile.optimizado | Dockerfile.multistage |
|---|---|---|---|
| Imagen base | `python:3.12` (completa) | `python:3.12-slim` | `python:3.12-slim` (build y runtime) |
| Capas | `COPY . .` antes de instalar dependencias | `requirements.txt` copiado antes que el código (aprovecha cache) | Igual que optimizado, además separa build/runtime |
| Cache de pip | Sin limpiar | Limpia (`--no-cache-dir`) | Limpia, y el `pip` de la etapa builder no viaja a la imagen final |
| Usuario | root | usuario no root (`appuser`) | usuario no root (`appuser`) |
| Tamaño final | Mayor | Menor | El más pequeño |

## Notas

- El archivo `data/miembros_mesa.xlsx` se crea automáticamente con los encabezados la primera vez
  que arranca la aplicación.
- El DNI se valida como 8 dígitos numéricos antes de registrarse.
- En la tabla de registros, "Miembro de mesa" se muestra como una etiqueta verde (Sí) o roja (No).
- No compartas el Excel generado ni lo subas a un repositorio público: contiene datos personales (DNIs).
- Si ya tienes un contenedor corriendo con una versión anterior de la imagen, los cambios de código
  no aparecen ahí solos: hay que reconstruir la imagen (`docker build ...`) y volver a correr el
  contenedor para verlos reflejados en `http://localhost:5000`.
