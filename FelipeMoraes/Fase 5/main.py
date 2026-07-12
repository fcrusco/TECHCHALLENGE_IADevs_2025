"""Aplicação web Flask do Sistema de Modelagem de Ameaças STRIDE."""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path

import requests as req
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, send_file, send_from_directory, url_for

load_dotenv()

_STRIDE_GGUF_DOWNLOAD_URL = (
    "https://1drv.ms/u/c/00d0a6a099986c76/"
    "IQCQa17fkDcwRqPt04rnq-QzAcwb1jkWhpkIjwjtfkCwfxs?e=YO1bcI"
)
_STRIDE_GGUF_FILENAME = "stride-qwen2.5-3b-q8_0.gguf"

# ── Configuração de logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)
# Silencia loggers de terceiros muito verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── App Flask ───────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "stride-hackathon-fase5")

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# Armazenamento em memória dos resultados — indexado pelo UUID da execução (uso local/single-process)
_store: dict[str, dict] = {}

# Log de progresso de cada execução em andamento — indexado pelo mesmo run_id,
# consultado pelo frontend via polling em /progress/<run_id> enquanto a análise roda.
_progress: dict[str, list[str]] = {}


def _log_step(run_id: str, message: str) -> None:
    """Registra uma etapa no terminal e no log de progresso consultado pelo frontend."""
    logger.info(message)
    _progress.setdefault(run_id, []).append(message)


