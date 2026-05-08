import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ef, _ei


class SelfHarmDetector(BaseDetector):
    """Detects suspicious sharp objects or weapons that may indicate self-harm risk."""

    MODEL_NAME = "selfharm_detector"
    MODEL_FOLDER = "automutilacao"
    CLASSES = [0, 1]
    NAMES_PTBR = {
        0: "Faca_Lamina",
        1: "Arma_Fogo",
    }
    DATASET_YAML = "download_dataset/dataset_automutilacao.yaml"
    BASE_MODEL = "yolov8s.pt"

    CONFIDENCE_THRESHOLD = _ef("HARM_CONFIDENCE", 0.40)
    MIN_ASPECT_RATIO     = _ef("HARM_MIN_ASPECT", 1.0)
    MAX_BOX_AREA_RATIO   = _ef("HARM_MAX_BOX_AREA", 0.75)

    OBJECT_WARN_FRAMES     = _ei("HARM_WARN_FRAMES", 3)
    OBJECT_CRITICAL_FRAMES = _ei("HARM_CRITICAL_FRAMES", 8)

    ABSENCE_WARN_FRAMES     = 999999
    ABSENCE_CRITICAL_FRAMES = 999999
    EXCESS_THRESHOLD        = 9999

    def _object_streak(self):
        streak = 0
        for v in reversed(self._history):
            if v > 0:
                streak += 1
            else:
                break
        return streak

    def _has_gun(self, results):
        if not results or len(results) == 0:
            return False
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return False
        cls_ids = boxes.cls.cpu().numpy().astype(int).tolist()
        return 1 in cls_ids

    def _check_anomalies(self, frame_count, num_detections, avg_recent, no_streak):
        anomaly = None
        alert_text = ""
        alert_color = (0, 255, 0)

        # Gun detected = immediate CRITICAL regardless of streak
        if hasattr(self, "_current_results") and self._has_gun(self._current_results):
            anomaly = self._make_anomaly(
                frame_count, "ARMA_DETECTADA", "CRÍTICO",
                "Arma de fogo detectada no campo — protocolo de segurança imediato"
            )
            alert_text = "ALERTA CRITICO: ARMA DETECTADA"
            alert_color = (0, 0, 180)
            return anomaly, alert_text, alert_color

        streak = self._object_streak()

        if streak >= self.OBJECT_CRITICAL_FRAMES:
            if streak == self.OBJECT_CRITICAL_FRAMES:
                anomaly = self._make_anomaly(
                    frame_count, "OBJETO_SUSPEITO", "CRÍTICO",
                    f"Objeto cortante persistente ({streak} frames consecutivos) — "
                    "acionar segurança imediatamente"
                )
            alert_text = f"ALERTA CRITICO: OBJETO SUSPEITO ({streak}q)"
            alert_color = (0, 0, 200)

        elif streak >= self.OBJECT_WARN_FRAMES:
            if streak == self.OBJECT_WARN_FRAMES:
                anomaly = self._make_anomaly(
                    frame_count, "OBJETO_SUSPEITO", "ALTO",
                    f"Objeto suspeito detectado por {streak} frames consecutivos — verificar paciente"
                )
            alert_text = f"ALERTA: OBJETO SUSPEITO ({streak}q)"
            alert_color = (0, 0, 255)

        elif num_detections > 0 and streak == 1:
            anomaly = self._make_anomaly(
                frame_count, "OBJETO_SUSPEITO", "MÉDIO",
                "Objeto cortante detectado no campo cirúrgico — aguardando confirmação"
            )
            alert_text = "ATENCAO: OBJETO SUSPEITO DETECTADO"
            alert_color = (0, 165, 255)

        return anomaly, alert_text, alert_color

    def detect_video(self, video_path, model_path=None, headless=False, save_output=True):
        self._current_results = None
        super().detect_video(video_path, model_path, headless, save_output)

    def _draw_hud(self, frame, frame_count, num_detections, avg_recent, alert_text, alert_color, height):
        import cv2
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (400, 110), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        streak = self._object_streak()
        det_color = (0, 0, 255) if num_detections > 0 else (0, 200, 0)
        status = f"Obj. Suspeito: {'SIM' if num_detections > 0 else 'NAO'}"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, det_color, 2)
        cv2.putText(frame, f"Consecutivos: {streak}q", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, f"Quadro: {frame_count}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 160, 160), 2)

        if alert_text:
            bar_h = 50
            cv2.rectangle(frame, (0, height - bar_h), (frame.shape[1], height), (0, 0, 0), -1)
            cv2.putText(frame, alert_text, (10, height - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, alert_color, 3)
