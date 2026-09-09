import os
import uuid

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
import yt_dlp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

SUPPORTED_PLATFORMS = {
    "YouTube": ("youtube.com", "youtu.be"),
    "Instagram": ("instagram.com",),
    "TikTok": ("tiktok.com",),
    "Facebook": ("facebook.com", "fb.watch"),
    "LinkedIn": ("linkedin.com",),
}


def detect_platform(url: str) -> str | None:
    for platform, domains in SUPPORTED_PLATFORMS.items():
        if any(domain in url for domain in domains):
            return platform
    return None


def attempt_download(url: str, ydl_opts: dict) -> str:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if not path.endswith(".mp4") and os.path.exists(os.path.splitext(path)[0] + ".mp4"):
            path = os.path.splitext(path)[0] + ".mp4"
        return path


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", platforms=SUPPORTED_PLATFORMS.keys())


@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()

    if not url:
        flash("Ingresa una URL de video.")
        return redirect(url_for("index"))

    platform = detect_platform(url)
    if not platform:
        flash("Plataforma no soportada. Usa un enlace de YouTube, Instagram, TikTok, Facebook o LinkedIn.")
        return redirect(url_for("index"))

    file_id = uuid.uuid4().hex
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    cookies_file = os.environ.get("COOKIES_FILE")
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
        print(f"[cookies] usando cookies desde {cookies_file}", flush=True)
    elif cookies_file:
        print(f"[cookies] COOKIES_FILE={cookies_file} pero el archivo no existe dentro del contenedor", flush=True)

    attempts = [ydl_opts]
    if platform == "YouTube" and not ydl_opts.get("cookiefile"):
        # Sin cookies, YouTube a veces exige "sign in to confirm you're not a bot"
        # solo para el cliente web. Los clientes android/ios no siempre lo piden.
        fallback_opts = dict(ydl_opts)
        fallback_opts["extractor_args"] = {"youtube": {"player_client": ["android", "ios"]}}
        attempts.append(fallback_opts)

    downloaded_path = None
    last_error = None
    for opts in attempts:
        try:
            downloaded_path = attempt_download(url, opts)
            break
        except Exception as exc:  # yt_dlp raises varied exception types depending on the extractor
            last_error = exc

    if downloaded_path is None:
        flash(f"No se pudo descargar el video ({platform}): {last_error}")
        return redirect(url_for("index"))

    download_name = f"{platform.lower()}_{file_id}.mp4"
    return send_file(downloaded_path, as_attachment=True, download_name=download_name)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
