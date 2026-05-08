import os
import sys

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from detectors.base import BaseDetector, _ef


class InstrumentDetector(BaseDetector):
    """Detects gynecological surgical instruments (scalpel, clamp, scissors)."""

    MODEL_NAME = "instrument_detector"
    MODEL_FOLDER = "instrumentos"
    CLASSES = [0, 1, 2, 3]
    NAMES_PTBR = {
        0: "Bisturi",
        1: "Pinca de Dissecao",
        2: "Tesoura Mayo Reta",
        3: "Tesoura Mayo Curva",
    }
    DATASET_YAML = "download_dataset/dataset_instrumentos.yaml"

    CONFIDENCE_THRESHOLD = _ef("INST_CONFIDENCE", 0.55)
    MIN_ASPECT_RATIO     = _ef("INST_MIN_ASPECT", 1.5)
