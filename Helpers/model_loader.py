import urllib.request
from pathlib import Path
from Helpers.logger import get_logger

logger = get_logger(__name__)

MODEL_URL = (
    "https://googleapis.com"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# Guarda el modelo en la raíz del proyecto (FaceCursor/face_landmarker.task)
MODEL_PATH = Path(__file__).resolve().parent.parent / "Helpers/face_landmarker.task"


def get_face_landmarker_model():
    """Verifica si existe face_landmarker.task localmente o lo descarga desde MediaPipe."""
    if MODEL_PATH.exists():
        file_size_mb = MODEL_PATH.stat().st_size / (1024 * 1024)
        if file_size_mb > 0.1:
            logger.debug(f"Found cached MediaPipe model at {MODEL_PATH} ({file_size_mb:.2f} MB).")
            return str(MODEL_PATH)
        else:
            logger.warning(f"Cached model at {MODEL_PATH} appears empty or corrupted ({file_size_mb:.2f} MB). Re-downloading...")

    logger.info(f"Downloading MediaPipe FaceLandmarker model from {MODEL_URL}...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        file_size_mb = MODEL_PATH.stat().st_size / (1024 * 1024)
        logger.info(f"Model downloaded successfully to {MODEL_PATH} ({file_size_mb:.2f} MB).")
        return str(MODEL_PATH)
    except Exception as e:
        logger.error(f"Failed to download MediaPipe FaceLandmarker model: {e}")
        raise
