import math
import pyautogui
from Helpers.logger import get_logger

logger = get_logger(__name__)


class NoseCursorController:
    """Translates calibrated nose coordinates into smoothed screen cursor movements."""

    def __init__(self, screen_w, screen_h, config):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.smooth_x = screen_w // 2
        self.smooth_y = screen_h // 2
        self.load_settings(config)
        logger.info(
            f"NoseCursorController initialized (screen={screen_w}x{screen_h}, "
            f"deadzone={self.DEADZONE_PX}px, smoothing=[{self.MIN_SMOOTHING}, {self.MAX_SMOOTHING}])"
        )

    def load_settings(self, config):
        """Loads or hot-reloads cursor kinematics and calibration bounds from config."""
        c_cfg = config["cursor"]
        cal_cfg = config["calibration"]

        self.min_range = c_cfg["min_range"]
        self.max_range = c_cfg["max_range"]
        self.DEADZONE_PX = c_cfg["deadzone_px"]
        self.MIN_SMOOTHING = c_cfg["min_smoothing"]
        self.MAX_SMOOTHING = c_cfg["max_smoothing"]
        self.SPEED_THRESHOLD = c_cfg["speed_threshold"]

        self.set_calibration_bounds(
            cal_cfg["min_x"],
            cal_cfg["max_x"],
            cal_cfg["min_y"],
            cal_cfg["max_y"],
        )
        logger.debug(
            f"Cursor settings loaded -> range=[{self.min_range}, {self.max_range}], "
            f"deadzone={self.DEADZONE_PX}, speed_threshold={self.SPEED_THRESHOLD}"
        )

    def set_calibration_bounds(self, min_x, max_x, min_y, max_y):
        if (max_x - min_x) < 0.01 or (max_y - min_y) < 0.01:
            logger.warning(
                f"Narrow calibration span detected -> X: [{min_x:.4f}, {max_x:.4f}], "
                f"Y: [{min_y:.4f}, {max_y:.4f}]. Clamping span to 0.01 to avoid division by zero."
            )

        self.cal_min_x = min_x
        self.cal_max_x = max_x
        self.cal_min_y = min_y
        self.cal_max_y = max_y
        logger.debug(
            f"Active cursor calibration bounds updated -> X: [{min_x:.4f}, {max_x:.4f}], Y: [{min_y:.4f}, {max_y:.4f}]"
        )

    @property
    def current_pos(self):
        return int(self.smooth_x), int(self.smooth_y)

    def move(self, nose_pos):
        """Moves the OS cursor using calibrated bounds, deadzone, and adaptive smoothing."""
        if not nose_pos:
            return

        rel_x, rel_y = nose_pos
        span_x = max(0.01, self.cal_max_x - self.cal_min_x)
        span_y = max(0.01, self.cal_max_y - self.cal_min_y)

        norm_x = max(0.0, min(1.0, (rel_x - self.cal_min_x) / span_x))
        norm_y = max(0.0, min(1.0, (rel_y - self.cal_min_y) / span_y))

        scaled_x = self.min_range + norm_x * (self.max_range - self.min_range)
        scaled_y = self.min_range + norm_y * (self.max_range - self.min_range)

        target_x = scaled_x * self.screen_w
        target_y = scaled_y * self.screen_h

        dist = math.hypot(target_x - self.smooth_x, target_y - self.smooth_y)

        if dist > self.DEADZONE_PX:
            speed_ratio = min(1.0, dist / self.SPEED_THRESHOLD)
            dynamic_smoothing = self.MAX_SMOOTHING - speed_ratio * (self.MAX_SMOOTHING - self.MIN_SMOOTHING)

            self.smooth_x += (target_x - self.smooth_x) / dynamic_smoothing
            self.smooth_y += (target_y - self.smooth_y) / dynamic_smoothing

            try:
                pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))
            except Exception as e:
                logger.error(f"PyAutoGUI moveTo failed at ({int(self.smooth_x)}, {int(self.smooth_y)}): {e}")
