import os
import urllib.request

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

def get_face_landmarker_model(filename="face_landmarker.task"):
    """Verifica si el modelo existe en src/; si no, lo descarga y devuelve su ruta absoluta."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, filename)

    if not os.path.exists(model_path):
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
        print("Download completed.")

    return model_path
