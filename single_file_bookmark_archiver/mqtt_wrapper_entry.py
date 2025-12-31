#!/usr/bin/env python3
"""
MQTT Wrapper for a Python Script

Currently specified for the Single File Bookmark Archiver but it should be made Generic

"""

import os
import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from mqtt_script_wrapper.wrapper import MQTTScriptWrapper

script_id = "single_file_bookmark_archiver"

log_file = Path.home() / f".local/state/{script_id}/wrapper.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10  # Keep 5 old logs
)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        handler,
    ]
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get bundle directory
WRAPPER_DIR = Path(__file__).parent.resolve()

# MQTT Topics
MQTT_TOPIC_PREFIX = f"homeassistant/sensor/{script_id}"

# Sync Script Alias and Path
SYNC_SCRIPT_ALIAS = "Single File Bookmark Archiver"
SYNC_SCRIPT = WRAPPER_DIR / "bookmark_archiver.py"

# YAML config for MQTT connection
MQTT_CONFIG = Path(os.getenv('SINGLE_FILE_BOOKMARK_ARCHIVER_CONFIG', 
                                Path.home() / f'.config/{script_id}/config.yaml'))
if not MQTT_CONFIG.exists():
    logging.error(f"Config file not found: {MQTT_CONFIG}")
    sys.exit(1)

# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main execution function."""

    wrapper = MQTTScriptWrapper(
        SYNC_SCRIPT_ALIAS,
        SYNC_SCRIPT,
        MQTT_CONFIG,
        MQTT_TOPIC_PREFIX,
    )

    wrapper.wrap_script()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user")
        sys.exit(1)
