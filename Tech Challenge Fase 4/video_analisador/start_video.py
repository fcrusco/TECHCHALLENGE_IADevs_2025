import importlib.util
import os
import shutil
import subprocess
import sys

_VIDEO_DIR    = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_VIDEO_DIR)
_SRC_DIR      = os.path.join(_PROJECT_ROOT, "src")

if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _VIDEO_DIR not in sys.path:
    sys.path.insert(0, _VIDEO_DIR)

import gradio as gr
from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# ── Detectores ────────────────────────────────────────────────────────────────

_DETECTORS = {
    "instrumentos":   ("src/detectors/instrumentos.py",   "InstrumentosDetector",  "instrumentos"),
    "areas-criticas": ("src/detectors/areas_criticas.py", "AreasCriticasDetector", "areas_criticas"),
    "sangramento":    ("src/detectors/sangramento.py",    "SangramentoDetector",   "sangramento"),
}

MODEL_CHOICES = {
    "Instrumentos Cirúrgicos":                "instrumentos",
    "Áreas Críticas (Útero / Tuba / Ovário)": "areas-criticas",
    "Sangramento":                            "sangramento",
}

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── 1. Sobrescreve variáveis CSS do Gradio 6 para forçar tema claro ──── */
html, html.dark, :root, .dark {
    color-scheme: light !important;

    --body-background-fill:           #fdf8f5 !important;
    --background-fill-primary:        #ffffff !important;
    --background-fill-secondary:      #f5f0ec !important;
    --panel-background-fill:          #fdf8f5 !important;
    --block-background-fill:          #ffffff !important;
    --block-label-background-fill:    #ffffff !important;
    --stat-background-fill:           #ffffff !important;
    --table-even-background-fill:     #f9f5f7 !important;
    --table-odd-background-fill:      #ffffff !important;
    --input-background-fill:          #ffffff !important;
    --input-background-fill-focus:    #ffffff !important;
    --checkbox-background-color:      #ffffff !important;
    --code-background-fill:           #f5f0ec !important;

    --body-text-color:                #1e1a1d !important;
    --body-text-color-subdued:        #5a5059 !important;
    --block-title-text-color:         #1e1a1d !important;
    --block-label-text-color:         #5a5059 !important;
    --section-header-text-color:      #1e1a1d !important;
    --input-text-color:               #1e1a1d !important;
    --input-placeholder-color:        #b0a5aa !important;
    --table-text-color:               #1e1a1d !important;
    --prose-text-color:               #1e1a1d !important;

    --border-color-primary:           #e8dde3 !important;
    --border-color-accent:            #c0446a !important;
    --block-border-color:             #e8dde3 !important;
    --input-border-color:             #e8dde3 !important;
    --input-border-color-focus:       #c0446a !important;
    --table-border-color:             #e8dde3 !important;

    --color-accent:                   #c0446a !important;
    --link-text-color:                #c0446a !important;
    --link-text-color-hover:          #8b2a47 !important;
    --link-text-color-visited:        #8b2a47 !important;

    --button-secondary-background-fill:  #f5f0ec !important;
    --button-secondary-text-color:       #1e1a1d !important;
    --button-secondary-border-color:     #e8dde3 !important;
}

@media (prefers-color-scheme: dark) {
    html, html.dark, :root, .dark {
        color-scheme: light !important;
        --body-background-fill:       #fdf8f5 !important;
        --background-fill-primary:    #ffffff !important;
        --block-background-fill:      #ffffff !important;
        --input-background-fill:      #ffffff !important;
        --body-text-color:            #1e1a1d !important;
        --block-title-text-color:     #1e1a1d !important;
        --block-label-text-color:     #5a5059 !important;
        --input-text-color:           #1e1a1d !important;
        --panel-background-fill:      #fdf8f5 !important;
    }
}

/* ── 2. Resets de elementos concretos (backup caso variável não pegue) ── */
* { box-sizing: border-box; }

html, body, .gradio-container {
    background: #fdf8f5 !important;
    color: #1e1a1d !important;
    font-family: 'DM Sans', sans-serif !important;
}

.gradio-container {
    max-width: 1000px !important;
    margin: 0 auto !important;
    padding: 2rem 1.5rem !important;
}

.block, [class*="block"], .gr-box, .gr-form, .gr-panel, .gr-padded {
    background: #ffffff !important;
    border: 1px solid #e8dde3 !important;
    border-radius: 14px !important;
    color: #1e1a1d !important;
}

textarea, input[type="text"], input[type="number"], input[type="search"],
.block textarea, [class*="scroll-hide"] {
    background: #ffffff !important;
    color: #1e1a1d !important;
    width: 100% !important;
    max-width: 100% !important;
    resize: none !important;
}

