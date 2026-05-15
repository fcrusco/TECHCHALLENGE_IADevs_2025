"""
Download e preparo do dataset de Áreas Anatômicas Críticas — GynSurge.

Fonte  : https://ftp.itec.aau.at/datasets/GynSurge/GynSurg_Anatomy_Dataset.zip
Licença: CC BY-NC-ND 4.0 (somente pesquisa científica)
Tamanho: ~350 MB compactado

Máscaras PNG 8-bit single-channel → mapeamento de pixel → classe YOLO:
   85 → 0: Utero
  170 → 1: Tuba_Uterina
  255 → 2: Ovario

Uso:
    python app.py download --mode areas-criticas
"""

import os
import random
import shutil
import zipfile
from urllib.request import urlretrieve

import cv2
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT   = os.path.join(PROJECT_ROOT, "dataset", "dataset_areas_criticas")
TMP_DIR  = os.path.join(PROJECT_ROOT, "_gynsurge_tmp_anat")
ZIP_FILE = os.path.join(PROJECT_ROOT, "_gynsurge_anat.zip")

ZIP_URL = "https://ftp.itec.aau.at/datasets/GynSurge/Semantic_Segmentation_Dataset/GynSurg_Anatomy_Dataset.zip"

# pixel value na máscara → (class_id, nome)
PIXEL_MAP = {
     85: (0, "Utero"),
    170: (1, "Tuba_Uterina"),
    255: (2, "Ovario"),
}

MIN_BOX_AREA_PX = 150   # órgãos são grandes; valor menor que instrumentos
TRAIN_RATIO     = 0.80
RANDOM_SEED     = 42


# ── Utilitários ───────────────────────────────────────────────────────────────

def _progress(count, block_size, total):
    done = count * block_size
    pct  = min(100, done * 100 // max(total, 1))
    mb   = done / 1_048_576
    if total > 0:
        print(f"\r  {pct:3d}%  {mb:.0f}/{total/1_048_576:.0f} MB", end="", flush=True)
    else:
        print(f"\r  {mb:.0f} MB baixados", end="", flush=True)


def _makedirs():
    for split in ("train", "val"):
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)


def _find_mask(img_path):
    """
    Localiza a máscara GynSurge para um frame.
    Padrão esperado (idêntico ao dataset de instrumentos):
      frame:   .../X/subpastas/nome.png
      máscara: .../X_mask/subpastas/nome_mask.png
    Percorre os segmentos do caminho procurando por um diretório irmão com sufixo _mask.
    """
    stem = os.path.splitext(os.path.basename(img_path))[0]
    parts = img_path.split(os.sep)

    # Tenta substituir cada segmento do caminho por segmento + "_mask"
    for i in range(len(parts) - 1, 0, -1):
        candidate_parts = parts[:i] + [parts[i] + "_mask"] + parts[i + 1:]
        # Troca o nome do arquivo: stem_mask.png
        candidate_parts[-1] = stem + "_mask.png"
        candidate = os.sep.join(candidate_parts)
        if os.path.exists(candidate):
            return candidate

    # Fallback: mesmo diretório, sufixo _mask
    fallback = os.path.join(os.path.dirname(img_path), stem + "_mask.png")
    if os.path.exists(fallback):
        return fallback

    return None


def _mask_to_boxes(mask_path, img_w, img_h):
    """Converte máscara GynSurge em lista de (class_id, cx, cy, bw, bh) normalizados."""
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        return []
    boxes = []
    for pv, (cls_id, _) in PIXEL_MAP.items():
        binary = np.uint8(mask == pv) * 255
        if not binary.any():
            continue
        cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            if cv2.contourArea(cnt) < MIN_BOX_AREA_PX:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append((
                cls_id,
                (x + w / 2) / img_w,
                (y + h / 2) / img_h,
                w / img_w,
                h / img_h,
            ))
    return boxes


