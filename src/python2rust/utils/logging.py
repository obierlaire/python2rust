import logging
from pathlib import Path
from datetime import datetime
# logging.py
# logging.py
def setup_logger(log_dir: Path = Path("logs")) -> logging.Logger:
    """Set up logging configuration."""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("python2rust")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    # Debug file handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_handler = logging.FileHandler(
        log_dir / f"debug_{timestamp}.log"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Info console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    
    logger.addHandler(debug_handler)
    logger.addHandler(console_handler)
    
    return logger