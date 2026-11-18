import math
from operator import itemgetter
import cv2
import numpy as np
import mediapipe as mp
from Helpers.logger import get_logger

logger = get_logger(__name__)


def get_distance(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)


def get_nose_position(landmarks):
    """Returns scale-normalized nose offset (rel_x, rel_y) relative to head center."""
    nose_tip, face_left, face_right, face_top, face_bottom = itemgetter(4, 234, 454, 10, 152)(landmarks)

    face_width = get_distance(face_left, face_right)
    face_height = get_distance(face_top, face_bottom)

    if face_width <= 0 or face_height <= 0:
        logger.debug("Invalid facial bounding dimensions (width or height <= 0); skipping nose offset.")
        return None

    face_center_x = (face_left.x + face_right.x) / 2.0
    face_center_y = (face_top.y + face_bottom.y) / 2.0

    nose_rel_x = (nose_tip.x - face_center_x) / face_width
    nose_rel_y = (nose_tip.y - face_center_y) / face_height

    return nose_rel_x, nose_rel_y


def get_blink_scores(face_blendshapes):
    """Returns (left_blink_score, right_blink_score) from 0.0 (open) to 1.0 (closed) in mirrored view."""
    scores = {b.category_name: b.score for b in face_blendshapes}
    left_blink = scores.get("eyeBlinkRight", 0.0)
    right_blink = scores.get("eyeBlinkLeft", 0.0)
    return left_blink, right_blink


def draw_debug_landmarks(frame, landmarks):
    """Draws color-coded dots and MediaPipe index numbers for active tracking points."""
    h, w, _ = frame.shape
    groups = [
        ((33, 133, 159, 145), (255, 200, 0)),      # Left eye (Cyan)
        ((362, 263, 386, 374), (0, 255, 0)),       # Right eye (Green)
        ((4,), (0, 0, 255)),                       # Nose tip (Red)
        ((10, 152, 234, 454), (255, 0, 255)),      # Face bounds (Magenta)
    ]

    for indices, color in groups:
        for idx in indices:
            lm = landmarks[idx]
            px, py = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (px, py), 3, color, -1)
            cv2.putText(
                frame,
                str(idx),
                (px + 4, py - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                color,
                1,
            )


def run_calibration(cap, detector, screen_w, screen_h, min_range=0.05, max_range=0.95):
    """4-corner fullscreen calibration triggered by pressing SPACE."""
    logger.info("Starting 4-corner fullscreen calibration.")

    corners = [
        ("TOP-LEFT", int(screen_w * min_range), int(screen_h * min_range)),
        ("TOP-RIGHT", int(screen_w * max_range), int(screen_h * min_range)),
        ("BOTTOM-RIGHT", int(screen_w * max_range), int(screen_h * max_range)),
        ("BOTTOM-LEFT", int(screen_w * min_range), int(screen_h * max_range)),
    ]

    cal_win = "Calibration"
    cv2.namedWindow(cal_win, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(cal_win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    recorded_x, recorded_y = [], []
    current_idx = 0
    sampling = False
    samples_x, samples_y = [], []
    face_missing_warned = False

    while cap.isOpened() and current_idx < len(corners):
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to read webcam frame during calibration. Reverting to fallback bounds.")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
        result = detector.detect_for_video(mp_image, timestamp_ms)

        canvas = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
        label, cx, cy = corners[current_idx]

        cv2.putText(
            canvas,
            f"Step {current_idx + 1}/4: Point your NOSE at the RED dot ({label})",
            (screen_w // 2 - 410, screen_h // 2 - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.85,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            canvas,
            "Press SPACE to record",
            (screen_w // 2 - 150, screen_h // 2 + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (180, 180, 180),
            2,
        )

        dot_color = (0, 255, 0) if sampling else (0, 0, 255)
        cv2.circle(canvas, (cx, cy), 22, dot_color, -1)
        cv2.circle(canvas, (cx, cy), 6, (255, 255, 255), -1)

        if result.face_landmarks:
            face_missing_warned = False
            if sampling:
                first_face = next(iter(result.face_landmarks))
                nose_pos = get_nose_position(first_face)
                if nose_pos:
                    nx, ny = nose_pos
                    samples_x.append(nx)
                    samples_y.append(ny)

                if len(samples_x) >= 15:
                    avg_x = sum(samples_x) / len(samples_x)
                    avg_y = sum(samples_y) / len(samples_y)
                    recorded_x.append(avg_x)
                    recorded_y.append(avg_y)
                    logger.debug(
                        f"Corner {current_idx + 1}/4 ({label}) captured -> avg_rel_x={avg_x:.4f}, avg_rel_y={avg_y:.4f}"
                    )
                    samples_x.clear()
                    samples_y.clear()
                    sampling = False
                    current_idx += 1
        elif sampling and not face_missing_warned:
            logger.warning(f"Face lost while sampling corner {label}. Waiting for face detection to resume.")
            face_missing_warned = True

        cv2.imshow(cal_win, canvas)
        key = cv2.waitKey(1) & 0xFF
        if key == 32 and not sampling:
            sampling = True
            logger.debug(f"Started 15-frame sampling for corner {label}.")
        elif key == 27:
            logger.warning("Calibration cancelled by user (ESC). Returning default fallback bounds.")
            cv2.destroyWindow(cal_win)
            return -0.12, 0.12, -0.05, 0.15

    cv2.destroyWindow(cal_win)

    if len(recorded_x) < 4 or len(recorded_y) < 4:
        logger.warning("Incomplete calibration data (< 4 corners recorded). Returning default fallback bounds.")
        return -0.12, 0.12, -0.05, 0.15

    tl_x, tr_x, br_x, bl_x = recorded_x
    tl_y, tr_y, br_y, bl_y = recorded_y

    min_x = (tl_x + bl_x) / 2.0
    max_x = (tr_x + br_x) / 2.0
    min_y = (tl_y + tr_y) / 2.0
    max_y = (bl_y + br_y) / 2.0

    logger.info(f"Calibration completed successfully -> X: [{min_x:.4f}, {max_x:.4f}], Y: [{min_y:.4f}, {max_y:.4f}]")
    return min_x, max_x, min_y, max_y
