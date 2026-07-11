"""Ponto de entrada — execute a partir da raiz do projeto: python run.py"""
from main import app, _ensure_stride_model_on_startup

if __name__ == "__main__":
    _ensure_stride_model_on_startup()
    app.run(debug=True, port=5000, host="0.0.0.0")
