"""
Download e preparo do dataset de Objetos Suspeitos (automutilação).

Fonte (Kaggle via kagglehub):
  iqmansingh/guns-knives-object-detection
  - Imagens de facas e armas com labels YOLO
  - 2 classes mapeadas: Faca_Lamina (0), Arma_Fogo (1)

Uso:
    python app.py download --mode automutilacao
"""

import os
import shutil
import random

import kagglehub
from sklearn.model_selection import train_test_split

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "dataset", "dataset_automutilacao")

random.seed(42)
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}

# Our class IDs
CLASS_FACA = 0    # knife / blade / razor
CLASS_ARMA = 1    # gun / firearm

# Keywords to identify source classes
_KNIFE_KW = {"knife", "blade", "razor", "knif", "cutter", "scissor"}
_GUN_KW = {"gun", "weapon", "pistol", "firearm", "handgun", "rifle", "revolver"}


def _makedirs():
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)


def _read_source_class_map(base_path):
    """
    Inspect data.yaml or classes.txt inside the dataset to build a
    mapping {source_class_id -> our_class_id}.
    Returns None if nothing useful is found (caller will default to all→0).
    """
    import glob

    yaml_candidates = glob.glob(os.path.join(base_path, "**", "*.yaml"), recursive=True)
    yaml_candidates += glob.glob(os.path.join(base_path, "**", "data.yaml"), recursive=True)

    for yp in yaml_candidates:
        try:
            # Minimal YAML parse (avoid dependency if pyyaml not installed)
            names = _extract_names_from_yaml(yp)
            if names:
                return _build_map(names)
        except Exception:
            continue

    txt_candidates = glob.glob(os.path.join(base_path, "**", "classes.txt"), recursive=True)
    for tp in txt_candidates:
        try:
            with open(tp, "r") as f:
                names = [line.strip() for line in f if line.strip()]
            if names:
                return _build_map(names)
        except Exception:
            continue

    return None


def _extract_names_from_yaml(yaml_path):
    """Lightweight extraction of the 'names' field without full YAML parser."""
    names = []
    in_names = False
    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("names:"):
                in_names = True
                # Handle inline list: names: [knife, gun]
                rest = stripped[len("names:"):].strip()
                if rest.startswith("["):
                    rest = rest.strip("[]")
                    names = [n.strip().strip("'\"") for n in rest.split(",") if n.strip()]
                    return names
                continue
            if in_names:
                if stripped.startswith("-"):
                    names.append(stripped.lstrip("- ").strip().strip("'\""))
                elif ":" in stripped and not stripped[0].isdigit():
                    break
                elif stripped[0:1].isdigit() and ":" in stripped:
                    # format: "0: knife"
                    names.append(stripped.split(":", 1)[1].strip().strip("'\""))
                elif not stripped:
                    break
    return names


def _build_map(names):
    mapping = {}
    for i, name in enumerate(names):
        n = name.lower()
        if any(k in n for k in _KNIFE_KW):
            mapping[i] = CLASS_FACA
        elif any(k in n for k in _GUN_KW):
            mapping[i] = CLASS_ARMA
    return mapping if mapping else None


def _find_yolo_pairs(base_path):
    """Walk dataset looking for (image, label) YOLO pairs."""
    image_map = {}
    label_map = {}

    for root, _, files in os.walk(base_path):
        for f in files:
            stem, ext = os.path.splitext(f)
            ext = ext.lower()
            path = os.path.join(root, f)
            if ext in IMG_EXTS:
                image_map[stem] = path
            elif ext == ".txt" and "label" in root.lower():
                label_map[stem] = path

    if not label_map:
        for root, _, files in os.walk(base_path):
            for f in files:
                stem, ext = os.path.splitext(f)
                if ext == ".txt":
                    label_map[stem] = os.path.join(root, f)

    pairs = [(image_map[s], label_map[s]) for s in image_map if s in label_map]
    return pairs


def _remap_labels(label_path, class_map):
    """
    Remap source class IDs to our class IDs.
    Lines whose source class is not in class_map are discarded.
    If class_map is None, everything maps to CLASS_FACA.
    """
    lines = []
    with open(label_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                src_cls = int(parts[0])
                if class_map is None:
                    dst_cls = CLASS_FACA
                else:
                    dst_cls = class_map.get(src_cls)
                    if dst_cls is None:
                        continue  # skip classes not in our mapping
                parts[0] = str(dst_cls)
                lines.append(" ".join(parts))
    return "\n".join(lines)


def _copy_pair(img_path, lbl_path, stem, split, class_map):
    ext = os.path.splitext(img_path)[1]
    dst_img = os.path.join(OUTPUT, split, "images", stem + ext)
    dst_lbl = os.path.join(OUTPUT, split, "labels", stem + ".txt")
    shutil.copy(img_path, dst_img)
    content = _remap_labels(lbl_path, class_map)
    with open(dst_lbl, "w") as f:
        f.write(content)


def main():
    print("=== Download: Dataset de Objetos Suspeitos (Automutilação) ===\n")

    if os.path.exists(OUTPUT):
        print(f"Limpando dataset anterior: {OUTPUT}")
        shutil.rmtree(OUTPUT)
    _makedirs()

    print("Baixando guns-knives-object-detection...")
    base_path = kagglehub.dataset_download("iqmansingh/guns-knives-object-detection")
    print(f"Extraído em: {base_path}\n")

    class_map = _read_source_class_map(base_path)
    if class_map:
        print(f"Mapeamento de classes detectado: {class_map}")
    else:
        print("Mapeamento de classes não detectado — todas as classes serão mapeadas para Faca_Lamina (0)")

    pairs = _find_yolo_pairs(base_path)
    if not pairs:
        print("ERRO: Nenhum par imagem+label YOLO encontrado.")
        print(f"Verifique manualmente a estrutura em: {base_path}")
        return

    print(f"Pares válidos encontrados: {len(pairs)}")

    train_pairs, val_pairs = train_test_split(pairs, test_size=0.2, random_state=42)

    for i, (img, lbl) in enumerate(train_pairs):
        _copy_pair(img, lbl, f"selfharm_train_{i:04d}", "train", class_map)

    for i, (img, lbl) in enumerate(val_pairs):
        _copy_pair(img, lbl, f"selfharm_val_{i:04d}", "val", class_map)

    print(f"\n=== Dataset montado em: {OUTPUT} ===")
    print(f"  Treino: {len(train_pairs)} imagens")
    print(f"  Val:    {len(val_pairs)} imagens")
    print(f"  Classe 0: Faca_Lamina (faca, navalha, lâmina)")
    print(f"  Classe 1: Arma_Fogo (pistola, arma de fogo)")
    print()
    print("Próximo passo: python app.py train --mode automutilacao")


if __name__ == "__main__":
    main()
