import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ei, _ef, _es


class AreasCriticasDetector(BaseDetector):
    """Detecta áreas anatômicas críticas em cirurgias ginecológicas (ovário, mama)."""

    MODEL_NAME = "critical_areas_detector"
    MODEL_FOLDER = "areas_criticas"
    CLASSES = [0, 1, 2]
    NAMES_PTBR = {
        0: "Utero",
        1: "Tuba Uterina",
        2: "Ovario",
    }
    DATASET_YAML = "download_dataset/dataset_areas_criticas.yaml"

    EPOCHS     = _ei("AREAS_TRAIN_EPOCHS",     _ei("TRAIN_EPOCHS", 100))
    IMGSZ      = _ei("AREAS_TRAIN_IMGSZ",      _ei("TRAIN_IMGSZ", 640))
    BATCH      = _ei("AREAS_TRAIN_BATCH",      _ei("TRAIN_BATCH", 8))
    PATIENCE   = _ei("AREAS_TRAIN_PATIENCE",   _ei("TRAIN_PATIENCE", 20))
    BASE_MODEL = _es("AREAS_TRAIN_BASE_MODEL", _es("TRAIN_BASE_MODEL", "yolov8m.pt"))

    CONFIDENCE_THRESHOLD = _ef("AREAS_CONFIDENCE", 0.50)
    MIN_ASPECT_RATIO     = _ef("AREAS_MIN_ASPECT", 1.0)
    MAX_BOX_AREA_RATIO   = _ef("AREAS_MAX_BOX_AREA", 0.65)
    EXCESS_THRESHOLD     = _ei("AREAS_EXCESS", 2)

    def _check_anomalies(self, frame_count, num_detections, avg_recent, no_streak):
        anomaly = None
        alert_text = ""
        alert_color = (0, 255, 0)

        if no_streak == self.ABSENCE_CRITICAL_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "CRÍTICO",
                f"Estruturas ginecológicas não identificadas ({no_streak} frames) — "
                "possível desvio de procedimento obstétrico ou complicação grave"
            )
            alert_text = "ALERTA CRITICO: ESTRUTURA NAO VISIVEL"
            alert_color = (0, 0, 200)
        elif no_streak == self.ABSENCE_WARN_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "ALTO",
                f"Estruturas ginecológicas ausentes ({no_streak} frames) — "
                "verificar campo cirúrgico e protocolo obstétrico"
            )
            alert_text = "ALERTA: ESTRUTURA AUSENTE"
            alert_color = (0, 0, 255)
        elif num_detections > self.EXCESS_THRESHOLD:
            anomaly = self._make_anomaly(
                frame_count, "EXCESSO", "MÉDIO",
                f"Múltiplas estruturas detectadas ({num_detections}) — "
                "revisar campo obstétrico e possível confusão anatômica"
            )
            alert_text = f"ALERTA: MULTIPLAS ESTRUTURAS ({num_detections})"
            alert_color = (0, 165, 255)
        elif len(self._history) >= self.WINDOW:
            delta = abs(num_detections - avg_recent)
            if delta > self.VARIATION_THRESHOLD:
                anomaly = self._make_anomaly(
                    frame_count, "VARIAÇÃO", "MÉDIO",
                    f"Variação inesperada de estruturas (delta={delta:.1f}, média={avg_recent:.1f}) — "
                    "possível complicação em procedimento ginecológico"
                )
                alert_text = "ANOMALIA: VARIACAO DE CAMPO"
                alert_color = (255, 0, 255)

        return anomaly, alert_text, alert_color
