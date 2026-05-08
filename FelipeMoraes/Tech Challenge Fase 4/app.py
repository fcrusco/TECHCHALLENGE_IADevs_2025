import argparse
import importlib.util
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Make src/ importable so detectors can use absolute imports
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
        m = _load("instruments", os.path.join("src", "detectors", "instruments.py"))
        return m.InstrumentDetector()
    elif mode == "areas-criticas":
        m = _load("critical_areas", os.path.join("src", "detectors", "critical_areas.py"))
        return m.CriticalAreasDetector()
    elif mode == "sangramento":
        m = _load("bleeding", os.path.join("src", "detectors", "bleeding.py"))
        return m.BleedingDetector()
    elif mode == "automutilacao":
        m = _load("selfharm", os.path.join("src", "detectors", "selfharm.py"))
        return m.SelfHarmDetector()
    raise ValueError(f"Modo desconhecido: {mode}")


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Análise de Vídeo Cirúrgico — Tech Challenge Fase 4 (YOLOv8)"
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
        help="Modo de detecção: instrumentos (default) | areas-criticas | sangramento | automutilacao | todos (download only)",
    )
    parser.add_argument("--video", help="Caminho para o vídeo a analisar")
    parser.add_argument("--output", help="Pasta de saída para extração de frames")
    parser.add_argument("--model", default=None, help="Caminho para o modelo (.pt)")
    parser.add_argument(
        "--headless", action="store_true",
        help="Executar sem janela de visualização (para servidores/CI)",
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
        _get_detector(args.mode).train()

    elif args.action == "detect":
        if not args.video:
            print("Erro: --video é obrigatório para a ação 'detect'")
            parser.print_help()
            return
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
