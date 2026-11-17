import math
import pyautogui


class NoseCursorController:
    """Translates calibrated nose coordinates into smoothed screen cursor movements."""

    def __init__(self, screen_w, screen_h, min_range=0, max_range=1):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.min_range = min_range
        self.max_range = max_range

        self.smooth_x = screen_w // 2
        self.smooth_y = screen_h // 2

        # Precision & stability parameters
        self.DEADZONE_PX = 4.0
        self.MIN_SMOOTHING = 2.0
        self.MAX_SMOOTHING = 8.0
        self.SPEED_THRESHOLD = 100.0

        # Default calibration bounds
        self.cal_min_x = -0.12
        self.cal_max_x = 0.12
        self.cal_min_y = -0.05
        self.cal_max_y = 0.15

    def set_calibration_bounds(self, min_x, max_x, min_y, max_y):
        self.cal_min_x = min_x
        self.cal_max_x = max_x
        self.cal_min_y = min_y
        self.cal_max_y = max_y

    @property
    def current_pos(self):
        return int(self.smooth_x), int(self.smooth_y)

    def move(self, nose_pos):
        """4. NOSE POINTER CURSOR MOVEMENT"""
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
