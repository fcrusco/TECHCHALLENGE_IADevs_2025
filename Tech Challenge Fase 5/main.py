"""Flask web application for the STRIDE Threat Modeling System."""

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

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, send_file, url_for

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)
# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "stride-hackathon-fase5")

# In-memory result store — keyed by run UUID (single-process / local use)
_store: dict[str, dict] = {}


@app.route("/")
def index():
    return render_template(
        "index.html",
        lm_url=os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1"),
        lm_model=os.environ.get("LM_STUDIO_MODEL", "google/gemma-4-e4b"),
        lm_max_tokens=os.environ.get("LM_STUDIO_MAX_TOKENS", "1024"),
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    lm_url = request.form.get("lm_url", "http://localhost:1234/v1")
    lm_model = request.form.get("lm_model", "google/gemma-4-e4b")
    lm_max_tokens = request.form.get("lm_max_tokens", "1024")
    os.environ["LM_STUDIO_URL"] = lm_url
    os.environ["LM_STUDIO_MODEL"] = lm_model
    os.environ["LM_STUDIO_MAX_TOKENS"] = lm_max_tokens

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
    logger.info("NOVA ANÁLISE INICIADA")
    logger.info("  Arquivo : %s (%.1f KB)", file.filename, file_size_kb)
    logger.info("  Modelo  : %s", lm_model)
    logger.info("  URL API : %s", lm_url)
    logger.info("  MaxTok  : %s", lm_max_tokens)
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
        }

        # ── Step 1 ────────────────────────────────────────────────────────────
        t = time.time()
        logger.info("[1/4] analyze_image_node — iniciando")
        state.update(analyze_image_node(state))
        desc_len = len(state.get("raw_description") or "")
        logger.info("[1/4] analyze_image_node — concluído em %.1fs | descrição: %d chars", time.time() - t, desc_len)

        # ── Step 2 ────────────────────────────────────────────────────────────
        t = time.time()
        logger.info("[2/4] extract_components_node — iniciando")
        state.update(extract_components_node(state))
        n_comp = len(state.get("components") or [])
        n_tb = len(state.get("trust_boundaries") or [])
        n_df = len(state.get("data_flows") or [])
        logger.info(
            "[2/4] extract_components_node — concluído em %.1fs | %d componentes | %d trust boundaries | %d data flows",
            time.time() - t, n_comp, n_tb, n_df,
        )
        if state.get("components"):
            for c in state["components"]:
                logger.info("      componente: %-30s tipo=%-25s boundary=%s",
                            c.get("name", "?"), c.get("type", "?"), c.get("trust_boundary", "?"))

        # ── Step 3 ────────────────────────────────────────────────────────────
        t = time.time()
        logger.info("[3/4] analyze_stride_node — iniciando")
        state.update(analyze_stride_node(state))
        threats = state.get("threats") or {}
        total_threats = sum(len(v) for v in threats.values())
        logger.info("[3/4] analyze_stride_node — concluído em %.1fs | %d ameaças em %d componentes",
                    time.time() - t, total_threats, len(threats))

        # ── Step 4 ────────────────────────────────────────────────────────────
        t = time.time()
        logger.info("[4/4] generate_report_node — iniciando")
        state.update(generate_report_node(state))
        report_len = len(state.get("report_markdown") or "")
        logger.info("[4/4] generate_report_node — concluído em %.1fs | relatório: %d chars", time.time() - t, report_len)

        # ── Enrich ────────────────────────────────────────────────────────────
        logger.info("Enriquecendo relatório com tabelas e matriz de risco...")
        full_report = enrich_report(
            state.get("report_markdown", ""),
            state.get("components", []),
            state.get("threats", {}),
            state.get("report_json", {}),
        )
        state["report_markdown"] = full_report
        state.pop("messages", None)

        run_id = str(uuid.uuid4())
        _store[run_id] = state

        elapsed = time.time() - run_start
        logger.info("=" * 60)
        logger.info("ANÁLISE CONCLUÍDA em %.1fs — run_id: %s", elapsed, run_id)
        logger.info("  Componentes : %d", n_comp)
        logger.info("  Ameaças     : %d", total_threats)
        logger.info("  Relatório   : %d chars", len(full_report))
        logger.info("=" * 60)

        return redirect(url_for("results", run_id=run_id))

    except Exception as exc:
        import traceback as tb

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
