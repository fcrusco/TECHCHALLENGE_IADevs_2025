"""Renderers procedurais de ícones de componentes de arquitetura.

Cada classe (ver CLASS_SHAPE) é desenhada com PIL puro — sem depender de
arquivos de ícone de terceiros (evita qualquer questão de licença de ícones
reais da AWS/Azure/GCP). Duas variantes de estilo:

- "icon": bloco preenchido com cor sólida por classe, cantos arredondados —
  simula a convenção visual de diagramas de nuvem (AWS/Azure/GCP) sem usar
  os ícones oficiais.
- "generic": só contorno, traço com leve tremor (jitter) simulando um
  diagrama desenhado à mão.

Se existir um ícone real do usuário em
`training/vision/assets/icons/<classe>/*.png`, ele é usado no lugar do
desenho procedural (ver `render_icon`) — ponto de extensão opcional para
quem quiser colar ícones oficiais depois (fora do escopo deste MVP).
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS_DIR = Path(__file__).parent / "assets" / "icons"

# (forma_base, cor RGB) por classe — vocabulário de 20 tipos usado em
# agents/nodes.py (extract_components_node).
CLASS_SHAPE: dict[str, tuple[str, tuple[int, int, int]]] = {
    "user": ("actor", (66, 133, 244)),
    "web_server": ("box", (52, 168, 83)),
    "api_gateway": ("box", (251, 140, 0)),
    "load_balancer": ("box", (156, 39, 176)),
    "application_server": ("box", (0, 150, 136)),
    "database": ("cylinder", (211, 47, 47)),
    "cache": ("cylinder", (255, 111, 0)),
    "message_queue": ("tray", (121, 85, 72)),
    "authentication_service": ("shield", (48, 63, 159)),
    "cdn": ("cloud", (0, 172, 193)),
    "firewall": ("shield", (183, 28, 28)),
    "storage": ("folder", (99, 115, 129)),
    "microservice": ("box", (0, 121, 107)),
    "container": ("box", (93, 64, 55)),
    "function": ("box", (255, 160, 0)),
    "network": ("cloud", (69, 90, 100)),
    "external_service": ("cloud", (120, 120, 120)),
    "monitoring": ("box", (67, 160, 71)),
    "dns": ("cloud", (30, 136, 229)),
    "vpn": ("shield", (94, 53, 177)),
}

CLASSES = list(CLASS_SHAPE.keys())


def _jitter_point(x: float, y: float, rng: random.Random, amount: float) -> tuple[float, float]:
    return x + rng.uniform(-amount, amount), y + rng.uniform(-amount, amount)


def _draw_wobbly_line(draw: ImageDraw.ImageDraw, p0, p1, rng: random.Random, amount: float, **kwargs):
    """Desenha uma linha em 2-3 segmentos com leve tremor, simulando traço à mão."""
    n = rng.randint(2, 3)
    pts = [p0]
    for i in range(1, n):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        pts.append(_jitter_point(x, y, rng, amount))
    pts.append(p1)
    draw.line(pts, **kwargs)


def _wobbly_polygon(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], rng: random.Random,
                     amount: float, color=(40, 40, 40), width: int = 3):
    closed = points + [points[0]]
    for p0, p1 in zip(closed, closed[1:]):
        _draw_wobbly_line(draw, p0, p1, rng, amount, fill=color, width=width)


def _rounded_rect(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    radius = min(x1 - x0, y1 - y0) * 0.18
    if style == "icon":
        draw.rounded_rectangle(bbox, radius=radius, fill=color, outline=None)
    else:
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        _wobbly_polygon(draw, pts, rng, amount=max(2.0, (x1 - x0) * 0.02), width=3)


def _cylinder(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    w = x1 - x0
    ell_h = max(6, (y1 - y0) * 0.18)
    if style == "icon":
        draw.rectangle((x0, y0 + ell_h / 2, x1, y1 - ell_h / 2), fill=color)
        draw.ellipse((x0, y0, x1, y0 + ell_h), fill=color)
        draw.ellipse((x0, y1 - ell_h, x1, y1), fill=color)
    else:
        amount = max(2.0, w * 0.02)
        draw.arc((x0, y0, x1, y0 + ell_h), 0, 180, fill=(40, 40, 40), width=3)
        draw.arc((x0, y1 - ell_h, x1, y1), 0, 360, fill=(40, 40, 40), width=3)
        _draw_wobbly_line(draw, (x0, y0 + ell_h / 2), (x0, y1 - ell_h / 2), rng, amount, fill=(40, 40, 40), width=3)
        _draw_wobbly_line(draw, (x1, y0 + ell_h / 2), (x1, y1 - ell_h / 2), rng, amount, fill=(40, 40, 40), width=3)


def _cloud(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    cx, cy = x0 + w / 2, y0 + h / 2
    lobes = [
        (x0 + w * 0.30, cy, w * 0.30),
        (x0 + w * 0.55, cy - h * 0.15, w * 0.32),
        (x0 + w * 0.75, cy + h * 0.05, w * 0.26),
    ]
    if style == "icon":
        for lx, ly, r in lobes:
            draw.ellipse((lx - r, ly - r, lx + r, ly + r), fill=color)
        draw.rectangle((x0 + w * 0.20, cy, x1 - w * 0.10, y1 - h * 0.05), fill=color)
    else:
        amount = max(2.0, w * 0.02)
        pts = []
        n_arcs = 8
        for i in range(n_arcs + 1):
            ang = math.pi * i / n_arcs
            pts.append((cx + (w / 2) * math.cos(ang), cy + (h / 2.2) * math.sin(-ang) + h * 0.1))
        _wobbly_polygon(draw, pts, rng, amount, width=3)


def _actor(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    cx = x0 + w / 2
    head_r = min(w, h) * 0.18
    head_cy = y0 + head_r * 1.2
    body_top = head_cy + head_r
    body_bottom = y1 - h * 0.15
    fill = color if style == "icon" else None
    outline = (40, 40, 40)
    draw.ellipse((cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r), fill=fill, outline=outline, width=3)
    amount = max(1.5, w * 0.015) if style != "icon" else 0
    if style == "icon":
        draw.line((cx, body_top, cx, body_bottom), fill=color, width=int(max(4, w * 0.12)))
        draw.line((x0 + w * 0.15, body_top + (body_bottom - body_top) * 0.35, x1 - w * 0.15,
                    body_top + (body_bottom - body_top) * 0.35), fill=color, width=int(max(3, w * 0.08)))
        draw.line((cx, body_bottom, x0 + w * 0.15, y1), fill=color, width=int(max(3, w * 0.08)))
        draw.line((cx, body_bottom, x1 - w * 0.15, y1), fill=color, width=int(max(3, w * 0.08)))
    else:
        _draw_wobbly_line(draw, (cx, body_top), (cx, body_bottom), rng, amount, fill=outline, width=3)
        _draw_wobbly_line(draw, (x0 + w * 0.15, body_top + (body_bottom - body_top) * 0.35),
                           (x1 - w * 0.15, body_top + (body_bottom - body_top) * 0.35), rng, amount, fill=outline, width=3)
        _draw_wobbly_line(draw, (cx, body_bottom), (x0 + w * 0.15, y1), rng, amount, fill=outline, width=3)
        _draw_wobbly_line(draw, (cx, body_bottom), (x1 - w * 0.15, y1), rng, amount, fill=outline, width=3)


def _shield(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    pts = [
        (x0 + w * 0.5, y0),
        (x1, y0 + h * 0.22),
        (x1, y0 + h * 0.55),
        (x0 + w * 0.5, y1),
        (x0, y0 + h * 0.55),
        (x0, y0 + h * 0.22),
    ]
    if style == "icon":
        draw.polygon(pts, fill=color)
    else:
        _wobbly_polygon(draw, pts, rng, amount=max(2.0, w * 0.02), width=3)


def _folder(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    tab = [(x0, y0 + h * 0.12), (x0 + w * 0.35, y0 + h * 0.12), (x0 + w * 0.45, y0), (x0 + w * 0.8, y0),
           (x0 + w * 0.8, y0 + h * 0.12)]
    body = [(x0, y0 + h * 0.12), (x1, y0 + h * 0.12), (x1, y1), (x0, y1)]
    if style == "icon":
        draw.polygon(body, fill=color)
        draw.polygon(tab, fill=color)
    else:
        amount = max(2.0, w * 0.02)
        _wobbly_polygon(draw, body, rng, amount, width=3)
        _wobbly_polygon(draw, tab, rng, amount, width=3)


def _tray(draw: ImageDraw.ImageDraw, bbox, color, style: str, rng: random.Random):
    """Fila de mensagens: pilha de retângulos (mensagens numa fila)."""
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    n = 3
    gap = h * 0.08
    seg_h = (h - gap * (n - 1)) / n
    for i in range(n):
        yy0 = y0 + i * (seg_h + gap)
        yy1 = yy0 + seg_h
        box = (x0, yy0, x1, yy1)
        if style == "icon":
            draw.rounded_rectangle(box, radius=seg_h * 0.2, fill=color)
        else:
            pts = [(x0, yy0), (x1, yy0), (x1, yy1), (x0, yy1)]
            _wobbly_polygon(draw, pts, rng, amount=max(1.5, w * 0.015), width=2)


_SHAPE_FN = {
    "box": _rounded_rect,
    "cylinder": _cylinder,
    "cloud": _cloud,
    "actor": _actor,
    "shield": _shield,
    "folder": _folder,
    "tray": _tray,
}

_real_icon_cache: dict[str, list[Path]] = {}


def _real_icon_for(class_name: str) -> Path | None:
    if class_name not in _real_icon_cache:
        d = ASSETS_DIR / class_name
        _real_icon_cache[class_name] = sorted(d.glob("*.png")) if d.is_dir() else []
    candidates = _real_icon_cache[class_name]
    return random.choice(candidates) if candidates else None


def render_icon(img: Image.Image, class_name: str, bbox: tuple[float, float, float, float],
                 style: str, rng: random.Random) -> None:
    """Desenha o ícone da classe dentro de bbox=(x0,y0,x1,y1), na imagem RGBA `img`.

    Usa um ícone real do usuário em assets/icons/<classe>/ se existir; senão
    desenha proceduralmente via PIL (ver CLASS_SHAPE / _SHAPE_FN acima).
    """
    real_icon = _real_icon_for(class_name)
    if real_icon is not None:
        x0, y0, x1, y1 = bbox
        size = (max(1, int(x1 - x0)), max(1, int(y1 - y0)))
        icon = Image.open(real_icon).convert("RGBA").resize(size, Image.LANCZOS)
        img.paste(icon, (int(x0), int(y0)), icon)
        return

    shape, color = CLASS_SHAPE[class_name]
    draw = ImageDraw.Draw(img)
    _SHAPE_FN[shape](draw, bbox, color, style, rng)
