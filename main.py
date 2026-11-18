import time
import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from config.config_loader import load_config, save_calibration_bounds
from Helpers.model_loader import get_face_landmarker_model
from Helpers.calibration import run_calibration, get_nose_position, get_blink_scores, draw_debug_landmarks
from Helpers.eye_gestures import EyeGestureController
from Helpers.cursor_controller import NoseCursorController

pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()

# Load JSON configuration
config = load_config()

# Initialize MediaPipe FaceLandmarker with Blendshapes enabled
model_path = get_face_landmarker_model()
options = vision.FaceLandmarkerOptions(
    base_options=python.BaseOptions(model_asset_path=model_path),
    running_mode=vision.RunningMode.VIDEO,
    output_face_blendshapes=True,
    num_faces=1
)
detector = vision.FaceLandmarker.create_from_options(options)
cap = cv2.VideoCapture(config["app"]["camera_index"])

# Initialize modular controllers from config.json
cursor = NoseCursorController(screen_w, screen_h, config)
gestures = EyeGestureController(config)
show_debug = config["app"]["show_debug_on_start"]


def calibrate_system():
    min_x, max_x, min_y, max_y = run_calibration(
        cap, detector, screen_w, screen_h, cursor.min_range, cursor.max_range
    )
    cursor.set_calibration_bounds(min_x, max_x, min_y, max_y)
    save_calibration_bounds(min_x, max_x, min_y, max_y)
    gestures.reset()
    print(f"Calibrated & saved -> X: [{min_x:.3f}, {max_x:.3f}], Y: [{min_y:.3f}, {max_y:.3f}]")


def draw_hud(frame, blink_l, blink_r):
    cv2.putText(frame, f"Blink L: {blink_l:.2f} | Blink R: {blink_r:.2f}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    if gestures.anchor_mode == 'LEFT':
        cv2.putText(frame, f"ANCHOR: LEFT (Right 2x wink = Right Click) [{len(gestures.wink_timestamps)}/2]",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    elif gestures.anchor_mode == 'RIGHT':
        cv2.putText(frame, f"ANCHOR: RIGHT (Left 2x wink = Left Click) [{len(gestures.wink_timestamps)}/2]",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

    if gestures.both_blink_count > 0:
        cv2.putText(frame, f"Both-Eye Blinks: {gestures.both_blink_count} (3=Calibrate, 5=Exit)",
                    (20, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

    if time.time() - gestures.last_click_time < 0.8:
        cv2.putText(frame, gestures.last_click_label,
                    (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

    if time.time() < reload_banner_until:
        cv2.putText(frame, "CONFIG RELOADED!", (20, 185),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 0), 2)


reload_banner_until = 0.0

def reload_config():
    """Reloads config.json live without restarting the webcam."""
    global config, reload_banner_until
    try:
        config = load_config()
        cursor.load_settings(config)
        gestures.load_settings(config)
        reload_banner_until = time.time() + 1.5
        print("Hot-reloaded settings from config.json!")
    except Exception as e:
        print(f"Failed to reload config.json (check JSON syntax): {e}")


# Run calibration only if no saved calibration exists yet (press 'c' or blink 3x anytime to recalibrate)
if not config["calibration"]["is_calibrated"]:
    calibrate_system()
else:
    print(f"Loaded saved calibration -> X: [{cursor.cal_min_x:.3f}, {cursor.cal_max_x:.3f}], "
          f"Y: [{cursor.cal_min_y:.3f}, {cursor.cal_max_y:.3f}]")

# --- MAIN LOOP ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)

    result = detector.detect_for_video(mp_image, timestamp_ms)

    if result.face_landmarks and result.face_blendshapes:
        first_face = next(iter(result.face_landmarks))
        first_blendshapes = next(iter(result.face_blendshapes))

        if show_debug:
            draw_debug_landmarks(frame, first_face)

        nose_pos = get_nose_position(first_face)
        blink_l, blink_r = get_blink_scores(first_blendshapes)

        command = gestures.update(blink_l, blink_r, cursor.current_pos)
        if command == 'EXIT':
            print("5 bilateral blinks detected -> Stopping program.")
            break
        elif command == 'CALIBRATE':
            print("3 bilateral blinks detected -> Starting calibration.")
            calibrate_system()
            continue

        if gestures.can_move_cursor(blink_l, blink_r):
            cursor.move(nose_pos)

        draw_hud(frame, blink_l, blink_r)

    cv2.imshow('FaceCursor', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('d'):
        show_debug = not show_debug
    elif key == ord('c'):
        calibrate_system()
    elif key == ord('r'):
        reload_config()
    elif key == 27 or cv2.getWindowProperty('FaceCursor', cv2.WND_PROP_VISIBLE) < 1:
        break


cap.release()
cv2.destroyAllWindows()
