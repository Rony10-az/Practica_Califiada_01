# Caso 2 - Registro de Miembros de Mesa (ONPE)

Aplicación web simple en Python (Flask + `openpyxl`) para registrar en un Excel los datos de
miembros de mesa: DNI, ubicación (región/provincia/distrito) y dirección del local de votación.

## Paso 1: verificar si eres miembro de mesa (manual, fuera de la app)

Este paso lo haces tú directamente en el portal oficial, porque implica ingresar tu DNI real:

1. Ingresa a [https://consultaelectoral.onpe.gob.pe/inicio](https://consultaelectoral.onpe.gob.pe/inicio).
2. Busca la opción de consulta de miembro de mesa e ingresa tu DNI.
3. Si el resultado indica que **sí eres miembro de mesa**, anota:
   - Tu DNI.
   - Ubicación (Región / Provincia / Distrito).
   - Dirección del local de votación.
4. Usa esos datos para registrarte en la aplicación de este caso (ver más abajo), que los guarda
   en un archivo Excel (`data/miembros_mesa.xlsx`).

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
- No compartas el Excel generado ni lo subas a un repositorio público: contiene datos personales (DNIs).
