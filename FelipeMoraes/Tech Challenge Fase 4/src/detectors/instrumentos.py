import os
import sys

import cv2

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ei, _ef, _es
from ultralytics import YOLO
import relatorio as _relatorio_module

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _group_segments(frames_list, gap=30):
    """Agrupa frames consecutivos (tolerância de `gap` frames) em segmentos (start, end)."""
    if not frames_list:
        return []
    segments = []
    start = frames_list[0]
    prev  = frames_list[0]
    for f in frames_list[1:]:
        if f - prev > gap:
            segments.append((start, prev))
            start = f
        prev = f
    segments.append((start, prev))
    return segments


class InstrumentosDetector(BaseDetector):
    """Identifica instrumentos cirúrgicos ginecológicos em vídeo — modo rastreamento."""

    MODEL_NAME = "instrument_detector"
    MODEL_FOLDER = "instrumentos"
    CLASSES = [0, 1, 2, 3]
    NAMES_PTBR = {
        0: "Pinca Grasper",
        1: "Tesoura",
        2: "Pinca Bipolar",
        3: "Gancho",
    }
    DATASET_YAML = "download_dataset/dataset_instrumentos.yaml"

    EPOCHS     = _ei("INST_TRAIN_EPOCHS",     _ei("TRAIN_EPOCHS", 100))
    IMGSZ      = _ei("INST_TRAIN_IMGSZ",      _ei("TRAIN_IMGSZ", 640))
    BATCH      = _ei("INST_TRAIN_BATCH",      _ei("TRAIN_BATCH", 8))
    PATIENCE   = _ei("INST_TRAIN_PATIENCE",   _ei("TRAIN_PATIENCE", 20))
    BASE_MODEL = _es("INST_TRAIN_BASE_MODEL", _es("TRAIN_BASE_MODEL", "yolov8m.pt"))

    CONFIDENCE_THRESHOLD = _ef("INST_CONFIDENCE", 0.55)
    MIN_ASPECT_RATIO     = _ef("INST_MIN_ASPECT", 1.0)

    # ── HUD personalizado ────────────────────────────────────────────────────

    def _draw_instruments_hud(self, frame, frame_count, current_counts):
        n = len(self.NAMES_PTBR)
        hud_h = 38 + n * 28
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (310, hud_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        total = sum(current_counts.values())
        cv2.putText(frame, f"Frame: {frame_count}   Total: {total}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        y = 53
        for cls_id in sorted(self.NAMES_PTBR):
            name  = self.NAMES_PTBR[cls_id]
            count = current_counts.get(cls_id, 0)
            color = (0, 220, 80) if count > 0 else (70, 70, 70)
            cv2.putText(frame, f"{name}: {count}",
                        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)
            y += 28

    # ── Detecção principal ───────────────────────────────────────────────────

    def detect_video(self, video_path, model_path=None, headless=False, save_output=True):
        self._history = []

        if not os.path.exists(video_path):
            print(f"Vídeo não encontrado: {video_path}")
            return

        if model_path is None:
            model_path = self.find_model()
            if model_path:
                print(f"Usando modelo: {model_path}")
            else:
                print(f"ERRO: Nenhum modelo treinado encontrado para [{self.MODEL_NAME}].")
                print("Execute primeiro: python app.py train --mode instrumentos")
                return

        if not os.path.exists(model_path):
            print(f"ERRO: Modelo não encontrado: {model_path}")
            return

        try:
            model = YOLO(model_path)
            if len(model.names) == len(self.NAMES_PTBR):
                model.model.names = self.NAMES_PTBR
            else:
                print(f"AVISO: modelo tem {len(model.names)} classes, esperado {len(self.NAMES_PTBR)}.")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Não foi possível abrir o vídeo: {video_path}")
                return

            width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps    = cap.get(cv2.CAP_PROP_FPS) or 20

            saida_dir = os.path.join(_PROJECT_ROOT, "saida", self.MODEL_FOLDER)
            os.makedirs(saida_dir, exist_ok=True)

            out = None
            if save_output:
                out = cv2.VideoWriter(
                    os.path.join(saida_dir, "output.mp4"),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps, (width, height),
                )

            frame_count      = 0
            total_detections = 0
            # cls_id → lista de frames onde foi detectado
            class_frames: dict = {cls_id: [] for cls_id in self.NAMES_PTBR}

            print(f"Iniciando análise [{self.MODEL_NAME}] ...")
            print(f"Vídeo: {os.path.basename(video_path)} | {width}x{height} @ {fps:.1f}fps")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame is None or frame.size == 0:
                    continue

                frame_count += 1
                results = model(
                    frame,
                    conf=self.CONFIDENCE_THRESHOLD,
                    iou=self.IOU_THRESHOLD,
                    classes=self.CLASSES,
                    verbose=False,
                )
                results = self._filter_boxes(results, width, height, frame=frame)

                current_counts: dict = {cls_id: 0 for cls_id in self.NAMES_PTBR}
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes):
                        total_detections += len(boxes)
                        for cls_id in boxes.cls.cpu().numpy().astype(int).tolist():
                            if cls_id in current_counts:
                                current_counts[cls_id] += 1
                                class_frames[cls_id].append(frame_count)

                annotated = results[0].plot() if (results and len(results) > 0) else frame.copy()
                self._draw_instruments_hud(annotated, frame_count, current_counts)

                if out:
                    out.write(annotated)

                if not headless:
                    try:
                        cv2.imshow(f"Instrumentos — {self.MODEL_NAME}", annotated)
                        if cv2.waitKey(1) & 0xFF == 27:
                            break
                    except cv2.error:
                        headless = True

            cap.release()
            if out:
                out.release()
            if not headless:
                cv2.destroyAllWindows()

            # Construir timeline por instrumento
            instrument_timeline = {}
            class_summary_plain = {}
            for cls_id, frames_list in class_frames.items():
                name     = self.NAMES_PTBR[cls_id]
                segments = _group_segments(frames_list)
                instrument_timeline[name] = {
                    "count":       len(frames_list),
                    "first_frame": frames_list[0] if frames_list else None,
                    "last_frame":  frames_list[-1] if frames_list else None,
                    "frames_pct":  round(len(frames_list) / frame_count * 100, 1) if frame_count else 0.0,
                    "segments":    segments,
                }
                class_summary_plain[name] = {
                    "count":       len(frames_list),
                    "first_frame": frames_list[0] if frames_list else 0,
                    "last_frame":  frames_list[-1] if frames_list else 0,
                    "frames_pct":  round(len(frames_list) / frame_count * 100, 1) if frame_count else 0.0,
                }

            report_path = os.path.join(saida_dir, "relatorio.txt")
            _relatorio_module.generate_report(
                report_path, frame_count, total_detections, [],
                fps=fps, video_path=video_path, class_summary=class_summary_plain,
            )

            print(f"\n=== RESULTADO FINAL [{self.MODEL_NAME}] ===")
            print(f"Frames analisados : {frame_count}")
            print(f"Detecções totais  : {total_detections}")
            for name, info in instrument_timeline.items():
                if info["count"]:
                    print(f"  {name}: {info['count']} frames ({info['frames_pct']:.1f}%) "
                          f"— {len(info['segments'])} segmento(s)")
                else:
                    print(f"  {name}: não detectado")
            print(f"\nArquivos gerados em: saida/{self.MODEL_FOLDER}/")

            return {
                "frame_count":        frame_count,
                "detections_count":   total_detections,
                "anomalies":          [],
                "fps":                fps,
                "class_summary":      class_summary_plain,
                "instrument_timeline": instrument_timeline,
            }

        except Exception as e:
            print(f"Erro na detecção: {e}")
            raise
