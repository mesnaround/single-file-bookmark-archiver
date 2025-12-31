#!/usr/bin/env bash

set -e

# ============================================================================
# CONFIGURATION - Modify these variables for your project
# ============================================================================

# Project identification
PROJECT_NAME="single_file_bookmark_archiver"
PROJECT_DIR="single_file_bookmark_archiver"
SERVICE_NAME="single-file-bookmark-archiver"

# Scripts to install (relative to PROJECT_DIR)
SCRIPTS=(
    "bookmark_archiver.py"
    "mqtt_wrapper_entry.py"
)

# Config file settings
CONFIG_TEMPLATE="config.yaml.template"
CONFIG_FILENAME="config.yaml"

# Systemd service settings
SYSTEMD_SOURCE_DIR="systemd"
SYSTEMD_UNITS=("${SERVICE_NAME}.service" "${SERVICE_NAME}.timer")

# Additional files to copy (optional)
EXTRA_FILES=("pyproject.toml")

# ============================================================================
# AUTO-DETECT: Root vs User Installation
# ============================================================================

if [ "$EUID" -eq 0 ]; then
    # Running as root - use system paths
    IS_ROOT=true
    INSTALL_DIR="/root/.local/share/$PROJECT_NAME"
    CONFIG_DIR="/root/.config/$PROJECT_NAME"
    SERVICE_DIR="/etc/systemd/system"
    SYSTEMCTL_CMD="systemctl"
    echo "=== Installing as ROOT (system-wide) ==="
else
    # Running as regular user - use user paths
    IS_ROOT=false
    INSTALL_DIR="$HOME/.local/share/$PROJECT_NAME"
    CONFIG_DIR="$HOME/.config/$PROJECT_NAME"
    SERVICE_DIR="$HOME/.config/systemd/user"
    SYSTEMCTL_CMD="systemctl --user"
    echo "=== Installing as USER (user-level) ==="
fi

echo "Install directory: $INSTALL_DIR"
echo "Config directory:  $CONFIG_DIR"
echo "Service directory: $SERVICE_DIR"
echo

# ============================================================================
# INSTALLATION
# ============================================================================

# Install application scripts
echo "Installing application scripts..."
mkdir -p "$INSTALL_DIR"

for script in "${SCRIPTS[@]}"; do
    if [ -f "$PROJECT_DIR/$script" ]; then
        cp "$PROJECT_DIR/$script" "$INSTALL_DIR/"
        chmod +x "$INSTALL_DIR/$script"
        echo "  ✓ Installed $script"
    else
        echo "  ⚠ Warning: $script not found, skipping"
    fi
done

# Copy extra files
for file in "${EXTRA_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$INSTALL_DIR/"
        echo "  ✓ Copied $file"
    fi
done

# Create venv with uv (if uv.lock exists)
if [ -f "uv.lock" ]; then
    echo "Creating virtual environment with uv..."
    cp uv.lock "$INSTALL_DIR/"
    cd "$INSTALL_DIR"
    uv venv
    uv sync --frozen
    cd - > /dev/null
    echo "  ✓ Virtual environment created"
elif [ -f "requirements.txt" ]; then
    echo "Creating virtual environment with pip..."
    cp requirements.txt "$INSTALL_DIR/"
    cd "$INSTALL_DIR"
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    cd - > /dev/null
    echo "  ✓ Virtual environment created"
else
    echo "  ⚠ No uv.lock or requirements.txt found, skipping venv creation"
fi

# Install config if it doesn't exist
echo "Installing configuration..."
mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_TEMPLATE" ]; then
    if [ ! -f "$CONFIG_DIR/$CONFIG_FILENAME" ]; then
        cp "$CONFIG_TEMPLATE" "$CONFIG_DIR/$CONFIG_FILENAME"
        echo "  ✓ Config created at $CONFIG_DIR/$CONFIG_FILENAME"
        echo "  ⚠ Edit this file with your secrets!"
    else
        echo "  ℹ Config already exists at $CONFIG_DIR/$CONFIG_FILENAME"
    fi
else
    echo "  ⚠ Warning: Config template $CONFIG_TEMPLATE not found"
fi

# Install systemd units
if [ -d "$SYSTEMD_SOURCE_DIR" ]; then
    echo "Installing systemd units..."
    mkdir -p "$SERVICE_DIR"

    for unit in "${SYSTEMD_UNITS[@]}"; do
        if [ -f "$SYSTEMD_SOURCE_DIR/$unit" ]; then
            cp "$SYSTEMD_SOURCE_DIR/$unit" "$SERVICE_DIR/"
            echo "  ✓ Installed $unit"
        else
            echo "  ⚠ Warning: $unit not found in $SYSTEMD_SOURCE_DIR"
            exit 1
        fi
    done

    # Reload systemd daemon
    echo "Reloading systemd daemon..."
    $SYSTEMCTL_CMD daemon-reload

    # Enable and start timer
    echo "Enabling and starting ${SERVICE_NAME}.timer..."
    $SYSTEMCTL_CMD enable --now "${SERVICE_NAME}.timer"

    # Show status
    echo
    echo "=== Service Status ==="
    $SYSTEMCTL_CMD status "${SERVICE_NAME}.timer" --no-pager || true
else
    echo "  ⚠ Warning: Systemd directory $SYSTEMD_SOURCE_DIR not found"
fi

echo
echo "=== Installation Complete ==="
echo "Application:  $INSTALL_DIR"
echo "Config:       $CONFIG_DIR/$CONFIG_FILENAME"
if [ "$IS_ROOT" = true ]; then
    echo "Services:     $SERVICE_DIR"
    echo "View logs:    journalctl -u ${SERVICE_NAME}.service"
else
    echo "Services:     $SERVICE_DIR"
    echo "View logs:    journalctl --user -u ${SERVICE_NAME}.service"
fi