def _collect_pairs(base_dir):
    """
    Varre a pasta extraída e retorna pares (img_path, mask_path).
    Pula pastas cujo nome termina com _mask (contêm apenas máscaras).
    """
    pairs = []

    for root, dirs, files in os.walk(base_dir):
        # Pula diretórios de máscara
        if os.path.basename(root).endswith("_mask"):
            continue
        # Evita descer para subpastas de máscara
        dirs[:] = [d for d in dirs if not d.endswith("_mask")]

        for fname in files:
            if not fname.lower().endswith(".png"):
                continue
            if fname.lower().endswith("_mask.png"):
                continue

            img_path = os.path.join(root, fname)
            mask_path = _find_mask(img_path)
            if mask_path:
                pairs.append((img_path, mask_path))

    return pairs


def _split(items, ratio=TRAIN_RATIO, seed=RANDOM_SEED):
    random.seed(seed)
    shuffled = list(items)
    random.shuffle(shuffled)
    n = int(len(shuffled) * ratio)
    return shuffled[:n], shuffled[n:]


def _save_split(valid_pairs, split):
    for i, (img_path, boxes) in enumerate(valid_pairs):
        ext  = os.path.splitext(img_path)[1]
        stem = f"anat_{split}_{i:04d}"
        shutil.copy(img_path, os.path.join(OUTPUT, split, "images", stem + ext))
        with open(os.path.join(OUTPUT, split, "labels", stem + ".txt"), "w") as f:
            for cls_id, cx, cy, bw, bh in boxes:
                f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== Download: Áreas Anatômicas Críticas (GynSurge) ===\n")

    # 1. Download
    if not os.path.exists(ZIP_FILE):
        print(f"Baixando dataset (~350 MB):\n  {ZIP_URL}\n")
        urlretrieve(ZIP_URL, ZIP_FILE, _progress)
        print()
    else:
        print(f"ZIP já existe, pulando download: {ZIP_FILE}")

    # 2. Extrair
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    print("Extraindo...")
    with zipfile.ZipFile(ZIP_FILE, "r") as zf:
        zf.extractall(TMP_DIR)

    # 3. Pares frame/máscara
    print("Localizando pares frame/máscara...")
    pairs = _collect_pairs(TMP_DIR)
    print(f"  {len(pairs)} pares encontrados")

    if not pairs:
        print("ERRO: Nenhum par encontrado. Verifique a estrutura interna do ZIP.")
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        return

    # 4. Converter máscaras → bounding boxes
    print("Convertendo máscaras para formato YOLO...")
    valid = []
    class_counts = {cls_id: 0 for cls_id, _ in PIXEL_MAP.values()}

    for img_path, mask_path in pairs:
        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]
        boxes = _mask_to_boxes(mask_path, w, h)
        if boxes:
            valid.append((img_path, boxes))
            for cls_id, *_ in boxes:
                class_counts[cls_id] = class_counts.get(cls_id, 0) + 1

    print(f"  {len(valid)} imagens com pelo menos 1 estrutura anatômica válida")
    for pv, (cls_id, name) in PIXEL_MAP.items():
        print(f"    cls {cls_id} ({name}): {class_counts.get(cls_id, 0)} bboxes")

    if not valid:
        print("AVISO: Nenhuma imagem aproveitada. Verifique PIXEL_MAP vs dataset real.")
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        return

    # 5. Split e salvar
    train_pairs, val_pairs = _split(valid)
    print(f"\nDivisão: {len(train_pairs)} treino / {len(val_pairs)} val")

    if os.path.exists(OUTPUT):
        shutil.rmtree(OUTPUT)
    _makedirs()
    _save_split(train_pairs, "train")
    _save_split(val_pairs,   "val")

    # 6. Limpeza
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    try:
        os.remove(ZIP_FILE)
    except OSError:
        pass

    print(f"\n=== Dataset pronto: {len(valid)} imagens em {OUTPUT} ===")
    print("Próximo passo: python app.py train --mode areas-criticas")


if __name__ == "__main__":
    main()
