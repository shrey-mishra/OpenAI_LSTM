# src/utils.py
import json
import logging

def load_config(config_path="config.json"):
    """Load configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)

def setup_logging():
    """Configure logging."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    return logging.getLogger(__name__)