import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ei, _ef, _es


class InstrumentosDetector(BaseDetector):
    """Detecta instrumentos cirúrgicos ginecológicos (bisturi, pinça, tesoura)."""

    MODEL_NAME = "instrument_detector"
    MODEL_FOLDER = "instrumentos"
    CLASSES = [0, 1, 2, 3]
    NAMES_PTBR = {
        0: "Pinca Grasper",
        1: "Gancho",
        2: "Tesoura",
        3: "Clipador",
    }
    DATASET_YAML = "download_dataset/dataset_instrumentos.yaml"

    EPOCHS     = _ei("INST_TRAIN_EPOCHS",     _ei("TRAIN_EPOCHS", 100))
    IMGSZ      = _ei("INST_TRAIN_IMGSZ",      _ei("TRAIN_IMGSZ", 640))
    BATCH      = _ei("INST_TRAIN_BATCH",      _ei("TRAIN_BATCH", 8))
    PATIENCE   = _ei("INST_TRAIN_PATIENCE",   _ei("TRAIN_PATIENCE", 20))
    BASE_MODEL = _es("INST_TRAIN_BASE_MODEL", _es("TRAIN_BASE_MODEL", "yolov8m.pt"))

    CONFIDENCE_THRESHOLD = _ef("INST_CONFIDENCE", 0.55)
    MIN_ASPECT_RATIO     = _ef("INST_MIN_ASPECT", 1.0)

    def _check_anomalies(self, frame_count, num_detections, avg_recent, no_streak):
        anomaly = None
        alert_text = ""
        alert_color = (0, 255, 0)

        if no_streak == self.ABSENCE_CRITICAL_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "CRÍTICO",
                f"Ausência prolongada de instrumentos ({no_streak} frames) — "
                "possível desvio de protocolo em cirurgia ginecológica"
            )
            alert_text = "ALERTA CRITICO: INSTRUMENTOS AUSENTES"
            alert_color = (0, 0, 200)
        elif no_streak == self.ABSENCE_WARN_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "ALTO",
                f"Instrumentos não identificados ({no_streak} frames) — "
                "verificar campo cirúrgico ginecológico"
            )
            alert_text = "ALERTA: AUSENCIA DE INSTRUMENTOS"
            alert_color = (0, 0, 255)
        elif num_detections > self.EXCESS_THRESHOLD:
            anomaly = self._make_anomaly(
                frame_count, "EXCESSO", "MÉDIO",
                f"Múltiplos instrumentos no campo ({num_detections}) — "
                "verificar controle de contagem em procedimento ginecológico"
            )
            alert_text = f"ALERTA: EXCESSO DE INSTRUMENTOS ({num_detections})"
            alert_color = (0, 165, 255)
        elif len(self._history) >= self.WINDOW:
            delta = abs(num_detections - avg_recent)
            if delta > self.VARIATION_THRESHOLD:
                anomaly = self._make_anomaly(
                    frame_count, "VARIAÇÃO", "MÉDIO",
                    f"Variação brusca de instrumentos (delta={delta:.1f}, média={avg_recent:.1f}) — "
                    "possível manobra não planejada em cirurgia ginecológica"
                )
                alert_text = "ANOMALIA: VARIACAO DE INSTRUMENTOS"
                alert_color = (255, 0, 255)

        return anomaly, alert_text, alert_color
