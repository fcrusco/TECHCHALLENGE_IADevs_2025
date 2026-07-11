import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
# Silencia loggers de terceiros muito verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import settings
from routers.analysis import analysis_bp

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
IMAGES_DIR   = os.path.join(BASE_DIR, "images")

app = Flask(__name__)
CORS(app)
app.register_blueprint(analysis_bp, url_prefix="/api")


@app.get("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.get("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


@app.get("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(IMAGES_DIR, filename)


if __name__ == "__main__":
    log = logging.getLogger("main")
    log.info("Provider  : %s", settings.llm_provider)
    log.info("Frontend  : http://%s:%s", settings.backend_host, settings.backend_port)
    app.run(host=settings.backend_host, port=settings.backend_port, debug=True)
