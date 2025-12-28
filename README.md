# Pibooth Libcamera Plugin (Pi 5 Support)

This plugin enables the **Raspberry Pi 5 Camera** to work with [Pibooth](https://github.com/pibooth/pibooth) on Debian Bookworm/Trixie.

**Features:**
* Smooth 30fps Video Preview (using `rpicam-vid`)
* High-Res Capture (using `rpicam-still`)
* Fixes Wayland/Pillow compatibility issues.

## Installation

1. **Install Dependencies (on the Pi):**
   ```bash
   sudo apt install rpicam-apps