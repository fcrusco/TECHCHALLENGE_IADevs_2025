"""
Download e preparo do dataset de Áreas Críticas (Ovário, Mama).

Fontes (Kaggle — download via kagglehub):
  - Mama  → BUSI: aryashah2k/breast-ultrasound-images-dataset
             (~780 imagens de ultrassom mamário com máscaras de segmentação)
  - Ovário → PCOS: anaghachoudhari/pcos-detection-using-ultrasound-images
             (~1.932 imagens de ultrassom ovariano)

Nota: dataset de Útero não está disponível publicamente no Kaggle com labels
espaciais. A classe pode ser adicionada manualmente depois.

Uso:
    python app.py download --mode areas-criticas
"""

import os
import shutil
import random

import cv2
import kagglehub
import numpy as np
from sklearn.model_selection import train_test_split

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "dataset", "dataset_areas_criticas")

# YOLO class IDs (devem bater com dataset_critical_areas.yaml)
CLASS_OVARIO = 0
CLASS_MAMA   = 1

random.seed(42)


# ── Utilitários ───────────────────────────────────────────────────────────────

def _makedirs():
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)


def _write_label(label_path, class_id, cx, cy, bw, bh):
    with open(label_path, "w") as f:
        f.write(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")


def _mask_to_yolo_box(mask_path):
    """Convert a binary mask PNG to a YOLO bounding box (cx, cy, w, h) normalized."""
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return None
    img_h, img_w = mask.shape
    _, binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    x_min, y_min, x_max, y_max = img_w, img_h, 0, 0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x + w)
        y_max = max(y_max, y + h)

    if x_max <= x_min or y_max <= y_min:
        return None

    cx = (x_min + x_max) / 2 / img_w
    cy = (y_min + y_max) / 2 / img_h
    bw = (x_max - x_min) / img_w
    bh = (y_max - y_min) / img_h
    return cx, cy, bw, bh


def _copy_sample(src_img, stem, split, class_id, box):
    """Copy image + write label into the correct split folder."""
    ext = os.path.splitext(src_img)[1]
    dst_img = os.path.join(OUTPUT, split, "images", stem + ext)
    dst_lbl = os.path.join(OUTPUT, split, "labels", stem + ".txt")
    shutil.copy(src_img, dst_img)
    _write_label(dst_lbl, class_id, *box)


# ── MAMA (BUSI dataset) ───────────────────────────────────────────────────────

def _collect_busi_samples(base_path):
    """
    BUSI structure:
      Dataset_BUSI_with_GT/
        benign/   image (1).png  image (1)_mask.png  ...
        malignant/...
        normal/   (empty masks — skip)
    Returns list of (img_path, box) tuples for benign + malignant images.
    """
    samples = []
    dataset_root = None

    for root, dirs, files in os.walk(base_path):
        if "Dataset_BUSI_with_GT" in dirs:
            dataset_root = os.path.join(root, "Dataset_BUSI_with_GT")
            break
        if os.path.basename(root) == "Dataset_BUSI_with_GT":
            dataset_root = root
            break

    if dataset_root is None:
        # fallback: scan for benign/malignant folders directly
        dataset_root = base_path

    for category in ["benign", "malignant"]:
        cat_dir = os.path.join(dataset_root, category)
        if not os.path.exists(cat_dir):
            continue
        imgs = [f for f in os.listdir(cat_dir)
                if not f.endswith("_mask.png") and f.endswith(".png")]
        for img_name in imgs:
            img_path = os.path.join(cat_dir, img_name)
            stem = os.path.splitext(img_name)[0]
            mask_path = os.path.join(cat_dir, stem + "_mask.png")
            if not os.path.exists(mask_path):
                continue
            box = _mask_to_yolo_box(mask_path)
            if box is None:
                continue
            samples.append((img_path, box))

    return samples


