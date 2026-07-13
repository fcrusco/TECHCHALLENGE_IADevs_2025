"""Gera um dataset sintético de diagramas de arquitetura anotado em formato YOLO.

Cada imagem é composta colando ícones procedurais (ver shapes.py) em posições
conhecidas — por isso a bounding box de cada componente é exata, sem precisar
de anotação manual. Cobre dois estilos visuais por imagem (escolhido
aleatoriamente, mas consistente dentro da mesma imagem):

- "icon": blocos coloridos preenchidos, no estilo de diagramas de nuvem
  (AWS/Azure/GCP), mas desenhados do zero (sem usar ícones reais protegidos).
- "generic": contorno simples com leve tremor, simulando diagrama hand-drawn.

Uso:
    cd training/vision
    python generate_dataset.py                  # padrão: 1200 treino / 200 val
    python generate_dataset.py --n-train 500 --n-val 80
"""

from __future__ import annotations

import argparse
import math
import random
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import shapes

OUT_DIR = Path(__file__).parent / "data"

TYPE_NOUN_PT = {
    "user": "Usuário",
    "web_server": "Servidor Web",
    "api_gateway": "API Gateway",
    "load_balancer": "Load Balancer",
    "application_server": "Servidor de Aplicação",
    "database": "Banco de Dados",
    "cache": "Cache",
    "message_queue": "Fila de Mensagens",
    "authentication_service": "Serviço de Autenticação",
    "cdn": "CDN",
    "firewall": "Firewall",
    "storage": "Armazenamento",
    "microservice": "Microsserviço",
    "container": "Container",
    "function": "Função Serverless",
    "network": "Rede",
    "external_service": "Serviço Externo",
    "monitoring": "Monitoramento",
    "dns": "DNS",
    "vpn": "VPN",
}


def _ascii_label(text: str) -> str:
    """Remove acentos para o rótulo desenhado na imagem — o bitmap font padrão
    do PIL (ImageFont.load_default) não tem glifos para caracteres acentuados
    e renderiza tofu boxes no lugar (ex.: "ç"/"ã")."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _load_font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_arrow(draw: ImageDraw.ImageDraw, p0, p1, rng: random.Random):
    color = (90, 90, 90)
    draw.line([p0, p1], fill=color, width=2)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    head_len = 10
    for side in (-1, 1):
        a = ang + math.pi - side * 0.4
        hx = p1[0] + head_len * math.cos(a)
        hy = p1[1] + head_len * math.sin(a)
        draw.line([p1, (hx, hy)], fill=color, width=2)


def _rect_edge_point(bbox, target):
    """Ponto na borda de bbox mais próximo do centro de `target` (para desenhar setas entre ícones)."""
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tx, ty = target
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    scale_x = (x1 - x0) / 2 / abs(dx) if dx != 0 else float("inf")
    scale_y = (y1 - y0) / 2 / abs(dy) if dy != 0 else float("inf")
    scale = min(scale_x, scale_y)
    return cx + dx * scale, cy + dy * scale


def generate_image(idx: int, rng: random.Random) -> tuple[Image.Image, list[tuple[int, float, float, float, float]]]:
    n = rng.randint(4, 10)
    class_names = [rng.choice(shapes.CLASSES) for _ in range(n)]

    W = rng.randint(900, 1400)
    H = rng.randint(650, 1000)
    style = rng.choice(["icon", "generic"])

    bg = (255, 255, 255) if style == "icon" else (250, 249, 245)
    img = Image.new("RGBA", (W, H), bg + (255,))
    draw = ImageDraw.Draw(img)

    cols = max(1, math.ceil(math.sqrt(n * W / H)))
    rows = math.ceil(n / cols)
    cell_w = W / cols
    cell_h = H / rows

    font = _load_font(16)
    boxes: list[tuple[int, float, float, float, float]] = []
    centers: list[tuple[float, float]] = []
    bboxes: list[tuple[float, float, float, float]] = []

    for i, class_name in enumerate(class_names):
        row, col = divmod(i, cols)
        icon_w = cell_w * rng.uniform(0.40, 0.60)
        icon_h = cell_h * rng.uniform(0.35, 0.50)
        max_jx = max(0.0, (cell_w - icon_w) / 2 - 4)
        max_jy = max(0.0, (cell_h - icon_h) / 2 - 4)
        cx = col * cell_w + cell_w / 2 + rng.uniform(-max_jx, max_jx)
        cy = row * cell_h + cell_h / 2 + rng.uniform(-max_jy, max_jy) - cell_h * 0.08
        bbox = (cx - icon_w / 2, cy - icon_h / 2, cx + icon_w / 2, cy + icon_h / 2)
        bboxes.append(bbox)
        centers.append((cx, cy))

    # Setas de conexão (só decoração visual — não é alvo de detecção)
    n_edges = rng.randint(max(0, n - 2), max(1, n - 1))
    for _ in range(n_edges):
        a, b = rng.sample(range(n), 2)
        p0 = _rect_edge_point(bboxes[a], centers[b])
        p1 = _rect_edge_point(bboxes[b], centers[a])
        _draw_arrow(draw, p0, p1, rng)

    for i, class_name in enumerate(class_names):
        bbox = bboxes[i]
        shapes.render_icon(img, class_name, bbox, style, rng)

        label = _ascii_label(TYPE_NOUN_PT[class_name])
        tw = draw.textlength(label, font=font)
        lx = centers[i][0] - tw / 2
        ly = bbox[3] + 4
        draw.text((lx, ly), label, fill=(20, 20, 20), font=font)

        class_idx = shapes.CLASSES.index(class_name)
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        # bbox com pequena margem — cobre o ícone (o rótulo de texto fica fora)
        pad = 0.12
        x0 -= w * pad; x1 += w * pad
        y0 -= h * pad; y1 += h * pad
        cx_n = ((x0 + x1) / 2) / W
        cy_n = ((y0 + y1) / 2) / H
        w_n = (x1 - x0) / W
        h_n = (y1 - y0) / H
        boxes.append((class_idx, cx_n, cy_n, w_n, h_n))

    return img.convert("RGB"), boxes


def generate_split(split: str, n: int, seed: int) -> None:
    img_dir = OUT_DIR / "images" / split
    lbl_dir = OUT_DIR / "labels" / split
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    for i in range(n):
        img, boxes = generate_image(i, rng)
        img.save(img_dir / f"img_{i:05d}.png")
        with open(lbl_dir / f"img_{i:05d}.txt", "w") as f:
            for class_idx, cx, cy, w, h in boxes:
                f.write(f"{class_idx} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    print(f"[{split}] {n} imagens geradas em {img_dir}")


def write_dataset_yaml() -> None:
    yaml_path = OUT_DIR / "dataset.yaml"
    names_block = "\n".join(f"  {i}: {name}" for i, name in enumerate(shapes.CLASSES))
    yaml_path.write_text(
        f"path: {OUT_DIR.resolve().as_posix()}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"nc: {len(shapes.CLASSES)}\n"
        f"names:\n{names_block}\n",
        encoding="utf-8",
    )
    print(f"dataset.yaml escrito em {yaml_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-train", type=int, default=1200)
    parser.add_argument("--n-val", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_split("train", args.n_train, args.seed)
    generate_split("val", args.n_val, args.seed + 1)
    write_dataset_yaml()


if __name__ == "__main__":
    main()
