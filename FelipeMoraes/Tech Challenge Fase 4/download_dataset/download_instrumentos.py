"""
Download e preparo do dataset de Instrumentos Cirúrgicos via Roboflow.

Fonte: laparoscopic-yolo/laparoscopy (Roboflow Universe — CC BY 4.0)
Frames reais de colecistectomia laparoscópica.

Classes-alvo (4) e mapeamento das classes originais do dataset:
  0: Grasper   ← Forceps
  1: Hook      ← Cautery
  2: Tesoura   ← scissors
  3: Clipador  ← Clipper Duct / Clipper

Uso:
    python app.py download --mode instrumentos
    (requer ROBOFLOW_API_KEY no .env)
"""

import glob
import os
import shutil

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(PROJECT_ROOT, "dataset", "dataset_instrumentos")
TMP_DIR = os.path.join(PROJECT_ROOT, "_roboflow_tmp_inst")

ROBOFLOW_WORKSPACE = "laparoscopic-yolo"
ROBOFLOW_PROJECT = "laparoscopy"

# Mapeamento case-insensitive: nome no Roboflow → class_id nosso
CLASS_MAP = {
    "forceps":      0,
    "cautery":      1,
    "scissors":     2,
    "clipper duct": 3,
    "clipperduct":  3,
    "clipper":      3,
}

TARGET_NAMES = {0: "Grasper", 1: "Hook", 2: "Tesoura", 3: "Clipador"}


def _build_index_map(orig_names):
    """Retorna dict {indice_original: indice_nosso} para as classes de interesse."""
    idx_map = {}
    for i, name in enumerate(orig_names):
        key = name.lower().strip()
        if key in CLASS_MAP:
            idx_map[i] = CLASS_MAP[key]
    return idx_map


def _remap_split(src_dir, dst_img_dir, dst_lbl_dir, idx_map):
    """
    Copia imagens e relabela .txt remapeando/filtrando classes.
    Descarta imagens sem nenhum instrumento de interesse.
    """
    img_dir = os.path.join(src_dir, "images")
    lbl_dir = os.path.join(src_dir, "labels")
    if not os.path.isdir(img_dir):
        return 0

    count = 0
    for img_path in sorted(glob.glob(os.path.join(img_dir, "*.*"))):
        ext = os.path.splitext(img_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            continue

        stem = os.path.splitext(os.path.basename(img_path))[0]
        lbl_path = os.path.join(lbl_dir, stem + ".txt")

        new_lines = []
        if os.path.exists(lbl_path):
            for line in open(lbl_path):
                parts = line.strip().split()
                if not parts:
                    continue
                orig_cls = int(parts[0])
                if orig_cls in idx_map:
                    new_lines.append(f"{idx_map[orig_cls]} " + " ".join(parts[1:]))

        if not new_lines:
            continue  # imagem sem instrumento de interesse

        shutil.copy(img_path, os.path.join(dst_img_dir, os.path.basename(img_path)))
        with open(os.path.join(dst_lbl_dir, stem + ".txt"), "w") as f:
            f.write("\n".join(new_lines) + "\n")
        count += 1

    return count


def main():
    print("=== Download: Instrumentos Cirúrgicos (Roboflow) ===\n")

    api_key = os.getenv("ROBOFLOW_API_KEY", "").strip()
    if not api_key:
        print("ERRO: ROBOFLOW_API_KEY não definida no .env")
        print("  1. Cadastre-se em https://roboflow.com (gratuito, sem cartão)")
        print("  2. Vá em Settings → Roboflow API → copie a chave")
        print("  3. Adicione ao .env:  ROBOFLOW_API_KEY=sua_chave")
        return

    try:
        from roboflow import Roboflow
    except ImportError:
        print("ERRO: pacote 'roboflow' não instalado.")
        print("  Execute: pip install roboflow")
        return

    import yaml

    print(f"Conectando ao Roboflow ({ROBOFLOW_WORKSPACE}/{ROBOFLOW_PROJECT})...")
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(ROBOFLOW_WORKSPACE).project(ROBOFLOW_PROJECT)

    # Versão do dataset (a mais recente conhecida é 13; sobrescreva com ROBOFLOW_INST_VERSION)
    version_num = int(os.getenv("ROBOFLOW_INST_VERSION", "13"))
    print(f"Versão do dataset: {version_num}")

    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

    dataset = project.version(version_num).download("yolov8", location=TMP_DIR, overwrite=True)
    print(f"Download concluído: {TMP_DIR}\n")

    # Ler classes originais do data.yaml
    yaml_path = os.path.join(TMP_DIR, "data.yaml")
    with open(yaml_path) as f:
        cfg = yaml.safe_load(f)

    orig_names = cfg.get("names", [])
    if isinstance(orig_names, dict):
        orig_names = [orig_names[k] for k in sorted(orig_names.keys())]

    print(f"Classes originais do dataset: {orig_names}")
    idx_map = _build_index_map(orig_names)
    kept = {v: TARGET_NAMES[v] for v in sorted(set(idx_map.values()))}
    print(f"Classes mapeadas: {kept}\n")

    if not idx_map:
        print("AVISO: nenhuma classe de interesse encontrada nos nomes do dataset.")
        print("Nomes esperados (case-insensitive):", list(CLASS_MAP.keys()))
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        return

    # Preparar diretórios de saída
    if os.path.exists(OUTPUT):
        shutil.rmtree(OUTPUT)
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)

    # Processar cada split do Roboflow
    total = 0
    for rf_split, out_split in [("train", "train"), ("valid", "val"), ("test", "val")]:
        src = os.path.join(TMP_DIR, rf_split)
        if not os.path.isdir(src):
            continue
        n = _remap_split(
            src,
            os.path.join(OUTPUT, out_split, "images"),
            os.path.join(OUTPUT, out_split, "labels"),
            idx_map,
        )
        print(f"  {rf_split:6s} → {out_split}: {n} imagens com instrumentos")
        total += n

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    if total == 0:
        print("\nAVISO: nenhuma imagem aproveitada. Verifique CLASS_MAP.")
        return

    print(f"\n=== Dataset preparado: {total} imagens ===")
    print(f"Local: {OUTPUT}")
    print("Próximo passo: python app.py train --mode instrumentos")


if __name__ == "__main__":
    main()
