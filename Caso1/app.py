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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info)
            if not downloaded_path.endswith(".mp4") and os.path.exists(
                os.path.splitext(downloaded_path)[0] + ".mp4"
            ):
                downloaded_path = os.path.splitext(downloaded_path)[0] + ".mp4"
    except Exception as exc:  # yt_dlp raises varied exception types depending on the extractor
        flash(f"No se pudo descargar el video ({platform}): {exc}")
        return redirect(url_for("index"))

    download_name = f"{platform.lower()}_{file_id}.mp4"
    return send_file(downloaded_path, as_attachment=True, download_name=download_name)


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
