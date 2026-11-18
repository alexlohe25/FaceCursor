import math
import pyautogui


class NoseCursorController:
    """Translates calibrated nose coordinates into smoothed screen cursor movements."""

    def __init__(self, screen_w, screen_h, config):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.smooth_x = screen_w // 2
        self.smooth_y = screen_h // 2
        self.load_settings(config)

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

        self.cal_min_x = cal_cfg["min_x"]
        self.cal_max_x = cal_cfg["max_x"]
        self.cal_min_y = cal_cfg["min_y"]
        self.cal_max_y = cal_cfg["max_y"]


    def set_calibration_bounds(self, min_x, max_x, min_y, max_y):
        self.cal_min_x = min_x
        self.cal_max_x = max_x
        self.cal_min_y = min_y
        self.cal_max_y = max_y

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
            pyautogui.moveTo(int(self.smooth_x), int(self.smooth_y))
