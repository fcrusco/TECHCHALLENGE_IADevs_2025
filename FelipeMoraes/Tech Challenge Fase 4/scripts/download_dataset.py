import os
import shutil
import kagglehub

# Download dataset
BASE_DOWNLOAD = kagglehub.dataset_download("dilavado/labeled-surgical-tools")

from sklearn.model_selection import train_test_split

def auto_split():
    images = [f for f in os.listdir(IMAGES) if f.endswith(".jpg")]

    train, val = train_test_split(images, test_size=0.2, random_state=42)

    return train, val

# 🔍 Encontrar automaticamente a pasta correta
def find_dataset_root(base_path):
    for root, dirs, files in os.walk(base_path):
        if "Images" in dirs and "Labels" in dirs:
            return root
    return None


BASE_PATH = find_dataset_root(BASE_DOWNLOAD)

if BASE_PATH is None:
    raise Exception("❌ Não encontrou a estrutura do dataset!")

print(f"📁 Dataset encontrado em: {BASE_PATH}")

IMAGES = os.path.join(BASE_PATH, "Images", "All", "images")
LABELS = os.path.join(BASE_PATH, "Labels", "label object names")
SPLIT = os.path.join(BASE_PATH, "Test-Train Groups")

OUTPUT = "dataset"

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
        line = line.strip()

        # 🔥 pega só o nome do arquivo (remove caminho Linux)
        filename = os.path.basename(line)

        # 🔥 separa nome e extensão
        name, ext = os.path.splitext(filename)

        # 🔥 tenta localizar a imagem real
        img_src = None
        for e in [".jpg", ".png", ".jpeg"]:
            candidate = os.path.join(IMAGES, name + e)
            if os.path.exists(candidate):
                img_src = candidate
                img_name = name + e
                break

        if img_src is None:
            print(f"❌ Imagem não encontrada: {name}")
            continue

        # 🔥 label correspondente
        label_name = name + ".txt"
        label_src = os.path.join(LABELS, label_name)

        img_dst = os.path.join(OUTPUT, split_type, "images", img_name)
        label_dst = os.path.join(OUTPUT, split_type, "labels", label_name)

        shutil.copy(img_src, img_dst)

        if os.path.exists(label_src):
            shutil.copy(label_src, label_dst)
        else:
            print(f"⚠️ Label não encontrada: {label_name}")

        copied += 1

    print(f"✅ {copied} arquivos copiados para {split_type}")

def main():
    print("Downloading dataset...")
    # BASE_PATH is set above

    create_dirs()

    train_file, val_file = find_split_files()

    if not train_file or not val_file:
        print("❌ Não encontrou arquivos de split!")
        return

    print("Train:", train_file)
    print("Val:", val_file)

    move_files(train_file, "train")
    move_files(val_file, "val")

    print("✅ Dataset organizado com sucesso!")
    print("IMAGES existe?:", os.path.exists(IMAGES))
    print("LABELS existe?:", os.path.exists(LABELS))
    print("SPLIT existe?:", os.path.exists(SPLIT))

if __name__ == "__main__":
    main()
