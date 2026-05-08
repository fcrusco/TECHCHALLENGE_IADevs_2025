"""
Download e preparo do dataset de Sangramento Anômalo.

Fonte (Kaggle via kagglehub):
  darksoul007fedsdfds/wcebleedgen
  - 2.618 frames de cápsula endoscópica (WCE)
  - Labels em formato YOLO (bounding boxes de regiões com sangue)
  - 1 classe: Sangramento

Uso:
    python app.py download --mode sangramento
"""

import os
import shutil
import random

import kagglehub
from sklearn.model_selection import train_test_split

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "dataset", "dataset_sangramentos")

random.seed(42)
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def _makedirs():
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)


def _find_yolo_pairs(base_path):
    """
    Walk the dataset looking for (image, label) YOLO pairs.
    WCEBleedGen may have structure:
      WCEBleedGen/
        images/ *.png
        annotations/YOLO_TXT/ *.txt
      or
        bleeding/images/ + bleeding/YOLO_TXT/
    """
    image_map = {}  # stem → img_path
    label_map = {}  # stem → lbl_path

    for root, _, files in os.walk(base_path):
        for f in files:
            stem, ext = os.path.splitext(f)
            ext = ext.lower()
            path = os.path.join(root, f)
            # Skip mask files (common naming: _mask or _seg)
            if "_mask" in stem or "_seg" in stem:
                continue
            if ext in IMG_EXTS:
                image_map[stem] = path
            elif ext == ".txt" and "YOLO" in root.upper():
                label_map[stem] = path

    # Fallback: if no YOLO folder found, look for any .txt next to images
    if not label_map:
        for root, _, files in os.walk(base_path):
            for f in files:
                stem, ext = os.path.splitext(f)
                if ext == ".txt":
                    label_map[stem] = os.path.join(root, f)

    pairs = [(image_map[s], label_map[s]) for s in image_map if s in label_map]
    return pairs


def _remap_labels(label_path):
    """
    WCEBleedGen may have class IDs other than 0 for bleeding.
    Remap everything to class 0 (Sangramento).
    Returns the remapped content string.
    """
    lines = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                parts[0] = "0"
                lines.append(" ".join(parts))
    return "\n".join(lines)


def _copy_pair(img_path, lbl_path, stem, split):
    ext = os.path.splitext(img_path)[1]
    dst_img = os.path.join(OUTPUT, split, "images", stem + ext)
    dst_lbl = os.path.join(OUTPUT, split, "labels", stem + ".txt")
    shutil.copy(img_path, dst_img)
    content = _remap_labels(lbl_path)
    with open(dst_lbl, "w") as f:
        f.write(content)


def main():
    print("=== Download: Dataset de Sangramento Anômalo ===\n")

    if os.path.exists(OUTPUT):
        print(f"Limpando dataset anterior: {OUTPUT}")
        shutil.rmtree(OUTPUT)
    _makedirs()

    print("Baixando WCEBleedGen (Wireless Capsule Endoscopy Bleeding)...")
    base_path = kagglehub.dataset_download("darksoul007fedsdfds/wcebleedgen")
    print(f"Extraído em: {base_path}\n")

    pairs = _find_yolo_pairs(base_path)
    if not pairs:
        print("ERRO: Nenhum par imagem+label YOLO encontrado.")
        print(f"Verifique manualmente a estrutura em: {base_path}")
        return

    print(f"Pares válidos encontrados: {len(pairs)}")

    train_pairs, val_pairs = train_test_split(pairs, test_size=0.2, random_state=42)

    for i, (img, lbl) in enumerate(train_pairs):
        _copy_pair(img, lbl, f"bleed_train_{i:04d}", "train")

    for i, (img, lbl) in enumerate(val_pairs):
        _copy_pair(img, lbl, f"bleed_val_{i:04d}", "val")

    print(f"\n=== Dataset montado em: {OUTPUT} ===")
    print(f"  Treino: {len(train_pairs)} imagens")
    print(f"  Val:    {len(val_pairs)} imagens")
    print(f"  Classe: 0 = Sangramento")
    print()
    print("Próximo passo: python app.py train --mode sangramento")


if __name__ == "__main__":
    main()
