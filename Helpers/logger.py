import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Apunta a FaceCursor/logs/ (un nivel arriba de Helpers/)
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"

VALID_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def setup_logger(config):
    """
    Configura el logger raíz de FaceCursor con rotación diaria y salida opcional a consola.
    Puede llamarse al iniciar el programa y al recargar config.json con 'R'.
    """
    log_cfg = config.get("logging", {})
    level_name = str(log_cfg.get("level", "INFO")).upper()
    log_level = VALID_LEVELS.get(level_name, logging.INFO)

    log_to_file = log_cfg.get("log_to_file", True)
    log_to_console = log_cfg.get("log_to_console", True)
    backup_count = int(log_cfg.get("backup_count", 14))

    root_logger = logging.getLogger("FaceCursor")
    root_logger.setLevel(log_level)

    # Limpia handlers previos para evitar líneas duplicadas al recargar con 'R'
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_to_file:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_file_path = LOGS_DIR / f"facecursor_{today_str}.log"

        file_handler = TimedRotatingFileHandler(
            filename=log_file_path,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        # En consola mostramos desde INFO hacia arriba para no saturar la terminal en modo DEBUG
        console_handler.setLevel(max(log_level, logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger


def get_logger(module_name):
    """
    Devuelve un logger hijo bajo el espacio de nombres 'FaceCursor.<modulo>'.
    Uso en otros archivos: logger = get_logger(__name__)
    """
    clean_name = module_name.split(".")[-1]
    return logging.getLogger(f"FaceCursor.{clean_name}")