def _process_busi(base_path):
    samples = _collect_busi_samples(base_path)
    if not samples:
        print("  AVISO: Nenhuma imagem BUSI válida encontrada.")
        return 0, 0

    train_s, val_s = train_test_split(samples, test_size=0.2, random_state=42)
    for i, (img_path, box) in enumerate(train_s):
        stem = f"mama_train_{i:04d}"
        _copy_sample(img_path, stem, "train", CLASS_MAMA, box)
    for i, (img_path, box) in enumerate(val_s):
        stem = f"mama_val_{i:04d}"
        _copy_sample(img_path, stem, "val", CLASS_MAMA, box)

    print(f"  Mama: {len(train_s)} treino / {len(val_s)} val")
    return len(train_s), len(val_s)


# ── OVÁRIO (PCOS dataset) ─────────────────────────────────────────────────────

def _collect_pcos_samples(base_path):
    """
    PCOS dataset: folders with ultrasound images of ovaries (no spatial labels).
    We create full-image bounding boxes (cx=0.5, cy=0.5, w=0.95, h=0.95) as
    a bootstrap annotation — adequate for classification-like detection.
    """
    FULL_BOX = (0.5, 0.5, 0.95, 0.95)
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    samples = []

    for root, _, files in os.walk(base_path):
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                samples.append((os.path.join(root, f), FULL_BOX))

    return samples


def _process_pcos(base_path):
    samples = _collect_pcos_samples(base_path)
    if not samples:
        print("  AVISO: Nenhuma imagem PCOS encontrada.")
        return 0, 0

    # Cap at 1000 to keep dataset balanced with BUSI
    if len(samples) > 1000:
        random.shuffle(samples)
        samples = samples[:1000]

    train_s, val_s = train_test_split(samples, test_size=0.2, random_state=42)
    for i, (img_path, box) in enumerate(train_s):
        ext = os.path.splitext(img_path)[1]
        stem = f"ovario_train_{i:04d}"
        _copy_sample(img_path, stem, "train", CLASS_OVARIO, box)
    for i, (img_path, box) in enumerate(val_s):
        ext = os.path.splitext(img_path)[1]
        stem = f"ovario_val_{i:04d}"
        _copy_sample(img_path, stem, "val", CLASS_OVARIO, box)

    print(f"  Ovário: {len(train_s)} treino / {len(val_s)} val")
    return len(train_s), len(val_s)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Download: Dataset de Áreas Críticas Ginecológicas ===\n")

    if os.path.exists(OUTPUT):
        print(f"Limpando dataset anterior: {OUTPUT}")
        shutil.rmtree(OUTPUT)
    _makedirs()

    # --- MAMA: BUSI ---
    print("Baixando BUSI (Breast Ultrasound Images)...")
    busi_path = kagglehub.dataset_download("aryashah2k/breast-ultrasound-images-dataset")
    print(f"  Extraído em: {busi_path}")
    mama_train, mama_val = _process_busi(busi_path)

    # --- OVÁRIO: PCOS ---
    print("\nBaixando PCOS Ultrasound (ovário)...")
    pcos_path = kagglehub.dataset_download("anaghachoudhari/pcos-detection-using-ultrasound-images")
    print(f"  Extraído em: {pcos_path}")
    ov_train, ov_val = _process_pcos(pcos_path)

    # --- Resumo ---
    total_train = mama_train + ov_train
    total_val   = mama_val   + ov_val
    print(f"\n=== Dataset montado em: {OUTPUT} ===")
    print(f"  Treino: {total_train} imagens  |  Val: {total_val} imagens")
    print(f"  Classes: 0=Ovario ({ov_train}/{ov_val})  1=Mama ({mama_train}/{mama_val})")
    print()
    print("NOTA: Labels de Ovário são bounding boxes de imagem inteira (bootstrap).")
    print("      Para melhor precisão, anote manualmente ou use um dataset com labels espaciais.")
    print()
    print("Próximo passo: python app.py train --mode areas-criticas")


if __name__ == "__main__":
    main()
