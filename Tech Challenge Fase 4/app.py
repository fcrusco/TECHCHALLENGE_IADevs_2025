import argparse
import importlib.util
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

_SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def _load(name, rel_path):
    path = os.path.join(PROJECT_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_detector(mode):
    if mode == "instrumentos":
        m = _load("instrumentos", os.path.join("src", "detectors", "instrumentos.py"))
        return m.InstrumentosDetector()
    elif mode == "areas-criticas":
        m = _load("areas_criticas", os.path.join("src", "detectors", "areas_criticas.py"))
        return m.AreasCriticasDetector()
    elif mode == "sangramento":
        m = _load("sangramento", os.path.join("src", "detectors", "sangramento.py"))
        return m.SangramentoDetector()
    raise ValueError(f"Modo informado não é conhecido pela aplicação: {mode}")


_ALL_MODES = ["instrumentos", "areas-criticas", "sangramento"]

_MODEL_FOLDER = {
    "instrumentos":   "instrumentos",
    "areas-criticas": "areas_criticas",
    "sangramento":    "sangramento",
}


# ── Vídeo ────────────────────────────────────────────────────────────────────

def _detect_all(video_path, model_path):
    import relatorio as _relatorio_module

    model_results = []
    total = len(_ALL_MODES)

    for i, mode in enumerate(_ALL_MODES, 1):
        print(f"\n{'='*60}")
        print(f"  [{i}/{total}] Processando modelo: {mode}")
        print(f"{'='*60}")
        detector = _get_detector(mode)
        result = detector.detect_video(video_path, model_path, headless=True)
        if result is None:
            print(f"  AVISO: {mode} não retornou resultados (modelo ausente?).")
            continue
        model_results.append({
            "model_folder":        _MODEL_FOLDER[mode],
            "frame_count":         result["frame_count"],
            "detections":          result["detections_count"],
            "anomalies":           result["anomalies"],
            "fps":                 result["fps"],
            "class_summary":       result.get("class_summary", {}),
            "instrument_timeline": result.get("instrument_timeline", {}),
        })

    if not model_results:
        print("\nNenhum modelo retornou resultados. Relatório consolidado não será gerado.")
        return

    saida_dir = os.path.join(PROJECT_ROOT, "saida")
    os.makedirs(saida_dir, exist_ok=True)
    report_path = os.path.join(saida_dir, "relatorio_geral.txt")
    _relatorio_module.generate_combined_report(report_path, model_results, video_path)

    print(f"\n{'='*60}")
    print(f"  ANÁLISE COMPLETA CONCLUÍDA")
    print(f"  Modelos processados: {len(model_results)}/{total}")
    print(f"  Relatório: saida/relatorio_geral.txt/.html/.json")
    print(f"{'='*60}")


# ── Vídeo Frontend ───────────────────────────────────────────────────────────

def _start_video_frontend():
    import subprocess
    script = os.path.join(PROJECT_ROOT, "video_analisador", "start_video.py")
    if not os.path.exists(script):
        print(f"Erro: front-end não encontrado em {script}")
        return
    print("Iniciando interface Gradio de análise de vídeo...")
    print("Acesse: http://localhost:7861")
    subprocess.run([sys.executable, script])


# ── Áudio ────────────────────────────────────────────────────────────────────

def _start_audio_frontend():
    import subprocess
    script = os.path.join(PROJECT_ROOT, "audio_analisador", "start_audio.py")
    if not os.path.exists(script):
        print(f"Erro: front-end não encontrado em {script}")
        return
    print("Iniciando interface Gradio de análise de áudio...")
    print("Acesse: http://localhost:7860")
    subprocess.run([sys.executable, script])


def _extract_audio_from_video(video_path):
    import subprocess
    if not os.path.exists(video_path):
        print(f"Erro: vídeo não encontrado: {video_path}")
        return None

    audios_dir = os.path.join(PROJECT_ROOT, "audios")
    os.makedirs(audios_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(audios_dir, f"{base}.mp3")

    print(f"Extraindo áudio de: {os.path.basename(video_path)}")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "mp3", "-q:a", "2", audio_path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Erro ao extrair áudio (ffmpeg):\n{result.stderr[-800:]}")
        return None

    size_mb = os.path.getsize(audio_path) / 1024 / 1024
    print(f"Áudio salvo em: audios/{os.path.basename(audio_path)} ({size_mb:.1f} MB)")
    return audio_path


def _analyze_audio_headless(audio_path, tipo):
    if audio_path is None or not os.path.exists(audio_path):
        print(f"Erro: arquivo de áudio não encontrado: {audio_path}")
        return

    audio_dir = os.path.join(PROJECT_ROOT, "audio_analisador")
    if audio_dir not in sys.path:
        sys.path.insert(0, audio_dir)

    analyzer_path = os.path.join(audio_dir, "analyzer.py")
    if not os.path.exists(analyzer_path):
        print(f"Erro: analyzer.py não encontrado em {analyzer_path}")
        return

    mod = _load("analyzer", analyzer_path)
    analyzer = mod.AudioAnalyzer()

    print(f"\n{'='*60}")
    print(f"  ANÁLISE DE ÁUDIO: {os.path.basename(audio_path)}")
    print(f"  Tipo de consulta : {tipo}")
    print(f"{'='*60}")

    result = analyzer.analyze(audio_path, tipo)

    print(f"\nTranscrição:")
    print(f"  {result.get('transcricao', 'N/A')}")
    print(f"\nNível de Risco: {result.get('nivel_risco', 'N/A')}")
    print(f"\nSinais Detectados:")
    print(f"  {result.get('sinais_detectados', 'N/A')}")
    print(f"\nRecomendações:")
    print(f"  {result.get('recomendacoes', 'N/A')}")
    print(f"\n{'='*60}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Tech Challenge Fase 4 — Análise de Vídeo e Áudio Cirúrgico"
    )
    parser.add_argument(
        "action",
        choices=["download", "train", "detect", "extract", "audio", "video"],
        help="Ação a executar",
    )
    parser.add_argument(
        "--mode",
        choices=["instrumentos", "areas-criticas", "sangramento", "audio", "todos"],
        default="instrumentos",
        help="Modo: instrumentos | areas-criticas | sangramento | audio | todos",
    )
    parser.add_argument("--video",    help="Caminho para o vídeo a ser analisado ou extraído")
    parser.add_argument("--audio",    help="Caminho para o arquivo de áudio a analisar (sem interface)")
    parser.add_argument("--frontend", action="store_true", help="Abre a interface Gradio de análise de áudio")
    parser.add_argument(
        "--tipo",
        choices=["ginecologica", "pre_natal", "pos_parto", "violencia"],
        default="ginecologica",
        help="Tipo de consulta para análise de áudio (default: ginecologica)",
    )
    parser.add_argument("--output",   help="Pasta de saída para extração de frames")
    parser.add_argument("--model",    default=None, help="Caminho alternativo para o modelo (.pt)")
    parser.add_argument("--headless", action="store_true", help="Executar sem janela de visualização do vídeo")

    args = parser.parse_args()

    # ── download ──────────────────────────────────────────────────────────────
    if args.action == "download":
        _DOWNLOAD_SCRIPTS = {
            "instrumentos":   ("download_instrumentos",   os.path.join("download_dataset", "download_instrumentos.py")),
            "areas-criticas": ("download_areas_criticas", os.path.join("download_dataset", "download_areas_criticas.py")),
            "sangramento":    ("download_sangramento",    os.path.join("download_dataset", "download_sangramento.py")),
            "audio":          ("download_audio",          os.path.join("download_dataset", "download_audio.py")),
        }
        modes = (
            ["instrumentos", "areas-criticas", "sangramento", "audio"]
            if args.mode == "todos"
            else [args.mode]
        )
        for i, m in enumerate(modes, 1):
            if args.mode == "todos":
                print(f"\n{'='*60}")
                print(f"  [{i}/{len(modes)}] Baixando dataset: {m}")
                print(f"{'='*60}")
            name, rel = _DOWNLOAD_SCRIPTS[m]
            _load(name, rel).main()

    # ── train ─────────────────────────────────────────────────────────────────
    elif args.action == "train":
        modes = _ALL_MODES if args.mode == "todos" else [args.mode]
        for i, mode in enumerate(modes, 1):
            if args.mode == "todos":
                print(f"\n{'='*60}")
                print(f"  [{i}/{len(modes)}] Treinando modelo: {mode}")
                print(f"{'='*60}")
            _get_detector(mode).train()

    # ── detect ────────────────────────────────────────────────────────────────
    elif args.action == "detect":
        if not args.video:
            print("Erro: --video é obrigatório para a ação 'detect'")
            parser.print_help()
            return
        if args.mode == "todos":
            _detect_all(args.video, args.model)
        else:
            _get_detector(args.mode).detect_video(args.video, args.model, args.headless)

    # ── extract ───────────────────────────────────────────────────────────────
    elif args.action == "extract":
        if not args.video or not args.output:
            print("Erro: --video e --output são obrigatórios para a ação 'extract'")
            parser.print_help()
            return
        utils = _load("utils", os.path.join("src", "utils.py"))
        utils.extract_frames(args.video, args.output)

    # ── video frontend ────────────────────────────────────────────────────────
    elif args.action == "video":
        _start_video_frontend()

    # ── audio ─────────────────────────────────────────────────────────────────
    elif args.action == "audio":
        if args.frontend:
            _start_audio_frontend()
        elif args.audio:
            _analyze_audio_headless(args.audio, args.tipo)
        elif args.video:
            audio_path = _extract_audio_from_video(args.video)
            if audio_path:
                _analyze_audio_headless(audio_path, args.tipo)
        else:
            print("Erro: informe --frontend, --audio <arquivo> ou --video <arquivo>")
            print("")
            print("Exemplos:")
            print("  python app.py audio --frontend")
            print("  python app.py audio --audio consulta.mp3 --tipo ginecologica")
            print("  python app.py audio --video cirurgia.mp4 --tipo pos_parto")


if __name__ == "__main__":
    main()
