import importlib.util
import os
import shutil
import sys

import gc
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# NumPy 2.0 removeu np.trapz — restaura alias para compatibilidade com Ultralytics
if not hasattr(np, "trapz"):
    np.trapz = np.trapezoid

# PyTorch 2.6+ mudou o padrão de torch.load para weights_only=True,
# quebrando arquivos .pt do Ultralytics. Restaura o comportamento anterior
# apenas quando weights_only não é passado explicitamente.
try:
    import functools as _functools
    _orig_load = torch.load

    @_functools.wraps(_orig_load)
    def _patched_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig_load(*args, **kwargs)

    torch.load = _patched_load
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import relatorio as _relatorio_module

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass


def _ei(key, default):
    v = os.getenv(key)
    return int(v) if v is not None else default


def _ef(key, default):
    v = os.getenv(key)
    return float(v) if v is not None else default


def _es(key, default):
    return os.getenv(key, default)


class BaseDetector:
    MODEL_NAME: str = None
    MODEL_FOLDER: str = None  # PT-BR folder name inside model/
    CLASSES: list = None
    NAMES_PTBR: dict = None
    DATASET_YAML: str = None
    BASE_MODEL: str = _es("TRAIN_BASE_MODEL", "yolov8s.pt")

    CONFIDENCE_THRESHOLD = _ef("DETECT_CONFIDENCE", 0.55)
    IOU_THRESHOLD        = _ef("DETECT_IOU", 0.45)
    WINDOW               = _ei("DETECT_WINDOW", 10)

    ABSENCE_WARN_FRAMES     = _ei("ANOMALY_ABSENCE_WARN", 10)
    ABSENCE_CRITICAL_FRAMES = _ei("ANOMALY_ABSENCE_CRITICAL", 30)
    EXCESS_THRESHOLD        = _ei("ANOMALY_EXCESS", 5)
    VARIATION_THRESHOLD     = _ei("ANOMALY_VARIATION", 3)

    MIN_BOX_AREA_RATIO    = _ef("FILTER_MIN_BOX_AREA", 0.002)
    MAX_BOX_AREA_RATIO    = _ef("FILTER_MAX_BOX_AREA", 0.50)
    MIN_ASPECT_RATIO      = _ef("FILTER_MIN_ASPECT", 1.5)
    EDGE_MARGIN_RATIO     = _ef("FILTER_EDGE_MARGIN", 0.04)
    OVERLAY_ZONE_TOP      = _ef("FILTER_OVERLAY_TOP", 0.22)
    OVERLAY_ZONE_BOTTOM   = _ef("FILTER_OVERLAY_BOTTOM", 0.80)
    # Filtro anti-banner de texto: rejeita caixas muito largas e rasas
    MAX_BANNER_WH_RATIO   = _ef("FILTER_BANNER_WH", 4.0)
    MAX_BANNER_H_RATIO    = _ef("FILTER_BANNER_H", 0.08)

    EPOCHS   = _ei("TRAIN_EPOCHS", 80)
    IMGSZ    = _ei("TRAIN_IMGSZ", 640)
    BATCH    = _ei("TRAIN_BATCH", 16)
    PATIENCE = _ei("TRAIN_PATIENCE", 20)

    def __init__(self):
        self._history = []

    def find_model(self):
        folder = self.MODEL_FOLDER
        candidates = [
            os.path.join(PROJECT_ROOT, "model", folder, "weights", "best.pt"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def train(self):
        dataset_yaml = os.path.join(PROJECT_ROOT, self.DATASET_YAML)
        if not os.path.exists(dataset_yaml):
            print(f"dataset YAML não encontrado: {dataset_yaml}")
            return

        model_dir = os.path.join(PROJECT_ROOT, "model")
        output_dir = os.path.join(model_dir, self.MODEL_FOLDER)
        if os.path.exists(output_dir):
            print(f"Limpando treino anterior: {output_dir}")
            shutil.rmtree(output_dir)

        model = None
        try:
            print(f"Iniciando treinamento [{self.MODEL_FOLDER}] ...")
            model = YOLO(self.BASE_MODEL)
            model.train(
                data=dataset_yaml,
                epochs=self.EPOCHS,
                imgsz=self.IMGSZ,
                batch=self.BATCH,
                patience=self.PATIENCE,
                device=_es("TRAIN_DEVICE", "0"),
                name=self.MODEL_FOLDER,
                project=model_dir,
                exist_ok=True,
            )
            print(f"Treinamento concluído!")
            print(f"Modelo: {os.path.join(output_dir, 'weights', 'best.pt')}")
        except Exception as e:
            print(f"Erro no treinamento: {e}")
        finally:
            del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

    def _filter_boxes(self, results, frame_w, frame_h):
        if not results or len(results) == 0:
            return results
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return results

        frame_area = frame_w * frame_h
        edge_x = frame_w * self.EDGE_MARGIN_RATIO
        edge_y = frame_h * self.EDGE_MARGIN_RATIO
        xyxy = boxes.xyxy.cpu().numpy()

        keep = []
        for i, (x1, y1, x2, y2) in enumerate(xyxy):
            w = float(x2 - x1)
            h = float(y2 - y1)
            cy = (y1 + y2) / 2.0
            area_ratio = (w * h) / frame_area
            aspect = max(w, h) / max(min(w, h), 1.0)

            if area_ratio < self.MIN_BOX_AREA_RATIO:
                continue
            if area_ratio > self.MAX_BOX_AREA_RATIO:
                continue
            if aspect < self.MIN_ASPECT_RATIO:
                continue
            # Borda do frame (margem assimétrica X/Y para capturar logos de canto)
            if x1 < edge_x or x2 > frame_w - edge_x:
                continue
            if y1 < edge_y or y2 > frame_h - edge_y:
                continue
            # Zona de overlay (HUD/título): qualquer orientação
            in_overlay = cy < frame_h * self.OVERLAY_ZONE_TOP or cy > frame_h * self.OVERLAY_ZONE_BOTTOM
            if in_overlay:
                continue
            # Banner de texto: caixa muito larga e rasa (legenda, título, watermark)
            wh_ratio = w / max(h, 1.0)
            if wh_ratio > self.MAX_BANNER_WH_RATIO and h / frame_h < self.MAX_BANNER_H_RATIO:
                continue
            keep.append(i)

        results[0].boxes = results[0].boxes[keep]
        return results

    def _make_anomaly(self, frame, atype, severity, description):
        return {"frame": frame, "type": atype, "severity": severity, "description": description}

    def _check_anomalies(self, frame_count, num_detections, avg_recent, no_streak):
        anomaly = None
        alert_text = ""
        alert_color = (0, 255, 0)

        if no_streak == self.ABSENCE_CRITICAL_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "CRÍTICO",
                f"Ausência crítica ({no_streak} frames consecutivos) — possível falha de controle cirúrgico"
            )
            alert_text = "ALERTA CRITICO: AUSENCIA PROLONGADA"
            alert_color = (0, 0, 200)
        elif no_streak == self.ABSENCE_WARN_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "ALTO",
                f"Ausência prolongada ({no_streak} frames consecutivos) — possível troca não registrada"
            )
            alert_text = "ALERTA: AUSENCIA PROLONGADA"
            alert_color = (0, 0, 255)
        elif num_detections > self.EXCESS_THRESHOLD:
            anomaly = self._make_anomaly(
                frame_count, "EXCESSO", "MÉDIO",
                f"Excesso no campo cirúrgico ({num_detections} detectados) — verificar controle"
            )
            alert_text = f"ALERTA: EXCESSO ({num_detections})"
            alert_color = (0, 165, 255)
        elif len(self._history) >= self.WINDOW:
            delta = abs(num_detections - avg_recent)
            if delta > self.VARIATION_THRESHOLD:
                anomaly = self._make_anomaly(
                    frame_count, "VARIAÇÃO", "MÉDIO",
                    f"Variação brusca (delta={delta:.1f}, média={avg_recent:.1f}) — possível manobra não planejada"
                )
                alert_text = "ANOMALIA: VARIACAO BRUSCA"
                alert_color = (255, 0, 255)

        return anomaly, alert_text, alert_color

    def _draw_hud(self, frame, frame_count, num_detections, avg_recent, alert_text, alert_color, height):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (340, 110), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        det_color = (0, 255, 0) if num_detections > 0 else (80, 80, 80)
        cv2.putText(frame, f"Detectados: {num_detections}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, det_color, 2)
        cv2.putText(frame, f"Media (10q): {avg_recent:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, f"Quadro: {frame_count}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 160, 160), 2)

        if alert_text:
            bar_h = 50
            cv2.rectangle(frame, (0, height - bar_h), (frame.shape[1], height), (0, 0, 0), -1)
            cv2.putText(frame, alert_text, (10, height - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, alert_color, 3)

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
                print(f"Execute primeiro: python app.py train --mode {self._cli_mode()}")
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
                print(f"  Classes do modelo: {model.names}")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Não foi possível abrir o vídeo: {video_path}")
                return

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 20

            saida_dir = os.path.join(PROJECT_ROOT, "saida", self.MODEL_FOLDER)
            os.makedirs(saida_dir, exist_ok=True)

            out = None
            if save_output:
                output_video = os.path.join(saida_dir, "output.mp4")
                out = cv2.VideoWriter(
                    output_video,
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps,
                    (width, height),
                )

            frame_count = 0
            detections_count = 0
            anomalies = []
            no_streak = 0
            class_frames = {}

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
                results = self._filter_boxes(results, width, height)

                num_detections = 0
                if results and len(results) > 0:
                    boxes = results[0].boxes
                    if boxes is not None and len(boxes):
                        num_detections = len(boxes)
                        detections_count += num_detections
                        for cls_id in boxes.cls.cpu().numpy().astype(int).tolist():
                            cls_name = self.NAMES_PTBR.get(cls_id, str(cls_id))
                            class_frames.setdefault(cls_name, []).append(frame_count)

                self._history.append(num_detections)
                if len(self._history) > self.WINDOW:
                    self._history.pop(0)

                avg_recent = sum(self._history) / len(self._history)

                if num_detections == 0:
                    no_streak += 1
                else:
                    no_streak = 0

                anomaly, alert_text, alert_color = self._check_anomalies(
                    frame_count, num_detections, avg_recent, no_streak
                )
                if anomaly:
                    anomalies.append(anomaly)

                annotated_frame = results[0].plot() if (results and len(results) > 0) else frame.copy()
                self._draw_hud(annotated_frame, frame_count, num_detections, avg_recent, alert_text, alert_color, height)

                if out:
                    out.write(annotated_frame)

                if not headless:
                    try:
                        cv2.imshow(f"Análise — {self.MODEL_NAME}", annotated_frame)
                        if cv2.waitKey(1) & 0xFF == 27:
                            break
                    except cv2.error:
                        headless = True  # GUI indisponível — continua sem janela

            cap.release()
            if out:
                out.release()
            if not headless:
                cv2.destroyAllWindows()

            avg = detections_count / frame_count if frame_count > 0 else 0
            anomaly_rate = (len(anomalies) / frame_count) * 100 if frame_count > 0 else 0

            class_summary = {}
            for name, frames in class_frames.items():
                class_summary[name] = {
                    "count": len(frames),
                    "first_frame": frames[0],
                    "last_frame": frames[-1],
                    "frames_pct": round(len(frames) / frame_count * 100, 1) if frame_count else 0,
                }

            report_path = os.path.join(saida_dir, "relatorio.txt")
            _relatorio_module.generate_report(
                report_path, frame_count, detections_count, anomalies,
                fps=fps, video_path=video_path, class_summary=class_summary
            )

            print(f"\n=== RESULTADO FINAL [{self.MODEL_NAME}] ===")
            print(f"Frames analisados: {frame_count}")
            print(f"Detecções totais:  {detections_count}")
            print(f"Média por frame:   {avg:.2f}")
            print(f"Anomalias:         {len(anomalies)}")
            print(f"Taxa de anomalia:  {anomaly_rate:.2f}%")
            print(f"\nArquivos gerados em: saida/{self.MODEL_FOLDER}/")
            print(f"  Vídeo anotado: output.mp4")
            print(f"  Relatório:     relatorio.txt/.html/.json")

            return {
                "frame_count": frame_count,
                "detections_count": detections_count,
                "anomalies": anomalies,
                "fps": fps,
                "class_summary": class_summary,
            }

        except Exception as e:
            print(f"Erro na detecção: {e}")
            raise

    def _cli_mode(self):
        mapping = {
            "instrument_detector": "instrumentos",
            "critical_areas_detector": "areas-criticas",
            "bleeding_detector": "sangramento",
            "selfharm_detector": "automutilacao",
        }
        return mapping.get(self.MODEL_NAME, self.MODEL_NAME)
