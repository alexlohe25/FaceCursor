import time
import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config.config_loader import load_config, save_calibration_bounds
from Helpers.logger import setup_logger, get_logger
from Helpers.model_loader import get_face_landmarker_model
from Helpers.calibration import (
    run_calibration,
    get_nose_position,
    get_blink_scores,
    draw_debug_landmarks,
)
from Helpers.eye_gestures import EyeGestureController
from Helpers.cursor_controller import NoseCursorController

pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()

# 1. Cargar configuración e inicializar el sistema de logging diario
config = load_config()
setup_logger(config)
logger = get_logger(__name__)

logger.info("=== Starting FaceCursor Session ===")
logger.info(f"Detected primary display resolution: {screen_w}x{screen_h}")

# 2. Inicializar MediaPipe FaceLandmarker con Blendshapes habilitados
try:
    model_path = get_face_landmarker_model()
    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO,
        output_face_blendshapes=True,
        num_faces=1,
    )
    detector = vision.FaceLandmarker.create_from_options(options)
    logger.info("MediaPipe FaceLandmarker initialized successfully in VIDEO mode.")
except Exception as e:
    logger.error(f"Critical failure initializing MediaPipe FaceLandmarker: {e}")
    raise

# 3. Abrir webcam
cam_idx = config["app"]["camera_index"]
cap = cv2.VideoCapture(cam_idx)
if not cap.isOpened():
    logger.error(f"Unable to open webcam at camera_index={cam_idx}. Exiting application.")
    raise RuntimeError(f"Cannot open camera index {cam_idx}")
logger.info(f"Webcam opened successfully (camera_index={cam_idx}).")

# 4. Inicializar controladores modulares desde config/config.json
cursor = NoseCursorController(screen_w, screen_h, config)
gestures = EyeGestureController(config)
show_debug = config["app"]["show_debug_on_start"]
reload_banner_until = 0.0
face_lost = False


def calibrate_system():
    min_x, max_x, min_y, max_y = run_calibration(
        cap, detector, screen_w, screen_h, cursor.min_range, cursor.max_range
    )
    cursor.set_calibration_bounds(min_x, max_x, min_y, max_y)
    save_calibration_bounds(min_x, max_x, min_y, max_y)
    gestures.reset()


def reload_config():
    """Recarga config/config.json en vivo (incluyendo nivel de logging) sin reiniciar."""
    global config, reload_banner_until
    try:
        config = load_config()
        setup_logger(config)
        cursor.load_settings(config)
        gestures.load_settings(config)
        reload_banner_until = time.time() + 1.5
        logger.info("Hot-reloaded settings from config/config.json (key 'R').")
    except Exception as e:
        logger.error(f"Failed to hot-reload config/config.json: {e}")


def draw_hud(frame, blink_l, blink_r):
    cv2.putText(
        frame,
        f"Blink L: {blink_l:.2f} | Blink R: {blink_r:.2f}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2,
    )

    if gestures.anchor_mode == "LEFT":
        cv2.putText(
            frame,
            f"ANCHOR: LEFT (Right 2x wink = Right Click) [{len(gestures.wink_timestamps)}/2]",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 165, 255),
            2,
        )
    elif gestures.anchor_mode == "RIGHT":
        cv2.putText(
            frame,
            f"ANCHOR: RIGHT (Left 2x wink = Left Click) [{len(gestures.wink_timestamps)}/2]",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 165, 255),
            2,
        )

    if gestures.both_blink_count > 0:
        cv2.putText(
            frame,
            f"Both-Eye Blinks: {gestures.both_blink_count} (3=Calibrate, 5=Exit)",
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2,
        )

    if time.time() - gestures.last_click_time < 0.8:
        cv2.putText(
            frame,
            gestures.last_click_label,
            (20, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            3,
        )

    if time.time() < reload_banner_until:
        cv2.putText(
            frame,
            "CONFIG RELOADED!",
            (20, 185),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 0),
            2,
        )


# Calibración inicial solo si aún no hay límites guardados
if not config["calibration"]["is_calibrated"]:
    logger.info("No saved calibration found. Launching initial 4-corner calibration.")
    calibrate_system()
else:
    logger.info(
        f"Loaded saved calibration -> X: [{cursor.cal_min_x:.4f}, {cursor.cal_max_x:.4f}], "
        f"Y: [{cursor.cal_min_y:.4f}, {cursor.cal_max_y:.4f}]"
    )

# --- BUCLE PRINCIPAL ---
try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to grab frame from webcam stream. Terminating main loop.")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)

        result = detector.detect_for_video(mp_image, timestamp_ms)

        if result.face_landmarks and result.face_blendshapes:
            if face_lost:
                logger.info("Face tracking re-acquired.")
                face_lost = False

            first_face = next(iter(result.face_landmarks))
            first_blendshapes = next(iter(result.face_blendshapes))

            if show_debug:
                draw_debug_landmarks(frame, first_face)

            nose_pos = get_nose_position(first_face)
            blink_l, blink_r = get_blink_scores(first_blendshapes)

            command = gestures.update(blink_l, blink_r, cursor.current_pos)
            if command == "EXIT":
                logger.info("Exit requested via 5 bilateral blinks.")
                break
            elif command == "CALIBRATE":
                logger.info("Recalibration requested via 3 bilateral blinks.")
                calibrate_system()
                continue

            if gestures.can_move_cursor(blink_l, blink_r):
                cursor.move(nose_pos)

            draw_hud(frame, blink_l, blink_r)
        else:
            if not face_lost:
                logger.warning("Face lost from camera view. Pausing cursor and gesture updates.")
                face_lost = True

        cv2.imshow("FaceCursor", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("d"):
            show_debug = not show_debug
            logger.debug(f"Debug landmark overlay toggled: {show_debug}")
        elif key == ord("c"):
            logger.info("Manual recalibration triggered via keyboard ('C').")
            calibrate_system()
        elif key == ord("r"):
            reload_config()
        elif key == 27 or cv2.getWindowProperty("FaceCursor", cv2.WND_PROP_VISIBLE) < 1:
            logger.info("Exit requested via ESC or window close.")
            break

except Exception as e:
    logger.exception(f"Unhandled exception in FaceCursor main loop: {e}")
finally:
    cap.release()
    cv2.destroyAllWindows()
    logger.info("=== FaceCursor Session Closed Cleanly ===")
