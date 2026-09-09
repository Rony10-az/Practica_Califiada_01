import json
import os
import re
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook, load_workbook

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
EXCEL_PATH = os.path.join(DATA_DIR, "miembros_mesa.xlsx")

HEADERS = [
    "DNI",
    "Nombre completo",
    "Miembro de mesa",
    "Región",
    "Provincia",
    "Distrito",
    "Dirección del local de votación",
    "Registrado",
]


def get_workbook() -> Workbook:
    if os.path.exists(EXCEL_PATH):
        return load_workbook(EXCEL_PATH)
    wb = Workbook()
    ws = wb.active
    ws.title = "Miembros de Mesa"
    ws.append(HEADERS)
    wb.save(EXCEL_PATH)
    return wb


def read_entries() -> list:
    wb = get_workbook()
    ws = wb.active
    return [row for row in ws.iter_rows(min_row=2, values_only=True) if row and row[0]]


_KV_RE = re.compile(
    r'"?([A-Za-z_][A-Za-z0-9_]*)"?\s*:\s*("(?:[^"\\]|\\.)*"|null|true|false|-?\d+(?:\.\d+)?)'
)


def _parse_loose(texto: str) -> dict:
    """Extrae pares clave-valor aunque el texto no sea JSON estricto (p. ej. el volcado
    de un objeto copiado desde la consola de DevTools, con numeración tipo '1. clave: valor')."""
    data = {}
    for key, raw in _KV_RE.findall(texto):
        if raw == "null":
            value = None
        elif raw == "true":
            value = True
        elif raw == "false":
            value = False
        elif raw.startswith('"'):
            value = raw[1:-1]
        else:
            value = raw
        data[key] = value
    return data


def _parse_texto_visible(texto: str) -> dict:
    """Extrae los datos directamente del texto visible de la página de resultado de ONPE
    (lo que se obtiene con un simple Ctrl+A/Ctrl+C sobre el resultado, sin abrir DevTools)."""
    data = {}

    if re.search(r"NO\s+ERES\s+MIEMBRO\s+DE\s+MESA", texto, re.I):
        data["miembroMesa"] = False
    elif re.search(r"ERES\s+MIEMBRO\s+DE\s+MESA", texto, re.I):
        data["miembroMesa"] = True

    m = re.search(r"DNI\D{0,10}?(\d{8})", texto, re.S)
    if m:
        data["dni"] = m.group(1)

    m = re.search(
        r"Nombres?\s+y\s+Apellidos\s*[:\n]+(.*?)(?:\n\s*\n|Regi[oó]n|DNI|$)", texto, re.S | re.I
    )
    if m:
        data["nombres"] = " ".join(m.group(1).split())
        data["apellidos"] = ""

    m = re.search(r"Regi[oó]n\s*/\s*Provincia\s*/\s*Distrito\s*[:\n]+([^\n]+)", texto, re.I)
    if m:
        data["ubigeo"] = m.group(1).strip()

    m = re.search(
        r"Tu\s+local\s+de\s+votaci[oó]n\s*(.*?)(?:N[°ºo]\.?\s*de\s+Mesa|IMPORTANTE|$)",
        texto,
        re.S | re.I,
    )
    if m:
        lineas = [l.strip() for l in m.group(1).splitlines() if l.strip()]
        lineas = [l for l in lineas if l.lower() not in ("ver", "mapa", "ver mapa")]
        if lineas:
            data["localVotacion"] = lineas[0]
        resto = lineas[1:]
        direccion = next((l for l in resto if not l.lower().startswith("referencia")), None)
        referencia = next((l for l in resto if l.lower().startswith("referencia")), None)
        if direccion:
            data["direccion"] = direccion
        if referencia:
            data["referencia"] = re.sub(r"^Referencia:\s*", "", referencia, flags=re.I)

    return data


def extraer_datos_onpe(texto: str) -> dict:
    """Obtiene los campos de la consulta de ONPE (DNI, nombre, ubicación, local de votación)
    a partir de lo que el usuario copió del navegador luego de resolver el captcha él mismo:
    el JSON estricto de la respuesta, un volcado suelto tipo consola, o simplemente el texto
    visible de la página de resultado (Ctrl+A/Ctrl+C, sin necesidad de abrir DevTools)."""
    data = None
    try:
        payload = json.loads(texto)
        if isinstance(payload, dict):
            data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    except json.JSONDecodeError:
        data = None

    if not isinstance(data, dict) or not data.get("dni"):
        data = _parse_loose(texto)

    if not data.get("dni"):
        data = _parse_texto_visible(texto)

    if not data or not data.get("dni"):
        raise ValueError("No se encontraron los campos esperados (dni, nombres, ubigeo...).")

    nombre = " ".join(f"{data.get('nombres') or ''} {data.get('apellidos') or ''}".split())

    ubigeo = data.get("ubigeo") or ""
    partes = [p.strip() for p in ubigeo.split("/")]
    partes += ["", "", ""]
    region, provincia, distrito = partes[0], partes[1], partes[2]

    direccion_partes = [p for p in (data.get("localVotacion"), data.get("direccion")) if p]
    if data.get("referencia"):
        direccion_partes.append(f"Ref: {data['referencia']}")

    return {
        "dni": data.get("dni") or "",
        "nombre": nombre,
        "miembro_mesa": "si" if data.get("miembroMesa") else "no",
        "region": region,
        "provincia": provincia,
        "distrito": distrito,
        "direccion": ", ".join(direccion_partes),
    }


@app.route("/extraer", methods=["POST"])
def extraer():
    texto = request.form.get("texto", "").strip()
    if not texto:
        return jsonify(success=False, error="Pega el JSON de la respuesta de ONPE."), 400
    try:
        campos = extraer_datos_onpe(texto)
    except (ValueError, TypeError, json.JSONDecodeError):
        return jsonify(
            success=False,
            error="No se pudo leer eso como JSON de ONPE. Copia la respuesta completa desde "
            "DevTools (pestaña Network → click en la consulta → Response).",
        ), 400
    return jsonify(success=True, campos=campos)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", entries=read_entries())


@app.route("/registrar", methods=["POST"])
def registrar():
    dni = request.form.get("dni", "").strip()
    nombre = request.form.get("nombre", "").strip()
    miembro_mesa = request.form.get("miembro_mesa", "").strip()
    region = request.form.get("region", "").strip()
    provincia = request.form.get("provincia", "").strip()
    distrito = request.form.get("distrito", "").strip()
    direccion = request.form.get("direccion", "").strip()

    if not (dni and nombre and miembro_mesa and region and provincia and distrito and direccion):
        flash("Completa todos los campos.")
        return redirect(url_for("index"))

    if not (dni.isdigit() and len(dni) == 8):
        flash("El DNI debe tener 8 dígitos numéricos.")
        return redirect(url_for("index"))

    if miembro_mesa not in ("si", "no"):
        flash("Indica si es miembro de mesa.")
        return redirect(url_for("index"))

    miembro_mesa_label = "Sí" if miembro_mesa == "si" else "No"

    wb = get_workbook()
    ws = wb.active
    ws.append([
        dni,
        nombre,
        miembro_mesa_label,
        region,
        provincia,
        distrito,
        direccion,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ])
    wb.save(EXCEL_PATH)

    flash(f"{nombre} (DNI {dni}) registrado correctamente.")
    return redirect(url_for("index"))


@app.route("/descargar")
def descargar():
    if not os.path.exists(EXCEL_PATH):
        flash("Aún no hay datos registrados.")
        return redirect(url_for("index"))
    return send_file(EXCEL_PATH, as_attachment=True, download_name="miembros_mesa.xlsx")


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
