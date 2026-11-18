import copy
import json
from pathlib import Path
from Helpers.logger import get_logger

logger = get_logger(__name__)

# Apunta a FaceCursor/config/config.json (un nivel arriba de Helpers/)
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.json"

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
        "anchor_close_score": 0.42,
        "anchor_release_score": 0.25,
        "wink_close_score": 0.30,
        "asymmetry_margin": 0.15,
        "both_blink_score": 0.65,
        "anchor_hold_delay": 0.12,
        "min_wink_duration": 0.04,
        "max_wink_duration": 0.75,
        "double_wink_window": 1.40,
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
    "logging": {
        "level": "INFO",
        "log_to_file": True,
        "log_to_console": True,
        "backup_count": 14,
    },
}


def load_config():
    """Carga config/config.json, rellena claves faltantes y registra eventos."""
    config = copy.deepcopy(DEFAULT_CONFIG)

    if not CONFIG_PATH.exists():
        logger.warning(f"Config file not found at {CONFIG_PATH}. Creating default config.json.")
        save_config(config)
        return config

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        for section, default_values in DEFAULT_CONFIG.items():
            if section not in user_data or not isinstance(user_data[section], dict):
                logger.warning(f"Missing or invalid section '[{section}]' in config.json. Using defaults.")
                continue

            for key in default_values:
                if key not in user_data[section]:
                    logger.warning(f"Missing key '{section}.{key}' in config.json. Using default ({default_values[key]}).")

            config[section].update(user_data[section])

        logger.debug(f"Configuration successfully loaded from {CONFIG_PATH}")
        return config

    except json.JSONDecodeError as e:
        logger.error(f"Syntax error parsing {CONFIG_PATH}: {e}. Falling back to default configuration.")
        raise
    except OSError as e:
        logger.error(f"Unable to read {CONFIG_PATH}: {e}")
        raise


def save_config(config):
    """Guarda el diccionario de configuración completo en config/config.json."""
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Configuration saved to {CONFIG_PATH}")
    except OSError as e:
        logger.error(f"Failed to save configuration to {CONFIG_PATH}: {e}")
        raise


def save_calibration_bounds(min_x, max_x, min_y, max_y):
    """Actualiza y persiste los límites calibrados de la nariz en config.json."""
    config = load_config()
    config["calibration"].update({
        "is_calibrated": True,
        "min_x": round(float(min_x), 5),
        "max_x": round(float(max_x), 5),
        "min_y": round(float(min_y), 5),
        "max_y": round(float(max_y), 5),
    })
    save_config(config)
    logger.info(
        f"Saved new calibration bounds -> X: [{min_x:.4f}, {max_x:.4f}], Y: [{min_y:.4f}, {max_y:.4f}]"
    )
    return config
