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
    elif mode == "automutilacao":
        m = _load("automutilacao", os.path.join("src", "detectors", "automutilacao.py"))
        return m.AutomutilacaoDetector()
    raise ValueError(f"Modo informado não é conhecido pela aplicação: {mode}")


_ALL_MODES = ["instrumentos", "areas-criticas", "sangramento", "automutilacao"]

_MODEL_FOLDER = {
    "instrumentos":   "instrumentos",
    "areas-criticas": "areas_criticas",
    "sangramento":    "sangramento",
    "automutilacao":  "automutilacao",
}


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
            "model_folder": _MODEL_FOLDER[mode],
            "frame_count": result["frame_count"],
            "detections": result["detections_count"],
            "anomalies": result["anomalies"],
            "fps": result["fps"],
            "class_summary": result.get("class_summary", {}),
        })

    if not model_results:
        print("\nNão houve resultado de nenhum modelo para gerar o relatório geral. Relatório consolidade não será gerado.")
        return

    saida_dir = os.path.join(PROJECT_ROOT, "saida")
    os.makedirs(saida_dir, exist_ok=True)
    report_path = os.path.join(saida_dir, "relatorio_geral.txt")
    _relatorio_module.generate_combined_report(report_path, model_results, video_path)

    print(f"\n{'='*60}")
    print(f"  ANÁLISE COMPLETA CONCLUÍDA")
    print(f"  Modelos processados: {len(model_results)}/{total}")
    print(f"  Relatório geral - Output: saida/relatorio_geral.txt/.html/.json")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Análise de Vídeo Cirúrgico"
    )
    parser.add_argument(
        "action",
        choices=["download", "train", "detect", "extract"],
        help="Ação a executar",
    )
    parser.add_argument(
        "--mode",
        choices=["instrumentos", "areas-criticas", "sangramento", "automutilacao", "todos"],
        default="instrumentos",
        help="Modo de detecção: instrumentos (default) | areas-criticas | sangramento | automutilacao | todos",
    )
    parser.add_argument("--video", help="Caminho para o vídeo a ser analisado")
    parser.add_argument("--output", help="Pasta de saída para extração de frames")
    parser.add_argument("--model", default=None, help="Caminho para o modelo (.pt)")
    parser.add_argument(
        "--headless", action="store_true",
        help="Executar sem janela de visualização do vídeo",
    )

    args = parser.parse_args()

    if args.action == "download":
        modes = (
            ["instrumentos", "areas-criticas", "sangramento", "automutilacao"]
            if args.mode == "todos"
            else [args.mode]
        )
        _DOWNLOAD_SCRIPTS = {
            "instrumentos":   ("download_instrumentos",   os.path.join("download_dataset", "download_instrumentos.py")),
            "areas-criticas": ("download_areas_criticas", os.path.join("download_dataset", "download_areas_criticas.py")),
            "sangramento":    ("download_sangramento",    os.path.join("download_dataset", "download_sangramento.py")),
            "automutilacao":  ("download_automutilacao",  os.path.join("download_dataset", "download_automutilacao.py")),
        }
        for m in modes:
            if args.mode == "todos":
                print(f"\n{'='*60}")
                print(f"  [{modes.index(m)+1}/{len(modes)}] Baixando dataset: {m}")
                print(f"{'='*60}")
            name, rel = _DOWNLOAD_SCRIPTS[m]
            _load(name, rel).main()

    elif args.action == "train":
        modes = _ALL_MODES if args.mode == "todos" else [args.mode]
        for i, mode in enumerate(modes, 1):
            if args.mode == "todos":
                print(f"\n{'='*60}")
                print(f"  [{i}/{len(modes)}] Treinando modelo: {mode}")
                print(f"{'='*60}")
            _get_detector(mode).train()

    elif args.action == "detect":
        if not args.video:
            print("Erro: --video é obrigatório para a ação 'detect'")
            parser.print_help()
            return

        if args.mode == "todos":
            _detect_all(args.video, args.model)
        else:
            _get_detector(args.mode).detect_video(args.video, args.model, args.headless)

    elif args.action == "extract":
        if not args.video or not args.output:
            print("Erro: --video e --output são obrigatórios para a ação 'extract'")
            parser.print_help()
            return
        utils = _load("utils", os.path.join("src", "utils.py"))
        utils.extract_frames(args.video, args.output)


if __name__ == "__main__":
    main()