@app.get("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(IMAGES_DIR, filename)

# Mesmo modelo STRIDE fine-tuned usado pelo backend/ (ver training/) — servido via Ollama
from agents.nodes import STRIDE_MODEL_NAME, STRIDE_MODEL_URL  # noqa: E402


def _ping(url: str) -> bool:
    try:
        r = req.get(url, timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def _ollama_has_model(base_url: str, model_name: str) -> bool:
    try:
        r = req.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        if r.status_code >= 500:
            return False
        tags = [m.get("name", "").split(":")[0] for m in r.json().get("models", [])]
        return model_name in tags
    except Exception:
        return False


@app.route("/")
def index():
    return render_template(
        "index.html",
        lm_url=os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1"),
        lm_model=os.environ.get("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
        lm_max_tokens=os.environ.get("LM_STUDIO_MAX_TOKENS", "4096"),
    )


@app.route("/providers")
def providers():
    from pathlib import Path as _Path

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    lmstudio_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    lmstudio_base = lmstudio_url[:-3] if lmstudio_url.endswith("/v1") else lmstudio_url

    gguf_path = _Path(BASE_DIR) / "training" / "output" / _STRIDE_GGUF_FILENAME

    return jsonify([
        {
            "id": "openai",
            "name": "OpenAI",
            "available": bool(openai_key and not openai_key.startswith("sk-...")),
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        },
        {
            "id": "ollama",
            "name": "Ollama (local)",
            "available": _ping(os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")),
            "model": os.environ.get("OLLAMA_MODEL", "gemma3:4b"),
        },
        {
            "id": "lmstudio",
            "name": "LM Studio (local)",
            "available": _ping(lmstudio_base.rstrip("/")),
            "model": os.environ.get("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
        },
        {
            "id": "stride-trained",
            "name": "Modelo Treinado Stride - Ollama (Local)",
            "available": _ollama_has_model(STRIDE_MODEL_URL, STRIDE_MODEL_NAME),
            "model": os.environ.get("OLLAMA_MODEL", "gemma3:4b"),
            "gguf_on_disk": gguf_path.exists(),
            "gguf_dest_folder": "training/output/",
            "gguf_filename": _STRIDE_GGUF_FILENAME,
            "gguf_download_url": _STRIDE_GGUF_DOWNLOAD_URL,
        },
    ])


@app.route("/stride-model")
def stride_model_status():
    return jsonify({
        "id": STRIDE_MODEL_NAME,
        "name": "Modelo treinado STRIDE",
        "available": _ollama_has_model(STRIDE_MODEL_URL, STRIDE_MODEL_NAME),
    })


@app.route("/progress/<run_id>")
def progress(run_id: str):
    return jsonify({"steps": _progress.get(run_id, []), "done": run_id in _store})


@app.route("/analyze", methods=["POST"])
def analyze():
    # O run_id é gerado no navegador (crypto.randomUUID()) antes do envio do
    # formulário, para que o frontend já possa consultar /progress/<run_id>
    # enquanto esta requisição (síncrona) ainda está em andamento.
    run_id = request.form.get("run_id") or str(uuid.uuid4())
    _progress[run_id] = []

    provider = request.form.get("provider") or os.environ.get("LLM_PROVIDER", "lmstudio")
    local_url = request.form.get("local_url") or None
    local_model = request.form.get("local_model") or None

    # "stride-trained" é uma opção do dropdown Provedor, não um provider de
    # verdade: o modelo treinado STRIDE não tem visão, então a etapa de visão
    # continua rodando via Ollama (com o modelo escolhido no campo "Modelo"),
    # e só a etapa de análise STRIDE é roteada para o modelo treinado fixo.
    use_stride_model = provider == "stride-trained" or request.form.get("use_stride_model", "").lower() in ("true", "1", "on")
    if provider == "stride-trained":
        provider = "ollama"

    # LM Studio usa Max Tokens configurável (modelos locais de contexto menor)
    lm_url = request.form.get("lm_url", "http://localhost:1234/v1")
    lm_model = request.form.get("lm_model", "google/gemma-4-e4b")
    lm_max_tokens = request.form.get("lm_max_tokens", "1024")
    os.environ["LM_STUDIO_URL"] = lm_url
    os.environ["LM_STUDIO_MODEL"] = lm_model
    os.environ["LM_STUDIO_MAX_TOKENS"] = lm_max_tokens

    if provider == "openai" and (
        not os.environ.get("OPENAI_API_KEY") or os.environ["OPENAI_API_KEY"].startswith("sk-...")
    ):
        return render_template(
            "index.html",
            error="Chave da API da OpenAI não configurada",
            traceback="Configure OPENAI_API_KEY no arquivo .env para usar o provider OpenAI.",
            lm_url=lm_url, lm_model=lm_model, lm_max_tokens=lm_max_tokens,
        ), 500

    file = request.files.get("diagram")
    if not file or not file.filename:
        logger.warning("Requisição recebida sem arquivo — redirecionando")
        return redirect(url_for("index"))

    file_size_kb = len(file.read()) / 1024
    file.seek(0)
    file_bytes = file.read()
    image_b64 = base64.standard_b64encode(file_bytes).decode("utf-8")
    ext = Path(file.filename).suffix.lower() or ".png"

    logger.info("=" * 60)
    _log_step(run_id, "Nova análise iniciada")
    logger.info("  Arquivo         : %s (%.1f KB)", file.filename, file_size_kb)
    logger.info("  Provider        : %s", provider)
    logger.info("  URL/Modelo local: %s / %s", local_url, local_model)
    logger.info("  Modelo STRIDE   : %s", STRIDE_MODEL_NAME if use_stride_model else "(não usado)")
    logger.info("=" * 60)

    run_start = time.time()
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        from agents.nodes import (
            analyze_image_node,
            analyze_stride_node,
            extract_components_node,
            generate_report_node,
        )
        from utils.report import enrich_report

        state: dict = {
            "image_path": tmp_path,
            "image_base64": image_b64,
            "provider": provider,
            "override_url": local_url,
            "override_model": local_model,
            "use_stride_model": use_stride_model,
            "raw_description": None,
            "components": None,
            "trust_boundaries": None,
            "data_flows": None,
            "threats": None,
            "report_markdown": None,
            "report_json": None,
            "current_step": "start",
            "error": None,
            "messages": [],
            "model_used": None,
            "provider_used": None,
            "stride_model_used": None,
        }

        # ── Etapa 1 ───────────────────────────────────────────────────────────
        t = time.time()
        _log_step(run_id, "[1/4] Analisando o diagrama com visão computacional...")
        state.update(analyze_image_node(state))
        desc_len = len(state.get("raw_description") or "")
        _log_step(run_id, f"[1/4] Concluído em {time.time() - t:.1f}s — descrição gerada com {desc_len} caracteres")

        # ── Etapa 2 ───────────────────────────────────────────────────────────
        t = time.time()
        _log_step(run_id, "[2/4] Extraindo e classificando componentes da arquitetura...")
        state.update(extract_components_node(state))
        n_comp = len(state.get("components") or [])
        n_tb = len(state.get("trust_boundaries") or [])
        n_df = len(state.get("data_flows") or [])
        _log_step(
            run_id,
            f"[2/4] Concluído em {time.time() - t:.1f}s — {n_comp} componentes, "
            f"{n_tb} limites de confiança, {n_df} fluxos de dados",
        )
        if state.get("components"):
            for c in state["components"]:
                _log_step(run_id, f"      componente identificado: {c.get('name', '?')} (tipo: {c.get('type', '?')})")

        # ── Etapa 3 ───────────────────────────────────────────────────────────
        t = time.time()
        if use_stride_model:
            _log_step(run_id, f"[3/4] Aplicando metodologia STRIDE com o modelo treinado ({STRIDE_MODEL_NAME})...")
        else:
            _log_step(run_id, "[3/4] Aplicando metodologia STRIDE por componente...")
        state.update(analyze_stride_node(state))
        threats = state.get("threats") or {}
        total_threats = sum(len(v) for v in threats.values())
        _log_step(
            run_id,
            f"[3/4] Concluído em {time.time() - t:.1f}s — {total_threats} ameaças em {len(threats)} componentes",
        )

        # ── Etapa 4 ───────────────────────────────────────────────────────────
        t = time.time()
        _log_step(run_id, "[4/4] Gerando o relatório executivo...")
        state.update(generate_report_node(state))
        report_len = len(state.get("report_markdown") or "")
        _log_step(run_id, f"[4/4] Concluído em {time.time() - t:.1f}s — relatório com {report_len} caracteres")

        # ── Enriquecimento ────────────────────────────────────────────────────
        _log_step(run_id, "Adicionando tabelas, matriz de risco e plano de remediação ao relatório...")
        full_report = enrich_report(
            state.get("report_markdown", ""),
            state.get("components", []),
            state.get("threats", {}),
            state.get("report_json", {}),
        )
        state["report_markdown"] = full_report
        state.pop("messages", None)

        _store[run_id] = state

        elapsed = time.time() - run_start
        _log_step(run_id, f"Análise concluída em {elapsed:.1f}s")
        logger.info("=" * 60)
        logger.info("ANÁLISE CONCLUÍDA em %.1fs — run_id: %s", elapsed, run_id)
        logger.info("  Componentes   : %d", n_comp)
        logger.info("  Ameaças       : %d", total_threats)
        logger.info("  Relatório     : %d chars", len(full_report))
        logger.info("  Modelo visão  : %s (%s)", state.get("model_used"), state.get("provider_used"))
        logger.info("  Modelo STRIDE : %s", state.get("stride_model_used") or "(mesmo provider acima)")
        logger.info("=" * 60)

        return redirect(url_for("results", run_id=run_id))

    except Exception as exc:
        import traceback as tb

        _log_step(run_id, f"Erro na análise: {exc}")
        logger.error("ERRO na análise após %.1fs: %s", time.time() - run_start, exc, exc_info=True)
        return render_template(
            "index.html",
            error=str(exc),
            traceback=tb.format_exc(),
            lm_url=lm_url,
            lm_model=lm_model,
            lm_max_tokens=lm_max_tokens,
        ), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.route("/results/<run_id>")
def results(run_id: str):
    state = _store.get(run_id)
    if not state:
        logger.warning("run_id não encontrado: %s", run_id)
        return redirect(url_for("index"))

    logger.info("Servindo resultados — run_id: %s", run_id)

    from utils.report import get_severity_stats, get_stride_stats

    components = state.get("components") or []
    threats = state.get("threats") or {}

    return render_template(
        "results.html",
        run_id=run_id,
        state=state,
        components=components,
        threats=threats,
        trust_boundaries=state.get("trust_boundaries") or [],
        sev_stats=get_severity_stats(threats),
        stride_stats=get_stride_stats(threats),
        report_markdown=state.get("report_markdown", ""),
    )


@app.route("/download/<run_id>/<fmt>")
def download(run_id: str, fmt: str):
    state = _store.get(run_id)
    if not state:
        logger.warning("Download solicitado para run_id inexistente: %s", run_id)
        return redirect(url_for("index"))

    logger.info("Download solicitado — run_id: %s | formato: %s", run_id, fmt)

    if fmt == "md":
        data = (state.get("report_markdown") or "").encode()
        return send_file(io.BytesIO(data), mimetype="text/markdown",
                         as_attachment=True, download_name="stride_threat_model.md")
    if fmt == "json":
        data = json.dumps(state.get("report_json") or {}, indent=2, ensure_ascii=False).encode()
        return send_file(io.BytesIO(data), mimetype="application/json",
                         as_attachment=True, download_name="stride_threat_model.json")
    if fmt == "csv":
        from utils.report import threats_to_csv
        data = threats_to_csv(state.get("threats") or {}).encode()
        return send_file(io.BytesIO(data), mimetype="text/csv",
                         as_attachment=True, download_name="stride_threats.csv")

    return redirect(url_for("results", run_id=run_id))


def _ensure_stride_model_on_startup() -> None:
    """Verifica se o modelo STRIDE está disponível e registra no Ollama se o GGUF já estiver em disco."""
    try:
        from training.setup_model import ensure_stride_model
        ensure_stride_model(silent=False)
    except Exception as exc:
        logger.warning("Não foi possível verificar o modelo STRIDE: %s", exc)


if __name__ == "__main__":
    _ensure_stride_model_on_startup()
    logger.info("Provider  : LM Studio (local)")
    logger.info("Frontend  : http://0.0.0.0:5000")
    # threaded=True: permite que o navegador consulte /progress/<run_id> enquanto
    # a requisição síncrona POST /analyze ainda está em andamento.
    app.run(debug=True, port=5000, host="0.0.0.0", threaded=True)