textarea::placeholder, input::placeholder { color: #b0a5aa !important; }

label, .label-wrap, .label-wrap span, .label-wrap p, [class*="label"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #5a5059 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

select, [class*="dropdown"], ul[class*="options"], [class*="option"] {
    background: #ffffff !important;
    color: #1e1a1d !important;
}

[class*="file"], [class*="upload"], [class*="file"] *, [class*="upload"] * {
    background: #ffffff !important;
    color: #1e1a1d !important;
}

/* ── 3. Header (cores intencionalmente brancas sobre gradiente) ───────── */
#header {
    text-align: center; margin-bottom: 2.5rem; padding: 2.5rem 2rem;
    background: linear-gradient(135deg, #8b2a47 0%, #c0446a 60%, #d4607e 100%) !important;
    border-radius: 20px; color: white !important;
    position: relative; overflow: hidden; border: none !important;
}
#header::before {
    content: ''; position: absolute; top: -40px; right: -40px;
    width: 180px; height: 180px; background: rgba(255,255,255,0.06); border-radius: 50%;
}
#header *, #header h1, #header p { color: white !important; }
#header h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 2rem !important; font-weight: 400 !important;
    margin: 0 0 0.4rem 0 !important;
}
#header p { font-size: 0.95rem !important; opacity: 0.85; margin: 0 !important; font-weight: 300; }

