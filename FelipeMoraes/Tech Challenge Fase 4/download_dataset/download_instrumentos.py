"""
Download e preparo do dataset de Instrumentos Cirúrgicos.

Fonte (Kaggle via kagglehub):
  dilavado/labeled-surgical-tools
  - 1834 treino / 786 val
  - 4 classes: Bisturi, Pinça de Dissecção, Tesoura Mayo Reta, Tesoura Mayo Curva

Uso:
    python app.py download --mode instrumentos
"""

import os
import shutil

import kagglehub
from sklearn.model_selection import train_test_split

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DOWNLOAD = kagglehub.dataset_download("dilavado/labeled-surgical-tools")


def find_dataset_root(base_path):
    for root, dirs, files in os.walk(base_path):
        if "Images" in dirs and "Labels" in dirs:
            return root
    return None


BASE_PATH = find_dataset_root(BASE_DOWNLOAD)

if BASE_PATH is None:
    raise Exception("Não encontrou a estrutura do dataset!")

print(f"Dataset encontrado em: {BASE_PATH}")

IMAGES = os.path.join(BASE_PATH, "Images", "All", "images")
LABELS = os.path.join(BASE_PATH, "Labels", "label object names")
SPLIT  = os.path.join(BASE_PATH, "Test-Train Groups")
OUTPUT = os.path.join(PROJECT_ROOT, "dataset", "dataset_instrumentos")


def create_dirs():
    for split in ["train", "val"]:
        os.makedirs(os.path.join(OUTPUT, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT, split, "labels"), exist_ok=True)


def find_split_files():
    files = os.listdir(SPLIT)
    train_file = None
    val_file = None
    for f in files:
        name = f.lower()
        if "train" in name:
            train_file = os.path.join(SPLIT, f)
        elif "test" in name or "val" in name:
            val_file = os.path.join(SPLIT, f)
    return train_file, val_file


def move_files(split_file, split_type):
    with open(split_file, "r") as f:
        lines = f.read().splitlines()

    copied = 0
    for line in lines:
        filename = os.path.basename(line.strip())
        name, ext = os.path.splitext(filename)

        img_src = None
        for e in [".jpg", ".png", ".jpeg"]:
            candidate = os.path.join(IMAGES, name + e)
            if os.path.exists(candidate):
                img_src = candidate
                img_name = name + e
                break

        if img_src is None:
            print(f"Imagem não encontrada: {name}")
            continue

        label_name = name + ".txt"
        label_src  = os.path.join(LABELS, label_name)
        img_dst    = os.path.join(OUTPUT, split_type, "images", img_name)
        label_dst  = os.path.join(OUTPUT, split_type, "labels", label_name)

        shutil.copy(img_src, img_dst)
        if os.path.exists(label_src):
            shutil.copy(label_src, label_dst)
        else:
            print(f"Label não encontrada: {label_name}")
        copied += 1

    print(f"{copied} arquivos copiados para {split_type}")


def main():
    print("=== Download: Dataset de Instrumentos Cirúrgicos ===\n")

    create_dirs()

    train_file, val_file = find_split_files()
    if not train_file or not val_file:
        print("Não encontrou arquivos de split!")
        return

    print("Train:", train_file)
    print("Val:", val_file)

    move_files(train_file, "train")
    move_files(val_file, "val")

    print("\n=== Dataset organizado com sucesso! ===")
    print("Próximo passo: python app.py train --mode instrumentos")


if __name__ == "__main__":
    main()
