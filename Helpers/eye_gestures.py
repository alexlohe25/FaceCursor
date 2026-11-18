import time
import pyautogui


class EyeGestureController:
    """Manages eye-based anchor locking, double-wink clicks, and bilateral blink commands."""

    def __init__(self, config):
        self.load_settings(config)
        self.reset()

    def load_settings(self, config):
        """Loads or hot-reloads eye blendshape thresholds and timing windows from config."""
        g_cfg = config["gestures"]

        # Blendshape thresholds (0.0 = open, 1.0 = closed)
        self.ANCHOR_CLOSE_SCORE = g_cfg["anchor_close_score"]
        self.ANCHOR_RELEASE_SCORE = g_cfg["anchor_release_score"]
        self.WINK_CLOSE_SCORE = g_cfg["wink_close_score"]
        self.ASYMMETRY_MARGIN = g_cfg["asymmetry_margin"]
        self.BOTH_BLINK_SCORE = g_cfg["both_blink_score"]

        # Timing parameters (seconds)
        self.ANCHOR_HOLD_DELAY = g_cfg["anchor_hold_delay"]
        self.MIN_WINK_DURATION = g_cfg["min_wink_duration"]
        self.MAX_WINK_DURATION = g_cfg["max_wink_duration"]
        self.DOUBLE_WINK_WINDOW = g_cfg["double_wink_window"]
        self.MULTI_BLINK_TIMEOUT = g_cfg["multi_blink_timeout"]

    def reset(self):
        """Resets all gesture states (e.g., right after calibration)."""
        self.left_closed_since = None
        self.right_closed_since = None
        self.anchor_mode = None  # None, 'LEFT', or 'RIGHT'
        self.locked_pos = None

        self.wink_active = False
        self.wink_start_time = 0.0
        self.wink_timestamps = []

        self.both_eyes_closed = False
        self.both_close_start = 0.0
        self.both_blink_count = 0
        self.last_both_blink_time = 0.0

        self.last_click_label = ""
        self.last_click_time = 0.0
        self.ignore_until = time.time() + 0.50

    def update(self, blink_l, blink_r, current_cursor_pos):
        """
        Processes current eye blendshape scores.
        Returns a command string: 'EXIT', 'CALIBRATE', or None.
        """
        now = time.time()
        if now < self.ignore_until:
            return None

        self._update_anchor_mode(blink_l, blink_r, current_cursor_pos, now)
        self._update_anchored_winks(blink_l, blink_r, current_cursor_pos, now)
        return self._update_bilateral_blinks(blink_l, blink_r, now)

    def _update_anchor_mode(self, blink_l, blink_r, current_cursor_pos, now):
        """1. ANCHOR MODE MANAGEMENT"""
        if self.anchor_mode is None:
            left_is_anchor = (blink_l >= self.ANCHOR_CLOSE_SCORE) and ((blink_l - blink_r) >= self.ASYMMETRY_MARGIN)
            right_is_anchor = (blink_r >= self.ANCHOR_CLOSE_SCORE) and ((blink_r - blink_l) >= self.ASYMMETRY_MARGIN)

            if left_is_anchor:
                self.both_eyes_closed = False  # Prioriza el anclaje si hay asimetría clara
                if self.left_closed_since is None:
                    self.left_closed_since = now
                elif now - self.left_closed_since >= self.ANCHOR_HOLD_DELAY:
                    self._lock_anchor('LEFT', current_cursor_pos)
            else:
                self.left_closed_since = None

            if right_is_anchor and self.anchor_mode is None:
                self.both_eyes_closed = False
                if self.right_closed_since is None:
                    self.right_closed_since = now
                elif now - self.right_closed_since >= self.ANCHOR_HOLD_DELAY:
                    self._lock_anchor('RIGHT', current_cursor_pos)
            else:
                self.right_closed_since = None

        # Soltar el anclaje cuando el ojo ancla vuelve a abrirse
        if self.anchor_mode == 'LEFT' and blink_l < self.ANCHOR_RELEASE_SCORE:
            self._release_anchor()
        elif self.anchor_mode == 'RIGHT' and blink_r < self.ANCHOR_RELEASE_SCORE:
            self._release_anchor()

    def _lock_anchor(self, side, cursor_pos):
        self.anchor_mode = side
        self.locked_pos = cursor_pos
        self.wink_active = False
        self.wink_timestamps.clear()
        self.both_blink_count = 0

    def _release_anchor(self):
        self.anchor_mode = None
        self.left_closed_since = None
        self.right_closed_since = None
        self.wink_active = False
        self.wink_timestamps.clear()

    def _update_anchored_winks(self, blink_l, blink_r, current_cursor_pos, now):
        """2. ANCHORED DOUBLE-WINK CLICKS"""
        if self.anchor_mode == 'LEFT':
            self._process_wink(blink_r >= self.WINK_CLOSE_SCORE, 'RIGHT', current_cursor_pos, now)
        elif self.anchor_mode == 'RIGHT':
            self._process_wink(blink_l >= self.WINK_CLOSE_SCORE, 'LEFT', current_cursor_pos, now)

    def _process_wink(self, is_winking, click_button, fallback_pos, now):
        if is_winking and not self.wink_active:
            self.wink_active = True
            self.wink_start_time = now
        elif not is_winking and self.wink_active:
            self.wink_active = False
            dur = now - self.wink_start_time
            if self.MIN_WINK_DURATION <= dur <= self.MAX_WINK_DURATION:
                self.wink_timestamps.append(now)
                self.wink_timestamps = [t for t in self.wink_timestamps if now - t <= self.DOUBLE_WINK_WINDOW]

                if len(self.wink_timestamps) >= 2:
                    lx, ly = self.locked_pos if self.locked_pos else fallback_pos
                    if click_button == 'RIGHT':
                        pyautogui.rightClick(lx, ly)
                        self.last_click_label = "RIGHT CLICK!"
                    else:
                        pyautogui.leftClick(lx, ly)
                        self.last_click_label = "LEFT CLICK!"
                    self.last_click_time = now
                    self.wink_timestamps.clear()

    def _update_bilateral_blinks(self, blink_l, blink_r, now):
        """3. BILATERAL BLINKS (3x = Calibrate, 5x = Exit)"""
        if self.anchor_mode is not None:
            return None

        # Solo cuenta como parpadeo bilateral si AMBOS ojos están muy cerrados y parejos
        is_symmetric = abs(blink_l - blink_r) < self.ASYMMETRY_MARGIN
        both_shut = (blink_l >= self.BOTH_BLINK_SCORE) and (blink_r >= self.BOTH_BLINK_SCORE) and is_symmetric
        both_open = (blink_l < self.ANCHOR_RELEASE_SCORE) and (blink_r < self.ANCHOR_RELEASE_SCORE)

        if both_shut and not self.both_eyes_closed:
            self.both_eyes_closed = True
            self.both_close_start = now
        elif both_open and self.both_eyes_closed:
            self.both_eyes_closed = False
            if self.MIN_WINK_DURATION <= (now - self.both_close_start) <= self.MAX_WINK_DURATION:
                self.both_blink_count += 1
                self.last_both_blink_time = now

        if self.both_blink_count > 0 and not self.both_eyes_closed and (now - self.last_both_blink_time > self.MULTI_BLINK_TIMEOUT):
            count = self.both_blink_count
            self.both_blink_count = 0
            if count >= 5:
                return 'EXIT'
            elif count == 3:
                return 'CALIBRATE'

        return None

    def can_move_cursor(self, blink_l, blink_r):
        """Returns True only when unanchored and both eyes are clearly open."""
        return (
            self.anchor_mode is None
            and blink_l < self.ANCHOR_RELEASE_SCORE
            and blink_r < self.ANCHOR_RELEASE_SCORE
        )
