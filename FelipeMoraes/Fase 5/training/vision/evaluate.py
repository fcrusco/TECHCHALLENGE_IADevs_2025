"""Roda o detector treinado sobre imagens reais para inspeção qualitativa.

Coloque as imagens de teste (ex.: as 2 arquiteturas de avaliação do PDF do
hackathon, exportadas manualmente como PNG/JPG) em training/vision/samples/,
depois rode:

    cd training/vision
    python evaluate.py

As detecções anotadas (bounding boxes + classe + confiança) são salvas em
training/vision/samples_output/.
"""

from __future__ import annotations

from pathlib import Path

from ultralytics import YOLO

VISION_DIR = Path(__file__).parent
WEIGHTS = VISION_DIR / "output" / "stride-vision-yolov8n.pt"
SAMPLES_DIR = VISION_DIR / "samples"
OUTPUT_DIR = VISION_DIR / "samples_output"


def main() -> None:
    if not WEIGHTS.exists():
        raise SystemExit(f"Pesos não encontrados em {WEIGHTS} — rode train.py primeiro.")

    images = sorted(SAMPLES_DIR.glob("*.png")) + sorted(SAMPLES_DIR.glob("*.jpg")) + sorted(SAMPLES_DIR.glob("*.jpeg"))
    if not images:
        raise SystemExit(f"Nenhuma imagem encontrada em {SAMPLES_DIR} — adicione PNGs/JPGs de teste.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(WEIGHTS))

    for img_path in images:
        results = model.predict(str(img_path), conf=0.30, verbose=False)[0]
        out_path = OUTPUT_DIR / img_path.name
        results.save(filename=str(out_path))

        print(f"\n{img_path.name} — {len(results.boxes)} componentes detectados:")
        for box in results.boxes:
            cls_name = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            print(f"  {cls_name:<24} confiança={conf:.0%}")
        print(f"  -> anotado em {out_path}")


if __name__ == "__main__":
    main()
