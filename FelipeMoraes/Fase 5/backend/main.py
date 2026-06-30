from flask import Flask
from flask_cors import CORS

from config import settings
from routers.analysis import analysis_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(analysis_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(host=settings.backend_host, port=settings.backend_port, debug=True)
