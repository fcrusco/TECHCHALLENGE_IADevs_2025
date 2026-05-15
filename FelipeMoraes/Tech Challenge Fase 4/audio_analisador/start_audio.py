import os
import sys

# Garante que audio_analisador/ esteja no path ao ser chamado da raiz do projeto
_AUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_AUDIO_DIR)
if _AUDIO_DIR not in sys.path:
    sys.path.insert(0, _AUDIO_DIR)

import gradio as gr
from analyzer import AudioAnalyzer
from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

analyzer = AudioAnalyzer()

CONSULTATION_TYPES = {
    "ginecologica": "Consulta Ginecológica",
    "pre_natal": "Acompanhamento Pré-Natal",
    "pos_parto": "Consulta Pós-Parto",
    "violencia": "Atendimento a Vítimas de Violência"
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --rose: #c0446a;
    --rose-light: #f7dde6;
    --rose-dark: #8b2a47;
    --cream: #fdf8f5;
    --charcoal: #1e1a1d;
    --muted: #7a6e74;
    --border: #e8dde3;
    --success: #2d7a5a;
    --warning: #c07a20;
    --danger: #b03030;
    --card-bg: #ffffff;
}

* { box-sizing: border-box; }

body, .gradio-container {
    background: var(--cream) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--charcoal) !important;
}

.gradio-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding: 2rem 1.5rem !important;
}

.gradio-container,
.gradio-container > *,
.gradio-container > * > *,
.gradio-container > * > * > * {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
}

.gr-row,
[class*="gr-row"],
[class*="flex-row"] {
    flex-wrap: wrap !important;
    overflow: hidden !important;
}

.gr-column,
[class*="gr-column"] {
    min-width: 0 !important;
    overflow: hidden !important;
}

.gr-audio,
[data-testid="audio"],
.waveform-container,
.waveform-visualizer,
.audio-player {
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
    min-height: 80px !important;
    height: 80px !important;
}

.gr-audio svg,
.gr-audio canvas,
[data-testid="audio"] svg,
[data-testid="audio"] canvas {
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
    height: auto !important;
}

textarea {
    width: 100% !important;
    max-width: 100% !important;
    resize: none !important;
    transition: none !important;
    box-sizing: border-box !important;
}

#header {
    text-align: center;
    margin-bottom: 2.5rem;
    padding: 2.5rem 2rem;
    background: linear-gradient(135deg, var(--rose-dark) 0%, var(--rose) 60%, #d4607e 100%);
    border-radius: 20px;
    color: white;
    position: relative;
    overflow: hidden;
    width: 100% !important;
    box-sizing: border-box !important;
}

#header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 180px; height: 180px;
    background: rgba(255,255,255,0.06);
    border-radius: 50%;
}

#header h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 2rem !important;
    font-weight: 400 !important;
    margin: 0 0 0.4rem 0 !important;
    letter-spacing: -0.5px;
}

#header p {
    font-size: 0.95rem !important;
    opacity: 0.85;
    margin: 0 !important;
    font-weight: 300;
}

label, .label-wrap span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.gr-box, .gr-form, .gr-panel, [class*="block"], .gr-padded {
    background: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
}

button.primary {
    background: linear-gradient(135deg, var(--rose-dark), var(--rose)) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 2rem !important;
    transition: opacity 0.2s, transform 0.1s !important;
}

button.primary:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}

.risk-alto  { background: #fde8e8; color: var(--danger); }
.risk-medio { background: #fef3e2; color: var(--warning); }
.risk-baixo { background: #e4f5ed; color: var(--success); }
"""


def process_audio(audio_path, consultation_type_label):
    if audio_path is None:
        return "Nenhum áudio enviado.", "—", "—", "—"

    type_key = None
    for k, v in CONSULTATION_TYPES.items():
        if v == consultation_type_label:
            type_key = k
            break

    try:
        result = analyzer.analyze(audio_path, type_key)
        return (
            result["transcricao"],
            result["nivel_risco"],
            result["sinais_detectados"],
            result["recomendacoes"]
        )
    except Exception as e:
        return f"Erro ao processar: {str(e)}", "—", "—", "—"


def build_interface():
    with gr.Blocks(title="Analise de Audio — Análise Clínica de Áudio") as demo:

        gr.HTML("""
        <div id="header">
            <h1>Analise de Audio</h1>
            <p>Análise clínica de áudio especializada em saúde da mulher<br>
            Detecção de sinais de risco por inteligência artificial</p>
        </div>
        """)

        with gr.Column():
            audio_input = gr.Audio(
                label="Gravação da Consulta",
                type="filepath",
                sources=["upload"],
            )

            consultation_type = gr.Dropdown(
                choices=list(CONSULTATION_TYPES.values()),
                value=list(CONSULTATION_TYPES.values())[0],
                label="Tipo de Consulta",
            )

            analyze_btn = gr.Button("Analisar Áudio", variant="primary", size="lg")

        gr.HTML("<hr style='border:none;border-top:1px solid #e8dde3;margin:1.5rem 0'>")

        with gr.Column():
            transcricao_out = gr.Textbox(
                label="Transcrição do Áudio",
                lines=5,
                interactive=False,
                placeholder="A transcrição aparecerá aqui...",
            )

        with gr.Row():
            with gr.Column(scale=1):
                risco_out = gr.Textbox(
                    label="Nível de Risco Detectado",
                    interactive=False,
                    placeholder="—",
                )
            with gr.Column(scale=2):
                sinais_out = gr.Textbox(
                    label="Sinais Clínicos Identificados",
                    lines=4,
                    interactive=False,
                    placeholder="Os sinais detectados aparecerão aqui...",
                )

        with gr.Column():
            recomendacoes_out = gr.Textbox(
                label="Recomendações Clínicas",
                lines=4,
                interactive=False,
                placeholder="As recomendações aparecerão aqui...",
            )

        gr.HTML("""
        <div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:#a89aa3;">
            Este sistema é uma ferramenta de apoio clínico — não substitui avaliação médica profissional.<br>
            Todas as análises devem ser revisadas por profissional de saúde habilitado.
        </div>
        """)

        analyze_btn.click(
            fn=process_audio,
            inputs=[audio_input, consultation_type],
            outputs=[transcricao_out, risco_out, sinais_out, recomendacoes_out]
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        css=CSS,
        share=False,
        show_error=True,
        inbrowser=True,
    )
