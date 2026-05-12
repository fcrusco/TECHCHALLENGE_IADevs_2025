import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ef, _ei


class AreasCriticasDetector(BaseDetector):
    """Detecta áreas anatômicas críticas em cirurgias ginecológicas (ovário, mama)."""

    MODEL_NAME = "critical_areas_detector"
    MODEL_FOLDER = "areas_criticas"
    CLASSES = [0, 1]
    NAMES_PTBR = {
        0: "Ovario",
        1: "Mama",
    }
    DATASET_YAML = "download_dataset/dataset_areas_criticas.yaml"

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
                f"Estruturas anatômicas ausentes ({no_streak} frames) — "
                "possível perda de campo visual ou complicação grave"
            )
            alert_text = "ALERTA CRITICO: ESTRUTURA NAO VISIVEL"
            alert_color = (0, 0, 200)
        elif no_streak == self.ABSENCE_WARN_FRAMES:
            anomaly = self._make_anomaly(
                frame_count, "AUSÊNCIA", "ALTO",
                f"Estruturas anatômicas não identificadas ({no_streak} frames) — "
                "verificar posicionamento da câmera"
            )
            alert_text = "ALERTA: ESTRUTURA AUSENTE"
            alert_color = (0, 0, 255)
        elif num_detections > self.EXCESS_THRESHOLD:
            anomaly = self._make_anomaly(
                frame_count, "EXCESSO", "MÉDIO",
                f"Múltiplas estruturas detectadas ({num_detections}) — "
                "verificar campo cirúrgico e possível confusão de estruturas"
            )
            alert_text = f"ALERTA: MULTIPLAS ESTRUTURAS ({num_detections})"
            alert_color = (0, 165, 255)
        elif len(self._history) >= self.WINDOW:
            delta = abs(num_detections - avg_recent)
            if delta > self.VARIATION_THRESHOLD:
                anomaly = self._make_anomaly(
                    frame_count, "VARIAÇÃO", "MÉDIO",
                    f"Variação na visibilidade de estruturas (delta={delta:.1f}, média={avg_recent:.1f}) — "
                    "possível mudança de campo ou movimento brusco"
                )
                alert_text = "ANOMALIA: VARIACAO DE CAMPO"
                alert_color = (255, 0, 255)

        return anomaly, alert_text, alert_color
