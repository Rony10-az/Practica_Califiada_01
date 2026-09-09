import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
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
