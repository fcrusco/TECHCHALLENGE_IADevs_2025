import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ef, _ei


class SangramentoDetector(BaseDetector):
    """Detecta sangramento anômalo durante procedimentos cirúrgicos/endoscópicos."""

    MODEL_NAME = "bleeding_detector"
    MODEL_FOLDER = "sangramento"
    CLASSES = [0]
    NAMES_PTBR = {0: "Sangramento"}
    DATASET_YAML = "download_dataset/dataset_sangramento.yaml"

    CONFIDENCE_THRESHOLD = _ef("BLEED_CONFIDENCE", 0.45)
    MIN_ASPECT_RATIO     = _ef("BLEED_MIN_ASPECT", 1.0)
    MAX_BOX_AREA_RATIO   = _ef("BLEED_MAX_BOX_AREA", 0.80)

    BLEEDING_WARN_FRAMES     = _ei("BLEED_WARN_FRAMES", 5)
    BLEEDING_CRITICAL_FRAMES = _ei("BLEED_CRITICAL_FRAMES", 15)

    EXCESS_THRESHOLD = 9999

    def _bleeding_streak(self):
        streak = 0
        for v in reversed(self._history):
            if v > 0:
                streak += 1
            else:
                break
        return streak

    def _check_anomalies(self, frame_count, num_detections, avg_recent, no_streak):
        anomaly = None
        alert_text = ""
        alert_color = (0, 255, 0)

        streak = self._bleeding_streak()

        if streak >= self.BLEEDING_CRITICAL_FRAMES:
            if streak == self.BLEEDING_CRITICAL_FRAMES:
                anomaly = self._make_anomaly(
                    frame_count, "SANGRAMENTO", "CRÍTICO",
                    f"Sangramento persistente ({streak} frames consecutivos) — "
                    "intervenção imediata necessária"
                )
            alert_text = f"ALERTA CRITICO: SANGRAMENTO ({streak}q)"
            alert_color = (0, 0, 200)

        elif streak >= self.BLEEDING_WARN_FRAMES:
            if streak == self.BLEEDING_WARN_FRAMES:
                anomaly = self._make_anomaly(
                    frame_count, "SANGRAMENTO", "ALTO",
                    f"Sangramento contínuo detectado ({streak} frames consecutivos) — "
                    "monitorar e avaliar intervenção"
                )
            alert_text = f"ALERTA: SANGRAMENTO CONTINUO ({streak}q)"
            alert_color = (0, 0, 255)

        elif num_detections > 0 and streak == 1:
            anomaly = self._make_anomaly(
                frame_count, "SANGRAMENTO", "MÉDIO",
                "Sangramento detectado no campo cirúrgico — aguardando confirmação"
            )
            alert_text = "ATENCAO: SANGRAMENTO DETECTADO"
            alert_color = (0, 165, 255)

        return anomaly, alert_text, alert_color

    def _draw_hud(self, frame, frame_count, num_detections, avg_recent, alert_text, alert_color, height):
        import cv2
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (370, 110), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        streak = self._bleeding_streak()
        det_color = (0, 0, 255) if num_detections > 0 else (0, 200, 0)
        cv2.putText(frame, f"Sangramento: {'SIM' if num_detections > 0 else 'NAO'}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, det_color, 2)
        cv2.putText(frame, f"Consecutivos: {streak}q", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, f"Quadro: {frame_count}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (160, 160, 160), 2)

        if alert_text:
            cv2.rectangle(frame, (0, height - 50), (frame.shape[1], height), (0, 0, 0), -1)
            cv2.putText(frame, alert_text, (10, height - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, alert_color, 3)
