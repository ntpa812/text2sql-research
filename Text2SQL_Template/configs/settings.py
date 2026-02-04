import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

NER_MODEL_PATH = BASE_DIR / "weights" / "ner_ver2"
