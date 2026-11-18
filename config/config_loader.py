import copy
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG = {
    "cursor": {
        "min_range": 0.05,
        "max_range": 0.95,
        "deadzone_px": 4.0,
        "min_smoothing": 2.0,
        "max_smoothing": 8.0,
        "speed_threshold": 100.0,
    },
    "gestures": {
        "anchor_close_score": 0.55,
        "anchor_release_score": 0.35,
        "wink_close_score": 0.45,
        "asymmetry_margin": 0.25,
        "both_blink_score": 0.55,
        "anchor_hold_delay": 0.20,
        "min_wink_duration": 0.05,
        "max_wink_duration": 0.65,
        "double_wink_window": 1.10,
        "multi_blink_timeout": 0.70,
    },
    "calibration": {
        "is_calibrated": False,
        "min_x": -0.12,
        "max_x": 0.12,
        "min_y": -0.05,
        "max_y": 0.15,
    },
    "app": {
        "camera_index": 0,
        "show_debug_on_start": True,
    },
}


def load_config():
    """Loads config.json and backfills any missing default keys."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        for section, values in user_data.items():
            if section in config and isinstance(values, dict):
                config[section].update(values)
    else:
        save_config(config)
    return config


def save_config(config):
    """Writes the full configuration dictionary back to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def save_calibration_bounds(min_x, max_x, min_y, max_y):
    """Updates and persists calibrated nose bounds into config.json."""
    config = load_config()
    config["calibration"] = {
        "is_calibrated": True,
        "min_x": round(float(min_x), 5),
        "max_x": round(float(max_x), 5),
        "min_y": round(float(min_y), 5),
        "max_y": round(float(max_y), 5),
    }
    save_config(config)
    return config
