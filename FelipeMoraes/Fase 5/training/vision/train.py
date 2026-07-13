"""Treina o detector de componentes de arquitetura (YOLOv8n) sobre o dataset
sintético gerado por generate_dataset.py.

Uso:
    cd training/vision
    python generate_dataset.py     # se ainda não gerou o dataset
    python train.py
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

VISION_DIR = Path(__file__).parent
DATASET_YAML = VISION_DIR / "data" / "dataset.yaml"
OUTPUT_DIR = VISION_DIR / "output"
OUTPUT_WEIGHTS = OUTPUT_DIR / "stride-vision-yolov8n.pt"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()

    if not DATASET_YAML.exists():
        raise SystemExit(f"Dataset não encontrado em {DATASET_YAML} — rode generate_dataset.py primeiro.")

    try:
        model = YOLO("yolov8n.pt")  # pesos pré-treinados (COCO) — melhora convergência
        print("Usando pesos pré-treinados yolov8n.pt como ponto de partida.")
    except Exception as exc:
        print(f"Não foi possível baixar yolov8n.pt ({exc}) — treinando do zero com yolov8n.yaml.")
        model = YOLO("yolov8n.yaml")

    model.train(
        data=str(DATASET_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        project=str(VISION_DIR / "runs"),
        name="train",
        exist_ok=True,
    )

    best = VISION_DIR / "runs" / "train" / "weights" / "best.pt"
    if not best.exists():
        raise SystemExit(f"Treino concluído mas {best} não foi encontrado.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, OUTPUT_WEIGHTS)
    print(f"Modelo treinado salvo em {OUTPUT_WEIGHTS}")


if __name__ == "__main__":
    main()