/* ── 4. Botão primário ────────────────────────────────────────────────── */
button.primary, button[class*="primary"] {
    background: linear-gradient(135deg, #8b2a47, #c0446a) !important;
    border: none !important; border-radius: 10px !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.75rem 2rem !important;
    transition: opacity 0.2s, transform 0.1s !important;
}
button.primary:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _reencode_h264(path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not os.path.exists(path):
        return
    tmp = path + ".tmp.mp4"
    r = subprocess.run(
        [ffmpeg, "-y", "-i", path,
         "-vcodec", "libx264", "-preset", "fast", "-crf", "23", "-an", tmp],
        capture_output=True,
    )
    if r.returncode == 0:
        os.replace(tmp, path)
    elif os.path.exists(tmp):
        os.remove(tmp)


def _load_module(name, rel_path):
    path = os.path.join(_PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ts(frame, fps):
    sec = int(frame) // max(int(fps), 1)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _build_summary_html(mode, result, folder):
    fps        = result["fps"]
    frames     = result["frame_count"]
    detections = result["detections_count"]
    anomalies  = result["anomalies"]

    # ── Badge de risco ────────────────────────────────────────────────────────
    if mode == "instrumentos":
        badge = '<span style="background:#6c757d;color:white;padding:4px 14px;border-radius:12px;font-weight:bold;font-size:.85em">RASTREAMENTO</span>'
        anom_str = "—"
    else:
        rate = len(anomalies) / max(frames, 1) * 100
        if rate > 20:
            rl, rc = "CRÍTICO", "#dc3545"
        elif rate > 10:
            rl, rc = "ALTO", "#fd7e14"
        elif rate > 5:
            rl, rc = "MÉDIO", "#b8860b"
        else:
            rl, rc = "BAIXO", "#28a745"
        badge    = f'<span style="background:{rc};color:white;padding:4px 14px;border-radius:12px;font-weight:bold;font-size:.85em">{rl}</span>'
        anom_str = f"{len(anomalies)} ({len(anomalies)/max(frames,1)*100:.1f}%)"

    html = [
        '<div style="font-family:Arial,sans-serif;font-size:0.93em">',
        # cabeçalho azul
        f'<div style="background:#1a3a5c;color:white;padding:12px 18px;border-radius:8px 8px 0 0;'
        f'display:flex;justify-content:space-between;align-items:center;margin-top:8px">',
        f'<span style="font-weight:bold;text-transform:uppercase;letter-spacing:.06em">'
        f'{folder.replace("_"," ").title()}</span>{badge}</div>',
        # cards resumo
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);background:#f0f4f8;'
        'border:1px solid #d0dce8;border-top:none;padding:14px 18px;gap:12px;margin-bottom:14px">',
        f'<div><div style="font-size:1.6em;font-weight:bold;color:#1a3a5c">{frames:,}</div>'
        f'<div style="font-size:.78em;color:#666;margin-top:2px">Frames Analisados</div></div>',
        f'<div><div style="font-size:1.6em;font-weight:bold;color:#1a3a5c">{detections:,}</div>'
        f'<div style="font-size:.78em;color:#666;margin-top:2px">Detecções Totais</div></div>',
        f'<div><div style="font-size:1.6em;font-weight:bold;color:#1a3a5c">{anom_str}</div>'
        f'<div style="font-size:.78em;color:#666;margin-top:2px">Anomalias Detectadas</div></div>',
        '</div>',
    ]

    TH = 'style="background:#1a3a5c;color:white;padding:7px 12px;text-align:center;white-space:nowrap"'
    TD = 'style="padding:7px 12px;border-bottom:1px solid #eee;text-align:center"'
    TDL = 'style="padding:7px 12px;border-bottom:1px solid #eee"'

    # ── Instrumentos ──────────────────────────────────────────────────────────
    if mode == "instrumentos":
        timeline = result.get("instrument_timeline", {})
        detected = [(n, i) for n, i in timeline.items() if i["count"] > 0]
        if detected:
            html.append('<p style="font-weight:600;color:#1a3a5c;margin:4px 0 6px">Instrumentos Cirúrgicos Detectados</p>')
            html.append(f'<table style="width:100%;border-collapse:collapse"><thead><tr>'
                        f'<th {TH} style="text-align:left">Instrumento</th>'
                        f'<th {TH}>Detecções</th><th {TH}>% Vídeo</th>'
                        f'<th {TH}>Primeiro</th><th {TH}>Último</th><th {TH}>Segmentos</th>'
                        f'</tr></thead><tbody>')
            for name, info in sorted(detected, key=lambda x: -x[1]["count"]):
                f = _ts(info["first_frame"], fps) if info.get("first_frame") else "—"
                l = _ts(info["last_frame"],  fps) if info.get("last_frame")  else "—"
                s = len(info.get("segments", []))
                html.append(f'<tr><td {TDL}><strong>{name}</strong></td>'
                            f'<td {TD}>{info["count"]}</td><td {TD}>{info["frames_pct"]:.1f}%</td>'
                            f'<td {TD}>{f}</td><td {TD}>{l}</td><td {TD}>{s}</td></tr>')
            html.append('</tbody></table>')
        else:
            html.append('<p style="color:#888;font-style:italic">Nenhum instrumento detectado no vídeo.</p>')

    # ── Areas críticas / Sangramento ──────────────────────────────────────────
    else:
        crit  = sum(1 for a in anomalies if isinstance(a, dict) and a.get("severity") == "CRÍTICO")
        alto  = sum(1 for a in anomalies if isinstance(a, dict) and a.get("severity") == "ALTO")
        medio = sum(1 for a in anomalies if isinstance(a, dict) and a.get("severity") == "MÉDIO")

        if anomalies:
            html.append('<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px">')
            for val, label, bg, fc in [
                (crit,  "Crítico", "#fff0f0", "#dc3545"),
                (alto,  "Alto",    "#fff6ee", "#fd7e14"),
                (medio, "Médio",   "#fffbee", "#b8860b"),
            ]:
                html.append(f'<div style="background:{bg};border-left:4px solid {fc};padding:10px 14px;border-radius:4px">'
                            f'<div style="font-size:1.5em;font-weight:bold;color:{fc}">{val}</div>'
                            f'<div style="font-size:.78em;color:#666;margin-top:2px">{label}</div></div>')
            html.append('</div>')

        cs = result.get("class_summary", {})
        if cs:
            html.append('<p style="font-weight:600;color:#1a3a5c;margin:4px 0 6px">Classes Detectadas</p>')
            html.append(f'<table style="width:100%;border-collapse:collapse;margin-bottom:14px"><thead><tr>'
                        f'<th {TH} style="text-align:left">Classe</th>'
                        f'<th {TH}>Detecções</th><th {TH}>% Frames</th>'
                        f'<th {TH}>Primeiro</th><th {TH}>Último</th>'
                        f'</tr></thead><tbody>')
            for cls_name, info in sorted(cs.items(), key=lambda x: -x[1]["count"]):
                f = _ts(info["first_frame"], fps) if info.get("first_frame") else "—"
                l = _ts(info["last_frame"],  fps) if info.get("last_frame")  else "—"
                html.append(f'<tr><td {TDL}><strong>{cls_name}</strong></td>'
                            f'<td {TD}>{info["count"]}</td><td {TD}>{info["frames_pct"]:.1f}%</td>'
                            f'<td {TD}>{f}</td><td {TD}>{l}</td></tr>')
            html.append('</tbody></table>')

        if anomalies:
            SEV = {"CRÍTICO": "#dc3545", "ALTO": "#fd7e14", "MÉDIO": "#b8860b"}
            html.append('<p style="font-weight:600;color:#1a3a5c;margin:4px 0 6px">'
                        f'Linha do Tempo de Anomalias ({len(anomalies)} total)</p>')
            html.append('<div style="max-height:260px;overflow-y:auto">')
            html.append(f'<table style="width:100%;border-collapse:collapse"><thead><tr>'
                        f'<th {TH}>Timestamp</th><th {TH}>Frame</th>'
                        f'<th {TH}>Severidade</th><th {TH}>Tipo</th>'
                        f'<th {TH} style="text-align:left">Descrição</th>'
                        f'</tr></thead><tbody>')
            for a in anomalies[:40]:
                if isinstance(a, dict):
                    fr  = a.get("frame", 0)
                    sev = a.get("severity", "—")
                    sc  = SEV.get(sev, "#6c757d")
                    html.append(
                        f'<tr><td {TD}><strong>{_ts(fr, fps)}</strong></td>'
                        f'<td {TD}>{fr}</td>'
                        f'<td {TD}><span style="color:{sc};font-weight:bold">{sev}</span></td>'
                        f'<td {TD}>{a.get("type","—")}</td>'
                        f'<td {TDL}>{a.get("description","")}</td></tr>'
                    )
            if len(anomalies) > 40:
                html.append(f'<tr><td colspan="5" style="padding:8px;text-align:center;'
                            f'color:#888;font-style:italic">… e mais {len(anomalies)-40} anomalias '
                            f'(ver relatório completo)</td></tr>')
            html.append('</tbody></table></div>')

    html.append('</div>')
    return "\n".join(html)


# ── Função principal ──────────────────────────────────────────────────────────

def process_video(video_file, model_label):
    if video_file is None:
        return "Nenhum vídeo enviado.", None, None, "", ""

    # gr.File returns a path string, an object with .path, or one with .name
    if isinstance(video_file, str):
        src_path = video_file
    elif hasattr(video_file, "path"):
        src_path = video_file.path
    elif hasattr(video_file, "name"):
        src_path = video_file.name
    else:
        src_path = str(video_file)

    if not os.path.exists(src_path):
        return f"Arquivo não encontrado: {src_path}", None, None, "", ""

    mode = MODEL_CHOICES.get(model_label)
    if not mode:
        return f"Modelo desconhecido: {model_label}", None, None, "", ""

    rel_path, cls_name, folder = _DETECTORS[mode]
    log = []

    # Copia para um diretório próprio — gr.File não faz streaming do temp,
    # mas copiamos assim mesmo para garantir que OpenCV não interfere.
    _work_dir = os.path.join(_PROJECT_ROOT, "saida", "_upload")
    os.makedirs(_work_dir, exist_ok=True)
    _work_video = os.path.join(_work_dir, os.path.basename(src_path))
    shutil.copy2(src_path, _work_video)
    video_path = _work_video

    try:
        import relatorio as _rel
    except ImportError as e:
        return f"Erro ao carregar módulo de relatório: {e}", None, None, "", ""

    log.append(f"Iniciando análise: {model_label} ...")

    try:
        mod      = _load_module(mode, rel_path)
        detector = getattr(mod, cls_name)()
        result   = detector.detect_video(video_path, headless=True)
    except Exception as e:
        return f"Erro durante a detecção: {e}", None, None, "", ""

    if result is None:
        msg = "\n".join(log + [
            "AVISO: modelo ausente ou erro na detecção.",
            f"Execute: python app.py train --mode {mode}",
        ])
        return msg, None, None, "", ""

    # ── Relatório TXT + HTML ──────────────────────────────────────────────────
    saida_dir = os.path.join(_PROJECT_ROOT, "saida", folder)
    os.makedirs(saida_dir, exist_ok=True)
    try:
        _rel.generate_report(
            os.path.join(saida_dir, "relatorio.txt"),
            result["frame_count"],
            result["detections_count"],
            result["anomalies"],
            result["fps"],
            video_path,
            result.get("class_summary"),
        )
    except Exception as e:
        log.append(f"AVISO: falha ao gerar relatório: {e}")

    anom = len(result["anomalies"])
    pct  = anom / max(result["frame_count"], 1) * 100

    if mode == "instrumentos":
        timeline = result.get("instrument_timeline", {})
        detected = [n for n, inf in timeline.items() if inf["count"] > 0]
        log.append(f"Frames    : {result['frame_count']}")
        log.append(f"Detecções : {result['detections_count']}")
        log.append(f"Instrumentos: {', '.join(detected) if detected else '—'}")
    else:
        log.append(f"Frames    : {result['frame_count']}")
        log.append(f"Detecções : {result['detections_count']}")
        log.append(f"Anomalias : {anom} ({pct:.1f}%)")

    # ── Re-encode vídeo para H.264 ────────────────────────────────────────────
    video_result = os.path.join(saida_dir, "resultado.mp4")
    if os.path.exists(video_result):
        log.append("Re-encodando vídeo para H.264...")
        _reencode_h264(video_result)

    # ── Tabela resumo ─────────────────────────────────────────────────────────
    summary_html = _build_summary_html(mode, result, folder)

    # ── Parecer médico via GPT-4o ─────────────────────────────────────────────
    log.append("Gerando parecer médico via IA (GPT-4o)...")
    from medical_opinion import generate_medical_opinion

    # Monta model_results no formato esperado pelo módulo
    _mr = [{
        "model_folder":        folder,
        "frame_count":         result["frame_count"],
        "detections":          result["detections_count"],
        "anomalies":           result["anomalies"],
        "fps":                 result["fps"],
        "class_summary":       result.get("class_summary", {}),
        "instrument_timeline": result.get("instrument_timeline", {}),
    }]

    opinion, err = generate_medical_opinion(_mr, os.path.basename(video_path))

    if err:
        opinion_text = f"Parecer médico não gerado: {err}"
        log.append(f"AVISO: {err}")
    else:
        opinion_text = opinion
        # Salvar parecer
        parecer_path = os.path.join(saida_dir, "parecer_medico.txt")
        try:
            with open(parecer_path, "w", encoding="utf-8") as f:
                f.write(opinion)
            log.append("Parecer médico salvo.")
        except Exception as e:
            log.append(f"AVISO: falha ao salvar parecer: {e}")

    # ── Arquivos para download ────────────────────────────────────────────────
    report_files = []
    for fname in ("relatorio.txt", "relatorio.html", "parecer_medico.txt"):
        p = os.path.join(saida_dir, fname)
        if os.path.exists(p):
            report_files.append(p)

    log.append("Análise concluída.")

    return (
        "\n".join(log),
        report_files or None,
        video_result if os.path.exists(video_result) else None,
        summary_html,
        opinion_text,
    )


# ── Interface Gradio ──────────────────────────────────────────────────────────

def build_interface():
    with gr.Blocks(title="Análise de Vídeo Cirúrgico", theme=gr.themes.Default()) as demo:

        gr.HTML("""
        <div id="header">
            <h1>Análise de Vídeo - S</h1>
            <p>Detecção especializada para saúde da mulher<br>
            Instrumentos · Áreas Críticas · Sangramento · Parecer Médico IA</p>
        </div>
        """)

        with gr.Column():
            video_input = gr.File(
                label="Vídeo Cirúrgico (MP4, AVI, MOV, MKV)",
                file_count="single",
                file_types=[".mp4", ".avi", ".mov", ".mkv", ".MP4", ".AVI", ".MOV"],
            )
            model_select = gr.Dropdown(
                choices=list(MODEL_CHOICES.keys()),
                value=list(MODEL_CHOICES.keys())[0],
                label="Modelo a Executar",
            )
            analyze_btn = gr.Button("Analisar Vídeo", variant="primary", size="lg")

        gr.HTML("<hr style='border:none;border-top:1px solid #e8dde3;margin:1.5rem 0'>")

        status_out  = gr.Textbox(label="Log de Processamento", lines=6, interactive=False,
                                  placeholder="O progresso aparecerá aqui...")
        video_out   = gr.File(label="Vídeo Resultado — Download", file_count="single",
                              interactive=False)
        summary_out = gr.HTML(label="Resumo da Detecção")

        gr.HTML("<hr style='border:none;border-top:1px solid #e8dde3;margin:1rem 0'>")

        opinion_out = gr.Textbox(
            label="Parecer Médico — IA (GPT-4o)",
            lines=20,
            interactive=False,
            placeholder="O parecer médico gerado pela IA aparecerá aqui após a análise...",
        )

        files_out = gr.File(
            label="Relatórios para Download (TXT · HTML · Parecer Médico)",
            file_count="multiple",
            interactive=False,
        )

        gr.HTML("""
        <div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:#a89aa3;">
            O parecer médico é gerado por IA com base na análise computacional e requer validação por médico responsável.<br>
            O relatório HTML pode ser aberto diretamente no browser.
        </div>
        """)

        analyze_btn.click(
            fn=process_video,
            inputs=[video_input, model_select],
            outputs=[status_out, files_out, video_out, summary_out, opinion_out],
            api_name=False,
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch(css=CSS, share=False, show_error=True, inbrowser=True)
